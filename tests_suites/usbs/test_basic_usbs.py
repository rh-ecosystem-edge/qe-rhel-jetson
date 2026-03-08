"""
USB tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""

# 480M = USB2.0 / For charging only
# 5000M/ 10000M = USB3.2 Gen1/ USB3.2 Gen2
# hub/4p = 4x Ports

import pytest
from tests_suites import conftest as _conftest


class TestUSBs:
    """Test USB functionality on Jetson devices."""

    def test_usb(self, ssh):
        """Test USB devices are present."""
        result = ssh.sudo("ls -1 /sys/bus/usb/devices/")
        assert result.exit_status == 0, f"Failed to list USB devices: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No USB devices found"

    # TODO: add USB specification test
    def test_usb_spec(self, ssh):
        """
        Test USB specification.
        Check if controllers with expected values (capable_speed and ports) are present.
        Check if the amount of controllers with the same spec values present as amount of lines in lsusb output.
        """
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        ssh.sudo("dnf install usbutils -y")  # for lsusb cli tool
        usbs = spec.get("usbs")

        # Group by (ports, capable_speed): count controllers (keys) with same spec
        spec_groups = {}
        for _, values in usbs.items():
            capable_speed = values.get("capable_speed")
            ports = values.get("ports")
            key = (ports, capable_speed)
            spec_groups[key] = spec_groups.get(key, 0) + 1

        for (ports, capable_speed), amount_of_same_spec_controllers in spec_groups.items():
            result = ssh.sudo(f"lsusb -t | grep -v Bus | grep {ports}p | grep {capable_speed}")
            assert result.exit_status == 0, (f"Failed to find USB with speed {capable_speed} and {ports} ports: {result.stderr}")
            lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
            assert len(lines) == amount_of_same_spec_controllers, (
                f"Expected {amount_of_same_spec_controllers} line(s) for {ports}p @ {capable_speed} "
                f"({amount_of_same_spec_controllers} controller(s) in spec), got {len(lines)}: {result.stdout}"
            )
