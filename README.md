# mcp-server-startos

MCP (Model Context Protocol) server for [StartOS](https://start9.com) — exposes `start-cli` commands as MCP tools for use with Claude Code, Claude Desktop, and other MCP clients.

## Requirements

- Python 3.10+
- `start-cli` 0.4.0-beta.5+ installed and authenticated to at least one StartOS host
- An MCP client (e.g., Claude Code)

## Installation

### Claude Code (recommended)

```bash
claude mcp add startos -- uv --directory /path/to/mcp-server-startos run mcp-server-startos
```

### Manual (settings.json)

```json
{
  "mcpServers": {
    "startos": {
      "command": "uv",
      "args": ["--directory", "/path/to/mcp-server-startos", "run", "mcp-server-startos"]
    }
  }
}
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `START_CLI_PATH` | auto-detect | Path to the `start-cli` binary |

## Tools

### Read-only

| Tool | Description |
|---|---|
| `package_list` | List installed packages (JSON) |
| `package_logs` | Recent logs for a package |
| `package_stats` | LXC container stats (JSON) |
| `package_installed_version` | Installed version of a package |
| `server_device_info` | Device info: hostname, arch, OS version (JSON) |
| `server_metrics` | CPU, memory, disk, temperature (JSON) |
| `server_time` | Server time and uptime |
| `server_logs` | OS logs |
| `server_kernel_logs` | Kernel logs |
| `net_dns_table` | DNS resolution table |
| `net_forward_table` | Port forward table |
| `net_vhost_table` | Vhost proxy table |
| `notification_list` | Server notifications |
| `backup_target_list` | Available backup targets |

### Mutating

| Tool | Description |
|---|---|
| `package_install` | Install from .s9pk file |
| `package_uninstall` | Uninstall a package |
| `package_start` | Start a package |
| `package_stop` | Stop a package |
| `package_restart` | Restart a package |
| `package_action_run` | Run a package action |
| `backup_create` | Create a backup |
| `db_dump` | Dump database contents |

### Multi-host support

Every tool accepts an optional `host` parameter to target a specific StartOS server. If omitted, uses the default host from `~/.startos/config.yaml`.

```
# In Claude Code:
# "List packages on haz1upstart001"
# → calls package_list(host="http://haz1upstart001.local")
```

## License

MIT
