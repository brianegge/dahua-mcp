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


class TestEncodeConfigValue:
    def test_empty_becomes_space(self):
        """Dahua ignores a bare 'Key='; a space is how a field is cleared."""
        assert encode_config_value("") == "%20"

    def test_none_becomes_space(self):
        assert encode_config_value(None) == "%20"

    def test_spaces_are_encoded_colons_are_not(self):
        assert encode_config_value("1 00:00:00-24:00:00") == "1%2000:00:00-24:00:00"

    def test_structural_characters_are_escaped(self):
        assert encode_config_value("50%") == "50%25"

    def test_non_string_is_coerced(self):
        assert encode_config_value(15) == "15"


class TestBuildConfigQuery:
    def test_keys_are_left_literal(self):
        """Config paths contain [] : . which the firmware needs unencoded."""
        q = build_config_query({"RemoteDevice[0].VideoInputs[0].Name": "Lobby"})
        assert q == "RemoteDevice[0].VideoInputs[0].Name=Lobby"

    def test_multiple_pairs_joined_with_ampersand(self):
        q = build_config_query({"A": "1", "B": "2"})
        assert q == "A=1&B=2"

    def test_empty_value_clears_field(self):
        assert build_config_query({"A.Name": ""}) == "A.Name=%20"


class TestFormatBytes:
    def test_units(self):
        assert format_bytes(512) == "512 B"
        assert format_bytes(7921284939776) == "7.92 TB"
        assert format_bytes(2000324395008) == "2.00 TB"

    def test_zero(self):
        assert format_bytes(0) == "0 B"


STORAGE_SAMPLE = """list.info[0].Detail[0].TotalBytes=2000324395008.000000
list.info[0].Detail[0].UsedBytes=2000324395008.000000
list.info[0].Detail[0].IsError=false
list.info[0].Detail[0].Path=/dev/sda0
list.info[0].Detail[1].TotalBytes=1920311754752.000000
list.info[0].Detail[1].UsedBytes=1920311754752.000000
list.info[0].Detail[1].IsError=false
list.info[0].Detail[1].Path=/dev/sda1
list.info[0].Name=/dev/sda
list.info[0].State=Success
list.info[0].HealthDataFlag=0"""


class TestParseStorageInfo:
    def test_rolls_partitions_into_one_device(self):
        result = parse_storage_info(STORAGE_SAMPLE)
        assert result["device_count"] == 1
        dev = result["devices"][0]
        assert dev["name"] == "/dev/sda"
        assert dev["state"] == "Success"
        assert len(dev["partitions"]) == 2
        assert dev["total_bytes"] == 2000324395008 + 1920311754752
        assert dev["total_human"] == "3.92 TB"

    def test_healthy_when_no_partition_errors(self):
        dev = parse_storage_info(STORAGE_SAMPLE)["devices"][0]
        assert dev["healthy"] is True
        assert dev["partition_errors"] == []

    def test_unhealthy_on_partition_error(self):
        bad = STORAGE_SAMPLE.replace(
            "list.info[0].Detail[1].IsError=false",
            "list.info[0].Detail[1].IsError=true",
        )
        dev = parse_storage_info(bad)["devices"][0]
        assert dev["healthy"] is False
        assert dev["partition_errors"] == ["/dev/sda1"]

    def test_preallocation_note_present_when_full(self):
        """A freshly formatted Dahua disk reports used == total."""
        dev = parse_storage_info(STORAGE_SAMPLE)["devices"][0]
        assert "pre-allocates" in dev["note"]

    def test_no_note_when_space_is_free(self):
        partial = STORAGE_SAMPLE.replace(
            "list.info[0].Detail[0].UsedBytes=2000324395008.000000",
            "list.info[0].Detail[0].UsedBytes=1000000000000.000000",
        )
        dev = parse_storage_info(partial)["devices"][0]
        assert "note" not in dev
        assert dev["free_bytes"] > 0

    def test_empty_response(self):
        assert parse_storage_info("")["device_count"] == 0

    def test_ampersand_raises_rather_than_corrupting(self):
        """Firmware decodes before splitting on '&', so it cannot be escaped."""
        with pytest.raises(ValueError, match="cannot contain"):
            encode_config_value("a&b")

    def test_characters_the_firmware_accepts_once_encoded(self):
        # Confirmed round-tripping on an NV4116-HS.
        assert encode_config_value("a#b") == "a%23b"
        assert encode_config_value("a+b") == "a%2Bb"
        assert encode_config_value("a=b") == "a%3Db"
