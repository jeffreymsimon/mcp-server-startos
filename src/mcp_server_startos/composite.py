"""Composite high-level tools that aggregate multiple start-cli calls."""

import asyncio
import re

from .app import mcp
from .cli import run_cli, run_cli_json


# ---------------------------------------------------------------------------
# Composite: Package inspection
# ---------------------------------------------------------------------------


@mcp.tool(description="Comprehensive package inspection: returns version, status, recent logs, and resource usage in a single call. Aggregates package_list, installed-version, logs, and stats.")
async def package_inspect(package_id: str, host: str | None = None) -> dict:
    results = await asyncio.gather(
        _safe(run_cli_json, "package", "list", host=host),
        _safe(run_cli, "package", "installed-version", package_id, host=host),
        _safe(run_cli, "package", "logs", package_id, "-l", "20", host=host, timeout=15),
        _safe(run_cli_json, "package", "stats", host=host),
    )

    pkg_list, version_raw, logs_raw, stats_raw = results

    # Extract this package's status from the full list
    status = None
    if isinstance(pkg_list, (dict, list)):
        status = _find_package(pkg_list, package_id)

    # Extract this package's resource usage from stats
    resources = None
    if isinstance(stats_raw, (dict, list)):
        resources = _find_package(stats_raw, package_id)

    return {
        "package_id": package_id,
        "version": version_raw.strip() if isinstance(version_raw, str) else version_raw,
        "status": status if status else pkg_list,  # fall back to raw/error
        "resources": resources if resources else stats_raw,
        "recent_logs": logs_raw if isinstance(logs_raw, str) else str(logs_raw),
    }


# ---------------------------------------------------------------------------
# Composite: System health summary
# ---------------------------------------------------------------------------


@mcp.tool(description="System health summary: server metrics, package health, disk warnings, and recent error log scan in a single call. Flags packages not running and disk partitions over 85%.")
async def system_health_summary(host: str | None = None) -> dict:
    results = await asyncio.gather(
        _safe(run_cli_json, "server", "metrics", host=host),
        _safe(run_cli_json, "package", "list", host=host),
        _safe(run_cli, "server", "logs", "-l", "100", host=host, timeout=15),
    )

    metrics_raw, pkg_list_raw, logs_raw = results

    # Analyze packages
    packages_info = _analyze_packages(pkg_list_raw)

    # Analyze disk usage
    disk_warnings = _analyze_disk(metrics_raw)

    # Scan logs for errors
    recent_errors = _scan_log_errors(logs_raw)

    all_healthy = (
        packages_info.get("all_running", False)
        and len(disk_warnings) == 0
        and len(recent_errors) == 0
        and not isinstance(metrics_raw, str)  # no error fetching metrics
    )

    return {
        "metrics": metrics_raw,
        "packages": packages_info,
        "disk_warnings": disk_warnings,
        "recent_errors": recent_errors,
        "all_healthy": all_healthy,
    }


# ---------------------------------------------------------------------------
# Composite: Fleet comparison
# ---------------------------------------------------------------------------


@mcp.tool(description="Compare multiple StartOS hosts: version differences, package inventory diff, and resource usage side-by-side. Provide a list of host URLs.")
async def fleet_compare(hosts: list[str]) -> dict:
    # Gather device info, package lists, and metrics for all hosts in parallel
    tasks = []
    for h in hosts:
        tasks.append(_safe(run_cli_json, "server", "device-info", host=h))
        tasks.append(_safe(run_cli_json, "package", "list", host=h))
        tasks.append(_safe(run_cli_json, "server", "metrics", host=h))

    results = await asyncio.gather(*tasks)

    # Unpack results (3 per host)
    host_data = {}
    for i, h in enumerate(hosts):
        base = i * 3
        host_data[h] = {
            "device_info": results[base],
            "packages": results[base + 1],
            "metrics": results[base + 2],
        }

    # Extract versions
    versions = {}
    for h, data in host_data.items():
        if isinstance(data["device_info"], dict):
            versions[h] = data["device_info"].get("version", data["device_info"].get("startosVersion", "unknown"))
        else:
            versions[h] = str(data["device_info"])

    unique_versions = set(versions.values()) - {"unknown"}
    version_match = len(unique_versions) <= 1

    # Compare package inventories
    host_packages = {}
    for h, data in host_data.items():
        if isinstance(data["packages"], (dict, list)):
            host_packages[h] = _extract_package_ids(data["packages"])
        else:
            host_packages[h] = {}

    all_ids = set()
    for pkgs in host_packages.values():
        all_ids.update(pkgs.keys())

    common = []
    only_on = {h: [] for h in hosts}

    for pid in sorted(all_ids):
        present_on = [h for h in hosts if pid in host_packages.get(h, {})]
        if len(present_on) == len(hosts):
            pkg_versions = {h: host_packages[h][pid] for h in hosts}
            common.append({"id": pid, "versions": pkg_versions})
        else:
            for h in present_on:
                only_on[h].append(pid)

    # Resource comparison
    resources = {}
    for h, data in host_data.items():
        if isinstance(data["metrics"], dict):
            resources[h] = data["metrics"]
        else:
            resources[h] = str(data["metrics"])

    return {
        "versions": versions,
        "version_match": version_match,
        "packages": {
            "common": common,
            "only_on": only_on,
        },
        "resources": resources,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _safe(fn, *args, **kwargs):
    """Run an async function, returning error string on failure instead of raising."""
    try:
        return await fn(*args, **kwargs)
    except Exception as e:
        return f"error: {e}"


def _find_package(data, package_id: str):
    """Find a specific package in a list or dict response from start-cli."""
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and item.get("id") == package_id:
                return item
    elif isinstance(data, dict):
        if package_id in data:
            return data[package_id]
        # Some responses nest under a packages key
        pkgs = data.get("packages", data)
        if isinstance(pkgs, dict) and package_id in pkgs:
            return pkgs[package_id]
        if isinstance(pkgs, list):
            for item in pkgs:
                if isinstance(item, dict) and item.get("id") == package_id:
                    return item
    return None


def _analyze_packages(pkg_list_raw) -> dict:
    """Analyze package list for health issues."""
    if isinstance(pkg_list_raw, str):
        return {"error": pkg_list_raw, "total": 0, "running": 0, "all_running": False, "problems": []}

    packages = []
    if isinstance(pkg_list_raw, list):
        packages = pkg_list_raw
    elif isinstance(pkg_list_raw, dict):
        packages = list(pkg_list_raw.values()) if pkg_list_raw else []

    total = len(packages)
    problems = []
    running = 0

    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        status = pkg.get("status", pkg.get("state", ""))
        pkg_id = pkg.get("id", pkg.get("name", "unknown"))
        # Consider various status representations
        if isinstance(status, str) and status.lower() in ("running", "started"):
            running += 1
        elif isinstance(status, dict) and status.get("main", {}).get("status", "").lower() in ("running", "started"):
            running += 1
        else:
            problems.append({"id": pkg_id, "status": status})

    return {
        "total": total,
        "running": running,
        "all_running": len(problems) == 0 and total > 0,
        "problems": problems,
    }


def _analyze_disk(metrics_raw) -> list:
    """Check disk metrics for partitions over 85% usage."""
    warnings = []
    if not isinstance(metrics_raw, dict):
        return warnings

    disks = metrics_raw.get("disk", metrics_raw.get("disks", []))
    if isinstance(disks, dict):
        for mount, info in disks.items():
            if isinstance(info, dict):
                used = info.get("used", 0)
                total = info.get("total", 1)
                if total > 0:
                    pct = round(used / total * 100, 1)
                    if pct > 85:
                        warnings.append({"mount": mount, "usage_pct": pct, "used": used, "total": total})
    elif isinstance(disks, list):
        for disk in disks:
            if isinstance(disk, dict):
                used = disk.get("used", 0)
                total = disk.get("total", 1)
                mount = disk.get("mount", disk.get("name", "unknown"))
                if total > 0:
                    pct = round(used / total * 100, 1)
                    if pct > 85:
                        warnings.append({"mount": mount, "usage_pct": pct, "used": used, "total": total})

    return warnings


def _scan_log_errors(logs_raw) -> list[str]:
    """Scan log text for error-level entries."""
    if not isinstance(logs_raw, str):
        return [str(logs_raw)] if logs_raw else []

    error_pattern = re.compile(r"\b(error|fail|panic|critical|fatal)\b", re.IGNORECASE)
    errors = []
    for line in logs_raw.splitlines():
        if error_pattern.search(line):
            errors.append(line.strip())

    return errors[-20:]  # cap at 20 most recent errors


def _extract_package_ids(data) -> dict[str, str]:
    """Extract {package_id: version} from a package list response."""
    result = {}
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                pid = item.get("id", "")
                ver = item.get("version", item.get("installedVersion", "unknown"))
                if pid:
                    result[pid] = ver
    elif isinstance(data, dict):
        for pid, info in data.items():
            if isinstance(info, dict):
                result[pid] = info.get("version", info.get("installedVersion", "unknown"))
            else:
                result[pid] = str(info)
    return result
