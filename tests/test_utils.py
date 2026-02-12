from dahua_mcp.utils import parse_bool
from dahua_mcp.utils import parse_dahua_response


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
