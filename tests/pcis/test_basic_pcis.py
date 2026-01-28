"""
PCI tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest


class TestPCIs:
    """Test PCI functionality on Jetson devices."""

    def test_pcie(self, ssh):
        """Test PCI devices are present."""
        result = ssh.sudo("ls -1 /sys/bus/pci/devices/")
        assert result.exit_status == 0, f"Failed to list PCI devices: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No PCI devices found"
