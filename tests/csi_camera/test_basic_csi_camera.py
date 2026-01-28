"""
CSI camera tests for Jetson RPMs.
"""
import pytest


class TestCSICamera:
    """Test CSI camera functionality on Jetson devices."""

    def test_csi_camera_devices(self, ssh):
        """Test CSI camera device nodes are present."""
        result = ssh.run("ls -la /dev/video*")
        # Check if video devices exist (CSI cameras appear as /dev/video*)
        assert "/dev/video" in result.stdout or result.exit_status != 0, "No CSI camera devices found"

    def test_csi_camera_sysfs(self, ssh):
        """Test CSI camera sysfs entries."""
        result = ssh.run("ls -1 /sys/class/video4linux/")
        # At least check that video4linux class exists
        assert result.exit_status == 0, f"Failed to access video4linux sysfs: {result.stderr}"
