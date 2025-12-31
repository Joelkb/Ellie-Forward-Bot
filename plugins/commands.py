"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Command handlers for the Ellie Forward Bot.
"""

from database import db
from typing import Optional
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client, filters, enums
from plugins.callbacks import generate_settings_buttons

@Client.on_message(filters.command("start"))
async def start_handler(bot: Client, msg: Message):
    if msg.chat.type != enums.ChatType.PRIVATE:
        return await msg.reply_text("This command only works on private chats.")
    else:
        pass

    btn = [[InlineKeyboardButton("Forwarded Statistics 📊", callback_data="f_stats")]]
    
    return await msg.reply_text(
        "<b>👋 Hello! I'm Ellie Forward Bot.\n\n"
        "I can help my ADMINS to forward and index media files efficiently.\n\n"
        "Use /settings to configure the bot [ADMIN Only].</b>",
        True,
        enums.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(btn)
    )

@Client.on_message(filters.command("skip"))
async def skip_handler(bot: Client, msg: Message):
    if msg.chat.type != enums.ChatType.PRIVATE:
        return await msg.reply_text("This command only works on private chats.")
    elif msg.from_user.id not in await db.get_admins():
        return await msg.reply_text("Only admins are allowed to use this command !")
    else:
        pass
    
    try:
        num: Optional[Message] = await bot.ask(
            chat_id=msg.chat.id,
            text="<b>Enter number of message to index first from each source chat.\nFor example: 34765 skips 34764 messages and start indexing from 34765th message.</b>",
            filters=filters.text & filters.private,
            parse_mode=enums.ParseMode.HTML,
            timeout=60
        )
    except TimeoutError:
        return await msg.reply_text("<b>Timeout Error! You took too long to respond. Please try again.</b>", True, enums.ParseMode.HTML)
    
    if not num or not num.text.isdigit():
        return await msg.reply_text("<b>Please enter a valid number.</b>", True, enums.ParseMode.HTML)
    
    settings = await db.get_settings()
    settings["skip"] = int(num.text)
    await db.update_settings(settings)

    return await msg.reply_text(f"<b>Successfully updated skip to {num.text}.</b>", True, enums.ParseMode.HTML)

@Client.on_message(filters.command("logs"))
async def logs_handler(bot: Client, msg: Message):
    """Send log file"""
    
    if msg.chat.type != enums.ChatType.PRIVATE:
        return await msg.reply_text("This command only works on private chats.")
    elif msg.from_user.id not in await db.get_admins():
        return await msg.reply_text("Only admins are allowed to use this command !")
    else:
        pass
    
    try:
        await msg.reply_document('Logs.txt')
    except Exception as e:
        await msg.reply(str(e))

@Client.on_message(filters.command("settings"))
async def settings_handler(bot: Client, msg: Message):
    if msg.chat.type != enums.ChatType.PRIVATE:
        return await msg.reply_text("This command only works on private chats.")
    elif msg.from_user.id not in await db.get_admins():
        return await msg.reply_text("Only admins are allowed to use this command !")
    else:
        pass
    
    return await msg.reply_text(
        "<b>⚙️ Settings</b>",
        True,
        enums.ParseMode.HTML,
        reply_markup=await generate_settings_buttons()
    )

@Client.on_message(filters.command("limit"))
async def limit_handler(bot: Client, msg: Message):
    if msg.chat.type != enums.ChatType.PRIVATE:
        return await msg.reply_text("This command only works on private chats.")
    elif msg.from_user.id not in await db.get_admins():
        return await msg.reply_text("Only admins are allowed to use this command !")
    else:
        pass
    
    try:
        limit_msg: Optional[Message] = await bot.ask(
            chat_id=msg.chat.id,
            text="<b>Enter maximum number of files to forward per chat.\nFor example: 500 means each forwarding per chat will forward maximum 500 files and switch to another target chat if there's one.</b>",
            filters=filters.text & filters.private,
            parse_mode=enums.ParseMode.HTML,
            timeout=60
        )
    except TimeoutError:
        return await msg.reply_text("<b>Timeout Error! You took too long to respond. Please try again.</b>", True, enums.ParseMode.HTML)
    
    if not limit_msg or not limit_msg.text.isdigit():
        return await msg.reply_text("<b>Please enter a valid number.</b>", True, enums.ParseMode.HTML)
    
    settings = await db.get_settings()
    settings["limit"] = int(limit_msg.text)
    await db.update_settings(settings)

    return await msg.reply_text(f"<b>Successfully updated limit to {limit_msg.text}.</b>", True, enums.ParseMode.HTML)