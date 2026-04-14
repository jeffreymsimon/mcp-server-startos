"""MCP server for StartOS — exposes start-cli commands as MCP tools."""

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from .cli import run_cli, run_cli_json

mcp = FastMCP("startos")


# ---------------------------------------------------------------------------
# Read-only: Packages
# ---------------------------------------------------------------------------


@mcp.tool(description="List all installed packages on a StartOS host. Returns JSON with package IDs, titles, versions, and status.")
async def package_list(host: str | None = None) -> dict | list:
    return await run_cli_json("package", "list", host=host)


@mcp.tool(description="Show recent logs for a specific package. Returns log text lines.")
async def package_logs(
    package_id: str,
    limit: int = 50,
    host: str | None = None,
) -> str:
    return await run_cli("package", "logs", package_id, "-l", str(limit), host=host, timeout=15)


@mcp.tool(description="Show LXC container stats (CPU, memory, PIDs) for installed packages. Returns JSON.")
async def package_stats(host: str | None = None) -> dict | list:
    return await run_cli_json("package", "stats", host=host)


@mcp.tool(description="Get the installed version of a specific package.")
async def package_installed_version(package_id: str, host: str | None = None) -> str:
    return (await run_cli("package", "installed-version", package_id, host=host)).strip()


@mcp.tool(description="Get the input specification (form schema) for a package action. Returns JSON describing the fields, types, defaults, and validation rules. Use this before package_action_run to understand what inputs an action expects.")
async def package_action_get_input(
    package_id: str,
    action_id: str,
    host: str | None = None,
) -> dict | list:
    return await run_cli_json("package", "action", "get-input", package_id, action_id, host=host)


@mcp.tool(description="Execute a command inside a running package's LXC container. Equivalent to 'docker exec'. Use for debugging: check configs, query databases, inspect processes inside the container.")
async def package_attach(
    package_id: str,
    command: list[str],
    subcontainer: str | None = None,
    user: str | None = None,
    host: str | None = None,
) -> str:
    args = ["package", "attach", package_id]
    if subcontainer:
        args.extend(["-s", subcontainer])
    if user:
        args.extend(["-u", user])
    args.extend(command)
    return await run_cli(*args, host=host, timeout=60)


@mcp.tool(description="List network host addresses for a package (domain names, bindings).")
async def package_host_address_list(
    package_id: str,
    host_id: str,
    host: str | None = None,
) -> str:
    return await run_cli("package", "host", package_id, "address", host_id, "list", host=host)


@mcp.tool(description="List network host bindings for a package (port/protocol mappings).")
async def package_host_binding_list(
    package_id: str,
    host_id: str,
    host: str | None = None,
) -> str:
    return await run_cli("package", "host", package_id, "binding", host_id, "list", host=host)


# ---------------------------------------------------------------------------
# Read-only: Server
# ---------------------------------------------------------------------------


@mcp.tool(description="Get device information (hostname, platform, architecture, StartOS version). Returns JSON.")
async def server_device_info(host: str | None = None) -> dict | list:
    return await run_cli_json("server", "device-info", host=host)


@mcp.tool(description="Get server metrics (CPU, memory, disk usage, temperature). Returns JSON.")
async def server_metrics(host: str | None = None) -> dict | list:
    return await run_cli_json("server", "metrics", host=host)


@mcp.tool(description="Get server time and uptime.")
async def server_time(host: str | None = None) -> str:
    return (await run_cli("server", "time", host=host)).strip()


@mcp.tool(description="Show recent OS logs from the StartOS server.")
async def server_logs(limit: int = 50, host: str | None = None) -> str:
    return await run_cli("server", "logs", "-l", str(limit), host=host, timeout=15)


@mcp.tool(description="Show recent kernel logs from the StartOS server.")
async def server_kernel_logs(limit: int = 50, host: str | None = None) -> str:
    return await run_cli("server", "kernel-logs", "-l", str(limit), host=host, timeout=15)


@mcp.tool(description="Display the full API specification / system state schema.")
async def server_state(host: str | None = None) -> str:
    return await run_cli("state", host=host, timeout=15)


@mcp.tool(description="Show CPU governor options for the server.")
async def server_cpu_governor(host: str | None = None) -> str:
    return await run_cli("server", "experimental", "governor", host=host)


# ---------------------------------------------------------------------------
# Read-only: Network
# ---------------------------------------------------------------------------


@mcp.tool(description="Dump the DNS address resolution table.")
async def net_dns_table(host: str | None = None) -> str:
    return await run_cli("net", "dns", "dump-table", host=host)


@mcp.tool(description="Test DNS resolution for a specific fully-qualified domain name through the StartOS resolver.")
async def net_dns_query(fqdn: str, host: str | None = None) -> dict | list:
    return await run_cli_json("net", "dns", "query", fqdn, host=host)


@mcp.tool(description="Dump the port forward table.")
async def net_forward_table(host: str | None = None) -> str:
    return await run_cli("net", "forward", "dump-table", host=host)


@mcp.tool(description="Dump the vhost proxy table.")
async def net_vhost_table(host: str | None = None) -> str:
    return await run_cli("net", "vhost", "dump-table", host=host)


@mcp.tool(description="List vhost SSL passthroughs (SNI-based TLS forwarding rules). Returns JSON.")
async def net_vhost_list_passthrough(host: str | None = None) -> dict | list:
    return await run_cli_json("net", "vhost", "list-passthrough", host=host)


@mcp.tool(description="List network gateways that StartOS can listen on. Returns JSON with gateway IDs, names, and types.")
async def net_gateway_list(host: str | None = None) -> dict | list:
    return await run_cli_json("net", "gateway", "list", host=host)


@mcp.tool(description="Check if a specific port is reachable from the WAN on a given gateway. Useful for verifying port forwarding. Returns JSON.")
async def net_gateway_check_port(
    port: int,
    gateway: str,
    host: str | None = None,
) -> dict | list:
    return await run_cli_json("net", "gateway", "check-port", str(port), gateway, host=host)


@mcp.tool(description="Check DNS configuration for a gateway. Verifies that DNS records resolve correctly for services behind this gateway. Returns JSON.")
async def net_gateway_check_dns(gateway: str, host: str | None = None) -> dict | list:
    return await run_cli_json("net", "gateway", "check-dns", gateway, host=host)


# ---------------------------------------------------------------------------
# Read-only: Notifications & Backups
# ---------------------------------------------------------------------------


@mcp.tool(description="List notifications on the StartOS server.")
async def notification_list(host: str | None = None) -> str:
    return await run_cli("notification", "list", host=host)


@mcp.tool(description="List available backup targets.")
async def backup_target_list(host: str | None = None) -> str:
    return await run_cli("backup", "target", "list", host=host)


@mcp.tool(description="Get detailed backup info for a specific package on a backup target. Requires target ID, server ID, and backup password. Returns JSON.")
async def backup_target_info(
    target_id: str,
    server_id: str,
    password: str,
    host: str | None = None,
) -> dict | list:
    return await run_cli_json(
        "backup", "target", "info", target_id, server_id, password, host=host, timeout=60
    )


# ---------------------------------------------------------------------------
# Read-only: Registry / Marketplace
# ---------------------------------------------------------------------------


@mcp.tool(description="List all packages and categories in a StartOS registry (marketplace). Requires registry URL (e.g. 'https://registry.start9.com'). Returns JSON.")
async def registry_index(registry: str, host: str | None = None) -> dict | list:
    return await run_cli_json("registry", "index", host=host, registry=registry, timeout=30)


@mcp.tool(description="Get installation candidates for a specific package from a registry. Requires registry URL. Returns JSON.")
async def registry_package_get(package_id: str, registry: str, host: str | None = None) -> dict | list:
    return await run_cli_json("registry", "package", "get", package_id, host=host, registry=registry)


@mcp.tool(description="List packages in a registry index with categories. Requires registry URL. Returns JSON.")
async def registry_package_index(registry: str, host: str | None = None) -> dict | list:
    return await run_cli_json("registry", "package", "index", host=host, registry=registry, timeout=30)


@mcp.tool(description="Query registry usage metrics. Requires registry URL. Returns JSON.")
async def registry_metrics(registry: str, host: str | None = None) -> dict | list:
    return await run_cli_json("registry", "metrics", host=host, registry=registry)


# ---------------------------------------------------------------------------
# Read-only: Database
# ---------------------------------------------------------------------------


@mcp.tool(description="Dump the full system database or a filtered subset. The database contains the complete system state. Use path to filter (e.g. 'public' for public state).")
async def db_dump(
    path: str | None = None,
    include_private: bool = False,
    host: str | None = None,
) -> dict | list:
    args = ["db", "dump"]
    if include_private:
        args.append("--include-private")
    if path:
        args.append(path)
    return await run_cli_json(*args, host=host, timeout=30)


# ---------------------------------------------------------------------------
# Read-only: SSH keys
# ---------------------------------------------------------------------------


@mcp.tool(description="List SSH public keys authorized on the StartOS server.")
async def ssh_list(host: str | None = None) -> str:
    return await run_cli("ssh", "list", host=host)


# ---------------------------------------------------------------------------
# Fleet: Multi-host operations
# ---------------------------------------------------------------------------


@mcp.tool(description="Run server_device_info across multiple StartOS hosts in parallel. Provide a list of host URLs. Returns a dict keyed by host with device info or error for each.")
async def fleet_device_info(hosts: list[str]) -> dict:
    async def _query(h: str) -> tuple[str, dict | str]:
        try:
            info = await run_cli_json("server", "device-info", host=h)
            return h, info
        except Exception as e:
            return h, f"error: {e}"

    results = await asyncio.gather(*[_query(h) for h in hosts])
    return dict(results)


@mcp.tool(description="Run server_metrics across multiple StartOS hosts in parallel. Returns a dict keyed by host with metrics or error for each.")
async def fleet_metrics(hosts: list[str]) -> dict:
    async def _query(h: str) -> tuple[str, dict | str]:
        try:
            info = await run_cli_json("server", "metrics", host=h)
            return h, info
        except Exception as e:
            return h, f"error: {e}"

    results = await asyncio.gather(*[_query(h) for h in hosts])
    return dict(results)


@mcp.tool(description="Run package_list across multiple StartOS hosts in parallel. Returns a dict keyed by host with package lists or error for each. Useful for comparing installed packages across a fleet.")
async def fleet_package_list(hosts: list[str]) -> dict:
    async def _query(h: str) -> tuple[str, dict | list | str]:
        try:
            info = await run_cli_json("package", "list", host=h)
            return h, info
        except Exception as e:
            return h, f"error: {e}"

    results = await asyncio.gather(*[_query(h) for h in hosts])
    return dict(results)


# ---------------------------------------------------------------------------
# Mutating: Packages
# ---------------------------------------------------------------------------


@mcp.tool(description="Install a package from a local .s9pk file path.")
async def package_install(s9pk_path: str, host: str | None = None) -> str:
    return await run_cli("package", "install", "-s", s9pk_path, host=host, timeout=300)


@mcp.tool(description="Uninstall a package by ID.")
async def package_uninstall(package_id: str, host: str | None = None) -> str:
    return await run_cli("package", "uninstall", package_id, host=host, timeout=120)


@mcp.tool(description="Start a stopped package.")
async def package_start(package_id: str, host: str | None = None) -> str:
    return await run_cli("package", "start", package_id, host=host, timeout=60)


@mcp.tool(description="Stop a running package.")
async def package_stop(package_id: str, host: str | None = None) -> str:
    return await run_cli("package", "stop", package_id, host=host, timeout=60)


@mcp.tool(description="Restart a package (stop + start).")
async def package_restart(package_id: str, host: str | None = None) -> str:
    return await run_cli("package", "restart", package_id, host=host, timeout=120)


@mcp.tool(description="Run a package action by action ID. Use package_action_get_input first to discover required inputs. Returns the action result.")
async def package_action_run(
    package_id: str,
    action_id: str,
    host: str | None = None,
) -> str:
    return await run_cli(
        "package", "action", "run", package_id, action_id, host=host, timeout=120
    )


@mcp.tool(description="Rebuild a package's LXC container. Useful after configuration changes or container issues.")
async def package_rebuild(package_id: str, host: str | None = None) -> str:
    return await run_cli("package", "rebuild", package_id, host=host, timeout=120)


# ---------------------------------------------------------------------------
# Mutating: Network
# ---------------------------------------------------------------------------


@mcp.tool(description="Add a vhost SSL passthrough rule (SNI-based TLS forwarding).")
async def net_vhost_add_passthrough(
    hostname: str,
    listen_port: int,
    backend: str,
    public_gateway: str | None = None,
    private_ip: str | None = None,
    host: str | None = None,
) -> str:
    args = [
        "net", "vhost", "add-passthrough",
        "--hostname", hostname,
        "--listen-port", str(listen_port),
        "--backend", backend,
    ]
    if public_gateway:
        args.extend(["--public-gateway", public_gateway])
    if private_ip:
        args.extend(["--private-ip", private_ip])
    return await run_cli(*args, host=host)


@mcp.tool(description="Remove a vhost SSL passthrough rule.")
async def net_vhost_remove_passthrough(
    hostname: str,
    host: str | None = None,
) -> str:
    return await run_cli("net", "vhost", "remove-passthrough", hostname, host=host)


@mcp.tool(description="Add a WireGuard tunnel. Provide the WireGuard config file contents and optional gateway type.")
async def net_tunnel_add(
    name: str,
    config: str,
    gateway_type: str | None = None,
    set_as_default_outbound: bool = False,
    host: str | None = None,
) -> str:
    args = ["net", "tunnel", "add", name, config]
    if gateway_type:
        args.append(gateway_type)
    if set_as_default_outbound:
        args.append("--set-as-default-outbound")
    return await run_cli(*args, host=host)


@mcp.tool(description="Remove a tunnel by gateway ID.")
async def net_tunnel_remove(gateway_id: str, host: str | None = None) -> str:
    return await run_cli("net", "tunnel", "remove", gateway_id, host=host)


@mcp.tool(description="Set static DNS servers for the StartOS host.")
async def net_dns_set_static(dns_servers: str, host: str | None = None) -> str:
    return await run_cli("net", "dns", "set-static", dns_servers, host=host)


# ---------------------------------------------------------------------------
# Mutating: Backups
# ---------------------------------------------------------------------------


@mcp.tool(description="Create a backup for all packages to the specified target.")
async def backup_create(target: str, password: str, host: str | None = None) -> str:
    return await run_cli("backup", "create", target, password, host=host, timeout=600)


# ---------------------------------------------------------------------------
# Mutating: Database
# ---------------------------------------------------------------------------


@mcp.tool(description="Apply a patch expression to the system database. Use with caution — this modifies system state directly. The expr is a database patch expression.")
async def db_apply(
    expr: str,
    path: str | None = None,
    host: str | None = None,
) -> str:
    args = ["db", "apply", expr]
    if path:
        args.append(path)
    return await run_cli(*args, host=host, timeout=30)


# ---------------------------------------------------------------------------
# Mutating: SSH keys
# ---------------------------------------------------------------------------


@mcp.tool(description="Add an SSH public key to the StartOS server.")
async def ssh_add(public_key: str, host: str | None = None) -> str:
    return await run_cli("ssh", "add", public_key, host=host)


@mcp.tool(description="Remove an SSH key from the StartOS server by fingerprint or key content.")
async def ssh_remove(key_identifier: str, host: str | None = None) -> str:
    return await run_cli("ssh", "remove", key_identifier, host=host)


# ---------------------------------------------------------------------------
# Mutating: Notifications
# ---------------------------------------------------------------------------


@mcp.tool(description="Mark notifications as seen by their IDs.")
async def notification_mark_seen(notification_ids: list[str], host: str | None = None) -> str:
    return await run_cli("notification", "mark-seen", *notification_ids, host=host)


@mcp.tool(description="Remove notifications by their IDs.")
async def notification_remove(notification_ids: list[str], host: str | None = None) -> str:
    return await run_cli("notification", "remove", *notification_ids, host=host)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
