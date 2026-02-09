"""
PCI tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest
from tests import conftest as _conftest

# Repo base URL for RHEL 9.7
REPO_BASEURL = "http://download.eng.rdu.redhat.com/released/rhel-9/RHEL-9/9.7.0/BaseOS/aarch64/os/"

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
        ssh.sudo(f"dnf config-manager --add-repo {REPO_BASEURL}")
        ssh.sudo("dnf install pciutils -y --transient") # for lspci cli tool
        for controller, values in spec.get("pcis").items():
          capable_speed = values.get("capable_speed")
          lanes = values.get("lanes")
          result = ssh.sudo(f"lspci -vv | grep -P 'LnkCap:' | grep -A 1 'Port' | grep -E '{capable_speed}GT' | grep -E 'Width x{lanes}'")
          assert result.exit_status == 0, f"Failed to find PCI controller {controller}: {result.stderr}"
          assert len(result.stdout.splitlines()) >= values.get("logical_slots"), f"Found {len(result.stdout.splitlines())} {controller} controllers, but expected at least {values.get('logical_slots')} logical slots for {controller}"
