"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Forwarding plugin for Ellie Forward Bot.
"""

from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from helpers.caption_parser import human_readable_size, render_caption
from helpers.button_parser import parse_keyboard, to_pyrogram_keyboard
from pymongo.errors import DuplicateKeyError
from plugins.workers import WORKER_CLIENTS
from datetime import datetime, timezone
from pyrogram.errors import FloodWait
from pyrogram import Client, enums
from database import db
from config import temp
import logging
import asyncio

# parts staus : pending, running, done, cancelled, failed
# jobs status : forwarding, resuming, completed, cancelled, failed, indexing

lock = asyncio.Lock()
logger = logging.getLogger(__name__)

async def progress_updater(bot: Client, job_id: str, settings: dict):
    try:
        await lock.acquire()
        job = await db.jobs.find_one({"_id": job_id})
        if not job:
            return

        temp.TARGET_CACHE[job_id] = job['t_chat']
        chat_id = job["progress_chat_id"]
        msg_id = job["progress_msg_id"]
        is_switched = False

        while True:
            job = await db.jobs.find_one({"_id": job_id})
            if job["status"] not in ("forwarding", "resuming"):
                return await bot.edit_message_text(
                    chat_id,
                    msg_id,
                    f"<b>📤 Forwarding Progress</b>\n\n"
                    f"Status: <code>{job['status'].upper()}</code>\n"
                    f"Total files: <b>{(await db.deliveries.count_documents({'job_id': job_id}))}</b>\n"
                    f"Forwarded: <b>{(await db.deliveries.count_documents({'job_id': job_id, 'forwarded': True}))}</b>\n"
                    f"Pending: <b>{(await db.deliveries.count_documents({'job_id': job_id, 'forwarded': False}))}</b>\n"
                    f"Failed workers: <b>{(await db.parts.count_documents({'job_id': job_id, 'status': 'failed'}))}</b>",
                    parse_mode=enums.ParseMode.HTML
                )
            
            progress = await db.get_job_progress(job_id)
            limit = settings.get('limit', 0)

            if limit > 0 and progress['done'] >= limit and job.get("switch_chats") and not is_switched:
                # update the target chat to the next one (switching) and continue forwarding to that chat
                switch_chats = job["switch_chats"]
                new_target = switch_chats.pop(0)

                await db.jobs.update_one(
                    {"_id": job_id},
                    {
                        "$set": {
                            "t_chat": new_target, 
                            "switch_chats": switch_chats
                        }
                    }
                )
                temp.TARGET_CACHE[job_id] = new_target
                is_switched = True

                logger.info(f"Limit reached. Switched Job {job_id} target to: {new_target}")

            btn = [[InlineKeyboardButton("Cancel Forwarding ❌", callback_data=f"c_frwd:{job_id}")]] if job["status"] in ("forwarding", "resuming") else None

            text = (
                "<b>📤 Forwarding Progress</b>\n\n"
                f"Status: <code>{job['status'].upper()}</code>\n"
                f"Total files: <b>{progress['total']}</b>\n"
                f"Forwarded: <b>{progress['done']}</b>\n"
                f"Pending: <b>{progress['pending']}</b>\n"
                f"Failed workers: <b>{progress['failed_parts']}</b>"
            )

            try:
                await bot.edit_message_text(
                    chat_id,
                    msg_id,
                    text,
                    parse_mode=enums.ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(btn) if btn else None
                )
            except FloodWait as e:
                await asyncio.sleep(e.value)
            except Exception:
                pass

            await asyncio.sleep(5)  # update interval
    finally:
        lock.release()

async def run_partition(bot: Client, part: dict, settings: dict):
    logger.info(
        f"[{bot.me.username}] Running partition "
        f"{part['start_msg_id']} → {part['end_msg_id']}"
    )

    c_cap = settings["cap_template"]
    c_btn = settings["btn_template"]

    await db.parts.update_one(
        {"_id": part["_id"]},
        {"$set": {"status": "running"}}
    )

    try:
        cursor = db.deliveries.find({
            "job_id": part["job_id"],
            "forwarded": False,
            "last_source.msg_id": {
                "$gte": part["current_msg_id"],
                "$lte": part["end_msg_id"]
            }
        }).sort("last_source.msg_id", 1)

        async for doc in cursor:
            switched_target = temp.TARGET_CACHE.get(part["job_id"])

            if temp.CANCEL_FORWARD:
                return await db.parts.update_one(
                    {"_id": part["_id"]},
                    {"$set": {"status": "cancelled", "updated_at": datetime.now(timezone.utc)}}
                )
            elif switched_target and switched_target != doc["target_chat"]:
                # target chat has been switched by progress updater due to limit reached
                logger.info(f"[{bot.me.username}] Switching target chat for job {part['job_id']} to {switched_target}")
                doc["target_chat"] = switched_target

                try:
                    await db.deliveries.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"target_chat": switched_target}}
                    )
                except DuplicateKeyError:
                    # delivery with new target chat already exists, skip updating
                    pass
            
            msg = None
            while True:
                try:
                    msg = await bot.copy_message(
                        doc["target_chat"],
                        doc["last_source"]["chat_id"],
                        doc["last_source"]["msg_id"],
                        caption=render_caption(
                            c_cap,
                            file_name=doc['file_name'],
                            file_size=doc['file_size'],
                            caption=doc['caption']
                        ) if settings['custom_caption'] else None,
                        parse_mode=enums.ParseMode.HTML,
                        reply_markup=to_pyrogram_keyboard(parse_keyboard(c_btn), False) if settings['custom_btn'] and c_btn else None
                    )
                    break
                except FloodWait as e:
                    logger.warning(f"[{bot.me.username}] Flood wait {e.value} seconds")
                    print(f"[{bot.me.username}] Flood wait {e.value} seconds")
                    await asyncio.sleep(e.value)
                except Exception as e:
                    logger.exception(f"[{bot.me.username}] Failed to forward message {doc['last_source']['msg_id']} to {doc['target_chat']}: {e}")
                    print(f"[{bot.me.username}] Failed to forward message {doc['last_source']['msg_id']} to {doc['target_chat']}: {e}")
                    raise          
            
            if msg:
                # mark delivered
                await db.mark_delivered(doc["_id"])

            # update progress
            await db.parts.update_one(
                {"_id": part["_id"]},
                {
                    "$set": {
                        "current_msg_id": doc["last_source"]["msg_id"],
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )

            await asyncio.sleep(2)  # to avoid hitting flood limits

        await db.parts.update_one(
            {"_id": part["_id"]},
            {"$set": {"status": "done"}}
        )
        return True
    except Exception as e:
        logger.exception(f"[{bot.me.username}] Partition failed")
        print(f"{bot.me.username} - Partition failed: {e}")
        await db.parts.update_one(
            {"_id": part["_id"]},
            {
                "$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return False

async def start_forwarding(bot: Client, job_id: str, p_msg: Message, w_client: list) -> None:
    if lock.locked():
        return await p_msg.edit_text("❌ Another forwarding operation is in progress. Please wait until it finishes.") if p_msg else None

    if not await db.partitions_exist(job_id):
        await db.create_partitions(job_id, w_client)

    await db.update_job_status(job_id, "forwarding")
    settings = await db.get_settings()

    updater_task = asyncio.create_task(
        progress_updater(bot, job_id, settings)
    )

    tasks = []
    async for part in db.parts.find({"job_id": job_id}):
        worker_prefix = part["worker"].split(":")[0]
        worker_bot = WORKER_CLIENTS.get(worker_prefix)

        if not worker_bot:
            logger.warning(f"Worker with prefix {worker_prefix} is not initialized.")
            await db.remove_job(job_id)
            return await p_msg.edit_text("❌ Forwarding failed: Worker with prefix {worker_prefix} is not initialized.\n\nDeleting job data...") if p_msg else None

        tasks.append(asyncio.create_task(run_partition(worker_bot, part, settings)))


    await asyncio.gather(*tasks)

    await db.update_job_status(job_id, "completed")
    await asyncio.sleep(10)  # wait for last progress update
    updater_task.cancel()
    await db.remove_job(job_id)