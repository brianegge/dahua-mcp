from pydantic import BaseModel
from pydantic import Field


class CameraConfig(BaseModel):
    name: str = Field(..., description="Unique camera name (e.g. 'front-door')")
    host: str = Field(..., description="Camera hostname or IP address")
    port: int = Field(80, description="HTTP port")
    username: str = Field(..., description="Camera username")
    password: str = Field(..., description="Camera password")
    verify_ssl: bool = Field(False, description="Verify SSL certificates")
    type: str = Field("camera", description="Device type: 'camera' or 'nvr'")


class DahuaConfig(BaseModel):
    cameras: list[CameraConfig] = Field(
        ..., description="List of camera configurations"
    )
    config_path: str = Field("", description="Path to cameras config file")
    timeout: int = Field(20, description="HTTP request timeout in seconds")
    read_only_mode: bool = Field(False, description="Read-only mode (true/false)")
    disabled_tags: set[str] = Field(
        default_factory=set, description="Set of tags to disable tools for"
    )
    rate_limit_enabled: bool = Field(
        False, description="Enable rate limiting (true/false)"
    )
    rate_limit_max_requests: int = Field(60, description="Maximum requests per window")
    rate_limit_window_minutes: int = Field(
        1, description="Rate limit window in minutes"
    )


class TransportConfig(BaseModel):
    """Configuration for MCP transport layer"""

    transport_type: str = Field(
        "stdio",
        description="Transport type: 'stdio', 'sse', or 'http'",
    )
    http_host: str = Field("0.0.0.0", description="Host to bind for HTTP transports")
    http_port: int = Field(8000, description="Port to bind for HTTP transports")
    http_bearer_token: str | None = Field(
        None, description="Bearer token for HTTP authentication"
    )
