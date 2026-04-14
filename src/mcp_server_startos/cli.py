"""Thin async wrapper around the start-cli binary."""

import asyncio
import json
import os
import shutil
from pathlib import Path


def _find_start_cli() -> str:
    env = os.environ.get("START_CLI_PATH")
    if env:
        return env
    local = Path.home() / ".local" / "bin" / "start-cli"
    if local.exists():
        return str(local)
    found = shutil.which("start-cli")
    if found:
        return found
    raise FileNotFoundError(
        "start-cli not found. Set START_CLI_PATH, install to ~/.local/bin/, or add to PATH."
    )


START_CLI = _find_start_cli()


async def run_cli(*args: str, host: str | None = None, registry: str | None = None, timeout: int = 30) -> str:
    cmd = [START_CLI]
    if host:
        cmd.extend(["-H", host])
    if registry:
        cmd.extend(["-r", registry])
    cmd.extend(args)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise RuntimeError(f"start-cli exited {proc.returncode}: {err}")

    return stdout.decode()


async def run_cli_json(*args: str, host: str | None = None, registry: str | None = None, timeout: int = 30) -> dict | list:
    raw = await run_cli(*args, "--format", "json", host=host, registry=registry, timeout=timeout)
    return json.loads(raw)
