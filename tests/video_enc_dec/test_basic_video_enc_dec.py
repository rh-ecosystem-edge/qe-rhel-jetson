"""
Video Encoder/Decoder tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
# References:
# Install EPEL repository on RHEL: https://www.redhat.com/en/blog/install-epel-linux

import pytest
from tests import conftest as _conftest
import warnings

class TestVideoEncDec:
    """Test Video Encoder/Decoder functionality on Jetson devices."""

    def test_hardware_video_acceleration(self, ssh):
        """Test hardware video acceleration with GStreamer."""
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        if not spec.get("video_enc").get("supported"):
          warnings.warn(UserWarning("Only Video Decoder is supported on this hardware (see jetson_hardware_specs.yaml), running test with Video Decoder only"))
          ssh.sudo("dnf install gstreamer1-plugin-openh264 -y") # for openh264enc CPU encoding
          ssh.sudo("dnf install gstreamer1-plugins-good gstreamer1-plugins-bad-free -y") # for h264parse
          result = ssh.sudo(
            # Using the Cisco OpenH264 software encoder (running on your CPU) instead of the NVIDIA GPU encoder (nvv4l2h264enc)
            "gst-launch-1.0 videotestsrc num-buffers=300 ! openh264enc usage-type=camera complexity=low ! h264parse ! nvv4l2decoder ! fakesink"
          )
        else:
          result = ssh.sudo(
              "gst-launch-1.0 videotestsrc num-buffers=300 ! nvvidconv ! nvv4l2h264enc ! nvv4l2decoder ! fakesink"
          )
        assert result.exit_status == 0, f"Video acceleration test failed: {result.stderr}"
