"""
CAN bus tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest


class TestCANBus:
    """Test CAN bus functionality on Jetson devices."""

    @pytest.mark.xfail  # not available on Jetson Thor and Jetson Orin Nano Super Developer Kit
    def test_can(self, ssh):
        """Test CAN bus interfaces are present."""
        result = ssh.sudo("ip -o link show type can")
        assert result.exit_status == 0, f"Failed to list CAN interfaces: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No CAN bus interfaces found"
