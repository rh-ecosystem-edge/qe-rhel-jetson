"""
PVA (Programmable Vision Accelerator) tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""

import pytest
import os
from datetime import datetime
from pathlib import Path
from tests_suites import conftest as _conftest

FILE = Path(os.path.realpath(__file__)).parent


class TestPVA:
    """Test PVA functionality on Jetson devices."""

    @pytest.mark.critical
    def test_pva(self, ssh):
        """Test PVA with VPI samples in a container."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        tmp = ssh.run("mktemp -d").stdout.strip()
        ssh.put(FILE / "Dockerfile", f"{tmp}/Dockerfile")
        # Disable PVA authentication for testing
        result = ssh.sudo("ls -1 /sys/kernel/debug/pva0", fail_on_rc=False)
        if not spec.get("pva").get("supported"):
            assert result.exit_status != 0, (
                "/sys/kernel/debug/pva found, but not supported on this hardware (see jetson_hardware_specs.yaml)"
            )
        else:
            assert result.exit_status == 0, (
                f"PVA devices not loaded on the system: {result.stderr}"
            )
            ssh.sudo("bash -c 'echo 0 > /sys/kernel/debug/pva0/vpu_app_authentication'")
            result = ssh.sudo(
                "podman build --build-arg CACHEBUST={} --device nvidia.com/gpu=all {}".format(
                    datetime.now().timestamp(), tmp
                )
            )
            assert result.exit_status == 0, f"PVA test failed: {result.stderr}"
