"""
CUDA tests for Jetson RPMs.
- PyTorch container: multiply two random tensors on the GPU.
- NVIDIA samples: deviceQuery and bandwidthTest (basic CUDA validation).
"""
import pytest
import os
from datetime import datetime
from pathlib import Path

FILE = Path(os.path.realpath(__file__)).parent

# NVIDIA CUDA samples image (same as orin-kmods)
CUDA_SAMPLES_IMAGE = "quay.io/sroyer/jetpack-6-cuda-12.2-samples:latest"


class TestCUDA:
    """Test CUDA functionality on Jetson devices."""

    @pytest.mark.critical
    def test_cuda_pytorch_container(self, ssh):
        """Test CUDA with PyTorch in a container (multiply tensors on GPU)."""
        tmp = ssh.run("mktemp -d").stdout.strip()
        ssh.put(FILE / "Dockerfile", f"{tmp}/Dockerfile")
        result = ssh.sudo(
            "podman build --build-arg CACHEBUST={} --device nvidia.com/gpu=all {}".format(datetime.now().timestamp(), tmp)
            , fail_on_rc=False
        )
        assert result.exit_status == 0, f"CUDA test failed: {result.stderr}"

    def test_cuda_device_query(self, ssh):
        """Test CUDA with NVIDIA deviceQuery sample (GPU properties)."""
        result = ssh.sudo(
            "podman run --rm --device nvidia.com/gpu=all {} deviceQuery".format(CUDA_SAMPLES_IMAGE),
            timeout=120, fail_on_rc=False
        )
        assert result.exit_status == 0, f"CUDA deviceQuery failed: {result.stderr}"
        assert "CUDA" in result.stdout, "CUDA deviceQuery produced no CUDA output"

    def test_cuda_bandwidth_test(self, ssh):
        """Test CUDA with NVIDIA bandwidthTest sample (memory bandwidth)."""
        result = ssh.sudo(
            "podman run --rm --device nvidia.com/gpu=all {} bandwidthTest".format(CUDA_SAMPLES_IMAGE),
            timeout=120, fail_on_rc=False
        )
        assert result.exit_status == 0, f"CUDA bandwidthTest failed: {result.stderr}"
