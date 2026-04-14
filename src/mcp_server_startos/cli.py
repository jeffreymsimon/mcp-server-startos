"""Thin async wrapper around the start-cli binary."""

import asyncio
import json
import os
import shutil
import time
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


async def run_cli(
    *args: str,
    host: str | None = None,
    registry: str | None = None,
    timeout: int = 30,
    dry_run: bool = False,
    debug_trace: bool = False,
) -> str | dict:
    cmd = [START_CLI]
    if host:
        cmd.extend(["-H", host])
    if registry:
        cmd.extend(["-r", registry])
    cmd.extend(args)

    if dry_run:
        return " ".join(cmd)

    t0 = time.monotonic() if debug_trace else 0

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)

    if debug_trace:
        duration_ms = round((time.monotonic() - t0) * 1000)
        out = stdout.decode()
        return {
            "command": " ".join(cmd),
            "raw_output": out,
            "duration_ms": duration_ms,
            "exit_code": proc.returncode,
        }

    if proc.returncode != 0:
        err = stderr.decode().strip()
        raise RuntimeError(f"start-cli exited {proc.returncode}: {err}")

    return stdout.decode()


async def run_cli_json(
    *args: str,
    host: str | None = None,
    registry: str | None = None,
    timeout: int = 30,
    dry_run: bool = False,
    debug_trace: bool = False,
) -> dict | list:
    if dry_run:
        cmd = [START_CLI]
        if host:
            cmd.extend(["-H", host])
        if registry:
            cmd.extend(["-r", registry])
        cmd.extend(args)
        cmd.extend(["--format", "json"])
        return " ".join(cmd)

    raw = await run_cli(
        *args, "--format", "json",
        host=host, registry=registry, timeout=timeout,
        debug_trace=debug_trace,
    )

    if debug_trace:
        # raw is a dict from run_cli's debug_trace path
        raw["parsed_output"] = json.loads(raw["raw_output"])
        return raw

    return json.loads(raw)
