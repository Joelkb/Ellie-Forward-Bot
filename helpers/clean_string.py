"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Clean a Telegram file name or caption for database storage.
"""

import re

def clean_text(text: str) -> str:
    """
    Clean a Telegram file name or caption for database storage.

    Rules:
    - Replace dots (.) with spaces
    - Remove unwanted special characters
    - Keep: letters, numbers, spaces, [], (), -
    - Collapse multiple spaces into one
    - Strip leading/trailing spaces
    """

    if not text:
        return ""

    # Replace dots with spaces
    text = text.replace(".", " ")

    # Remove unwanted characters
    # Allowed: A-Z a-z 0-9 space [ ] ( ) -
    text = re.sub(r"[^A-Za-z0-9\[\]\(\)\-\s]", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text