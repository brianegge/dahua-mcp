import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

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
    """
    Parse Dahua CGI key=value text responses into a dict.

    Strips common prefixes like 'table.' and 'status.' from keys.
    Lines without '=' are stored with their content as the value.
    """
    result = {}
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            # Strip common Dahua prefixes
            for prefix in ("table.", "status."):
                if key.startswith(prefix):
                    key = key[len(prefix) :]
                    break
            result[key] = value
        else:
            result[line] = line
    return result


# Characters Dahua CGI accepts literally inside a setConfig value. Anything else
# (notably & = # % +) is percent-encoded so a value cannot break out of the
# query string and corrupt neighbouring parameters.
_CONFIG_VALUE_SAFE = ":/-_.,[]()@'"


def encode_config_value(value: Any) -> str:
    """Encode a single ``configManager.cgi?action=setConfig`` value.

    Two firmware behaviours are handled here, both confirmed against an
    NV4116-HS:

    * An **empty value is silently ignored**. Sending ``&Foo.Name=`` returns
      ``OK`` while leaving the field unchanged. A single space *is* accepted and
      the device trims it back to "", so that is how a field is actually
      cleared. Callers pass "" to mean "clear this field" and it is translated.
    * Percent-encoding is required for ``#``, ``+`` and ``%``, which would
      otherwise be truncated at the fragment, decoded as a space, or break
      decoding entirely.

    Raises:
        ValueError: if the value contains "&". The firmware percent-decodes the
            whole query string before splitting it on "&", so an encoded "&"
            still terminates the value -- the request either 400s or the value
            is silently truncated. There is no way to escape it, so this fails
            loudly rather than writing corrupted data.
    """
    text = "" if value is None else str(value)
    if "&" in text:
        raise ValueError(
            "Dahua config values cannot contain '&': the firmware decodes the "
            "query string before splitting on '&', so the value would be "
            f"truncated or rejected. Offending value: {text!r}"
        )
    if text == "":
        text = " "
    return quote(text, safe=_CONFIG_VALUE_SAFE)


def build_config_query(params: Mapping[str, Any]) -> str:
    """Build the ``&``-joined ``key=value`` query string for setConfig.

    Keys are passed through literally: Dahua config paths contain ``[]``, ``:``
    and ``.`` which the firmware expects unencoded.
    """
    return "&".join(f"{k}={encode_config_value(v)}" for k, v in params.items())


def format_bytes(num: float) -> str:
    """Render a byte count as a short human-readable string (decimal units)."""
    value = float(num)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if abs(value) < 1000 or unit == "PB":
            return f"{value:.2f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1000
    return f"{value:.2f} PB"


def parse_storage_info(text: str) -> dict:
    """Parse ``storageDevice.cgi?action=getDeviceAllInfo`` into structured data.

    The raw response is a flat list of
    ``list.info[i].Detail[j].<Field>=<value>`` lines. This groups them into one
    entry per physical device with its partitions rolled up.
    """
    raw = parse_dahua_response(text)
    devices: dict[int, dict] = {}

    for key, value in raw.items():
        m = re.match(r"list\.info\[(\d+)\]\.(.+)", key)
        if not m:
            continue
        idx, rest = int(m.group(1)), m.group(2)
        dev = devices.setdefault(idx, {"partitions": {}})

        pm = re.match(r"Detail\[(\d+)\]\.(.+)", rest)
        if pm:
            part = dev["partitions"].setdefault(int(pm.group(1)), {})
            field = pm.group(2)
            if field in ("TotalBytes", "UsedBytes"):
                part[field] = int(float(value))
            elif field == "IsError":
                part["is_error"] = value.strip().lower() == "true"
            elif field == "Path":
                part["path"] = value
            else:
                part[field.lower()] = value
        elif rest == "Name":
            dev["name"] = value
        elif rest == "State":
            dev["state"] = value
        else:
            dev[rest.lower()] = value

    out = []
    for idx in sorted(devices):
        dev = devices[idx]
        parts = [dev["partitions"][i] for i in sorted(dev["partitions"])]
        total = sum(p.get("TotalBytes", 0) for p in parts)
        used = sum(p.get("UsedBytes", 0) for p in parts)
        for p in parts:
            p["total_bytes"] = p.pop("TotalBytes", 0)
            p["used_bytes"] = p.pop("UsedBytes", 0)
            p["total_human"] = format_bytes(p["total_bytes"])
        entry = {
            "name": dev.get("name", f"device{idx}"),
            "state": dev.get("state"),
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": max(total - used, 0),
            "total_human": format_bytes(total),
            "free_human": format_bytes(max(total - used, 0)),
            "healthy": dev.get("state") == "Success"
            and not any(p.get("is_error") for p in parts),
            "partition_errors": [p.get("path") for p in parts if p.get("is_error")],
            "partitions": parts,
        }
        if total and used >= total:
            entry["note"] = (
                "used == total is normal on a Dahua recorder: the firmware "
                "pre-allocates the whole disk into fixed-size blocks when it "
                "formats, so a freshly formatted drive also reports 100% used. "
                "It does not mean the disk is full or that recording has "
                "stopped -- use find_recordings to confirm writes are landing."
            )
        out.append(entry)

    return {"devices": out, "device_count": len(out)}
