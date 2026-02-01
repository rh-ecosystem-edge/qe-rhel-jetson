"""
Collect hardware and system information from a Jetson device via SSH.
Used by tests/conftest.py to expose variables to all tests.
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
    except Exception as e:
        logger.debug("Command %r failed: %s", command, e)
        return ""


def _run_sudo(ssh, command: str, timeout: Optional[int] = 30) -> str:
    """Run command with sudo via SSH and return stripped stdout, or empty string on failure."""
    try:
        result = ssh.run(f"sudo {command}", timeout=timeout, print_output=False)
        return (result.stdout or "").strip() if result.exit_status == 0 else ""
    except Exception as e:
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


def collect(ssh) -> dict[str, Any]:
    """
    Collect hardware and system info from the remote host via SSH.

    Args:
        ssh: An SSHConnection instance (from infra-tests.ssh_client).

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
    out: dict[str, Any] = {
        "rhel_version": None,
        "jetpack_version": None,
        "firmware_version": None,
        "firmware_type": None,
        "hardware_model_name": None,
        "kernel_version": None,
        "cpu_arch": None,
        "bootc_available": False,
        "bootc_version": None,
        "bootc_image_url": None,
        "bootc_image_version": None,
    }

    # 1. RHEL version
    rhel = _run(ssh, "cat /etc/redhat-release 2>/dev/null")
    rhel_number = _parse_decimal(rhel)
    out["rhel_version"] = rhel_number if rhel_number else None

    # 2. Jetpack version (from /etc/nv_tegra_release or similar on Jetson)
    # Target: 2-dot version X.Y.Z (e.g. R32 + REVISION: 7.1 -> "32.7.1"); stored as str since float cannot hold two dots.
    jetpack_raw = _run(ssh, "head -n 1 /etc/nv_tegra_release 2>/dev/null")
    if jetpack_raw:
        r_match = re.search(r"R(\d+)(?:\.(\d+))?", jetpack_raw)
        rev_match = re.search(r"REVISION:\s*([\d.]+)", jetpack_raw)
        if r_match and rev_match:
            # Combine R and REVISION into X.Y.Z (e.g. R32, REVISION: 7.1 -> "32.7.1")
            r_major = int(r_match.group(1))
            r_minor = int(r_match.group(2) or 0)
            rev_str = rev_match.group(1).strip()
            rev_parts = rev_str.split(".")
            rev_first = int(rev_parts[0]) if rev_parts and rev_parts[0].isdigit() else 0
            rev_second = int(rev_parts[1]) if len(rev_parts) > 1 and rev_parts[1].isdigit() else 0
            # Always produce 2-dot version string (e.g. "32.7.1"); float cannot hold two dots
            out["jetpack_version"] = f"{r_major}.{rev_first}.{rev_second}"
        elif rev_match:
            # Only REVISION (one-dot or single number) -> float
            try:
                out["jetpack_version"] = float(rev_match.group(1).strip())
            except ValueError:
                pass
        if out["jetpack_version"] is None and r_match:
            try:
                major = int(r_match.group(1))
                minor = int(r_match.group(2) or 0)
                out["jetpack_version"] = float(f"{major}.{minor}")
            except ValueError:
                pass
        if out["jetpack_version"] is None:
            out["jetpack_version"] = _parse_decimal(jetpack_raw)

    # 3 & 4. Firmware version and type (dmidecode may need sudo)
    dmidecode = _run_sudo(ssh, "dmidecode -t bios 2>/dev/null")
    if dmidecode:
        ver_match = re.search(r"Version:\s*(.+)", dmidecode, re.MULTILINE | re.IGNORECASE)
        if ver_match:
            out["firmware_version"] = _parse_decimal(ver_match.group(1).strip())
        # Firmware type: UEFI vs BIOS
        if "UEFI" in dmidecode.upper() or "EFI" in dmidecode.upper():
            out["firmware_type"] = "UEFI"
        else:
            out["firmware_type"] = "BIOS"
    if out["firmware_type"] is None:
        # Fallback: check /sys/firmware/efi
        efi_check = _run(ssh, "test -d /sys/firmware/efi && echo UEFI || echo BIOS").strip()
        out["firmware_type"] = efi_check if efi_check else None

    # 5. Hardware model name (devicetree on ARM, else dmidecode)
    model = _run(ssh, "cat /sys/firmware/devicetree/base/model 2>/dev/null | tr -d '\\0'")
    if not model:
        sysinfo = _run_sudo(ssh, "dmidecode -t system 2>/dev/null")
        if sysinfo:
            m = re.search(r"Product Name:\s*(.+)", sysinfo, re.MULTILINE | re.IGNORECASE)
            if m:
                model = m.group(1).strip()
    out["hardware_model_name"] = model if model else None

    # 6. Kernel version
    kernel = _run(ssh, "uname -r")
    out["kernel_version"] = kernel if kernel else None

    # 7. CPU arch
    arch = _run(ssh, "uname -m")
    out["cpu_arch"] = arch if arch else None

    # 8–10. Bootc / rpm-ostree (bootc_available defaults False)
    bootc_which = _run(ssh, "which bootc 2>/dev/null")
    rpm_ostree_which = _run(ssh, "which rpm-ostree 2>/dev/null")
    out["bootc_available"] = bool(bootc_which or rpm_ostree_which)
    if out["bootc_available"]:
        ver_out = _run(ssh, "bootc --version 2>/dev/null")
        if ver_out:
            out["bootc_version"] = _parse_decimal(ver_out)
        status_out = _run(ssh, "rpm-ostree status 2>/dev/null")
        if status_out:
            # Try to extract image version (e.g. line with Version: or similar)
            img_ver_match = re.search(r"(?:Version)\s*[:\s]+\s*(\S+.*?)(?:\s*$|\n)", status_out, re.MULTILINE | re.IGNORECASE)
            # Try to extract image URL (e.g. line with Image: or similar)
            img_match = re.search(r"(?:Image|ostree)\s*[:\s]+\s*(\S+.*?)(?:\s*$|\n)", status_out, re.MULTILINE | re.IGNORECASE)
            if img_ver_match:
                out["bootc_image_version"] = img_ver_match.group(1).strip() if img_ver_match.group(1).strip() else None
            if img_match:
                out["bootc_image_url"] = img_match.group(1).strip()
            # Alternative: first URL-like string
            if not out["bootc_image_url"]:
                url_match = re.search(r"(https?://\S+|[\w.-]+/[\w.-]+:[\w.-]+)", status_out)
                if url_match:
                    out["bootc_image_url"] = url_match.group(1).strip()

    return out
