import pytest
from tests_resources.device_ops import reboot_and_reconnect, set_kernel_arg


@pytest.fixture(scope="class")
def ensure_pd_ignore_unused(ssh):
    """Ensure pd_ignore_unused is in the kernel cmdline before display tests.

    - Already present -> proceed normally
    - Missing + Beaker -> add via grubby, reboot, return new ssh
    - Missing + Jumpstarter -> skip (reboot would kill the SSH tunnel)
    """
    needs_reboot = set_kernel_arg(ssh, "pd_ignore_unused")
    if not needs_reboot:
        yield ssh
        return

    # Needs reboot to apply. On Jumpstarter this will pytest.skip().
    new_ssh = reboot_and_reconnect(ssh)
    # Verify the arg took effect
    check = new_ssh.run("grep -i pd_ignore_unused /proc/cmdline", fail_on_rc=False)
    assert check.exit_status == 0, "pd_ignore_unused not in cmdline after reboot"
    yield new_ssh
