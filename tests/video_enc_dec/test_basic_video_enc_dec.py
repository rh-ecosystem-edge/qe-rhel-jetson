"""
Video Encoder/Decoder tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import pytest


class TestVideoEncDec:
    """Test Video Encoder/Decoder functionality on Jetson devices."""

    def test_hardware_video_acceleration(self, ssh):
        """Test hardware video acceleration with GStreamer."""
        result = ssh.sudo(
            "gst-launch-1.0 videotestsrc num-buffers=300 ! nvvidconv ! nvv4l2h264enc ! nvv4l2decoder ! fakesink"
        )
        assert result.exit_status == 0, f"Video acceleration test failed: {result.stderr}"
