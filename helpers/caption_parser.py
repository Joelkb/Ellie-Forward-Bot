"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly.

Caption parsing utilities.
"""

import string
from html import escape

class SafeFormatDict(dict):
    """Return {key} literally when a key is missing instead of raising KeyError."""
    def __missing__(self, key):
        return "{" + key + "}"

def human_readable_size(size_bytes: int | None) -> str:
    """Convert bytes to a human readable form (e.g. 1.2 MB)."""
    if size_bytes is None:
        return ""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} EB"

def render_caption(
    template: str,
    *,
    file_name: str | None = None,
    file_size: int | None = None,
    caption: str | None = None,
    **extra
) -> str:
    """
    Render a caption template with HTML-escaped values.

    Placeholders you can use (by default):
      {file_name}      – file name
      {file_size}      – human-readable file size (e.g. 1.23 MB)
      {raw_file_size}  – raw size in bytes
      {caption}        – original message caption (if any)

    Any extra keyword arguments will also be available as {key}.
    """
    data: dict[str, str] = {
        "file_name": escape(file_name) if file_name else "",
        "file_size": escape(human_readable_size(file_size)) if file_size is not None else "",
        "raw_file_size": str(file_size) if file_size is not None else "",
        "caption": escape(caption) if caption else "",
    }

    # Add extra placeholders (also HTML-escaped)
    for key, value in extra.items():
        data[key] = escape(str(value)) if value is not None else ""

    formatter = string.Formatter()
    return formatter.vformat(template, args=(), kwargs=SafeFormatDict(data))
