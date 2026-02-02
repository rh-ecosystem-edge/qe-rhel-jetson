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

    #def test_usb_spec(self, ssh):
    #    """Test USB specification."""
    #    spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
    #    ssh.sudo("dnf install usbutils -y") # for lsusb cli tool
    #    for controller, values in spec.get("usbs").items():

# 480M = USB2.0 / For charging only
# 5000M/ 10000M = USB3.0/ USB3.2 Gen2
# xusb/4p = 4x Ports