"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Main entry point for the Ellie Forward Bot.
"""

import logging
import asyncio
import logging.config
from database import db
from pyrogram import Client, enums
from config import configVars
from pyrogram.types import Message
from plugins.index import resume_indexing_job
from plugins.workers import init_worker_clients, stop_worker_clients
from plugins.forwarding import start_forwarding
from typing import AsyncGenerator, Optional, Union

# logging configurations
logging.config.fileConfig(
    "logging.conf",
    disable_existing_loggers=False
)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

class Bot(Client):
    def __init__(self) -> None:
        super().__init__(
            name=configVars.SESSION_NAME,
            api_id=configVars.API_ID,
            api_hash=configVars.API_HASH,
            bot_token=configVars.BOT_TOKEN,
            workers=200,
            sleep_threshold=10,
            plugins=dict(root="plugins")
        )

    async def start(self):
        await super().start()
        b_object = await self.get_me()

        for id in configVars.ADMINS:
            await db.add_or_update_user(id, True)

        await db.ensure_indexes()
            
        settings = await db.get_settings()
        await init_worker_clients(settings["worker_clients"])
        
        logging.info(f"Bot started with username @{b_object.username}")

        # await self.resume_interrupted_indexing()
        await self.resume_interrupted_jobs()  # forwarding

    async def stop(self, *args):
        await super().stop()
        logging.info("Stopping worker clients...")
        await stop_worker_clients()
        logging.info("Bot stopped. Bye.")

    async def resume_interrupted_jobs(self):
        jobs = db.jobs.find({
            "status": {"$in": ["forwarding", "resuming"]}
        })

        async for job in jobs:
            await db.update_job_status(job["_id"], "resuming")

            # Notify user
            try:
                p_msg = await self.edit_message_text(
                    job["progress_chat_id"],
                    job["progress_msg_id"],
                    "<b>♻️ Bot restarted.\nResuming forwarding…</b>",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                p_msg = None
                pass

            asyncio.create_task(
                start_forwarding(
                    self,
                    job["_id"],
                    p_msg,
                    job["worker_clients"],
                    job['is_direct'],
                    l_msg_id=job.get('l_msg_id', 0)
                )
            )

    async def resume_interrupted_indexing(self):
        cursor = db.jobs.find({
            "status": "indexing"
        })

        async for job in cursor:
            await db.update_job_status(job["_id"], "resuming")

            # Notify user
            try:
                await self.edit_message_text(
                    job["progress_chat_id"],
                    job["progress_msg_id"],
                    "<b>♻️ Bot restarted.\nResuming indexing…</b>",
                    parse_mode=enums.ParseMode.HTML
                )
            except Exception:
                pass

            asyncio.create_task(
                resume_indexing_job(self, job)
            )

    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).
                
            limit (``int``):
                Identifier of the last message to be returned.
                
            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

bot = Bot()
bot.run()