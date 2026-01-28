"""
USB tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest


class TestUSBs:
    """Test USB functionality on Jetson devices."""

    def test_usb(self, ssh):
        """Test USB devices are present."""
        result = ssh.sudo("ls -1 /sys/bus/usb/devices/")
        assert result.exit_status == 0, f"Failed to list USB devices: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No USB devices found"
