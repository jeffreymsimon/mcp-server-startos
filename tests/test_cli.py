"""Tests for cli.py — the thin subprocess wrapper around start-cli."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mcp_server_startos.cli import run_cli, run_cli_json

DEVNULL = asyncio.subprocess.DEVNULL
PIPE = asyncio.subprocess.PIPE


@pytest.fixture
def mock_proc():
    """Create a mock subprocess with configurable returncode and output."""
    proc = AsyncMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"output", b""))
    return proc


@pytest.fixture
def patched_subprocess(mock_proc):
    """Patch create_subprocess_exec to return mock_proc."""
    with patch("mcp_server_startos.cli.asyncio.create_subprocess_exec", new_callable=AsyncMock) as m:
        m.return_value = mock_proc
        yield m, mock_proc


@pytest.mark.asyncio
async def test_run_cli_basic(patched_subprocess):
    create_sub, proc = patched_subprocess
    result = await run_cli("package", "list")
    assert result == "output"
    # Verify start-cli was called with the right args
    call_args = create_sub.call_args[0]
    assert call_args[-2:] == ("package", "list")


@pytest.mark.asyncio
async def test_run_cli_with_host(patched_subprocess):
    create_sub, proc = patched_subprocess
    await run_cli("package", "list", host="http://myhost.local")
    call_args = create_sub.call_args[0]
    assert "-H" in call_args
    idx = call_args.index("-H")
    assert call_args[idx + 1] == "http://myhost.local"


@pytest.mark.asyncio
async def test_run_cli_with_registry(patched_subprocess):
    create_sub, proc = patched_subprocess
    await run_cli("registry", "index", registry="https://registry.start9.com")
    call_args = create_sub.call_args[0]
    assert "-r" in call_args
    idx = call_args.index("-r")
    assert call_args[idx + 1] == "https://registry.start9.com"


@pytest.mark.asyncio
async def test_run_cli_nonzero_exit(patched_subprocess):
    create_sub, proc = patched_subprocess
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"", b"something went wrong"))
    with pytest.raises(RuntimeError, match="start-cli exited 1"):
        await run_cli("package", "list")


@pytest.mark.asyncio
async def test_run_cli_dry_run(patched_subprocess):
    create_sub, proc = patched_subprocess
    result = await run_cli("package", "start", "bitcoind", dry_run=True)
    # Should return command string without executing
    assert isinstance(result, str)
    assert "package" in result
    assert "start" in result
    assert "bitcoind" in result
    # create_subprocess_exec should NOT have been called
    create_sub.assert_not_called()


@pytest.mark.asyncio
async def test_run_cli_dry_run_with_host(patched_subprocess):
    create_sub, proc = patched_subprocess
    result = await run_cli("package", "start", "bitcoind", host="http://myhost.local", dry_run=True)
    assert "-H" in result
    assert "http://myhost.local" in result
    create_sub.assert_not_called()


@pytest.mark.asyncio
async def test_run_cli_debug_trace(patched_subprocess):
    create_sub, proc = patched_subprocess
    proc.communicate = AsyncMock(return_value=(b"some output", b""))
    result = await run_cli("package", "list", debug_trace=True)
    assert isinstance(result, dict)
    assert "command" in result
    assert "raw_output" in result
    assert "duration_ms" in result
    assert "exit_code" in result
    assert result["raw_output"] == "some output"
    assert result["exit_code"] == 0
    assert isinstance(result["duration_ms"], int)


@pytest.mark.asyncio
async def test_run_cli_debug_trace_includes_errors(patched_subprocess):
    """debug_trace should return even on non-zero exit (no RuntimeError)."""
    create_sub, proc = patched_subprocess
    proc.returncode = 1
    proc.communicate = AsyncMock(return_value=(b"partial", b"err"))
    result = await run_cli("package", "list", debug_trace=True)
    assert isinstance(result, dict)
    assert result["exit_code"] == 1


@pytest.mark.asyncio
async def test_run_cli_json_parses(patched_subprocess):
    create_sub, proc = patched_subprocess
    proc.communicate = AsyncMock(return_value=(json.dumps({"id": "test"}).encode(), b""))
    result = await run_cli_json("package", "list")
    assert isinstance(result, dict)
    assert result["id"] == "test"


@pytest.mark.asyncio
async def test_run_cli_json_malformed(patched_subprocess):
    create_sub, proc = patched_subprocess
    proc.communicate = AsyncMock(return_value=(b"not json", b""))
    with pytest.raises(json.JSONDecodeError):
        await run_cli_json("package", "list")


@pytest.mark.asyncio
async def test_run_cli_json_dry_run(patched_subprocess):
    create_sub, proc = patched_subprocess
    result = await run_cli_json("package", "list", dry_run=True)
    assert isinstance(result, str)
    assert "--format" in result
    assert "json" in result
    create_sub.assert_not_called()


@pytest.mark.asyncio
async def test_run_cli_json_debug_trace(patched_subprocess):
    create_sub, proc = patched_subprocess
    proc.communicate = AsyncMock(return_value=(json.dumps({"count": 5}).encode(), b""))
    result = await run_cli_json("package", "list", debug_trace=True)
    assert isinstance(result, dict)
    assert "parsed_output" in result
    assert result["parsed_output"]["count"] == 5
    assert "command" in result
    assert "duration_ms" in result


# ---------------------------------------------------------------------------
# Regression tests for Redmine #1258 (action run hang / silent "Error: ")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_cli_defaults_stdin_to_devnull(patched_subprocess):
    """No stdin_data -> child must get DEVNULL, never the inherited JSON-RPC pipe.

    A child that inherits the MCP server's stdin can block forever reading an
    action input body that never arrives — the #1258 hang.
    """
    create_sub, proc = patched_subprocess
    await run_cli("package", "action", "run", "openbrain", "issue-capture-token")
    assert create_sub.call_args.kwargs["stdin"] is DEVNULL
    # No input is piped when stdin_data is None.
    assert proc.communicate.call_args.kwargs.get("input") is None


@pytest.mark.asyncio
async def test_run_cli_stdin_data_pipes_input(patched_subprocess):
    """stdin_data -> child gets a PIPE and the encoded body is written to it."""
    create_sub, proc = patched_subprocess
    body = json.dumps({"label": "x"})
    await run_cli(
        "package", "action", "run", "openbrain", "issue-capture-token",
        "--event-id", "ABC", stdin_data=body,
    )
    assert create_sub.call_args.kwargs["stdin"] is PIPE
    assert proc.communicate.call_args.kwargs["input"] == body.encode()


@pytest.mark.asyncio
async def test_run_cli_timeout_raises_nonempty_error(patched_subprocess):
    """A timeout must raise a RuntimeError with a NON-EMPTY message.

    A bare asyncio.TimeoutError stringifies to "" and FastMCP renders it as the
    mysterious "Error: " with no body (#1258). The wrapper must convert it.
    """
    create_sub, proc = patched_subprocess
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    with pytest.raises(RuntimeError, match="timed out"):
        await run_cli("package", "action", "run", "openbrain", "x", timeout=1)
    proc.kill.assert_called_once()
