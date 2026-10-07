import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml
from aiodahua import DahuaClient
from aiodahua import parse_kv

from dahua_mcp.models import CameraConfig
from dahua_mcp.models import DahuaConfig
from dahua_mcp.models import TransportConfig
from dahua_mcp.utils import parse_bool

logger = logging.getLogger(__name__)


class DahuaCamera:
    """One device, wrapped around aiodahua's client.

    The transport lives in aiodahua now: digest auth with a basic fallback,
    the firmware quirks (400 vs 501 for a missing endpoint, error bodies
    served with HTTP 200), and the self-signed certificates. What stays here
    is the shape the MCP tools expect -- parsed dicts with the ``table.`` and
    ``status.`` prefixes stripped.

    ``client`` is the underlying :class:`aiodahua.DahuaClient`, for tools that
    want its higher-level methods rather than raw CGI.
    """

    def __init__(self, config: CameraConfig, timeout: int = 20):
        self.config = config
        self.timeout = timeout
        protocol = "https" if config.port == 443 else "http"
        self.base_url = f"{protocol}://{config.host}:{config.port}"
        self.client = DahuaClient(
            config.host,
            config.username,
            config.password,
            port=config.port,
            timeout=timeout,
            verify_ssl=config.verify_ssl,
        )

    async def close(self):
        await self.client.async_close()

    async def get_parsed(self, endpoint: str) -> dict:
        """GET a CGI endpoint and parse key=value response into a dict."""
        return parse_kv(await self.client.async_get_text(endpoint), strip_prefix=True)

    async def get_raw(self, endpoint: str) -> str:
        """GET a CGI endpoint and return raw text."""
        return await self.client.async_get_text(endpoint)

    async def get_bytes(self, endpoint: str) -> bytes:
        """GET a CGI endpoint and return raw bytes (e.g. a snapshot JPEG)."""
        return await self.client.async_get_bytes(endpoint)


class DahuaCameraManager:
    """Manages multiple DahuaCamera instances loaded from config."""

    def __init__(self, config: DahuaConfig):
        self.config = config
        self._cameras: dict[str, DahuaCamera] = {}
        for cam_config in config.cameras:
            self._cameras[cam_config.name] = DahuaCamera(
                cam_config, timeout=config.timeout
            )

    def get_camera(self, name: str) -> DahuaCamera:
        """Get a camera by name. Raises ValueError if not found."""
        if name not in self._cameras:
            available = ", ".join(sorted(self._cameras.keys()))
            raise ValueError(
                f"Camera '{name}' not found. Available cameras: {available}"
            )
        return self._cameras[name]

    def list_cameras(self) -> list[dict[str, Any]]:
        """List all cameras (name, host, port, type — no credentials)."""
        return [
            {
                "name": c.config.name,
                "host": c.config.host,
                "port": c.config.port,
                "type": c.config.type,
            }
            for c in self._cameras.values()
        ]

    async def close_all(self):
        for cam in self._cameras.values():
            await cam.close()


def _load_cameras_file(path: str) -> dict:
    """Load cameras config from a JSON or YAML file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Cameras config file not found: {path}")

    text = p.read_text()
    suffix = p.suffix.lower()

    if suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    elif suffix == ".json":
        return json.loads(text)
    else:
        # Try JSON first, fall back to YAML
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return yaml.safe_load(text)


def _find_cameras_config() -> str:
    """Find cameras config file, checking default locations.

    Search order:
    1. DAHUA_CAMERAS_CONFIG env var (if set)
    2. ~/.config/dahua-mcp/cameras.yaml
    3. ~/.config/dahua-mcp/cameras.json
    4. cameras.json in current directory (fallback)
    """
    env_path = os.getenv("DAHUA_CAMERAS_CONFIG")
    if env_path:
        return env_path

    config_dir = Path.home() / ".config" / "dahua-mcp"
    for name in ("cameras.yaml", "cameras.yml", "cameras.json"):
        candidate = config_dir / name
        if candidate.exists():
            return str(candidate)

    return "cameras.json"


def get_dahua_config_from_env() -> DahuaConfig:
    """Load Dahua configuration from environment variables + cameras config file."""
    config_path = _find_cameras_config()
    raw = _load_cameras_file(config_path)

    cameras = [CameraConfig(**cam) for cam in raw.get("cameras", [])]
    if not cameras:
        raise ValueError(f"No cameras defined in {config_path}")

    disabled_tags_str = os.getenv("DISABLED_TAGS", "")
    disabled_tags = set()
    if disabled_tags_str.strip():
        disabled_tags = {
            tag.strip() for tag in disabled_tags_str.split(",") if tag.strip()
        }

    return DahuaConfig(
        cameras=cameras,
        config_path=str(Path(config_path).resolve()),
        timeout=int(os.getenv("DAHUA_TIMEOUT", "20")),
        read_only_mode=parse_bool(os.getenv("READ_ONLY_MODE"), default=False),
        disabled_tags=disabled_tags,
        rate_limit_enabled=parse_bool(os.getenv("RATE_LIMIT_ENABLED"), default=False),
        rate_limit_max_requests=int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "60")),
        rate_limit_window_minutes=int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "1")),
    )


def get_transport_config_from_env() -> TransportConfig:
    """Get transport configuration from environment variables."""
    return TransportConfig(
        transport_type=os.getenv("MCP_TRANSPORT", "stdio").lower(),
        http_host=os.getenv("MCP_HTTP_HOST", "0.0.0.0"),
        http_port=int(os.getenv("MCP_HTTP_PORT", "8000")),
        http_bearer_token=os.getenv("MCP_HTTP_BEARER_TOKEN"),
    )


_camera_manager_singleton: DahuaCameraManager | None = None


def get_camera_manager(config: DahuaConfig | None = None) -> DahuaCameraManager:
    """Get the singleton camera manager instance."""
    global _camera_manager_singleton
    if _camera_manager_singleton is None:
        if config is None:
            raise ValueError("DahuaConfig must be provided for first initialization")
        _camera_manager_singleton = DahuaCameraManager(config)
    return _camera_manager_singleton
