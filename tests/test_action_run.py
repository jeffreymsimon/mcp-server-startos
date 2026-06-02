"""Tests for package_action_run — the inputs/event-id handshake (Redmine #1258).

Actions defined with sdk.Action.withInput(...) require a two-step handshake:
get-input yields an eventId + current value, then `run --event-id <id>` reads
the full input JSON from stdin. Before #1258 the MCP tool had no `inputs`
parameter and no way to supply that body, so the call either hung (inherited
stdin) or surfaced a bare "Error: " (empty TimeoutError).
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from mcp_server_startos import server

# The tool is FastMCP-wrapped; the raw coroutine lives on .fn.
_run = getattr(server.package_action_run, "fn", server.package_action_run)

CLI_PATCH = "mcp_server_startos.server.run_cli"
CLI_JSON_PATCH = "mcp_server_startos.server.run_cli_json"


@pytest.mark.asyncio
async def test_action_run_no_inputs_is_plain_run():
    """inputs=None -> single plain run, no get-input, no stdin body."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json:
        mock_cli.return_value = "done"
        result = await _run(package_id="openbrain", action_id="restart")

    assert result == "done"
    mock_json.assert_not_called()  # no get-input handshake
    args = mock_cli.call_args[0]
    assert args[:5] == ("package", "action", "run", "openbrain", "restart")
    # No event-id / stdin when there are no inputs.
    assert "--event-id" not in args
    assert mock_cli.call_args.kwargs.get("stdin_data") is None


@pytest.mark.asyncio
async def test_action_run_with_inputs_does_handshake():
    """inputs={...} -> get-input for eventId, then run --event-id with stdin JSON."""
    inputs = {"label": "ios-shortcut"}
    with patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json:
        mock_json.return_value = {"eventId": "EVT123", "spec": {}, "value": {}}
        mock_cli.return_value = "token issued"
        result = await _run(
            package_id="openbrain", action_id="issue-capture-token", inputs=inputs
        )

    assert result == "token issued"
    # Step 1: get-input was called.
    mock_json.assert_awaited_once()
    assert mock_json.call_args[0][:3] == ("package", "action", "get-input")
    # Step 2: run paired the eventId and piped the FULL input JSON on stdin.
    run_args = mock_cli.call_args[0]
    assert "--event-id" in run_args
    assert run_args[run_args.index("--event-id") + 1] == "EVT123"
    assert mock_cli.call_args.kwargs["stdin_data"] == json.dumps(inputs)


@pytest.mark.asyncio
async def test_action_run_inputs_dry_run_skips_daemon():
    """dry_run with inputs returns the two-step command string, no daemon calls."""
    with patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli, \
         patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json:
        result = await _run(
            package_id="openbrain", action_id="configure-general-settings",
            inputs={"timezone": "UTC"}, dry_run=True,
        )

    assert isinstance(result, str)
    assert "get-input" in result and "run" in result
    mock_cli.assert_not_called()
    mock_json.assert_not_called()
