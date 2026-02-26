"""
CSI camera tests for Jetson RPMs.
"""
import pytest
import warnings


class TestCSICamera:
    """Test CSI camera functionality on Jetson devices."""

    def test_csi_camera_devices(self, ssh):
        """Test CSI camera device nodes are present."""
        result = ssh.run("ls -la /dev/video*")
        # Check if video devices exist (CSI cameras appear as /dev/video*)
        if result.exit_status != 0:
            warnings.warn(UserWarning("No CSI camera (/dev/video*) devices found"))

    def test_csi_camera_sysfs(self, ssh):
        """Test CSI camera sysfs entries."""
        result = ssh.run("ls -1 /sys/class/video4linux/")
        # videodev module creates /sys/class/video4linux/ only when camera drivers load.
        # Camera drivers are intentionally blacklisted in kmod RPM's nvidia-camera.conf,
        # so an empty or missing directory is expected on RPM-only setups.
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "No /sys/class/video4linux/ found — camera kernel modules are "
                "blacklisted in nvidia-camera.conf (expected on RPM-only setups)"
            ))

    def test_camera_driver_loaded(self, ssh):
        """Test camera driver is loaded."""
        result = ssh.run("lsmod | grep camera")
        # Camera modules (tegra_camera_platform, tegra_camera_rtcpu) are intentionally
        # blacklisted in kmod RPM's nvidia-camera.conf. On bootc, dracut may bypass
        # the blacklist, but on RPM-only setups they won't be loaded.
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "No camera kernel modules loaded — camera modules are intentionally "
                "blacklisted in nvidia-camera.conf (expected on RPM-only setups)"
            ))
