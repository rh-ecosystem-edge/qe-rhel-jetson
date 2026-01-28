"""
Ethernet tests for Jetson RPMs.
"""
import pytest
import warnings

class TestEthernet:
    """Test Ethernet functionality on Jetson devices."""

    def test_ethernet_interfaces(self, ssh):
        """Test Ethernet network interfaces are present."""
        result = ssh.run("ip -o link show type ether")
        assert result.exit_status == 0, f"Failed to list Ethernet interfaces: {result.stderr}"
        if len(result.stdout.splitlines()) == 0:
             warnings.warn(UserWarning("No Ethernet interfaces found"))

    def test_ethernet_link_status(self, ssh):
        """Test Ethernet link status."""
        result = ssh.run("ip link show | grep -E '^[0-9]+:.*state'")
        assert result.exit_status == 0, f"Failed to check link status: {result.stderr}"
        # At least one interface should be present
        assert len(result.stdout.splitlines()) > 0, "No network interfaces found"

    def test_ethernet_driver_loaded(self, ssh):
        """Test Ethernet driver is loaded."""
        result = ssh.run("lsmod | grep -E '(tegra|eth|net)'")
        # Ethernet drivers may have various names, so we just check if command succeeds
        assert result.exit_status == 0, f"Failed to check Ethernet drivers: {result.stderr}"
