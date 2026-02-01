"""
CAN bus tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest
from tests import conftest as _conftest


class TestCANBus:
    """Test CAN bus functionality on Jetson devices."""

    # not available on Jetson Orin Nano Super Developer Kit
    def test_can(self, ssh):
        """Test CAN bus interfaces are present."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        result = ssh.sudo("ip -o link show type can")
        if spec.get("can_bus").get("supported"):
          assert len(result.stdout.splitlines()) > 0, "No CAN bus interfaces found"
        else:
          assert len(result.stdout.splitlines()) == 0, "CAN bus interfaces found, but not supported (see jetson_hardware_specs.yaml)"
