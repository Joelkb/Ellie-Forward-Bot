"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Button parsing utilities for custom keyboards.
"""

import re
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

button_re = re.compile(r'^\s*(?P<label>.+?)\s*-\s*(?P<url>\S+)\s*$')

def parse_keyboard(config: str):
    keyboard = []
    if not config:
        return keyboard

    for line in config.strip().splitlines():
        line = line.strip()
        if not line:
            continue

        # Split multiple buttons in the same row
        chunks = [c.strip() for c in line.split("&&") if c.strip()]
        row = []
        
        for chunk in chunks:
            m = button_re.match(chunk)
            if m:
                row.append({
                    "text": m.group("label").strip(),
                    "url": m.group("url").strip()
                })
        
        if row:
            keyboard.append(row)

    return keyboard

def to_pyrogram_keyboard(parsed_keyboard, need_callback: bool = True) -> InlineKeyboardMarkup:
    keyboard = []

    for row in parsed_keyboard:
        btn_row = [
            InlineKeyboardButton(text=btn["text"], url=btn["url"])
            for btn in row
        ]
        keyboard.append(btn_row)

    # Fixed navigation buttons
    if need_callback:
        keyboard.append([
            InlineKeyboardButton("Back", callback_data="back:setgs"),
            InlineKeyboardButton("Set New", callback_data="setcbtn")
        ])
    
    return InlineKeyboardMarkup(keyboard)
