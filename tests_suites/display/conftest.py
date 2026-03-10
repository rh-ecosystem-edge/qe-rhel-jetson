import pytest
from tests_resources.device_ops import reboot_and_reconnect, set_kernel_arg, get_systemd_target
from tests_suites.conftest import RHEL_VERSION
import os
import warnings


@pytest.fixture(scope="class")
def ensure_pd_ignore_unused(ssh):
    """Ensure pd_ignore_unused is in the kernel cmdline before display tests.

    Only needed on RHEL 9.7 (Tech Preview) + multi-user.target when nvidia_drm
    is manually loaded — without it, modprobe nvidia_drm causes a kernel hang.
    RHEL 9.8+ (GA) does not require this workaround.
    (Source: Rupinder confirmed pd_ignore_unused is only applicable to RHEL 9.7 TP)

    - RHEL 9.8+ or graphical.target -> skip, just yield ssh
    - RHEL 9.7 + multi-user.target + already present -> proceed normally
    - RHEL 9.7 + multi-user.target + missing + Beaker -> add via grubby, reboot
    - RHEL 9.7 + multi-user.target + missing + Jumpstarter -> skip (reboot kills tunnel)
    """
    # Only needed on RHEL 9.7
    if RHEL_VERSION is not None and float(RHEL_VERSION) != 9.7:
        yield ssh
        print("RHEL 9.8+ skipping pd_ignore_unused")
        return

    # graphical.target loads nvidia_drm safely - no need to add pd_ignore_unused
    if get_systemd_target(ssh) == "graphical.target":
        yield ssh
        print("graphical.target - skipping pd_ignore_unused")
        return

    print("setting pd_ignore_unused is needed (RHEL 9.7 + non graphical.target)")
    needs_reboot = set_kernel_arg(ssh, "pd_ignore_unused")
    if not needs_reboot:
        yield ssh
        return

    # Needs reboot to apply. On Jumpstarter this will pytest.skip().
    if os.environ.get("JUMPSTARTER_IN_USE"):
        print("Reboot was needed to set pd_ignore_unused, but not supported through Jumpstarter SSH tunnel")
        warnings.warn(UserWarning(
            "Reboot was needed to set pd_ignore_unused (see jumpstarter/README.md), \
                but not supported through Jumpstarter SSH tunnel — the TCP port-forward breaks when the device goes down"
            ))
    new_ssh = reboot_and_reconnect(ssh)
    # Verify the arg took effect
    check = new_ssh.run("grep -i pd_ignore_unused /proc/cmdline", fail_on_rc=False)
    assert check.exit_status == 0, "pd_ignore_unused not in cmdline after reboot"
    yield new_ssh
