"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Bot information extraction utilities. [Deprecated, use Pyrogram Client methods instead.]
"""

import aiohttp
import logging

logger = logging.getLogger(__name__)

async def get_bot_info(bot_token: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to fetch bot info: HTTP {resp.status}")
                    return {}
                data = await resp.json()
                if not data.get("ok"):
                    logger.error(f"Failed to fetch bot info: {data}")
                    return {}
                return data["result"]
    except Exception as e:
        logger.error(f"Exception while fetching bot info: {e}")
        return {}