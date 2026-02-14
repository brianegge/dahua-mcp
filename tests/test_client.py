import json
from unittest.mock import AsyncMock

import httpx
import pytest
import yaml

from dahua_mcp.dahua_client import DahuaCamera
from dahua_mcp.dahua_client import DahuaCameraManager
from dahua_mcp.dahua_client import _find_cameras_config
from dahua_mcp.dahua_client import _load_cameras_file
from dahua_mcp.models import CameraConfig
from dahua_mcp.models import DahuaConfig


class TestLoadCamerasFile:
    def test_load_json(self, tmp_path):
        config = {
            "cameras": [
                {
                    "name": "test-cam",
                    "host": "192.168.1.100",
                    "username": "admin",
                    "password": "pass",
                }
            ]
        }
        f = tmp_path / "cameras.json"
        f.write_text(json.dumps(config))
        result = _load_cameras_file(str(f))
        assert result["cameras"][0]["name"] == "test-cam"

    def test_load_yaml(self, tmp_path):
        config = {
            "cameras": [
                {
                    "name": "test-cam",
                    "host": "192.168.1.100",
                    "username": "admin",
                    "password": "pass",
                }
            ]
        }
        f = tmp_path / "cameras.yaml"
        f.write_text(yaml.dump(config))
        result = _load_cameras_file(str(f))
        assert result["cameras"][0]["name"] == "test-cam"

    def test_load_yml_extension(self, tmp_path):
        config = {
            "cameras": [
                {
                    "name": "test-cam",
                    "host": "192.168.1.100",
                    "username": "admin",
                    "password": "pass",
                }
            ]
        }
        f = tmp_path / "cameras.yml"
        f.write_text(yaml.dump(config))
        result = _load_cameras_file(str(f))
        assert result["cameras"][0]["name"] == "test-cam"

    def test_load_unknown_extension_json(self, tmp_path):
        config = {
            "cameras": [{"name": "c", "host": "h", "username": "u", "password": "p"}]
        }
        f = tmp_path / "cameras.conf"
        f.write_text(json.dumps(config))
        result = _load_cameras_file(str(f))
        assert result["cameras"][0]["name"] == "c"

    def test_load_unknown_extension_yaml(self, tmp_path):
        config = {
            "cameras": [{"name": "c", "host": "h", "username": "u", "password": "p"}]
        }
        f = tmp_path / "cameras.conf"
        f.write_text(yaml.dump(config))
        result = _load_cameras_file(str(f))
        assert result["cameras"][0]["name"] == "c"

    def test_file_not_found(self):
        import pytest

        with pytest.raises(FileNotFoundError):
            _load_cameras_file("/nonexistent/path/cameras.json")


class TestFindCamerasConfig:
    def test_env_var_takes_priority(self, monkeypatch, tmp_path):
        custom = tmp_path / "custom.json"
        custom.write_text("{}")
        monkeypatch.setenv("DAHUA_CAMERAS_CONFIG", str(custom))
        assert _find_cameras_config() == str(custom)

    def test_finds_yaml_in_config_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DAHUA_CAMERAS_CONFIG", raising=False)
        config_dir = tmp_path / ".config" / "dahua-mcp"
        config_dir.mkdir(parents=True)
        (config_dir / "cameras.yaml").write_text("cameras: []")
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _find_cameras_config() == str(config_dir / "cameras.yaml")

    def test_finds_json_in_config_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DAHUA_CAMERAS_CONFIG", raising=False)
        config_dir = tmp_path / ".config" / "dahua-mcp"
        config_dir.mkdir(parents=True)
        (config_dir / "cameras.json").write_text('{"cameras": []}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _find_cameras_config() == str(config_dir / "cameras.json")

    def test_yaml_preferred_over_json(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DAHUA_CAMERAS_CONFIG", raising=False)
        config_dir = tmp_path / ".config" / "dahua-mcp"
        config_dir.mkdir(parents=True)
        (config_dir / "cameras.yaml").write_text("cameras: []")
        (config_dir / "cameras.json").write_text('{"cameras": []}')
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _find_cameras_config() == str(config_dir / "cameras.yaml")

    def test_falls_back_to_cwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("DAHUA_CAMERAS_CONFIG", raising=False)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        assert _find_cameras_config() == "cameras.json"


class TestDahuaCameraManager:
    def _make_config(self):
        return DahuaConfig(
            cameras=[
                CameraConfig(
                    name="cam1",
                    host="192.168.1.10",
                    username="admin",
                    password="pass",
                ),
                CameraConfig(
                    name="cam2",
                    host="192.168.1.11",
                    username="admin",
                    password="pass",
                ),
            ]
        )

    def test_list_cameras(self):
        mgr = DahuaCameraManager(self._make_config())
        cameras = mgr.list_cameras()
        assert len(cameras) == 2
        assert cameras[0]["name"] == "cam1"
        assert cameras[1]["name"] == "cam2"
        # No credentials in output
        assert "username" not in cameras[0]
        assert "password" not in cameras[0]

    def test_get_camera(self):
        mgr = DahuaCameraManager(self._make_config())
        cam = mgr.get_camera("cam1")
        assert cam.config.host == "192.168.1.10"

    def test_get_camera_not_found(self):
        import pytest

        mgr = DahuaCameraManager(self._make_config())
        with pytest.raises(ValueError, match="Camera 'unknown' not found"):
            mgr.get_camera("unknown")

    def test_https_for_port_443(self):
        config = DahuaConfig(
            cameras=[
                CameraConfig(
                    name="secure",
                    host="192.168.1.10",
                    port=443,
                    username="admin",
                    password="pass",
                ),
            ]
        )
        mgr = DahuaCameraManager(config)
        cam = mgr.get_camera("secure")
        assert cam.base_url.startswith("https://")


class TestDahuaCameraAuthFallback:
    def _make_camera(self):
        config = CameraConfig(
            name="test-cam",
            host="192.168.1.100",
            username="admin",
            password="pass",
        )
        return DahuaCamera(config)

    @pytest.mark.asyncio
    async def test_starts_with_digest_auth(self):
        cam = self._make_camera()
        assert cam._use_basic_auth is False
        await cam._ensure_client()
        assert isinstance(cam.client.auth, httpx.DigestAuth)
        await cam.close()

    @pytest.mark.asyncio
    async def test_fallback_to_basic_on_401(self):
        cam = self._make_camera()
        await cam._ensure_client()

        resp_401 = httpx.Response(401, request=httpx.Request("GET", "http://test"))
        resp_200 = httpx.Response(
            200, request=httpx.Request("GET", "http://test"), text="OK"
        )

        # Mock the first client's get to return 401
        cam.client.get = AsyncMock(return_value=resp_401)

        # Patch _recreate_client_with_basic to swap auth but keep mock client
        async def mock_recreate():
            cam._use_basic_auth = True
            cam.client.auth = httpx.BasicAuth(cam.config.username, cam.config.password)
            # After switching, the next get should succeed
            cam.client.get = AsyncMock(return_value=resp_200)

        cam._recreate_client_with_basic = mock_recreate

        resp = await cam._get("magicBox.cgi", {"action": "getDeviceType"})
        assert resp.status_code == 200
        assert cam._use_basic_auth is True
        assert isinstance(cam.client.auth, httpx.BasicAuth)
        await cam.close()

    @pytest.mark.asyncio
    async def test_no_fallback_when_already_basic(self):
        cam = self._make_camera()
        cam._use_basic_auth = True
        await cam._ensure_client()

        # Basic auth also returns 401 — should raise, not retry
        resp_401 = httpx.Response(401, request=httpx.Request("GET", "http://test"))
        cam.client.get = AsyncMock(return_value=resp_401)

        with pytest.raises(RuntimeError, match="HTTP 401"):
            await cam._get("magicBox.cgi", {"action": "getDeviceType"})
        await cam.close()

    @pytest.mark.asyncio
    async def test_digest_auth_succeeds_no_fallback(self):
        cam = self._make_camera()
        await cam._ensure_client()

        resp_200 = httpx.Response(
            200, request=httpx.Request("GET", "http://test"), text="OK"
        )
        cam.client.get = AsyncMock(return_value=resp_200)

        resp = await cam._get("magicBox.cgi", {"action": "getDeviceType"})
        assert resp.status_code == 200
        assert cam._use_basic_auth is False
        assert isinstance(cam.client.auth, httpx.DigestAuth)
        await cam.close()
