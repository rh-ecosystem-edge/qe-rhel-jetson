"""
Tools tests for Jetson RPMs.
Covers nvidia-jetpack-tools: nvpmodel (power model) and nvfancontrol.
"""
import pytest
from tests import conftest as _conftest


class TestTools:
    """Test nvidia-jetpack-tools on Jetson devices."""

    def test_nvpmodel_query(self, ssh):
        """Test nvpmodel can report power model (nvidia-jetpack-tools)."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        expected_modes = tuple(spec.get("tools").get("power_modes"))
        result = ssh.run("nvpmodel -q 2>/dev/null")
        assert result.exit_status == 0, f"nvpmodel -q failed: {result.stderr}"
        # Check if the power model is a number in the second line of the output
        assert result.stdout.splitlines()[1].isdigit(), "nvpmodel -q produced no power model"
        # Check if the power model is in the expected modes (according jetson_hardware_specs.yaml)
        assert any(m in result.stdout for m in expected_modes), (
            f"Expected one of power modes {expected_modes} in nvpmodel output"
        )
        assert result.stdout.strip(), "nvpmodel produced no output"

    def test_nvfancontrol_available(self, ssh):
        """Test nvfancontrol is available (nvidia-jetpack-tools)."""
        which_result = ssh.run("which nvfancontrol 2>/dev/null")
        if not which_result.stdout.strip():
            pytest.skip("nvfancontrol not in PATH")
        result = ssh.run("nvfancontrol -q 2>/dev/null")
        assert result.exit_status == 0, f"nvfancontrol failed: {result.stderr}"
