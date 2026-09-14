import pytest

from dahua_mcp.utils import build_config_query
from dahua_mcp.utils import encode_config_value
from dahua_mcp.utils import format_bytes
from dahua_mcp.utils import parse_bool
from dahua_mcp.utils import parse_dahua_response
from dahua_mcp.utils import parse_storage_info


class TestParseBool:
    def test_truthy_values(self):
        for val in ("1", "true", "True", "TRUE", "yes", "Yes", "on", "ON"):
            assert parse_bool(val) is True

    def test_falsy_values(self):
        for val in ("0", "false", "False", "no", "off", "anything"):
            assert parse_bool(val) is False

    def test_none_returns_default(self):
        assert parse_bool(None, default=True) is True
        assert parse_bool(None, default=False) is False

    def test_whitespace_stripped(self):
        assert parse_bool("  true  ") is True
        assert parse_bool("  false  ") is False


class TestParseDahuaResponse:
    def test_simple_key_value(self):
        text = "key1=value1\nkey2=value2"
        result = parse_dahua_response(text)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_strips_table_prefix(self):
        text = "table.General.MachineName=Cam4\ntable.MotionDetect[0].Enable=true"
        result = parse_dahua_response(text)
        assert result == {
            "General.MachineName": "Cam4",
            "MotionDetect[0].Enable": "true",
        }

    def test_strips_status_prefix(self):
        text = "status.status.Speaker=Off\nstatus.MoveStatus=Idle"
        result = parse_dahua_response(text)
        assert result == {"status.Speaker": "Off", "MoveStatus": "Idle"}

    def test_value_with_equals(self):
        text = "key=value=with=equals"
        result = parse_dahua_response(text)
        assert result == {"key": "value=with=equals"}

    def test_empty_lines_skipped(self):
        text = "\nkey1=value1\n\nkey2=value2\n"
        result = parse_dahua_response(text)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_line_without_equals(self):
        text = "OK"
        result = parse_dahua_response(text)
        assert result == {"OK": "OK"}

    def test_empty_string(self):
        assert parse_dahua_response("") == {}

    def test_system_info_response(self):
        text = (
            "appAutoStart=true\n"
            "deviceType=IPC-HDW5831R-ZE\n"
            "hardwareVersion=1.00\n"
            "processor=S3LM\n"
            "serialNumber=4X7C5A1ZAG21L3F\n"
        )
        result = parse_dahua_response(text)
        assert result["deviceType"] == "IPC-HDW5831R-ZE"
        assert result["serialNumber"] == "4X7C5A1ZAG21L3F"
        assert result["hardwareVersion"] == "1.00"


class TestReExports:
    """The protocol helpers moved to aiodahua and are re-exported from here.

    aiodahua tests their behaviour exhaustively -- the value-encoding quirks,
    the storage pre-allocation note, the byte formatting. What matters at this
    layer is that the names still resolve and still do the job, so a tool
    importing them does not break.
    """

    def test_encode_config_value_clears_with_a_space(self):
        # Sending an empty value is silently ignored by the firmware.
        assert encode_config_value("") == "%20"

    def test_encode_config_value_still_rejects_ampersand(self):
        with pytest.raises(ValueError, match="&"):
            encode_config_value("Bill & Ted")

    def test_build_config_query_joins_pairs(self):
        assert build_config_query({"General.MachineName": "front door"}) == (
            "General.MachineName=front%20door"
        )

    def test_format_bytes(self):
        assert format_bytes(1_500_000_000) == "1.50 GB"

    def test_parse_storage_info_keeps_the_mcp_shape(self):
        """aiodahua returns the device list; the tool's shape wraps it."""
        text = (
            "list.info[0].Name=/dev/sda\r\n"
            "list.info[0].State=Success\r\n"
            "list.info[0].Detail[0].TotalBytes=1000000000\r\n"
            "list.info[0].Detail[0].UsedBytes=400000000\r\n"
            "list.info[0].Detail[0].Path=/dev/sda0\r\n"
        )
        result = parse_storage_info(text)
        assert result["device_count"] == 1
        device = result["devices"][0]
        assert device["name"] == "/dev/sda"
        assert device["free_human"] == "600.00 MB"
        assert device["healthy"] is True
