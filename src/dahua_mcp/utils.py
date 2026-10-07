"""MCP-side helpers.

The Dahua protocol helpers that used to live here -- response parsing, config
value encoding, byte formatting, storage parsing -- moved into `aiodahua`,
where the Home Assistant side can use them too. What is left is either
MCP-specific or a re-shaping of an aiodahua result into what the tools return.
"""

from aiodahua import build_config_query
from aiodahua import encode_config_value
from aiodahua import format_bytes
from aiodahua import parse_kv
from aiodahua import parse_storage_info as _parse_storage_info

__all__ = [
    "build_config_query",
    "encode_config_value",
    "format_bytes",
    "parse_bool",
    "parse_dahua_response",
    "parse_storage_info",
]

TRUTHY_VALUES = ("1", "true", "yes", "on")


def parse_bool(val, default=True):
    """
    Convert a value to boolean.

    Returns:
        bool: True if val represents a truthy value, case-insensitive; otherwise False.
    """
    if val is None:
        return default
    return str(val).strip().casefold() in TRUTHY_VALUES


def parse_dahua_response(text: str) -> dict:
    """Parse Dahua CGI ``key=value`` text into a dict, without the prefixes.

    aiodahua keeps ``table.`` and ``status.`` because renaming keys breaks
    callers that index the literal response. The MCP tools have always
    returned them stripped, and that is a published output shape, so the
    stripping happens here.
    """
    return parse_kv(text, strip_prefix=True)


def parse_storage_info(text: str) -> dict:
    """Parse ``storageDevice.cgi?action=getDeviceAllInfo`` into structured data.

    aiodahua returns the list of devices; the tool's published shape wraps it
    with a count.
    """
    devices = _parse_storage_info(text)
    return {"devices": devices, "device_count": len(devices)}
