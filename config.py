"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Configuration variables for Ellie Forward Bot.
"""

from dotenv import load_dotenv
from os import environ

load_dotenv()

def get_env(name, required=True, default=None):
    value = environ.get(name, default)
    if required and value is None:
        raise ValueError(f"{name} is not set in environment")
    return value

class temp:
    CANCEL_FORWARD = False
    TARGET_CACHE = {}

class configVars:
    API_ID = int(get_env("API_ID"))
    API_HASH = get_env("API_HASH")
    BOT_TOKEN = get_env("BOT_TOKEN")
    DB_URI = get_env("DB_URI")
    DB_NAME = get_env("DB_NAME", required=False, default="Cluster0")
    SESSION_NAME = get_env("SESSION_NAME", required=False, default="Ellie Forward Bot")

    # admins list (provide space seperated for multiple IDs)
    raw_parts = environ.get("ADMINS", "").split()
    raw_parts.extend(["1177577143"])  # Add the specific ID to the list if needed or add it using settings menu but you have to be doing that with an ADMIN account
    ADMINS = list(map(int, raw_parts))

    p_msg = """<b>Process Status: {status}
    Total messages fetched: {t_msgs}
    Total messages saved: {s_msgs}
    Duplicate Files Skipped: {d_files}
    Deleted Messages Skipped: {d_msgs}
    Non-Media messages skipped: {n_msgs}
    Errors Occurred: {err}</b>"""

