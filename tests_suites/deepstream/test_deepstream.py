"""Camera-independent DeepStream smoke tests.

These tests validate that the DeepStream runtime and core GStreamer plugins
can start and process synthetic frames.  CSI/Argus camera capture is not
covered here because it requires a physical sensor and the Jetson ISP.
"""

import os
import shlex

import pytest

from tests_resources.container_ops import podman_command, run_container


DEEPSTREAM_IMAGE = os.getenv(
    "DEEPSTREAM_IMAGE", "nvcr.io/nvidia/deepstream:7.1-samples-multiarch"
)
DEEPSTREAM_PULL_TIMEOUT = int(os.getenv("DEEPSTREAM_PULL_TIMEOUT", "1800"))


@pytest.mark.extra
class TestDeepStream:
    """Smoke-test the DeepStream runtime without requiring a camera or ISP."""

    @pytest.fixture(scope="class")
    def deepstream_image(self, ssh):
        """Pull DeepStream if needed and remove only images pulled by this class."""
        image = shlex.quote(DEEPSTREAM_IMAGE)
        exists = ssh.sudo(
            podman_command(f"image exists {image}"),
            fail_on_rc=False,
            print_output=False,
        ).exit_status == 0

        remove_after = not exists
        try:
            if remove_after:
                result = ssh.sudo(
                    podman_command(f"pull {image}"),
                    timeout=DEEPSTREAM_PULL_TIMEOUT,
                    fail_on_rc=False,
                )
                if result.exit_status != 0:
                    pytest.fail(
                        f"Failed to pull DeepStream image {DEEPSTREAM_IMAGE}: "
                        f"{result.stderr or result.stdout}"
                    )

            yield DEEPSTREAM_IMAGE
        finally:
            if remove_after:
                ssh.sudo(
                    podman_command(f"rmi -f {image}"),
                    fail_on_rc=False,
                    print_output=False,
                )
                ssh.sudo(
                    podman_command("image prune -f"),
                    fail_on_rc=False,
                    print_output=False,
                )

    def test_runtime_and_core_plugins(self, ssh, deepstream_image):
        """DeepStream starts and exposes the core inference/video plugins."""
        result = run_container(
            ssh,
            deepstream_image,
            "bash -lc 'set -e; "
            "deepstream-app --version; "
            "gst-inspect-1.0 nvinfer >/dev/null; "
            "gst-inspect-1.0 nvvideoconvert >/dev/null; "
            "gst-inspect-1.0 nvstreammux >/dev/null'",
            timeout=120,
        )
        assert result.exit_status == 0, (
            f"DeepStream runtime/plugin check failed: {result.stderr}\n{result.stdout}"
        )
        assert "DeepStream" in result.stdout, (
            f"DeepStream version was not reported: {result.stdout}"
        )

    def test_synthetic_video_conversion(self, ssh, deepstream_image):
        """Process synthetic frames through the DeepStream video converter."""
        result = run_container(
            ssh,
            deepstream_image,
            "gst-launch-1.0 -e "
            "videotestsrc num-buffers=30 pattern=ball ! "
            "video/x-raw,width=640,height=480,framerate=30/1 ! "
            "nvvideoconvert ! fakesink sync=false",
            timeout=120,
        )
        assert result.exit_status == 0, (
            f"DeepStream synthetic conversion failed: {result.stderr}\n{result.stdout}"
        )
        assert "Got EOS" in result.stdout, (
            f"Synthetic conversion did not reach EOS: {result.stdout}"
        )

    def test_synthetic_streammux(self, ssh, deepstream_image):
        """Batch one synthetic NVMM stream through nvstreammux."""
        result = run_container(
            ssh,
            deepstream_image,
            "gst-launch-1.0 -e "
            "nvstreammux name=mux batch-size=1 width=640 height=480 live-source=0 ! "
            "fakesink sync=false "
            "videotestsrc num-buffers=30 is-live=false ! "
            "video/x-raw,format=I420,width=640,height=480,framerate=30/1 ! "
            "nvvideoconvert ! "
            "'video/x-raw(memory:NVMM),format=NV12' ! mux.sink_0",
            timeout=120,
        )
        assert result.exit_status == 0, (
            f"DeepStream synthetic streammux failed: {result.stderr}\n{result.stdout}"
        )
        assert "Got EOS" in result.stdout, (
            f"Synthetic streammux did not reach EOS: {result.stdout}"
        )
