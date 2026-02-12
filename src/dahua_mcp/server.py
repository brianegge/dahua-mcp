#!/usr/bin/env python3
"""
Dahua MCP Server

Provides a Model Context Protocol (MCP) server exposing tools that interact with
Dahua/Amcrest IP cameras via their CGI HTTP API.
"""

import logging
import os
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp.server.middleware.rate_limiting import SlidingWindowRateLimitingMiddleware

from dahua_mcp.dahua_client import get_dahua_config_from_env
from dahua_mcp.dahua_client import get_transport_config_from_env
from dahua_mcp.dahua_middlewares import DisabledTagsMiddleware
from dahua_mcp.dahua_middlewares import ReadOnlyTagMiddleware
from dahua_mcp.dahua_tools import register_tools

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get package version
try:
    __version__ = version("dahua-mcp")
except PackageNotFoundError:
    __version__ = "0.0.1"

try:
    DAHUA_CONFIG = get_dahua_config_from_env()
    TRANSPORT_CONFIG = get_transport_config_from_env()
except Exception as e:
    logger.error(f"Invalid configuration: {e}")
    raise

# Create auth provider if bearer token is configured
auth_provider = None
if getattr(TRANSPORT_CONFIG, "http_bearer_token", None):
    auth_provider = StaticTokenVerifier(
        tokens={
            TRANSPORT_CONFIG.http_bearer_token: {
                "client_id": "authenticated-client",
                "scopes": ["read", "write"],
            }
        }
    )

# Initialize FastMCP server
mcp = FastMCP(
    name="Dahua MCP Server",
    version=__version__,
    instructions=(
        "This MCP server exposes tools for managing Dahua/Amcrest IP cameras "
        "via their CGI HTTP API. Use list_cameras to discover available cameras, "
        "then use camera-specific tools with the camera name."
    ),
    auth=auth_provider,
)

# Register all tools
register_tools(mcp, DAHUA_CONFIG)

# Apply disabled tags middleware if any tags are disabled
if getattr(DAHUA_CONFIG, "disabled_tags", set()):
    logger.info(
        f"Disabled tags configured: {DAHUA_CONFIG.disabled_tags} - applying middleware"
    )
    mcp.add_middleware(DisabledTagsMiddleware(DAHUA_CONFIG.disabled_tags))

# Enforce read-only behavior via middleware
if getattr(DAHUA_CONFIG, "read_only_mode", False):
    logger.info("Read-only mode is enabled - applying middleware")
    mcp.add_middleware(ReadOnlyTagMiddleware())

# Optional rate limiting
if getattr(DAHUA_CONFIG, "rate_limit_enabled", False):
    logger.info("Rate limiting is enabled - applying middleware")
    mcp.add_middleware(
        SlidingWindowRateLimitingMiddleware(
            max_requests=DAHUA_CONFIG.rate_limit_max_requests,
            window_minutes=DAHUA_CONFIG.rate_limit_window_minutes,
        )
    )


def main():
    camera_count = len(DAHUA_CONFIG.cameras)
    logger.info(f"Starting Dahua MCP Server with {camera_count} camera(s)...")

    # Choose transport based on configuration
    if TRANSPORT_CONFIG.transport_type == "sse":
        logger.info(
            f"Using HTTP SSE transport on {TRANSPORT_CONFIG.http_host}:{TRANSPORT_CONFIG.http_port}"
        )
        mcp.run(
            transport="sse",
            host=TRANSPORT_CONFIG.http_host,
            port=TRANSPORT_CONFIG.http_port,
        )
    elif TRANSPORT_CONFIG.transport_type == "http":
        logger.info(
            f"Using HTTP Streamable transport on {TRANSPORT_CONFIG.http_host}:{TRANSPORT_CONFIG.http_port}"
        )
        mcp.run(
            transport="http",
            host=TRANSPORT_CONFIG.http_host,
            port=TRANSPORT_CONFIG.http_port,
        )
    else:
        # Default to STDIO transport
        logger.info("Using STDIO transport")
        mcp.run()


if __name__ == "__main__":
    main()
