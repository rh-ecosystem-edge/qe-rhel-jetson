"""
Hardware and system information collection from a Jetson device via SSH.

Provides individual getter functions (e.g. get_rhel_version, get_jetpack_version)
that any test can call directly, plus a collect() convenience function that gathers
everything at once (used by tests_suites/conftest.py to set global variables).

Usage:
    from tests_resources.hardware_info import get_rhel_version, get_kernel_version
    rhel = get_rhel_version(ssh)

    # Or collect everything at once:
    from tests_resources.hardware_info import collect
    info = collect(ssh)
"""
import re
import logging
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


def _run(ssh, command: str, timeout: Optional[int] = 30) -> str:
    """Run command via SSH and return stripped stdout, or empty string on failure."""
    try:
        result = ssh.run(command, timeout=timeout, print_output=False)
        return (result.stdout or "").strip() if result.exit_status == 0 else ""
    except (OSError, TimeoutError, RuntimeError, EOFError) as e:
        logger.debug("Command %r failed: %s", command, e)
        return ""


def _run_sudo(ssh, command: str, timeout: Optional[int] = 30) -> str:
    """Run command with sudo via SSH and return stripped stdout, or empty string on failure."""
    try:
        result = ssh.run(f"sudo {command}", timeout=timeout, print_output=False)
        return (result.stdout or "").strip() if result.exit_status == 0 else ""
    except (OSError, TimeoutError, RuntimeError, EOFError) as e:
        logger.debug("Command sudo %r failed: %s", command, e)
        return ""


def _parse_decimal(s: str) -> Optional[Union[float, str]]:
    """
    Extract a decimal from string.
    - If 3 numbers with 2 dots exist (e.g. 1.2.3), returns that string.
    - If only 1 dot exists (e.g. 1.2), returns a one-dot decimal as float.
    """
    if not s:
        return None
    # Prefer X.Y.Z (three numbers, two dots)
    match_three = re.search(r"(\d+\.\d+\.\d+)", s)
    if match_three:
        return match_three.group(1)
    # Else one dot: X.Y (two numbers)
    match_two = re.search(r"(\d+\.\d+)", s)
    if match_two:
        try:
            return float(match_two.group(1))
        except ValueError:
            pass
    # Else single integer
    match_one = re.search(r"(\d+)", s)
    if match_one:
        try:
            return float(match_one.group(1))
        except ValueError:
            pass
    return None


def get_rhel_version(ssh) -> Optional[float]:
    """Return RHEL version as float (e.g. 9.7), or None if not found."""
    rhel = _run(ssh, "cat /etc/redhat-release")
    rhel_number = _parse_decimal(rhel)
    return rhel_number if rhel_number else None


def get_jetpack_version(ssh) -> Optional[Union[float, str]]:
    """Return JetPack version from /etc/nv_tegra_release.
    Returns str for X.Y.Z (e.g. '36.4.4'), float for X.Y, or None.
    Note: this file comes from userspace RPMs (e.g. nvidia-jetpack-core), not kmod."""
    jetpack_raw = _run(ssh, "head -n 1 /etc/nv_tegra_release")
    if not jetpack_raw:
        return None

    r_match = re.search(r"R(\d+)(?:\.(\d+))?", jetpack_raw)
    rev_match = re.search(r"REVISION:\s*([\d.]+)", jetpack_raw)
    if r_match and rev_match:
        r_major = int(r_match.group(1))
        rev_str = rev_match.group(1).strip()
        rev_parts = rev_str.split(".")
        rev_first = int(rev_parts[0]) if rev_parts and rev_parts[0].isdigit() else 0
        rev_second = int(rev_parts[1]) if len(rev_parts) > 1 and rev_parts[1].isdigit() else 0
        return f"{r_major}.{rev_first}.{rev_second}"
    if rev_match:
        try:
            return float(rev_match.group(1).strip())
        except ValueError:
            pass
    if r_match:
        try:
            major = int(r_match.group(1))
            minor = int(r_match.group(2) or 0)
            return float(f"{major}.{minor}")
        except ValueError:
            pass
    return _parse_decimal(jetpack_raw)


def get_firmware_info(ssh) -> dict[str, Any]:
    """Return firmware version and type from dmidecode.
    Returns dict with keys: firmware_version (float|str|None), firmware_type (str|None)."""
    firmware_version = None
    firmware_type = None

    dmidecode = _run_sudo(ssh, "dmidecode -t bios")
    if dmidecode:
        ver_match = re.search(r"Version:\s*(.+)", dmidecode, re.MULTILINE | re.IGNORECASE)
        if ver_match:
            firmware_version = _parse_decimal(ver_match.group(1).strip())
        if "UEFI" in dmidecode.upper() or "EFI" in dmidecode.upper():
            firmware_type = "UEFI"
        else:
            firmware_type = "BIOS"
    if firmware_type is None:
        efi_check = _run(ssh, "test -d /sys/firmware/efi && echo UEFI || echo BIOS").strip()
        firmware_type = efi_check if efi_check else None

    return {"firmware_version": firmware_version, "firmware_type": firmware_type}


def get_hardware_model_name(ssh) -> Optional[str]:
    """Return hardware model name from devicetree or dmidecode."""
    model = _run(ssh, "cat /sys/firmware/devicetree/base/model | tr -d '\\0'")
    if not model:
        sysinfo = _run_sudo(ssh, "dmidecode -t system")
        if sysinfo:
            m = re.search(r"Product Name:\s*(.+)", sysinfo, re.MULTILINE | re.IGNORECASE)
            if m:
                model = m.group(1).strip()
    return model if model else None


def get_kernel_version(ssh) -> Optional[str]:
    """Return kernel version string (uname -r), or None."""
    kernel = _run(ssh, "uname -r")
    return kernel if kernel else None


def get_cpu_arch(ssh) -> Optional[str]:
    """Return CPU architecture (uname -m), or None."""
    arch = _run(ssh, "uname -m")
    return arch if arch else None


def get_bootc_info(ssh) -> dict[str, Any]:
    """Return bootc/rpm-ostree information.
    Returns dict with keys: bootc_available (bool), bootc_version (float|str|None),
    bootc_image_url (str|None), bootc_image_version (str|None)."""
    bootc_which = _run(ssh, "which bootc")
    rpm_ostree_which = _run(ssh, "which rpm-ostree")
    available = bool(bootc_which or rpm_ostree_which)

    info = {
        "bootc_available": available,
        "bootc_version": None,
        "bootc_image_url": None,
        "bootc_image_version": None,
    }
    if not available:
        return info

    ver_out = _run(ssh, "bootc --version")
    if ver_out:
        info["bootc_version"] = _parse_decimal(ver_out)

    status_out = _run(ssh, "rpm-ostree status")
    if status_out:
        img_ver_match = re.search(r"(?:Version)\s*[:\s]+\s*(\S+.*?)(?:\s*$|\n)", status_out, re.MULTILINE | re.IGNORECASE)
        if img_ver_match:
            info["bootc_image_version"] = img_ver_match.group(1).strip() if img_ver_match.group(1).strip() else None
        # Image URL: extract from "ostree-unverified-registry:<url>" or "ostree-image-signed:docker://<url>"
        registry_match = re.search(r"registry:(?:docker://)?(\S+)", status_out)
        if registry_match:
            info["bootc_image_url"] = registry_match.group(1).strip()

    return info


def collect(ssh) -> dict[str, Any]:
    """
    Collect all hardware and system info from the remote host via SSH.
    Calls individual getter functions and merges results into a single dict.

    Args:
        ssh: An SSHConnection instance (from infra_tests.ssh_client).

    Returns:
        Dict with keys (all None if value not found):
        - rhel_version: float | None
        - jetpack_version: float | str | None (str if X.Y.Z, float if X.Y)
        - firmware_version: float | str | None (str if X.Y.Z, float if X.Y)
        - firmware_type: str | None (e.g. "UEFI", "BIOS")
        - hardware_model_name: str | None
        - kernel_version: str | None
        - cpu_arch: str | None
        - bootc_available: bool (default False if not found)
        - bootc_version: float | str | None (str if X.Y.Z, float if X.Y)
        - bootc_image_url: str | None
        - bootc_image_version: str | None
    """
    firmware = get_firmware_info(ssh)
    bootc = get_bootc_info(ssh)

    return {
        "rhel_version": get_rhel_version(ssh),
        "jetpack_version": get_jetpack_version(ssh),
        "firmware_version": firmware["firmware_version"],
        "firmware_type": firmware["firmware_type"],
        "hardware_model_name": get_hardware_model_name(ssh),
        "kernel_version": get_kernel_version(ssh),
        "cpu_arch": get_cpu_arch(ssh),
        "bootc_available": bootc["bootc_available"],
        "bootc_version": bootc["bootc_version"],
        "bootc_image_url": bootc["bootc_image_url"],
        "bootc_image_version": bootc["bootc_image_version"],
    }
