"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Media indexing utilities for Ellie Forward Bot.
"""

from config import temp
from database import db
from typing import Union
from pyrogram.errors import FloodWait
from datetime import datetime, timezone
from pyrogram import Client, filters, enums
from helpers.clean_string import clean_text
from plugins.forwarding import start_forwarding
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, Document, Video
import asyncio
import logging

SAVE_BATCH = 50 # number of files to save in one batch
logger = logging.getLogger(__name__)
lock = asyncio.Lock()
p_msg = """<b>Process Status: {status}
Total messages fetched: {t_msgs}
Total messages saved: {s_msgs}
Duplicate Files Skipped: {d_files}
Deleted Messages Skipped: {d_msgs}
Non-Media messages skipped: {n_msgs}
Errors Occurred: {err}</b>"""

@Client.on_message((filters.document | filters.video) & filters.forwarded & filters.private & filters.incoming)
async def index_handler(bot: Client, msg: Message):
    if msg.from_user.id not in await db.get_admins():
        return await msg.reply_text("Only admins are allowed to use this feature !")
    elif lock.locked():
        return await msg.reply_text("<b>Another indexing/forwarding process is currently running. Please wait until it finishes.</b>", True, enums.ParseMode.HTML)

    settings = await db.get_settings()
    t_chats = settings.get("target_chats", [])
    w_client = settings.get("worker_clients", [])
    if not t_chats:
        return await msg.reply_text(
            "<b>No target chats have been set yet. Please use /settings and set a target channel.\nNote: Set up atleast two target channels if you want to limit number of msgs per chat and use auto-switch feature.</b>",
            True,
            enums.ParseMode.HTML
        )
    elif not w_client:
        return await msg.reply_text(
            "<b>No worker clients have been set yet. Please use /settings and set worker clients to proceed.</b>",
            True,
            enums.ParseMode.HTML
        )
    
    target_chat = t_chats[0]
    skip = settings.get("skip", 0)
    switch_chats = t_chats[1:]

    if len(t_chats) == 1:
        await msg.reply_text(
            f"<b>No other target channel found except {target_chat}, therefore auto-switch and limit won't work.</b>"
        )

    if temp.CANCEL_FORWARD:
        temp.CANCEL_FORWARD = False

    btn = [[InlineKeyboardButton("Cancel Forwarding ❌", callback_data="c_frwd:")]]
    p_rply = await msg.reply_text(
        f"<code>Forwarding media(s) to {target_chat}...</code>\n\n"+p_msg.format(
            status="Initializing...",
            t_msgs=skip,
            s_msgs=0,
            d_files=0,
            d_msgs=0,
            n_msgs=0,
            err=0
        ),
        True,
        enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
    )

    await index_media_handler(bot, msg, skip, p_rply, target_chat, switch_chats, w_client)

async def resume_indexing_job(bot: Client, job: dict):
    source_id = job["source_id"]
    limit = job["l_msg_id"]
    offset = job.get("index_cursor", 0)

    t_msgs = job.get("indexed_count", offset)
    d_files = job.get("duplicate_count", 0)
    d_msgs = job.get("deleted_count", 0)
    n_msgs = job.get("non_media_count", 0)
    err = job.get("error_count", 0)

    progress_chat = job["progress_chat_id"]
    progress_msg = job["progress_msg_id"]

    try:
        async for message in bot.iter_messages(
            chat_id=source_id,
            limit=limit,
            offset=offset
        ):
            if temp.CANCEL_FORWARD:
                await db.update_job_status(job["_id"], "cancelled")
                return

            t_msgs += 1

            if message.empty:
                d_msgs += 1
                continue
            elif not (message.document or message.video):
                n_msgs += 1
                continue

            media = message.document or message.video

            saved = await db.save_media(
                unique_id=media.file_unique_id,
                job_id=job["_id"],
                msg_id=message.id,
                f_name=clean_text(media.file_name),
                f_size=media.file_size,
                cap=clean_text(message.caption),
                s_chat=message.chat.id,
                t_chat=job["t_chat"]
            )

            if not saved:
                d_files += 1

            # checkpoint
            await db.jobs.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "index_cursor": message.id,
                        "indexed_count": t_msgs,
                        "duplicate_count": d_files,
                        "deleted_count": d_msgs,
                        "non_media_count": n_msgs,
                        "error_count": err,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

    except Exception as e:
        err += 1
        await db.update_job_status(job["_id"], "failed")
        logger.exception(f"Indexing resume failed: {e}")
        return

    # Continue to forwarding automatically
    await start_forwarding(
        bot,
        job["_id"],
        None,
        job["worker_clients"]
    )


async def index_media_handler(bot: Client, msg: Message, skip: int, progress_msg: Message, target_chat: int, switch_chats: list, w_client: list):
    t_msgs = skip # Total messages fetched
    s_msgs = 0 # Total messages saved
    d_files = 0 # Duplicate files skipped
    d_msgs = 0 # Deleted messages skipped
    n_msgs = 0 # Non-media messages skipped
    err = 0 # Errors occurred
    tasks = []

    job_id = await db.insert_job(
        source_id=msg.forward_origin.chat.id,
        l_msg_id=msg.forward_origin.message_id,
        status="indexing",
        t_chat=target_chat,
        switch_chats=switch_chats,
        w_client=w_client,
        p_chat_id=progress_msg.chat.id,
        p_msg_id=progress_msg.id,
        skip=skip
    )

    async with lock:
        try:
            temp.CANCEL_FORWARD = False
            async for message in bot.iter_messages(
                chat_id=msg.forward_origin.chat.id,
                limit=msg.forward_origin.message_id,
                offset=skip
            ):
                if temp.CANCEL_FORWARD:
                    temp.CANCEL_FORWARD = False
                    await db.remove_job(job_id)
                    return await progress_msg.edit_text(
                        "<code>Process CANCELED !</code>\n\n"+p_msg.format(
                            status="Cancelled!",
                            t_msgs=t_msgs,
                            s_msgs=s_msgs,
                            d_files=d_files,
                            d_msgs=d_msgs,
                            n_msgs=n_msgs,
                            err=err
                        )
                    )

                t_msgs += 1
                if t_msgs % 20 == 0:
                    btn = [[InlineKeyboardButton("Cancel Forwarding ❌", callback_data=f"c_frwd:{job_id}")]]

                    await db.jobs.update_one(
                        {"_id": job_id},
                        {
                            "$set": {
                                "index_cursor": message.id,
                                "indexed_count": t_msgs,
                                "duplicate_count": d_files,
                                "deleted_count": d_msgs,
                                "non_media_count": n_msgs,
                                "error_count": err,
                                "updated_at": datetime.now(timezone.utc)
                            }
                        }
                    )

                    try:
                        await progress_msg.edit_text(
                            "<code>Indexing media(s)...</code>\n\n"+p_msg.format(
                                status="Indexing...",
                                t_msgs=t_msgs,
                                s_msgs=s_msgs,
                                d_files=d_files,
                                d_msgs=d_msgs,
                                n_msgs=n_msgs,
                                err=err
                            ),
                            reply_markup=InlineKeyboardMarkup(btn)
                        )
                    except FloodWait as e:
                        logger.warning(f"FloodWait of {e.value} seconds while editing progress message.")
                        await asyncio.sleep(e.value)
                
                if message.empty:
                    d_msgs += 1
                    continue
                elif not (message.document or message.video):
                    n_msgs += 1
                    continue

                media: Union[Document, Video] = message.document or message.video
                f_name = clean_text(media.file_name)
                cap = clean_text(message.caption)
                f_size = media.file_size

                tasks.append(asyncio.create_task(
                    db.save_media(
                        unique_id=media.file_unique_id,
                        job_id=job_id,
                        msg_id=message.id,
                        f_name=f_name,
                        f_size=f_size,
                        cap=cap,
                        s_chat=message.chat.id,
                        t_chat=target_chat
                    )
                ))

                if len(tasks) >= SAVE_BATCH:
                    results = await asyncio.gather(*tasks)
                    for r in results:
                        if r:
                            s_msgs += 1
                        else:
                            d_files += 1
                    tasks.clear()
        except Exception as e:
            err += 1
            logger.error(f"Error while indexing message: {e}")
            await db.update_job_status(job_id, "failed")
            return await progress_msg.edit_text(
                "<code>Indexing interrupted due to an error !</code>\n\n"+p_msg.format(
                    status="Error!",
                    t_msgs=t_msgs,
                    s_msgs=s_msgs,
                    d_files=d_files,
                    d_msgs=d_msgs,
                    n_msgs=n_msgs,
                    err=err
                )
            )
        
        if tasks:
            results = await asyncio.gather(*tasks)
            for r in results:
                if r:
                    s_msgs += 1
                else:
                    d_files += 1
            tasks.clear()

        await progress_msg.edit_text(
            "<code>Indexing completed !</code>\n\n"+p_msg.format(
                status="Completed!",
                t_msgs=t_msgs,
                s_msgs=s_msgs,
                d_files=d_files,
                d_msgs=d_msgs,
                n_msgs=n_msgs,
                err=err
            )
        )

        await start_forwarding(bot, job_id, progress_msg, w_client)