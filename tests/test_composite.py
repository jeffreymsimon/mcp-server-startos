"""Tests for composite.py — high-level aggregation tools."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from tests.conftest import load_fixture


# We patch at the composite module level since that's where the imports resolve
CLI_PATCH = "mcp_server_startos.composite.run_cli"
CLI_JSON_PATCH = "mcp_server_startos.composite.run_cli_json"


@pytest.mark.asyncio
async def test_package_inspect_aggregates():
    """package_inspect should combine data from 4 CLI calls."""
    from mcp_server_startos.composite import package_inspect

    pkg_list = load_fixture("package_list.json")
    stats = load_fixture("package_stats.json")

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        # run_cli_json is called for package list and stats
        mock_json.side_effect = [pkg_list, stats]
        # run_cli is called for installed-version and logs
        mock_cli.side_effect = ["28.1.0\n", "2026-04-14 log line 1\n2026-04-14 log line 2\n"]

        result = await package_inspect("bitcoind")

    assert result["package_id"] == "bitcoind"
    assert result["version"] == "28.1.0"
    assert result["status"]["id"] == "bitcoind"
    assert result["resources"]["id"] == "bitcoind"
    assert "log line" in result["recent_logs"]


@pytest.mark.asyncio
async def test_package_inspect_partial_failure():
    """If one sub-call fails, others should still succeed."""
    from mcp_server_startos.composite import package_inspect

    pkg_list = load_fixture("package_list.json")

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        # package list succeeds, stats fails
        mock_json.side_effect = [pkg_list, RuntimeError("stats unavailable")]
        # version succeeds, logs fails
        mock_cli.side_effect = ["28.1.0\n", RuntimeError("logs unavailable")]

        result = await package_inspect("bitcoind")

    assert result["package_id"] == "bitcoind"
    assert result["version"] == "28.1.0"
    assert result["status"]["id"] == "bitcoind"
    # resources should contain the error string
    assert "error" in str(result["resources"]).lower()
    # logs should contain the error string
    assert "error" in result["recent_logs"].lower()


@pytest.mark.asyncio
async def test_system_health_summary_healthy():
    """Healthy system should report all_healthy=True."""
    from mcp_server_startos.composite import system_health_summary

    # Modify metrics to have disk under 85%
    metrics = load_fixture("server_metrics.json")
    metrics["disk"]["/"]["used"] = 200000000000  # 40% of 500GB

    # All packages running
    pkg_list = [
        {"id": "bitcoind", "status": {"main": {"status": "running"}}},
        {"id": "lnd", "status": {"main": {"status": "running"}}},
    ]

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        mock_json.side_effect = [metrics, pkg_list]
        mock_cli.return_value = "2026-04-14 INFO started ok\n2026-04-14 INFO all good\n"

        result = await system_health_summary()

    assert result["all_healthy"] is True
    assert result["packages"]["all_running"] is True
    assert len(result["disk_warnings"]) == 0
    assert len(result["recent_errors"]) == 0


@pytest.mark.asyncio
async def test_system_health_summary_disk_warning():
    """Disk over 85% should trigger a warning."""
    from mcp_server_startos.composite import system_health_summary

    metrics = load_fixture("server_metrics.json")
    # / partition is 450/500 = 90%

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        mock_json.side_effect = [metrics, []]
        mock_cli.return_value = ""

        result = await system_health_summary()

    assert len(result["disk_warnings"]) >= 1
    root_warn = [w for w in result["disk_warnings"] if w["mount"] == "/"]
    assert len(root_warn) == 1
    assert root_warn[0]["usage_pct"] == 90.0


@pytest.mark.asyncio
async def test_system_health_summary_stopped_package():
    """Stopped packages should appear in problems list."""
    from mcp_server_startos.composite import system_health_summary

    metrics = load_fixture("server_metrics.json")
    metrics["disk"]["/"]["used"] = 100000000000  # low disk
    pkg_list = load_fixture("package_list.json")  # vaultwarden is stopped

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        mock_json.side_effect = [metrics, pkg_list]
        mock_cli.return_value = ""

        result = await system_health_summary()

    assert result["packages"]["all_running"] is False
    problem_ids = [p["id"] for p in result["packages"]["problems"]]
    assert "vaultwarden" in problem_ids


@pytest.mark.asyncio
async def test_system_health_summary_log_errors():
    """Error lines in logs should be detected."""
    from mcp_server_startos.composite import system_health_summary

    metrics = load_fixture("server_metrics.json")
    metrics["disk"]["/"]["used"] = 100000000000

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json, \
         patch(CLI_PATCH, new_callable=AsyncMock) as mock_cli:
        mock_json.side_effect = [metrics, []]
        mock_cli.return_value = "2026-04-14 INFO ok\n2026-04-14 ERROR disk io failed\n2026-04-14 CRITICAL panic\n"

        result = await system_health_summary()

    assert len(result["recent_errors"]) == 2
    assert any("ERROR" in e for e in result["recent_errors"])
    assert any("CRITICAL" in e for e in result["recent_errors"])


@pytest.mark.asyncio
async def test_fleet_compare_detects_diff():
    """fleet_compare should detect package differences between hosts."""
    from mcp_server_startos.composite import fleet_compare

    host1_info = {"hostname": "host1", "version": "0.4.0-beta.5"}
    host2_info = {"hostname": "host2", "version": "0.4.0-alpha.22"}
    host1_pkgs = [
        {"id": "bitcoind", "version": "28.1.0"},
        {"id": "netbox", "version": "4.2.2"},
    ]
    host2_pkgs = [
        {"id": "bitcoind", "version": "28.0.1"},
        {"id": "jellyfin", "version": "10.9.0"},
    ]
    host1_metrics = {"cpu": {"percentage": 10}}
    host2_metrics = {"cpu": {"percentage": 50}}

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json:
        # Order: host1 device-info, host1 packages, host1 metrics, host2 device-info, host2 packages, host2 metrics
        mock_json.side_effect = [
            host1_info, host1_pkgs, host1_metrics,
            host2_info, host2_pkgs, host2_metrics,
        ]

        result = await fleet_compare(["http://host1.local", "http://host2.local"])

    assert result["version_match"] is False
    assert result["versions"]["http://host1.local"] == "0.4.0-beta.5"

    # bitcoind is common, netbox only on host1, jellyfin only on host2
    common_ids = [p["id"] for p in result["packages"]["common"]]
    assert "bitcoind" in common_ids
    assert "netbox" in result["packages"]["only_on"]["http://host1.local"]
    assert "jellyfin" in result["packages"]["only_on"]["http://host2.local"]

    # Version diff for common package
    btc = [p for p in result["packages"]["common"] if p["id"] == "bitcoind"][0]
    assert btc["versions"]["http://host1.local"] == "28.1.0"
    assert btc["versions"]["http://host2.local"] == "28.0.1"


@pytest.mark.asyncio
async def test_fleet_compare_host_error():
    """If one host is unreachable, its data should show the error."""
    from mcp_server_startos.composite import fleet_compare

    host1_info = {"hostname": "host1", "version": "0.4.0-beta.5"}
    host1_pkgs = [{"id": "bitcoind", "version": "28.1.0"}]
    host1_metrics = {"cpu": {"percentage": 10}}

    with patch(CLI_JSON_PATCH, new_callable=AsyncMock) as mock_json:
        mock_json.side_effect = [
            host1_info, host1_pkgs, host1_metrics,
            RuntimeError("connection refused"), RuntimeError("connection refused"), RuntimeError("connection refused"),
        ]

        result = await fleet_compare(["http://host1.local", "http://host2.local"])

    # host1 should have proper data
    assert result["versions"]["http://host1.local"] == "0.4.0-beta.5"
    # host2 should show error
    assert "error" in str(result["versions"]["http://host2.local"]).lower()
