"""
Dahua MCP Server Tools
"""

import base64
import contextlib
from typing import Annotated

from fastmcp import Context
from pydantic import Field

from dahua_mcp.dahua_client import DahuaCameraManager


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
    ) -> list[dict]:
        """
        List all configured cameras (name, host, port). No credentials are returned.

        Returns:
            list[dict]: List of camera info dicts.
        """
        try:
            await ctx.info("Listing configured cameras...")
            return manager.list_cameras()
        except Exception as e:
            await ctx.error(f"Error listing cameras: {_error_str(e)}")
            return [{"error": _error_str(e)}]

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
            dict[str, str],
            Field(
                description="Key-value pairs to set (e.g. {'MotionDetect[0].Enable': 'true', 'MotionDetect[0].DetectVersion': 'V3.0'})"
            ),
        ],
        ctx: Context = None,
    ) -> dict:
        """
        Set configuration values on a camera. This is the generic config setter.

        Each key-value pair is sent as a setConfig parameter.
        Example: set_config("front-door", {"MotionDetect[0].Enable": "true"})

        Args:
            camera: Camera name from list_cameras.
            params: Dict of config key=value pairs to set.

        Returns:
            dict: Response from the camera (typically contains "OK" on success).
        """
        try:
            await ctx.info(f"Setting config on {camera}: {params}...")
            cam = manager.get_camera(camera)
            param_str = "&".join(f"{k}={v}" for k, v in params.items())
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
        ctx: Context = None,
    ) -> dict:
        """
        Take a JPEG snapshot from a camera. Returns base64-encoded image data.

        Args:
            camera: Camera name from list_cameras.
            channel: Channel number, 1-based (default: 1).

        Returns:
            dict: {"image_base64": "...", "content_type": "image/jpeg", "size_bytes": N}
        """
        try:
            await ctx.info(f"Taking snapshot from {camera} channel {channel}...")
            cam = manager.get_camera(camera)
            data = await cam.get_bytes(f"snapshot.cgi?channel={channel}")
            encoded = base64.b64encode(data).decode("ascii")
            return {
                "image_base64": encoded,
                "content_type": "image/jpeg",
                "size_bytes": len(data),
            }
        except Exception as e:
            await ctx.error(f"Error taking snapshot: {_error_str(e)}")
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
            lt = log_type or "All"

            # Step 1: startFind
            start_resp = await cam.get_raw(
                f"log.cgi?action=startFind&condition.Channel=0&condition.Types=[{lt}]"
                f"&condition.StartTime={start_time}&condition.EndTime={end_time}"
            )
            # Extract token from response
            token = None
            for line in start_resp.strip().splitlines():
                if "token" in line.lower() and "=" in line:
                    token = line.split("=", 1)[1].strip()
                    break

            if not token:
                return {
                    "error": "Failed to start log search — no token returned",
                    "raw": start_resp,
                }

            # Step 2: doFind
            find_resp = await cam.get_parsed(
                f"log.cgi?action=doFind&token={token}&count={count}"
            )

            # Step 3: stopFind (best-effort cleanup)
            with contextlib.suppress(Exception):
                await cam.get_raw(f"log.cgi?action=stopFind&token={token}")

            return find_resp
        except Exception as e:
            await ctx.error(f"Error searching logs: {_error_str(e)}")
            return {"error": _error_str(e)}
