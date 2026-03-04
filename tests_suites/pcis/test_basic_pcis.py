"""
PCI tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest
from tests_suites import conftest as _conftest


class TestPCIs:
    """Test PCI functionality on Jetson devices."""

    def test_pcie(self, ssh):
        """Test PCI devices are present."""
        result = ssh.sudo("ls -1 /sys/bus/pci/devices/")
        assert result.exit_status == 0, f"Failed to list PCI devices: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No PCI devices found"

    # TODO: PCI specification is different on AGX Orin from Nano, not sure why
    def test_pci_spec(self, ssh):
        """Test PCI specification."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        ssh.sudo("dnf install pciutils -y") # for lspci cli tool
        # check controllers present with expected speed and amount of lanes
        for controller, values in spec.get("pcis").items():
            capable_speed = values.get("capable_speed")
            lanes = values.get("lanes")
            result = ssh.sudo(f"lspci -vv | grep -P 'LnkCap:' | grep -E '{capable_speed}' | grep -E 'Width x{lanes}'")
            assert result.exit_status == 0, f"Failed to find PCI controller {controller} with speed {capable_speed} and amount of lanes {lanes}: {result.stderr}"

        #TODO will check the lanes and logical slots later according ubuntu kernel version
        # check if the correct, speed, lanes and min required logical slots are present 
        #for controller, values in spec.get("pcis").items():
        #  capable_speed = values.get("capable_speed")
        #  lanes = values.get("lanes")
        #  result = ssh.sudo(f"lspci -vv | grep -P 'LnkCap:' | grep -E '{capable_speed}GT' | grep -E 'Width x{lanes}'")
        #  assert result.exit_status == 0, f"Failed to find PCI controller {controller}: {result.stderr}"
        #  assert len(result.stdout.splitlines()) >= values.get("logical_slots"), f"Found {len(result.stdout.splitlines())} {controller} controllers, but expected at least {values.get('logical_slots')} logical slots for {controller}"
