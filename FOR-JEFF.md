# mcp-server-startos — FOR JEFF

## What This Is

This is an MCP (Model Context Protocol) server that lets Claude Code talk directly to your StartOS hosts. Instead of me SSH'ing into a box and running `start-cli package list` manually, I can now call `mcp__startos__package_list` as a native tool — the same way I use the Redmine MCP server or the NetBox MCP server.

Think of it like giving Claude Code a remote control for StartOS.

## Why We Built It

Before this, every StartOS operation required me to:
1. Figure out which host to target
2. Run `start-cli` via Bash tool
3. Parse the text output manually
4. Hope I got the flags right

Now it's a structured tool call with typed parameters, JSON responses, and proper error handling. The MCP protocol handles all the plumbing.

This was Phase 2 of the broader MCP infrastructure plan (Redmine #668). Phase 1 installed existing MCP servers for GitHub, Redmine, NetBox, ntfy, Cloudflare, Uptime Kuma, and Bitwarden.

## How It Works

**Architecture**: It's embarrassingly simple. The MCP server is a Python script that:
1. Receives a JSON-RPC request from Claude Code (e.g., "call `package_list`")
2. Translates it into a `start-cli` subprocess call (e.g., `start-cli package list --format json`)
3. Captures stdout, parses JSON, returns it

That's it. No SDK reimplementation, no API reverse-engineering. Just a thin async wrapper around the CLI tool you already have installed.

**FastMCP pattern**: We used the `FastMCP` decorator from the MCP Python SDK (v1.27.0). Each tool is a simple decorated function:

```python
@mcp.tool(description="List all installed packages on a StartOS host.")
async def package_list(host: str | None = None) -> dict | list:
    return await run_cli_json("package", "list", host=host)
```

The framework auto-generates JSON schemas from the type hints, handles the MCP protocol negotiation, and manages the stdio transport. We write zero boilerplate.

**Multi-host**: Every single tool accepts an optional `host` parameter. If you say "check metrics on haz1upstart001", it passes `-H http://haz1upstart001.local` to start-cli. If you don't specify a host, it uses whatever `~/.startos/config.yaml` points to (currently muscular-boardroom.local = haz1upstart002).

## The 53 Tools

We started with 22 basic tools (list packages, get metrics, read logs) and then asked "what else is useful?" The answer was: everything.

**The interesting ones**:

- **`package_action_get_input`** — This is the "look before you leap" tool. Before running a package action, you can inspect its form schema to see what fields it expects, what types they are, what the defaults are. It's like reading the instruction manual before pressing buttons.

- **`package_attach`** — This is `docker exec` for StartOS. Run any command inside a running package's LXC container. Check a config file, query a SQLite database, inspect running processes. The debugging tool you always wish you had.

- **`fleet_*` tools** — These run the same query across multiple hosts in parallel using `asyncio.gather`. Instead of checking each host one at a time, you get a dict keyed by host with all results at once. Perfect for "is ntfy running on all three hosts?" type questions.

- **`registry_*` tools** — Browse the StartOS marketplace programmatically. Search for packages, check available versions, see what's new.

- **`db_dump` / `db_apply`** — The nuclear option. The StartOS database contains the *complete* system state. You can read any part of it with `db_dump` (filtered by path), or patch it with `db_apply`. It's the programmatic equivalent of editing the system's brain directly.

## Lessons Learned

1. **FastMCP is the right choice for new MCP servers**. The mempalace server uses raw JSON-RPC (manual protocol handling), which works but is verbose. FastMCP gives you the same result with 90% less code. Type hints become your API contract.

2. **start-cli's `--format json` isn't universal**. Some commands support it (package list, server metrics), others don't (logs, DNS table). For text-only commands, we just return the raw string — the LLM can parse it fine.

3. **uv as the runner is the cleanest pattern**. The settings.json entry uses `uv --directory <path> run mcp-server-startos`, which handles virtualenv creation, dependency resolution, and execution in one shot. No manual pip install, no venv activation.

4. **The `host` parameter pattern is worth standardizing**. Every tool taking an optional host makes multi-host management seamless. The fleet tools just call the same single-host functions in parallel.

## Tech Stack

- **Python 3.10+** — type hints with `str | None` union syntax
- **mcp SDK 1.27.0** — FastMCP decorator pattern
- **asyncio** — subprocess calls are async (non-blocking)
- **start-cli 0.4.0-beta.5** — the actual StartOS CLI tool being wrapped
- **uv** — package runner (handles deps and virtualenv)

## File Layout

```
src/mcp_server_startos/
├── __init__.py     # empty
├── cli.py          # 50 lines — finds start-cli, runs it, parses JSON
└── server.py       # ~350 lines — 53 @mcp.tool() functions + main()
```

Two files of actual code. That's the whole thing.
