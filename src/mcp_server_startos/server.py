"""MCP server for StartOS — exposes start-cli commands as MCP tools."""

from mcp.server.fastmcp import FastMCP

from .cli import run_cli, run_cli_json

mcp = FastMCP("startos")


# ---------------------------------------------------------------------------
# Read-only tools
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
    return await run_cli("diagnostic", "logs", "-l", str(limit), host=host, timeout=15)


@mcp.tool(description="Show recent kernel logs from the StartOS server.")
async def server_kernel_logs(limit: int = 50, host: str | None = None) -> str:
    return await run_cli("diagnostic", "kernel-logs", "-l", str(limit), host=host, timeout=15)


@mcp.tool(description="Dump the DNS address resolution table.")
async def net_dns_table(host: str | None = None) -> str:
    return await run_cli("net", "dns", "dump-table", host=host)


@mcp.tool(description="Dump the port forward table.")
async def net_forward_table(host: str | None = None) -> str:
    return await run_cli("net", "forward", "dump-table", host=host)


@mcp.tool(description="Dump the vhost proxy table.")
async def net_vhost_table(host: str | None = None) -> str:
    return await run_cli("net", "vhost", "dump-table", host=host)


@mcp.tool(description="List notifications on the StartOS server.")
async def notification_list(host: str | None = None) -> str:
    return await run_cli("notification", "list", host=host)


@mcp.tool(description="List available backup targets.")
async def backup_target_list(host: str | None = None) -> str:
    return await run_cli("backup", "target", "list", host=host)


# ---------------------------------------------------------------------------
# Mutating tools
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


@mcp.tool(description="Run a package action by action ID. Returns the action result.")
async def package_action_run(
    package_id: str,
    action_id: str,
    host: str | None = None,
) -> str:
    return await run_cli(
        "package", "action", "run", package_id, action_id, host=host, timeout=120
    )


@mcp.tool(description="Create a backup for all packages to the specified target.")
async def backup_create(target: str, password: str, host: str | None = None) -> str:
    return await run_cli("backup", "create", target, password, host=host, timeout=600)


@mcp.tool(description="Dump database contents, optionally filtering by path.")
async def db_dump(path: str | None = None, host: str | None = None) -> str:
    args = ["db", "dump"]
    if path:
        args.append(path)
    return await run_cli(*args, host=host, timeout=30)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
