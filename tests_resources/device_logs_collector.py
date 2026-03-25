"""
Device logs collector — collects diagnostic logs from a Jetson device via SSH,
packages them into a tar.gz archive, and saves locally.

Usage:
    from tests_resources.device_logs_collector import save_device_logs
    archive_path = save_device_logs(ssh, bootc_image_url, output_dir)
"""
import io
import os
import re
import tarfile
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from tests_resources.hardware_info import (
    collect as collect_hardware_info,
    get_log_secure_boot_state,
    get_log_modinfo_host1x,
    get_log_modinfo_tegra_drm,
    get_log_modinfo_nvgpu,
    get_log_module_files_updates,
    get_log_nvidia_modules_dep,
    get_log_modprobe_nvidia,
    get_log_journalctl_current_boot,
    get_log_journalctl_all,
    get_log_dmesg_all,
    get_log_dmesg_nvidia_errors,
    get_log_nvidia_rpms,
    get_log_nvidia_loaded_modules,
    get_log_tegra_release,
    get_log_boot_cmdline,
    get_log_systemctl_failed,
)

logger = logging.getLogger(__name__)

# Each entry: (filename for the .txt in the archive, getter function)
# The command string comes from the getter's return value — single source of truth.
LOG_ENTRIES: list[tuple[str, Callable]] = [
    ("secure_boot_state.txt", get_log_secure_boot_state),
    ("modinfo_host1x.txt", get_log_modinfo_host1x),
    ("modinfo_tegra_drm.txt", get_log_modinfo_tegra_drm),
    ("modinfo_nvgpu.txt", get_log_modinfo_nvgpu),
    ("module_files_updates.txt", get_log_module_files_updates),
    ("nvidia_modules_dep.txt", get_log_nvidia_modules_dep),
    ("modprobe_nvidia.txt", get_log_modprobe_nvidia),
    ("journalctl_current_boot.txt", get_log_journalctl_current_boot),
    ("journalctl_all.txt", get_log_journalctl_all),
    ("dmesg_all.txt", get_log_dmesg_all),
    ("dmesg_nvidia_errors.txt", get_log_dmesg_nvidia_errors),
    ("nvidia_rpms.txt", get_log_nvidia_rpms),
    ("nvidia_loaded_modules.txt", get_log_nvidia_loaded_modules),
    ("tegra_release.txt", get_log_tegra_release),
    ("boot_cmdline.txt", get_log_boot_cmdline),
    ("systemctl_failed.txt", get_log_systemctl_failed),
]

# internal functions

def _format_log_content(command: str, exit_status: int, stdout: str, stderr: str) -> str:
    """Format a single log entry as: command, blank line, then output/error/empty marker."""
    if exit_status != 0:
        error_detail = stderr if stderr else stdout if stdout else "no output"
        return f"{command}\n\nCOMMAND FAILED (exit code {exit_status}): {error_detail}"
    if not stdout:
        return f"{command}\n\n-EMPTY OUTPUT-"
    return f"{command}\n\n{stdout}"

def _unique_archive_path(output_dir: Path, base_name: str) -> Path:
    """Return a unique path for the archive, appending _1, _2, etc. if needed."""
    candidate = output_dir / f"{base_name}.tar.gz"
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        candidate = output_dir / f"{base_name}_{counter}.tar.gz"
        if not candidate.exists():
            return candidate
        counter += 1

# public functions

def extract_build_id(bootc_image_url: Optional[str]) -> str:
    """Extract the build ID (numbers after the final '-') from a bootc image URL.
    Example: '...rhel97-5140-611381:6.2.2-5.14.0_611.38.1-032526102349' -> '032526102349'
    Returns 'unknown' if URL is None or no match found."""
    if not bootc_image_url:
        return "unknown"
    match = re.search(r"-(\d+)$", bootc_image_url)
    return match.group(1) if match else "unknown"


def collect_logs(ssh) -> list[tuple[str, str]]:
    """Collect all device logs via SSH.
    Returns list of (filename, formatted_content) tuples. Never skips entries."""
    logs = []
    # add hardware info to the logs as a dictionary
    try:
        dict_hardware_info = collect_hardware_info(ssh)
    except Exception as e:
        dict_hardware_info = "-Failed to collect hardware info-"
    content = json.dumps(dict_hardware_info, indent=4)
    logs.append(("general_hardware_info.json", content))
    # add other logs to the logs
    for filename, getter_fn in LOG_ENTRIES:
        try:
            command, exit_status, stdout, stderr = getter_fn(ssh)
            content = _format_log_content(command, exit_status, stdout, stderr)
        except Exception as e:
            content = f"(unknown command)\n\nCOMMAND FAILED: {e}"
        logs.append((filename, content))
        logger.debug("Collected log: %s", filename)
    return logs


def create_logs_archive(
    logs: list[tuple[str, str]],
    bootc_image_url: Optional[str],
    output_dir: Path,
) -> Path:
    """Create a tar.gz archive from collected logs.
    Returns the Path to the created archive."""
    build_id = extract_build_id(bootc_image_url)
    date_str = datetime.now().strftime("%Y-%m-%d")
    base_name = f"device_logs_{date_str}_{build_id}"

    os.makedirs(output_dir, exist_ok=True)
    archive_path = _unique_archive_path(output_dir, base_name)

    with tarfile.open(archive_path, "w:gz") as tar:
        for filename, content in logs:
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=filename)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))

    logger.info("Created device logs archive: %s", archive_path)
    return archive_path


def save_device_logs(
    ssh,
    bootc_image_url: Optional[str],
    output_dir: Path,
) -> Path:
    """Collect all device logs and save as a tar.gz archive.
    Returns the Path to the created archive."""
    logs = collect_logs(ssh)
    return create_logs_archive(logs, bootc_image_url, output_dir)
