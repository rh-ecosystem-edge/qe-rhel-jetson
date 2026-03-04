"""
DLA (Deep Learning Accelerator) tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest
import os
from datetime import datetime
from pathlib import Path
from tests_suites import conftest as _conftest

FILE = Path(os.path.realpath(__file__)).parent


class TestDLA:
    """Test DLA functionality on Jetson devices."""

    @pytest.mark.critical
    def test_dla(self, ssh):
        """Test DLA with TensorRT in a container."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        tmp = ssh.run("mktemp -d").stdout.strip()
        ssh.put(FILE / "Dockerfile", f"{tmp}/Dockerfile")
        result = ssh.sudo(
            "podman build --build-arg CACHEBUST={} --device nvidia.com/gpu=all {}".format(
                datetime.now().timestamp(), tmp
            ), fail_on_rc=False
        )
        # check RC
        if not spec.get("dla").get("supported"):
          assert result.exit_status != 0, f"DLA test passed, but not supported (see jetson_hardware_specs.yaml)"
        else:
          assert result.exit_status == 0, f"DLA test failed, RC not 0: {result.stderr}"
          # check output if DLA is supported
          assert ("[V] [TRT] [DlaLayer]" in result.stdout
          ), f"DLA test failed - expected DlaLayer in output: {result.stderr}"
