"""Shared pytest fixtures for mcp-server-startos tests."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    """Load a JSON fixture file by name."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


@pytest.fixture
def mock_run_cli():
    """Patch run_cli with an AsyncMock. Set return_value on the mock in your test."""
    with patch("mcp_server_startos.cli.run_cli", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_run_cli_json():
    """Patch run_cli_json with an AsyncMock. Set return_value on the mock in your test."""
    with patch("mcp_server_startos.cli.run_cli_json", new_callable=AsyncMock) as m:
        yield m


@pytest.fixture
def mock_subprocess():
    """Patch asyncio.create_subprocess_exec for cli.py unit tests."""
    with patch("mcp_server_startos.cli.asyncio.create_subprocess_exec", new_callable=AsyncMock) as m:
        yield m
