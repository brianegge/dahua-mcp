"""
Dahua MCP Server Tools
"""

import asyncio
import base64
import json
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Annotated

from aiodahua import async_discover
from aiodahua import build_config_query
from fastmcp import Context
from pydantic import Field

from dahua_mcp.dahua_client import DahuaCameraManager


def _snapshot_dir() -> Path:
    """Directory snapshots are written to (DAHUA_SNAPSHOT_DIR, else a temp dir)."""
    path = Path(
        os.getenv("DAHUA_SNAPSHOT_DIR") or Path(tempfile.gettempdir()) / "dahua-mcp"
    )
    path.mkdir(parents=True, exist_ok=True)
    return path


def _error_str(e: Exception) -> str:
    """Format an exception into a useful error string, even if str(e) is empty."""
    msg = str(e)
    if msg:
        return f"{type(e).__name__}: {msg}"
    return f"{type(e).__name__} (no details)"


def register_tools(mcp, config):
    """Register Dahua camera tools with the MCP server"""

    manager = DahuaCameraManager(config)

    ##########################
    # Discovery
    ##########################

    @mcp.tool(
        tags={"dahua", "discovery", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def list_cameras(
        ctx: Context = None,
    ) -> dict:
        """
        List all configured cameras (name, host, port). No credentials are returned.

        Returns:
            dict: config_path and list of camera info dicts.
        """
        try:
            await ctx.info("Listing configured cameras...")
            return {
                "config_path": config.config_path,
                "cameras": manager.list_cameras(),
            }
        except Exception as e:
            await ctx.error(f"Error listing cameras: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "discovery", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def discover_devices(
        targets: Annotated[
            list[str] | None,
            Field(
                default=None,
                description=(
                    "Addresses to query. Omit to multicast/broadcast on this "
                    "host's own segment. Pass unicast addresses to probe "
                    "specific hosts across a routed network."
                ),
            ),
        ] = None,
        source_ip: Annotated[
            str | None,
            Field(
                default=None,
                description=(
                    "Local address to send from. Required on a multi-homed "
                    "host to aim the query at the camera VLAN."
                ),
            ),
        ] = None,
        mac: Annotated[
            str | None,
            Field(default=None, description="Restrict the query to one MAC."),
        ] = None,
        timeout: Annotated[
            float,
            Field(
                default=3.0, ge=0.5, le=30.0, description="Seconds to collect replies."
            ),
        ] = 3.0,
        ctx: Context = None,
    ) -> dict:
        """
        Find Dahua devices on the network, including ones not in cameras.yaml.

        Uses DHDiscover (UDP 37810), which needs no credentials and answers
        even from a device on the wrong subnet -- so this finds a
        factory-default camera that has no DHCP lease, no ARP entry, and does
        not respond to a ping sweep.

        Scope: a multicast/broadcast query only reaches the sending host's own
        layer-2 segment. To find unknown devices on a camera VLAN, run from a
        host on that VLAN, or pass unicast addresses in `targets`, which do
        follow normal routing.

        Args:
            targets: Addresses to query; defaults to multicast + broadcast.
            source_ip: Local source address, to pick the segment.
            mac: Restrict the query to one device.
            timeout: Seconds to collect replies.

        Returns:
            dict: List of devices with address, model, serial and DHCP state.
                `reachable` is False when a device's own IP does not match
                where it answered from -- i.e. it is on a foreign subnet.
        """
        try:
            await ctx.info("Discovering Dahua devices...")
            devices = await async_discover(
                targets=targets, source_ip=source_ip, mac=mac, timeout=timeout
            )
            return {
                "count": len(devices),
                "devices": [
                    {
                        "mac": d.mac,
                        "ip": d.ip,
                        "netmask": d.netmask,
                        "gateway": d.gateway,
                        "dhcp": d.dhcp,
                        "device_type": d.device_type,
                        "serial": d.serial,
                        "machine_name": d.machine_name,
                        "version": d.version,
                        "http_port": d.http_port,
                        "source_ip": d.source_ip,
                        "reachable": d.reachable,
                    }
                    for d in devices
                ],
            }
        except Exception as e:
            await ctx.error(f"Error discovering devices: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # System Info
    ##########################

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_system_info(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get system info from a Dahua/Amcrest camera (device type, serial number, firmware, etc).

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: System information key-value pairs.
        """
        try:
            await ctx.info(f"Getting system info for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getSystemInfo")
        except Exception as e:
            await ctx.error(f"Error getting system info: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_device_type(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the device type/model of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Device type info (e.g. {"type": "IPC-HDW5831R-ZE"}).
        """
        try:
            await ctx.info(f"Getting device type for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getDeviceType")
        except Exception as e:
            await ctx.error(f"Error getting device type: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_software_version(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the firmware/software version of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Software version info.
        """
        try:
            await ctx.info(f"Getting software version for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getSoftwareVersion")
        except Exception as e:
            await ctx.error(f"Error getting software version: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_machine_name(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the machine name of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Machine name (e.g. {"name": "FrontDoorCam"}).
        """
        try:
            await ctx.info(f"Getting machine name for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getMachineName")
        except Exception as e:
            await ctx.error(f"Error getting machine name: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_serial_number(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the serial number of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Serial number info.
        """
        try:
            await ctx.info(f"Getting serial number for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getSerialNo")
        except Exception as e:
            await ctx.error(f"Error getting serial number: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_hardware_version(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the hardware version of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Hardware version info.
        """
        try:
            await ctx.info(f"Getting hardware version for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getHardwareVersion")
        except Exception as e:
            await ctx.error(f"Error getting hardware version: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "system", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_vendor(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the vendor/manufacturer of a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Vendor info (e.g. {"vendor": "Dahua"}).
        """
        try:
            await ctx.info(f"Getting vendor for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=getVendor")
        except Exception as e:
            await ctx.error(f"Error getting vendor: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # Audio
    ##########################

    @mcp.tool(
        tags={"dahua", "audio", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_audio_capabilities(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get audio capabilities (microphone and speaker) from a camera.

        Returns device type, microphone input source, and speaker output capability.
        Speaker detection uses devAudioOutput.cgi caps endpoint, with model number
        suffix as fallback (AS/ASE = Audio Speaker, PV = Active Deterrence siren).

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Audio capabilities including device_type, mic, and speaker info.
        """
        try:
            await ctx.info(f"Getting audio capabilities for {camera}...")
            cam = manager.get_camera(camera)

            async def _get_system_info():
                return await cam.get_parsed("magicBox.cgi?action=getSystemInfo")

            async def _get_audio_input():
                try:
                    return await cam.get_parsed(
                        "configManager.cgi?action=getConfig&name=AudioInput"
                    )
                except Exception:
                    return None

            async def _get_audio_output():
                try:
                    return await cam.get_parsed("devAudioOutput.cgi?action=getCaps")
                except Exception:
                    return None

            system_info, audio_input, audio_output = await asyncio.gather(
                _get_system_info(), _get_audio_input(), _get_audio_output()
            )

            device_type = system_info.get("deviceType", "unknown")
            update_serial = system_info.get("updateSerial", "")

            result = {
                "device_type": device_type,
                "update_serial": update_serial,
            }

            # Mic capability
            if audio_input:
                source = audio_input.get("AudioInput[0].AudioSource", "unknown")
                result["mic"] = True
                result["mic_source"] = source
            else:
                result["mic"] = False

            # Speaker capability: check devAudioOutput caps first, then model suffix
            if audio_output:
                result["speaker"] = True
                result["speaker_source"] = "devAudioOutput"
            else:
                # Fallback: check model suffix for speaker indicators
                # AS/ASE = Audio Speaker, PV = Active deterrence (siren/speaker)
                serial_upper = update_serial.upper()
                parts = serial_upper.replace("-", " ").split()
                has_speaker = any(p in ("AS", "ASE", "PV") for p in parts) or any(
                    p.startswith("PV") for p in parts
                )
                result["speaker"] = has_speaker
                if has_speaker:
                    result["speaker_source"] = "model_suffix"

            return result
        except Exception as e:
            await ctx.error(f"Error getting audio capabilities: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # Config Read
    ##########################

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_config(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        name: Annotated[
            str,
            Field(
                description="Config name to retrieve (e.g. 'MotionDetect', 'Encode', 'Network', 'NTP', 'VideoInMode', 'Lighting_V2', 'General.MachineName')"
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get a configuration section from a camera by name.

        This is the generic config getter — use it for any configManager config name.

        Args:
            camera: Camera name from list_cameras.
            name: Config section name (e.g. 'MotionDetect', 'Encode', 'Network').

        Returns:
            dict: Configuration key-value pairs.
        """
        try:
            await ctx.info(f"Getting config '{name}' for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed(
                f"configManager.cgi?action=getConfig&name={name}"
            )
        except Exception as e:
            await ctx.error(f"Error getting config: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_motion_detection(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get motion detection configuration from a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Motion detection config (Enable, DetectVersion, etc).
        """
        try:
            await ctx.info(f"Getting motion detection config for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed(
                "configManager.cgi?action=getConfig&name=MotionDetect"
            )
        except Exception as e:
            await ctx.error(f"Error getting motion detection config: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_video_in_mode(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get the video input mode (day/night profile) from a camera.

        Mode values: 0=day config, 1=night config, 2=normal scene config.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Video input mode config.
        """
        try:
            await ctx.info(f"Getting video input mode for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed(
                "configManager.cgi?action=getConfig&name=VideoInMode"
            )
        except Exception as e:
            await ctx.error(f"Error getting video input mode: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_encoding_config(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get encoding/streaming configuration from a camera (resolution, bitrate, FPS, codec).

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Encoding config key-value pairs.
        """
        try:
            await ctx.info(f"Getting encoding config for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed(
                "configManager.cgi?action=getConfig&name=Encode"
            )
        except Exception as e:
            await ctx.error(f"Error getting encoding config: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_network_config(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get network configuration from a camera (IP, gateway, DNS, etc).

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Network config key-value pairs.
        """
        try:
            await ctx.info(f"Getting network config for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed(
                "configManager.cgi?action=getConfig&name=Network"
            )
        except Exception as e:
            await ctx.error(f"Error getting network config: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_ntp_config(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get NTP (time sync) configuration from a camera.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: NTP config key-value pairs.
        """
        try:
            await ctx.info(f"Getting NTP config for {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("configManager.cgi?action=getConfig&name=NTP")
        except Exception as e:
            await ctx.error(f"Error getting NTP config: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # Config Write
    ##########################

    @mcp.tool(
        tags={"dahua", "config", "write", "destructive"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def set_config(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        params: Annotated[
            str,
            Field(
                description='JSON object of key-value pairs to set (e.g. \'{"MotionDetect[0].Enable": "true"}\')'
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Set configuration values on a camera. This is the generic config setter.

        Each key-value pair is sent as a setConfig parameter. Values are
        percent-encoded, so they may safely contain spaces, "&" or "=".
        Example: set_config("front-door", {"MotionDetect[0].Enable": "true"})

        Pass an empty string to clear a field. Dahua firmware ignores a bare
        "Key=" (it answers OK but changes nothing), so "" is sent as a single
        space, which the device trims back to "".

        Args:
            camera: Camera name from list_cameras.
            params: Dict of config key=value pairs to set.

        Returns:
            dict: Response from the camera (typically contains "OK" on success).
        """
        try:
            parsed = json.loads(params) if isinstance(params, str) else params
            await ctx.info(f"Setting config on {camera}: {parsed}...")
            cam = manager.get_camera(camera)
            param_str = build_config_query(parsed)
            return await cam.get_parsed(
                f"configManager.cgi?action=setConfig&{param_str}"
            )
        except Exception as e:
            await ctx.error(f"Error setting config: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "write"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def enable_motion_detection(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        enabled: Annotated[
            bool,
            Field(description="True to enable, False to disable motion detection"),
        ],
        channel: Annotated[
            int,
            Field(default=0, description="Channel number (default: 0)"),
        ] = 0,
        ctx: Context = None,
    ) -> dict:
        """
        Enable or disable motion detection on a camera channel.

        Args:
            camera: Camera name from list_cameras.
            enabled: True to enable, False to disable.
            channel: Channel number (default: 0).

        Returns:
            dict: Response from the camera.
        """
        try:
            action = "Enabling" if enabled else "Disabling"
            await ctx.info(
                f"{action} motion detection on {camera} channel {channel}..."
            )
            cam = manager.get_camera(camera)
            val = str(enabled).lower()
            return await cam.get_parsed(
                f"configManager.cgi?action=setConfig&MotionDetect[{channel}].Enable={val}&MotionDetect[{channel}].DetectVersion=V3.0"
            )
        except Exception as e:
            await ctx.error(f"Error toggling motion detection: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "config", "write"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def set_record_mode(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        mode: Annotated[
            str,
            Field(description="Record mode: 'auto', 'manual'/'on', or 'off'"),
        ],
        channel: Annotated[
            int,
            Field(default=0, description="Channel number (default: 0)"),
        ] = 0,
        ctx: Context = None,
    ) -> dict:
        """
        Set the recording mode on a camera channel.

        Args:
            camera: Camera name from list_cameras.
            mode: 'auto' (0), 'manual'/'on' (1), or 'off' (2).
            channel: Channel number (default: 0).

        Returns:
            dict: Response from the camera.
        """
        try:
            await ctx.info(f"Setting record mode to '{mode}' on {camera}...")
            cam = manager.get_camera(camera)
            mode_map = {"auto": "0", "manual": "1", "on": "1", "off": "2"}
            mode_val = mode_map.get(mode.lower(), "0")
            return await cam.get_parsed(
                f"configManager.cgi?action=setConfig&RecordMode[{channel}].Mode={mode_val}"
            )
        except Exception as e:
            await ctx.error(f"Error setting record mode: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # System Control
    ##########################

    @mcp.tool(
        tags={"dahua", "system", "write", "destructive"},
        annotations={
            "readOnlyHint": False,
            "destructiveHint": True,
            "idempotentHint": False,
        },
    )
    async def reboot(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Reboot a camera. The camera will be unavailable for 1-2 minutes during restart.

        Args:
            camera: Camera name from list_cameras.

        Returns:
            dict: Response from the camera.
        """
        try:
            await ctx.info(f"Rebooting {camera}...")
            cam = manager.get_camera(camera)
            return await cam.get_parsed("magicBox.cgi?action=reboot")
        except Exception as e:
            await ctx.error(f"Error rebooting: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "snapshot", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def take_snapshot(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        channel: Annotated[
            int,
            Field(
                default=1,
                description="Channel number (default: 1). Note: channel is 1-based for snapshots.",
            ),
        ] = 1,
        return_base64: Annotated[
            bool,
            Field(
                default=False,
                description=(
                    "Also return the image inline as base64. Off by default: a "
                    "4K JPEG is ~1 MB, which is far larger than most model "
                    "context windows allow."
                ),
            ),
        ] = False,
        ctx: Context = None,
    ) -> dict:
        """
        Take a JPEG snapshot and save it to disk, returning the file path.

        A full-resolution snapshot is around a megabyte; returning it inline as
        base64 overflows a typical context window, so by default the image is
        written to DAHUA_SNAPSHOT_DIR (a temp directory if unset) and only the
        path is returned. Set return_base64=True if you genuinely need the bytes
        inline.

        Args:
            camera: Camera name from list_cameras.
            channel: Channel number, 1-based (default: 1).
            return_base64: Include the image inline as base64 (default: False).

        Returns:
            dict: {"path": "...", "content_type": "image/jpeg", "size_bytes": N}
        """
        try:
            await ctx.info(f"Taking snapshot from {camera} channel {channel}...")
            cam = manager.get_camera(camera)
            data = await cam.client.async_get_snapshot(channel)

            safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", camera)
            filename = (
                f"{safe_name}-ch{channel}-{time.strftime('%Y%m%d-%H%M%S')}"
                f"-{uuid.uuid4().hex[:8]}.jpg"
            )
            path = _snapshot_dir() / filename
            path.write_bytes(data)

            result = {
                "path": str(path),
                "content_type": "image/jpeg",
                "size_bytes": len(data),
            }
            if return_base64:
                result["image_base64"] = base64.b64encode(data).decode("ascii")
            return result
        except Exception as e:
            await ctx.error(f"Error taking snapshot: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # Storage / recordings
    ##########################

    @mcp.tool(
        tags={"dahua", "storage", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def get_storage_info(
        camera: Annotated[
            str,
            Field(description="Camera or NVR name from list_cameras"),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Get hard drive status and capacity from a recorder.

        Returns one entry per physical device with its partitions rolled up,
        a total/free capacity, and a "healthy" flag derived from the device
        state plus each partition's error flag.

        Note: a Dahua recorder pre-allocates the whole disk when it formats, so
        used == total even on a brand new drive. That is not a full disk. Use
        find_recordings to confirm footage is actually being written.

        Args:
            camera: Camera or NVR name from list_cameras.

        Returns:
            dict: {"devices": [...], "device_count": N}
        """
        try:
            await ctx.info(f"Getting storage info from {camera}...")
            cam = manager.get_camera(camera)
            devices = await cam.client.async_get_storage_info()
            return {"devices": devices, "device_count": len(devices)}
        except Exception as e:
            await ctx.error(f"Error getting storage info: {_error_str(e)}")
            return {"error": _error_str(e)}

    @mcp.tool(
        tags={"dahua", "storage", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def find_recordings(
        camera: Annotated[
            str,
            Field(description="Camera or NVR name from list_cameras"),
        ],
        start_time: Annotated[
            str,
            Field(description="Start time as 'YYYY-MM-DD HH:MM:SS'"),
        ],
        end_time: Annotated[
            str,
            Field(description="End time as 'YYYY-MM-DD HH:MM:SS'"),
        ],
        channel: Annotated[
            int,
            Field(
                default=1,
                description="Channel number, 1-based (channel 0 is rejected by the firmware)",
            ),
        ] = 1,
        count: Annotated[
            int,
            Field(default=20, description="Max number of files to return"),
        ] = 20,
        ctx: Context = None,
    ) -> dict:
        """
        List recorded video files, to confirm a recorder is really recording.

        Uses the 4-step mediaFileFind API (factory.create / findFile /
        findNextFile / close+destroy). Dahua marks each filename with its
        record type: [R] regular/continuous, [M] motion, [A] alarm.

        Args:
            camera: Camera or NVR name from list_cameras.
            start_time: Start time as 'YYYY-MM-DD HH:MM:SS'.
            end_time: End time as 'YYYY-MM-DD HH:MM:SS'.
            channel: Channel number, 1-based (default: 1).
            count: Max number of files to return (default: 20).

        Returns:
            dict: {"found": N, "channel": N, "files": [{"path", "start_time", ...}]}
        """
        try:
            await ctx.info(
                f"Finding recordings on {camera} channel {channel} "
                f"from {start_time} to {end_time}..."
            )
            cam = manager.get_camera(camera)
            found, files = await cam.client.async_find_recordings(
                start_time, end_time, channel=channel, count=count
            )
            return {"found": found, "channel": channel, "files": files}
        except Exception as e:
            await ctx.error(f"Error finding recordings: {_error_str(e)}")
            return {"error": _error_str(e)}

    ##########################
    # Logs
    ##########################

    @mcp.tool(
        tags={"dahua", "logs", "read-only"},
        annotations={
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
        },
    )
    async def search_logs(
        camera: Annotated[
            str,
            Field(description="Camera name from list_cameras"),
        ],
        start_time: Annotated[
            str,
            Field(
                description="Start time in format 'YYYY-MM-DD HH:MM:SS' (e.g. '2024-01-01 00:00:00')"
            ),
        ],
        end_time: Annotated[
            str,
            Field(
                description="End time in format 'YYYY-MM-DD HH:MM:SS' (e.g. '2024-01-02 00:00:00')"
            ),
        ],
        log_type: Annotated[
            str | None,
            Field(
                default=None,
                description="Log type filter (e.g. 'All', 'Alarm', 'System', 'Account', 'Storage', 'Event', 'Record'). Default: 'All'.",
            ),
        ] = None,
        count: Annotated[
            int,
            Field(
                default=100,
                description="Max number of log entries to return (default: 100)",
            ),
        ] = 100,
        ctx: Context = None,
    ) -> dict:
        """
        Search camera logs using the 3-step log.cgi API (startFind/doFind/stopFind).

        Args:
            camera: Camera name from list_cameras.
            start_time: Start time in 'YYYY-MM-DD HH:MM:SS' format.
            end_time: End time in 'YYYY-MM-DD HH:MM:SS' format.
            log_type: Log type filter (default: 'All').
            count: Max results (default: 100).

        Returns:
            dict: Log entries found.
        """
        try:
            await ctx.info(
                f"Searching logs on {camera} from {start_time} to {end_time}..."
            )
            cam = manager.get_camera(camera)
            entries = await cam.client.async_search_logs(
                start_time, end_time, log_type=log_type or "All", count=count
            )
            return {"count": len(entries), "entries": entries}
        except Exception as e:
            await ctx.error(f"Error searching logs: {_error_str(e)}")
            return {"error": _error_str(e)}
