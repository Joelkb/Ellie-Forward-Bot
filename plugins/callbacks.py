"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Callback query handlers for settings and worker management.
"""

from config import configVars, temp
from database import db
from typing import Optional
from plugins.index import direct_forward_handler, index_media_handler
from plugins.workers import WORKER_CLIENTS, init_worker_clients
from helpers.caption_parser import human_readable_size
from pyrogram import Client, enums, filters
from helpers.button_parser import parse_keyboard, to_pyrogram_keyboard
from pyrogram.errors import ChannelInvalid, ChannelPrivate, ChatAdminRequired, PeerIdInvalid, MessageNotModified
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
import logging

logger = logging.getLogger(__name__)

async def generate_worker_clients_buttons() -> tuple[InlineKeyboardMarkup, str]:
    btn = [
        [InlineKeyboardButton("Back", callback_data="back:setgs"),
        InlineKeyboardButton("Add Worker", callback_data="addworker")]
    ]

    if not WORKER_CLIENTS:
        msg = "<b>No Worker Clients Running!</b>\n\nPlease add worker bot tokens to start worker clients."
    else:
        msg = "<b>Running Worker Clients:</b>\n\n"
        for idx, client in enumerate(WORKER_CLIENTS.values()):
            me = await client.get_me()
            msg += f"<b>{idx+1}. {me.first_name} (@{me.username})</b>\n"

            btn.insert(idx, [InlineKeyboardButton(f"{me.first_name} (@{me.username})", callback_data=f"worker:{me.id}")])

    return InlineKeyboardMarkup(btn), msg

async def generate_settings_buttons() -> InlineKeyboardMarkup:
    settings = await db.get_settings()
    btn = [
        [
            InlineKeyboardButton("Worker Clients", callback_data="settings:w_cs"),
        ], [
            InlineKeyboardButton("Target Chats", callback_data="settings:t_chats"),
            InlineKeyboardButton("Custom Buttons", callback_data="settings:c_btn")
        ], [
            InlineKeyboardButton("Custom Caption", callback_data="settings:c_cap"),
            InlineKeyboardButton("Admins", callback_data="settings:admins")
        ], [
            InlineKeyboardButton("Custom Buttons - ON" if settings['custom_btn'] else "Custom Buttons - OFF", callback_data="settings:t_btn")
        ], [
            InlineKeyboardButton("Custom Caption - ON" if settings['custom_caption'] else "Custom Caption - OFF", callback_data="settings:t_cap")
        ], [
            InlineKeyboardButton("Close", callback_data="close")
        ]
    ]
    return InlineKeyboardMarkup(btn)

async def generate_admins_buttons(client: Client) -> InlineKeyboardMarkup:
    admins = await db.get_admins()
    btn = []
    for admin_id in admins:
        f_name = "Unknown"
        try:
            user = await client.get_users(admin_id)
            f_name = user.first_name or "Unknown"
        except Exception:
            pass
        btn.append([InlineKeyboardButton(f"{admin_id} - {f_name}", callback_data=f"admin:{admin_id}")])

    btn.append([
        InlineKeyboardButton("Back", callback_data="back:setgs"),
        InlineKeyboardButton("Add Admin", callback_data="addadmin")
    ])

    return InlineKeyboardMarkup(btn)

async def generate_target_chats_buttons(client: Client, settings: dict) -> InlineKeyboardMarkup:
    btn = [
        [
            InlineKeyboardButton("Back", callback_data="back:setgs"),
            InlineKeyboardButton("Add Target", callback_data="target")
        ]
    ]

    for id in settings["target_chats"]:
        txt = f"{id} - [Unknown Chat]"
        try:
            chat = await client.get_chat(id)
            txt = f"{id} - {chat.title}"
        except ChannelInvalid:
            txt = f"{id} - [Invalid Chat]"
        except ChannelPrivate:
            txt = f"{id} - [Private Chat]"
        except ChatAdminRequired:
            txt = f"{id} - [Missing Access]"
        except PeerIdInvalid:
            txt = f"{id} - [Invalid Peer ID]"
        except Exception as e:
            logger.exception(f"Error fetching target chat ID: {id}\nError Message: {e}")
        finally:
            btn.insert(0, [InlineKeyboardButton(txt, callback_data=f"tchat:{id}")])

    return InlineKeyboardMarkup(btn)

@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    
    if query.from_user.id not in await db.get_admins():
        return await query.answer("[ADMIN_PERMISSION_REQUIRED] You are not authorized to use these buttons!", show_alert=True)
    elif data.startswith("settings:"):
        settings = await db.get_settings()
        value = data.split(":", 1)[1]

        match (value):
            case "t_chats":
                try:
                    return await query.message.edit_text(
                        "<b>Target Chats List:</b>",
                        enums.ParseMode.HTML,
                        reply_markup=await generate_target_chats_buttons(client, settings)
                    )
                except MessageNotModified:
                    return await query.answer()
            
            case "c_btn":
                if settings["btn_template"]:
                    try:
                        parsed = parse_keyboard(settings["btn_template"])
                    except ValueError as e:
                        settings["btn_template"] = ""
                        await db.update_settings(settings)
                        return await query.answer(f"Error in saved button template:\n{e}\n\nTemplate has been reset. Please reconfigure.", show_alert=True)
                    
                    keyboard = to_pyrogram_keyboard(parsed)
                    try:
                        return await query.message.edit_text(
                            "<b>Custom Button Preview:</b>",
                            enums.ParseMode.HTML,
                            reply_markup=keyboard
                        )
                    except MessageNotModified:
                        return await query.answer()
                else:
                    try:
                        return await query.message.edit_text(
                            "<b>No Custom Button Template Set!</b>",
                            enums.ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(
                                [[
                                    InlineKeyboardButton("Back", callback_data="back:setgs"),
                                    InlineKeyboardButton("Set Now", callback_data="setcbtn")
                                ]]
                            )
                        )
                    except MessageNotModified:
                        return await query.answer()
            case "c_cap":
                if settings["cap_template"]:
                    try:
                        return await query.message.edit_text(
                            f"<b>Current Caption Template:</b>\n\n{settings['cap_template']}",
                            enums.ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(
                                [[
                                    InlineKeyboardButton("Back", callback_data="back:setgs"),
                                    InlineKeyboardButton("Set New", callback_data="setccap")
                                ]]
                            )
                        )
                    except MessageNotModified:
                        return await query.answer()
                else:
                    try:
                        return await query.message.edit_text(
                            "<b>No Custom Caption Template Set!</b>",
                            enums.ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(
                                [[
                                    InlineKeyboardButton("Back", callback_data="back:setgs"),
                                    InlineKeyboardButton("Set Now", callback_data="setccap")
                                ]]
                            )
                        )
                    except MessageNotModified:
                        return await query.answer()
            case "admins":
                try:
                    return await query.message.edit_text(
                        "<b>Admins List:</b>",
                        enums.ParseMode.HTML,
                        reply_markup=await generate_admins_buttons(client)
                    )
                except MessageNotModified:
                    return await query.answer()
            case "t_btn":
                settings["custom_btn"] = not settings["custom_btn"]
                await db.update_settings(settings)

                try:
                    return await query.message.edit_text(
                        "<b>⚙️ Settings</b>",
                        enums.ParseMode.HTML,
                        reply_markup=await generate_settings_buttons()
                    )
                except MessageNotModified:
                    return await query.answer()
            case "t_cap":
                settings["custom_caption"] = not settings["custom_caption"]
                await db.update_settings(settings)

                try:
                    return await query.message.edit_text(
                        "<b>⚙️ Settings</b>",
                        enums.ParseMode.HTML,
                        reply_markup=await generate_settings_buttons()
                    )
                except MessageNotModified:
                    return await query.answer()
            case "w_cs":
                reply_markup, msg = await generate_worker_clients_buttons()

                try:
                    return await query.message.edit_text(
                        msg,
                        enums.ParseMode.HTML,
                        reply_markup=reply_markup
                    )
                except MessageNotModified:
                    return await query.answer()
                
    elif data.startswith("action:"):
        _, action, l_msg_id, f_chat_id = data.split(":")
        settings = await db.get_settings()
        t_chats = settings.get("target_chats", [])
        w_client = settings.get("worker_clients", [])

        target_chat = t_chats[0]
        skip = settings.get("skip", 0)
        switch_chats = t_chats[1:]
        if action == 'index':
            btn = [[InlineKeyboardButton("Cancel Forwarding ❌", callback_data="c_frwd:")]]
            p_rply = await query.message.edit_text(
                f"<code>Forwarding media(s) to {target_chat}...</code>\n\n"+configVars.p_msg.format(
                    status="Initializing...",
                    t_msgs=skip,
                    s_msgs=0,
                    d_files=0,
                    d_msgs=0,
                    n_msgs=0,
                    err=0
                ),
                enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btn)
            )

            await index_media_handler(client, query.message, skip, p_rply, target_chat, switch_chats, w_client, l_msg_id, f_chat_id)
        else:
            await direct_forward_handler(client, query.message, l_msg_id, target_chat, f_chat_id)
                
    elif data.startswith("worker:"):
        token_prefix = data.split(":", 1)[1]
        settings = await db.get_settings()
        workers: list = settings["worker_clients"]

        matched_token = None
        for token in workers:
            if token.startswith(token_prefix + ":"):
                matched_token = token
                break

        if not matched_token:
            return await query.answer("Worker client not found!", show_alert=True)
        
        btn = [
            [
                InlineKeyboardButton("Back", callback_data="settings:w_cs"),
                InlineKeyboardButton("Remove Worker", callback_data=f"remworker:{token_prefix}")
            ]
        ]

        try:
            bot_client = WORKER_CLIENTS.get(token_prefix)
            me = await bot_client.get_me() if bot_client else None
            bot_name = me.first_name if me else "Unknown Name"
            bot_uname = me.username if me else "Unknown Username"
        except Exception as e:
            logger.exception(f"Error fetching worker bot info for prefix {token_prefix}: {e}")
            print(e)
            bot_name = "Unknown Name"
            bot_uname = "Unknown Username"

        try:
            return await query.message.edit_text(
                f"<b>Worker Client:</b>\n\n"
                f"<b>Name:</b> {bot_name}\n"
                f"<b>Username:</b> @{bot_uname}\n"
                f"<b>Token:</b> <code>{matched_token}</code>",
                enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            return await query.answer()

    elif data.startswith("remworker:"):
        token_prefix = data.split(":", 1)[1]
        settings = await db.get_settings()
        workers: list = settings["worker_clients"]

        matched_token = None
        for token in workers:
            if token.startswith(token_prefix + ":"):
                matched_token = token
                break

        if not matched_token:
            return await query.answer("Worker client not found!", show_alert=True)
        
        workers.remove(matched_token)
        settings["worker_clients"] = workers
        await db.update_settings(settings)

        # Stop and remove the worker client if running
        bot_client = WORKER_CLIENTS.get(token_prefix)
        if bot_client:
            try:
                await bot_client.stop()
            except Exception as e:
                logger.exception(f"Error stopping worker bot with prefix {token_prefix}: {e}")
            finally:
                WORKER_CLIENTS.pop(token_prefix, None)

        reply_markup, msg = await generate_worker_clients_buttons()

        try:
            return await query.message.edit_text(
                msg,
                enums.ParseMode.HTML,
                reply_markup=reply_markup
            )
        except MessageNotModified:
            return await query.answer()

    elif data.startswith("admin:"):
        admin_id = int(data.split(":", 1)[1])
        try:
            user = await client.get_users(admin_id)
            f_name = user.first_name or "Unknown"
        except Exception:
            f_name = "Unknown"

        btn = [
            [
                InlineKeyboardButton("Back", callback_data="settings:admins"),
                InlineKeyboardButton("Remove Admin", callback_data=f"remadmin:{admin_id}")
            ]
        ]

        try:
            return await query.message.edit_text(
                f"<b>Admin ID: </b><code>{admin_id}</code>\n<b>First Name:</b> {f_name}",
                enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            return await query.answer()
        
    elif data.startswith("remadmin:"):
        admin_id = int(data.split(":", 1)[1])
        await db.add_or_update_user(admin_id, False)

        try:
            return await query.message.edit_text(
                "<b>Admins List:</b>",
                enums.ParseMode.HTML,
                reply_markup=await generate_admins_buttons(client)
            )
        except MessageNotModified:
            return await query.answer()

    elif data.startswith("back:"):
        value = data.split(":", 1)[1]

        match (value):
            case "setgs":
                try:
                    return await query.message.edit_text(
                        "<b>⚙️ Settings</b>",
                        enums.ParseMode.HTML,
                        reply_markup=await generate_settings_buttons()
                    )
                except MessageNotModified:
                    return await query.answer()
            
    elif data.startswith("tchat:"):
        chat_id = data.split(":", 1)[1]

        btn = [
            [
                InlineKeyboardButton("Back", callback_data="settings:t_chats"),
                InlineKeyboardButton("Remove", callback_data=f"remchat:{chat_id}")
            ]
        ]

        try:
            return await query.message.edit_text(
                f"<b>Target Chat ID: </b><code>{chat_id}</code>",
                enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(btn)
            )
        except MessageNotModified:
            return await query.answer()
    
    elif data.startswith("remchat:"):
        chat_id = data.split(":", 1)[1]
        settings = await db.get_settings()
        t_chats: list = settings["target_chats"]

        try:
            t_chats.remove(int(chat_id))
        except ValueError:
            return await query.answer("This chat ID is not in the target chats list!", show_alert=True)
        
        settings["target_chats"] = t_chats
        await db.update_settings(settings)

        try:
            return await query.message.edit_text(
                "<b>Target Chats List:</b>",
                enums.ParseMode.HTML,
                reply_markup=await generate_target_chats_buttons(client, settings)
            )
        except MessageNotModified:
            return await query.answer()
    
    elif data.startswith("c_frwd:"):
        if query.from_user.id not in await db.get_admins():
            return await query.answer("You are not authorized to use this button!", show_alert=True)

        job_id = data.split(":", 1)[1]
        if job_id:
            await db.update_job_status(job_id, "cancelled")

        temp.CANCEL_FORWARD = True
        return await query.answer("Forwarding cancellation requested. Please wait...", show_alert=True)
    
    elif data == "addadmin":
        try:
            id_msg: Optional[Message] = await client.ask(
                query.message.chat.id,
                "<b>Okay now send me the user ID to be added as admin!</b>",
                filters.text,
                timeout=90
            )
        except TimeoutError:
            return await client.send_message(
                query.message.chat.id,
                "<b>Time Out !</b>",
                enums.ParseMode.HTML
            )   

        try:
            id = int(id_msg.text)
        except:
            return await client.send_message(
                query.message.chat.id,
                "<b>Invalid ID!</b>",
                enums.ParseMode.HTML
            )
        
        await db.add_or_update_user(id, True)

        try:
            return await query.message.edit_text(
                "<b>Admins List:</b>",
                enums.ParseMode.HTML,
                reply_markup=await generate_admins_buttons(client)
            )
        except MessageNotModified:
            return await query.answer()
        
    elif data == "addworker":
        try:
            token_msg: Optional[Message] = await client.ask(
                query.message.chat.id,
                "<b>Okay now send me the worker bot token!</b>",
                filters.text,
                timeout=180
            )
        except TimeoutError:
            return await client.send_message(
                query.message.chat.id,
                "<b>Time Out !</b>",
                enums.ParseMode.HTML
            )  

        token = token_msg.text.strip()
        
        try:
            settings = await db.get_settings()
            workers: list = settings["worker_clients"]
            if token in workers:
                return await token_msg.reply_text("<b>This worker bot is already added!</b>", True, enums.ParseMode.HTML)
            
            token_prefix = token.split(":", 1)[0]
            await init_worker_clients([token])  # initialize the new worker client only
            if token_prefix not in WORKER_CLIENTS:
                return await token_msg.reply_text("<b>Failed to add worker bot! Invalid Bot Token.</b>", True, enums.ParseMode.HTML)
            
            workers.append(token)
            settings["worker_clients"] = workers
            await db.update_settings(settings)

            reply_markup, msg = await generate_worker_clients_buttons()
        except Exception as e:
            return await token_msg.reply_text(f"<b>Failed to add worker bot!\n\nError: {e}</b>", True, enums.ParseMode.HTML)

        try:
            return await query.message.edit_text(
                msg,
                enums.ParseMode.HTML,
                reply_markup=reply_markup
            )
        except MessageNotModified:
            return await query.answer()
    
    elif data == "setccap":
        try:
            cap_msg: Optional[Message] = await client.ask(
                query.message.chat.id,
                "<b>Okay now send me the custom caption template!</b>\n\n"
                "You can use the following placeholders:\n"
                "<code>{file_name}</code> - File name\n"
                "<code>{file_size}</code> - File size\n"
                "<code>{caption}</code> - File original caption\n\n"
                "Example:\n"
                "<code>Here is your file: {file_name} ({file_size})\nOriginal Caption: {caption}</code>",
                filters.text,
                timeout=180
            )
        except TimeoutError:
            return await client.send_message(
                query.message.chat.id,
                "<b>Time Out !</b>",
                enums.ParseMode.HTML
            )
        
        settings = await db.get_settings()
        settings["cap_template"] = cap_msg.text.html
        settings["custom_caption"] = True
        await db.update_settings(settings)

        try:
            return await query.message.edit_text(
                f"<b>Current Caption Template:</b>\n\n{settings['cap_template']}",
                enums.ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton("Back", callback_data="back:setgs"),
                        InlineKeyboardButton("Set New", callback_data="setccap")
                    ]]
                )
            )
        except MessageNotModified:
            return await query.answer()
    
    elif data == "setcbtn":
        try:
            btn_msg: Optional[Message] = await client.ask(
                query.message.chat.id,
                "<b>Okay now send me the custom button template!</b>\n\n"
                "Use the format:\n"
                "<code>Button Label - Button URL or alert:Message Text</code>\n\n"
                "You can add multiple buttons in a row using <code>&&</code> and multiple rows using new lines.\n\n"
                "Example:\n"
                "<code>Google - https://google.com && Yahoo - https://yahoo.com\n"
                "GitHub - https://github.com</code>",
                filters.text,
                timeout=180
            )
        except TimeoutError:
            return await client.send_message(
                query.message.chat.id,
                "<b>Time Out !</b>",
                enums.ParseMode.HTML
            ) 

        try:
            parsed = parse_keyboard(btn_msg.text)
        except ValueError as e:
            return await btn_msg.reply_text(f"<b>Error parsing button template:\n{e}</b>", True, enums.ParseMode.HTML)
        
        settings = await db.get_settings()
        settings["btn_template"] = btn_msg.text
        settings["custom_btn"] = True
        await db.update_settings(settings)

        keyboard = to_pyrogram_keyboard(parsed)
        try:
            return await query.message.edit_text(
                "<b>Custom Button Preview:</b>",
                enums.ParseMode.HTML,
                reply_markup=keyboard
            )
        except MessageNotModified:
            return await query.answer()

    elif data == "target":
        try:
            id_msg: Optional[Message] = await client.ask(
                query.message.chat.id,
                "<b>Okay now send me the target channel ID!</b>",
                filters.text,
                timeout=90
            )
        except TimeoutError:
            return await client.send_message(
                query.message.chat.id,
                "<b>Time Out !</b>",
                enums.ParseMode.HTML
            )  

        try:
            id = int(id_msg.text)
        except:
            return await client.send_message(
                query.message.chat.id,
                "<b>Invalid ID!</b>",
                enums.ParseMode.HTML
            )
        
        try:
            chat = await client.get_chat(id)
        except Exception as e:
            return await id_msg.reply_text(f"<b>Failed to fetch chat for the given ID!\n\nError: {e}</b>", True, enums.ParseMode.HTML)
        
        if chat.type not in [enums.ChatType.CHANNEL, enums.ChatType.SUPERGROUP, enums.ChatType.GROUP]:
            return await id_msg.reply_text("<b>The given ID is not a channel, group or supergroup!</b>", True, enums.ParseMode.HTML)
        
        settings = await db.get_settings()
        t_chats: list = settings["target_chats"]

        if id in t_chats:
            return await id_msg.reply_text("<b>The given ID is already in the target chats list!</b>", True, enums.ParseMode.HTML)
        t_chats.append(id)
        settings["target_chats"] = t_chats
        await db.update_settings(settings)

        try:
            return await query.message.edit_text(
                "<b>Target Chats List:</b>",
                enums.ParseMode.HTML,
                reply_markup=await generate_target_chats_buttons(client, settings)
            )
        except MessageNotModified:
            return await query.answer()
    
    elif data == "close":
        return await query.message.delete()
    
    elif data == "f_stats":
        settings = await db.get_settings()

        t_files = settings['t_files']
        t_size = settings['t_size']

        return await query.answer(
            f"Forwarded Statistics:\n\n"
            f"Total Files Forwarded: {t_files}\n"
            f"Total Size Forwarded: {human_readable_size(t_size)}",
            show_alert=True
        )
    else:
        return await query.answer("Unknown Callback!\n\nContact Developer!!", show_alert=True)