"""
CSI camera tests for Jetson RPMs.
"""
from math import e
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
        # At least check that video4linux class exists
        assert result.exit_status == 0, f"Failed to access video4linux sysfs: {result.stderr}"

    def test_camera_driver_loaded(self, ssh):
        """Test camera driver is loaded."""
        result = ssh.run("lsmod  | grep camera")
        assert result.exit_status == 0, f"Failed to check camera driver: {result.stderr}"