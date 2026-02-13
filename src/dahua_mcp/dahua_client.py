import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from dahua_mcp.models import CameraConfig
from dahua_mcp.models import DahuaConfig
from dahua_mcp.models import TransportConfig
from dahua_mcp.utils import parse_bool
from dahua_mcp.utils import parse_dahua_response

logger = logging.getLogger(__name__)


class DahuaCamera:
    """Async client for a single Dahua/Amcrest camera using HTTP Digest Auth."""

    def __init__(self, config: CameraConfig, timeout: int = 20):
        self.config = config
        self.timeout = timeout
        protocol = "https" if config.port == 443 else "http"
        self.base_url = f"{protocol}://{config.host}:{config.port}"
        self.client: httpx.AsyncClient | None = None

    async def _ensure_client(self):
        if self.client is None:
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                auth=httpx.DigestAuth(self.config.username, self.config.password),
                verify=self.config.verify_ssl,
                timeout=self.timeout,
            )

    async def close(self):
        if self.client is not None:
            await self.client.aclose()
            self.client = None

    async def get_parsed(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict:
        """GET a CGI endpoint and parse key=value response into a dict."""
        await self._ensure_client()
        url = f"/cgi-bin/{endpoint}"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return parse_dahua_response(resp.text)

    async def get_raw(self, endpoint: str, params: dict[str, Any] | None = None) -> str:
        """GET a CGI endpoint and return raw text."""
        await self._ensure_client()
        url = f"/cgi-bin/{endpoint}"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.text

    async def get_bytes(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> bytes:
        """GET a CGI endpoint and return raw bytes (e.g. snapshot JPEG)."""
        await self._ensure_client()
        url = f"/cgi-bin/{endpoint}"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.content


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
        """List all cameras (name, host, port only — no credentials)."""
        return [
            {"name": c.config.name, "host": c.config.host, "port": c.config.port}
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
