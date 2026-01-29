"""
Tools tests for Jetson RPMs.
Covers nvidia-jetpack-tools: nvpmodel (power model) and nvfancontrol.
"""
import pytest


class TestTools:
    """Test nvidia-jetpack-tools on Jetson devices."""

    def test_nvpmodel_query(self, ssh):
        """Test nvpmodel can report power model (nvidia-jetpack-tools)."""
        result = ssh.run("nvpmodel -q 2>/dev/null")
        assert result.exit_status == 0, f"nvpmodel -q failed: {result.stderr}"
        assert result.stdout.splitlines()[1].isdigit(), "nvpmodel -q produced no power model"
        assert any(m in result.stdout for m in ("7W", "15W", "25W")), "This Power modes should not be supported"
        # Expect some power-model related output
        assert result.stdout.strip(), "nvpmodel produced no output"

    def test_nvfancontrol_available(self, ssh):
        """Test nvfancontrol is available (nvidia-jetpack-tools)."""
        which_result = ssh.run("which nvfancontrol 2>/dev/null")
        if not which_result.stdout.strip():
            pytest.skip("nvfancontrol not in PATH")
        result = ssh.run("nvfancontrol -q 2>/dev/null")
        assert result.exit_status == 0, f"nvfancontrol failed: {result.stderr}"
