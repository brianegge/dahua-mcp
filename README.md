# Dahua MCP Server

MCP server for managing Dahua/Amcrest IP cameras via their CGI HTTP API. Supports multiple cameras from a single instance, with both stdio and HTTP transports.

## Quick Start

### 1. Create a cameras config file

Create `cameras.json` or `cameras.yaml` with your camera credentials.

**JSON** (`cameras.json`):
```json
{
  "cameras": [
    {
      "name": "front-door",
      "host": "192.168.1.108",
      "port": 80,
      "username": "admin",
      "password": "secret"
    },
    {
      "name": "backyard",
      "host": "192.168.1.109",
      "port": 80,
      "username": "admin",
      "password": "secret"
    }
  ]
}
```

**YAML** (`cameras.yaml`):
```yaml
cameras:
  - name: front-door
    host: 192.168.1.108
    port: 80
    username: admin
    password: secret
  - name: backyard
    host: 192.168.1.109
    port: 80
    username: admin
    password: secret
```

Each camera entry supports:

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `name` | Yes | — | Unique camera name used in all tool calls |
| `host` | Yes | — | Camera hostname or IP address |
| `port` | No | `80` | HTTP port (`443` auto-enables HTTPS) |
| `username` | Yes | — | Camera username |
| `password` | Yes | — | Camera password |
| `verify_ssl` | No | `false` | Verify SSL certificates |

### 2. Add the MCP server

#### Option A: stdio (Claude Code / Claude Desktop)

Add to your Claude Code settings (`~/.claude.json`) or Claude Desktop config:

```json
{
  "mcpServers": {
    "dahua-mcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["dahua-mcp"],
      "env": {
        "DAHUA_CAMERAS_CONFIG": "/path/to/cameras.json"
      }
    }
  }
}
```

Or run from a local clone:

```json
{
  "mcpServers": {
    "dahua-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--directory", "/path/to/dahua-mcp", "dahua-mcp"],
      "env": {
        "DAHUA_CAMERAS_CONFIG": "/path/to/cameras.json"
      }
    }
  }
}
```

#### Option B: Docker container (HTTP transport)

Run the container with your config file volume-mounted:

```sh
docker run -d \
  -v /path/to/cameras.json:/config/cameras.json:ro \
  -p 8000:8000 \
  ghcr.io/brianegge/dahua-mcp:latest
```

Then add the HTTP server to your MCP client config:

```json
{
  "mcpServers": {
    "dahua-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

To use a YAML config with Docker:

```sh
docker run -d \
  -v /path/to/cameras.yaml:/config/cameras.yaml:ro \
  -e DAHUA_CAMERAS_CONFIG=/config/cameras.yaml \
  -p 8000:8000 \
  ghcr.io/brianegge/dahua-mcp:latest
```

To add bearer token authentication:

```sh
docker run -d \
  -v /path/to/cameras.json:/config/cameras.json:ro \
  -e MCP_HTTP_BEARER_TOKEN=your-secret-token \
  -p 8000:8000 \
  ghcr.io/brianegge/dahua-mcp:latest
```

```json
{
  "mcpServers": {
    "dahua-mcp": {
      "type": "http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-secret-token"
      }
    }
  }
}
```

## Environment Variables

All settings beyond camera credentials are configured via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DAHUA_CAMERAS_CONFIG` | `cameras.json` | Path to cameras config file (JSON or YAML) |
| `DAHUA_TIMEOUT` | `20` | HTTP request timeout in seconds |
| `READ_ONLY_MODE` | `false` | Disable all write tools (reboot, set_config, etc.) |
| `DISABLED_TAGS` | — | Comma-separated tags to disable (e.g. `destructive,write`) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `RATE_LIMIT_MAX_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW_MINUTES` | `1` | Rate limit window in minutes |
| `MCP_TRANSPORT` | `stdio` | Transport type: `stdio`, `sse`, or `http` |
| `MCP_HTTP_HOST` | `0.0.0.0` | HTTP bind host |
| `MCP_HTTP_PORT` | `8000` | HTTP bind port |
| `MCP_HTTP_BEARER_TOKEN` | — | Optional bearer token for HTTP auth |

## Available Tools

### Discovery

| Tool | Description | Read-Only |
|------|-------------|-----------|
| `list_cameras` | List all configured cameras (name, host, port) | Yes |

### System Info

| Tool | Description | Read-Only |
|------|-------------|-----------|
| `get_system_info` | Get full system info (device type, serial, firmware, etc.) | Yes |
| `get_device_type` | Get the device type/model | Yes |
| `get_software_version` | Get firmware version | Yes |
| `get_machine_name` | Get the camera's machine name | Yes |
| `get_serial_number` | Get the serial number | Yes |
| `get_hardware_version` | Get the hardware version | Yes |
| `get_vendor` | Get the vendor/manufacturer | Yes |

### Config Read

| Tool | Description | Read-Only |
|------|-------------|-----------|
| `get_config` | Get any config section by name | Yes |
| `get_motion_detection` | Get motion detection config | Yes |
| `get_video_in_mode` | Get video input mode (day/night profile) | Yes |
| `get_encoding_config` | Get encoding/streaming config | Yes |
| `get_network_config` | Get network config (IP, gateway, DNS) | Yes |
| `get_ntp_config` | Get NTP time sync config | Yes |

### Config Write

| Tool | Description | Destructive |
|------|-------------|-------------|
| `set_config` | Set arbitrary config key-value pairs | Yes |
| `enable_motion_detection` | Enable/disable motion detection | No |
| `set_record_mode` | Set recording mode (auto/manual/off) | No |

### System Control

| Tool | Description | Destructive |
|------|-------------|-------------|
| `reboot` | Reboot the camera | Yes |
| `take_snapshot` | Take a JPEG snapshot (base64) | No |

### Logs

| Tool | Description | Read-Only |
|------|-------------|-----------|
| `search_logs` | Search camera logs by time range and type | Yes |

## Development

```sh
git clone https://github.com/brianegge/dahua-mcp.git
cd dahua-mcp
uv sync
uv run pre-commit install  # Install ruff format/lint hook
uv run pytest              # Run tests
uv run ruff check .        # Lint
```

## License

MIT License - see LICENSE file for details.
