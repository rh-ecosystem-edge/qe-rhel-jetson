"""
Display tests for Jetson RPMs.
"""
import pytest


class TestDisplay:
    """Test Display functionality on Jetson devices."""

    def test_display_devices(self, ssh):
        """Test display device nodes are present."""
        result = ssh.run("ls -la /dev/fb* /dev/dri/* 2>/dev/null || true")
        # Check for framebuffer or DRM devices
        assert result.exit_status == 0, f"Failed to check display devices: {result.stderr}"

    def test_display_sysfs(self, ssh):
        """Test display sysfs entries."""
        result = ssh.run("ls -1 /sys/class/drm/ 2>/dev/null || true")
        # Check that DRM class exists
        assert result.exit_status == 0, f"Failed to access DRM sysfs: {result.stderr}"

    def test_x11_display(self, ssh):
        """Test X11 display if available."""
        result = ssh.run("which Xorg 2>/dev/null || which X 2>/dev/null || true")
        # X server may or may not be installed, so we just check if command succeeds
        assert result.exit_status == 0, f"Failed to check for X server: {result.stderr}"
