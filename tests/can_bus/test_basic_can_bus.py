"""
CAN bus tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest


class TestCANBus:
    """Test CAN bus functionality on Jetson devices."""

    # available on all Jetson modules (with or without Developer Kit board) because it's a built-in feature of the SoC.
    def test_can(self, ssh):
        """Test CAN bus interfaces are present."""
        result = ssh.sudo("ip -o link show type can")
        assert len(result.stdout.splitlines()) > 0, "No CAN bus interfaces found (should be part of Jetson SoC)"
    
    # TODO: add CAN bus loopback test