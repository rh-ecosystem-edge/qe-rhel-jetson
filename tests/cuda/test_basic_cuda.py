"""
CUDA tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest
import os
from datetime import datetime
from pathlib import Path

FILE = Path(os.path.realpath(__file__)).parent


class TestCUDA:
    """Test CUDA functionality on Jetson devices."""

    @pytest.mark.critical
    def test_cuda(self, ssh):
        """Test CUDA with PyTorch in a container."""
        tmp = ssh.run("mktemp -d").stdout.strip()
        ssh.put(FILE / "Dockerfile", f"{tmp}/Dockerfile")
        result = ssh.sudo(
            "podman build --build-arg CACHEBUST={} --device nvidia.com/gpu=all {}".format(
                datetime.now().timestamp(), tmp
            )
        )
        assert result.exit_status == 0, f"CUDA test failed: {result.stderr}"
