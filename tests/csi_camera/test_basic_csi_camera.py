"""
CSI camera tests for Jetson RPMs.

NOTE: MIPI/CSI2 camera modules (tegra_camera_platform, tegra_camera_rtcpu) are
blacklisted in kmod RPM's nvidia-camera.conf because they require kernel patches
not available in RHEL 9. The camera RPM itself is ready, but underlying kernel
support is only confirmed for RHEL 10 (see RHEL-56474, RHELBU-2601).

Camera tests should stay OPTIONAL (warnings, not hard asserts) for RHEL 9:
  - MIPI/CSI2 cameras are NOT a GA feature for RHEL 9
  - Most customers are aware and use USB or network cameras instead (no kmods needed)
  - One customer requested Allied Vision MIPI cameras — Nirmala Dalvi has it on her
    list to test with 9.7/9.8 nightly, but no GA commitment was made
  - On bootc, dracut may bypass the blacklist so modules load — this is an initramfs
    side effect, not an indication that camera functionality works

Future:
  - If MIPI/CSI2 support lands in RHEL 9.8+: unblacklist and convert to asserts
  - For RHEL 10+: convert to asserts (kernel patches confirmed — RHEL-56474, RHELBU-2601)
"""
import pytest
import warnings


class TestCSICamera:
    """Test CSI camera functionality on Jetson devices."""

    def test_csi_camera_devices(self, ssh):
        """Test CSI camera device nodes are present."""
        result = ssh.run("ls -la /dev/video*")
        # /dev/video* nodes are created by the videodev module when camera drivers load.
        # Camera drivers are blacklisted on RHEL 9 due to missing kernel support
        # (MIPI/CSI2 patches target RHEL 10 — see RHEL-56474, RHELBU-2601).
        # TODO: Convert to assert once camera support is confirmed for the RHEL version.
        if result.exit_status != 0:
            warnings.warn(UserWarning("No CSI camera (/dev/video*) devices found"))

    def test_csi_camera_sysfs(self, ssh):
        """Test CSI camera sysfs entries."""
        result = ssh.run("ls -1 /sys/class/video4linux/")
        # /sys/class/video4linux/ is created by the videodev module, which only loads
        # when camera drivers load. Camera drivers (tegra_camera_platform, etc.) are
        # blacklisted in nvidia-camera.conf because MIPI/CSI2 support requires kernel
        # patches not yet available on RHEL 9 (see RHEL-56474, RHELBU-2601).
        # On bootc, dracut may bypass the blacklist (initramfs side effect, not functional).
        # TODO: Convert to assert once camera support is confirmed for the RHEL version.
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "No /sys/class/video4linux/ found — camera kernel modules are "
                "blacklisted in nvidia-camera.conf (MIPI/CSI2 requires kernel patches "
                "not available on RHEL 9, targeting RHEL 10 — see RHEL-56474)"
            ))

    def test_camera_driver_loaded(self, ssh):
        """Test camera driver is loaded."""
        result = ssh.run("lsmod | grep camera")
        # Camera modules (tegra_camera_platform, tegra_camera_rtcpu) are blacklisted
        # in kmod RPM's nvidia-camera.conf. The blacklist exists because MIPI/CSI2
        # camera support requires kernel patches only targeting RHEL 10 (RHEL-56474,
        # RHELBU-2601).
        # TODO: Convert to assert once camera support is confirmed for the RHEL version.
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "No camera kernel modules loaded — blacklisted in nvidia-camera.conf "
                "(MIPI/CSI2 requires kernel patches not available on RHEL 9, "
                "targeting RHEL 10 — see RHEL-56474, RHELBU-2601)"
            ))
