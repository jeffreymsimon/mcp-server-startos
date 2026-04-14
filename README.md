# mcp-server-startos

MCP (Model Context Protocol) server for [StartOS](https://start9.com) — exposes `start-cli` commands as MCP tools for use with Claude Code, Claude Desktop, and other MCP clients.

**53 tools** covering packages, server diagnostics, networking, registry, backups, database, SSH keys, notifications, and multi-host fleet operations.

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

### Packages (read-only)

| Tool | Description |
|---|---|
| `package_list` | List installed packages (JSON) |
| `package_logs` | Recent logs for a package |
| `package_stats` | LXC container stats — CPU, memory, PIDs (JSON) |
| `package_installed_version` | Installed version of a package |
| `package_action_get_input` | Get action form schema — discover required inputs before running an action (JSON) |
| `package_attach` | Execute a command inside a package's LXC container (like `docker exec`) |
| `package_host_address_list` | List network host addresses for a package |
| `package_host_binding_list` | List network host bindings for a package |

### Packages (mutating)

| Tool | Description |
|---|---|
| `package_install` | Install from .s9pk file |
| `package_uninstall` | Uninstall a package |
| `package_start` | Start a package |
| `package_stop` | Stop a package |
| `package_restart` | Restart a package |
| `package_action_run` | Run a package action |
| `package_rebuild` | Rebuild a package's LXC container |

### Server

| Tool | Description |
|---|---|
| `server_device_info` | Hostname, platform, architecture, StartOS version (JSON) |
| `server_metrics` | CPU, memory, disk, temperature (JSON) |
| `server_time` | Server time and uptime |
| `server_logs` | OS logs |
| `server_kernel_logs` | Kernel logs |
| `server_state` | Full API specification / system state schema |
| `server_cpu_governor` | CPU governor options |

### Network

| Tool | Description |
|---|---|
| `net_dns_table` | DNS resolution table |
| `net_dns_query` | Test DNS resolution for an FQDN (JSON) |
| `net_dns_set_static` | Set static DNS servers |
| `net_forward_table` | Port forward table |
| `net_vhost_table` | Vhost proxy table |
| `net_vhost_list_passthrough` | List SNI-based TLS passthrough rules (JSON) |
| `net_vhost_add_passthrough` | Add a vhost SSL passthrough rule |
| `net_vhost_remove_passthrough` | Remove a vhost SSL passthrough rule |
| `net_gateway_list` | List network gateways (JSON) |
| `net_gateway_check_port` | Check if a port is WAN-reachable on a gateway (JSON) |
| `net_gateway_check_dns` | Check DNS configuration for a gateway (JSON) |
| `net_tunnel_add` | Add a WireGuard tunnel |
| `net_tunnel_remove` | Remove a tunnel |

### Registry / Marketplace

| Tool | Description |
|---|---|
| `registry_index` | List all packages and categories in the registry (JSON) |
| `registry_package_get` | Get installation candidates for a package (JSON) |
| `registry_package_index` | List packages with categories (JSON) |
| `registry_metrics` | Registry usage metrics (JSON) |

### Backups

| Tool | Description |
|---|---|
| `backup_target_list` | List available backup targets |
| `backup_target_info` | Detailed backup info for a package on a target (JSON) |
| `backup_create` | Create a backup |

### Database

| Tool | Description |
|---|---|
| `db_dump` | Dump system database, optionally filtered by path (JSON) |
| `db_apply` | Apply a patch expression to the database |

### SSH Keys

| Tool | Description |
|---|---|
| `ssh_list` | List authorized SSH keys |
| `ssh_add` | Add an SSH public key |
| `ssh_remove` | Remove an SSH key |

### Notifications

| Tool | Description |
|---|---|
| `notification_list` | List notifications |
| `notification_mark_seen` | Mark notifications as seen |
| `notification_remove` | Remove notifications |

### Fleet Operations

Run queries across multiple StartOS hosts in parallel:

| Tool | Description |
|---|---|
| `fleet_device_info` | Device info from multiple hosts |
| `fleet_metrics` | Server metrics from multiple hosts |
| `fleet_package_list` | Package lists from multiple hosts |

### Multi-host support

Every tool accepts an optional `host` parameter to target a specific StartOS server. If omitted, uses the default host from `~/.startos/config.yaml`.

```
# In Claude Code:
# "List packages on haz1upstart001"
# → calls package_list(host="http://haz1upstart001.local")
#
# "Compare packages across all hosts"
# → calls fleet_package_list(hosts=["http://host1.local", "http://host2.local", ...])
```

## License

MIT
