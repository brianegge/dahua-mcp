import json

import yaml

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
