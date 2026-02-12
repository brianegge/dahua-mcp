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
