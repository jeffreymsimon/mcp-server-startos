"""Tests for package_start/stop/restart verify-after-action (Redmine #1264).

start-cli returns exit 0 even when the StartOS daemon silently no-ops the
lifecycle request. These tools now poll `package stats` to confirm the package
reached the requested state and raise an actionable error if it didn't, instead
of reporting a false success.
"""

from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_startos import server

_start = getattr(server.package_start, "fn", server.package_start)
_stop = getattr(server.package_stop, "fn", server.package_stop)
_restart = getattr(server.package_restart, "fn", server.package_restart)

CLI_PATCH = "mcp_server_startos.server.run_cli"
CLI_JSON_PATCH = "mcp_server_startos.server.run_cli_json"

# `package stats` shapes: running => key present; stopped => key absent.
RUNNING = {"pingpong": {"container_id": "X", "memory_usage": 5}}
STOPPED = {"other": {"container_id": "Y", "memory_usage": 5}}


@pytest.mark.asyncio
async def test_stop_raises_when_daemon_noops():
    """stop returns success but stats still shows it running -> raise (#1264)."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = ""              # start-cli "succeeds"
        cli_json.return_value = RUNNING    # but stats says still running
        with pytest.raises(RuntimeError, match="STILL running"):
            await _stop(package_id="pingpong")


@pytest.mark.asyncio
async def test_stop_succeeds_when_container_gone():
    """stop + stats no longer lists it -> success."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = ""
        cli_json.return_value = STOPPED
        result = await _stop(package_id="pingpong")
    assert "stopped" in result and "verified" in result


@pytest.mark.asyncio
async def test_start_raises_when_not_up():
    """start returns success but stats never shows it -> raise."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = ""
        cli_json.return_value = STOPPED
        with pytest.raises(RuntimeError, match="NOT running"):
            await _start(package_id="pingpong")


@pytest.mark.asyncio
async def test_start_succeeds_when_up():
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = ""
        cli_json.return_value = RUNNING
        result = await _start(package_id="pingpong")
    assert "started" in result and "verified" in result


@pytest.mark.asyncio
async def test_restart_returns_caveat_when_running_after():
    """restart leaves it running -> success WITH the can't-prove-bounce caveat."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = ""
        cli_json.return_value = RUNNING
        result = await _restart(package_id="pingpong")
    assert "running after restart" in result
    assert "cannot positively confirm" in result


@pytest.mark.asyncio
async def test_verify_false_skips_polling():
    """verify=False returns the raw start-cli output, no stats poll."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = "raw-cli-out"
        result = await _stop(package_id="pingpong", verify=False)
    assert result == "raw-cli-out"
    cli_json.assert_not_called()


@pytest.mark.asyncio
async def test_dry_run_skips_verify():
    with patch(CLI_PATCH, new_callable=AsyncMock) as cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as cli_json:
        cli.return_value = "start-cli package stop pingpong"
        result = await _stop(package_id="pingpong", dry_run=True)
    assert "stop" in result
    cli_json.assert_not_called()
