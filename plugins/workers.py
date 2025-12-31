"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Worker bot management utilities..
"""

from pyrogram import Client
from typing import Dict
from config import configVars
import logging

logger = logging.getLogger(__name__)

WORKER_CLIENTS: Dict[str, Client] = {}

async def init_worker_clients(tokens: list[str]) -> Dict[str, Client]:
    """
    Initialize worker bots from bot tokens stored in DB.
    Keyed by bot token prefix (same as your UI uses).
    """
    global WORKER_CLIENTS

    for token in tokens:
        prefix = token.split(":")[0]

        if prefix in WORKER_CLIENTS:
            continue  # already running
        
        try:
            client = Client(
                name=f"worker_{prefix}",
                api_id=configVars.API_ID,
                api_hash=configVars.API_HASH,
                bot_token=token,
                workers=50,
                sleep_threshold=10,
                in_memory=True
            )

            await client.start()
            me = await client.get_me()
        except Exception as e:
            logger.exception(f"Failed to start worker bot with prefix {prefix}: {e}")
            continue

        WORKER_CLIENTS[prefix] = client
        logger.info(f"Worker started: @{me.username}")

    return WORKER_CLIENTS


async def stop_worker_clients():
    for client in WORKER_CLIENTS.values():
        try:
            await client.stop()
        except Exception as e:
            logger.exception(f"Failed to stop worker bot: {e}")