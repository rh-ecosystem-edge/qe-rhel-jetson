"""
Display tests for Jetson RPMs.
"""
import pytest


class TestDisplay:
    """Test Display functionality on Jetson devices."""

    def test_display_devices(self, ssh):
        """Test display device nodes are present."""
        result = ssh.run("ls -la /dev/fb* /dev/dri/* 2>/dev/null")
        # Check for framebuffer or DRM devices
        assert result.exit_status == 0, f"Failed to check display devices: {result.stderr}"

    def test_display_sysfs(self, ssh):
        """Test display sysfs entries."""
        result = ssh.run("ls -1 /sys/class/drm/ 2>/dev/null")
        # Check that DRM class exists
        assert result.exit_status == 0, f"Failed to access DRM sysfs: {result.stderr}"

    def test_x11_display(self, ssh):
        """Test X11 display if available."""
        result = ssh.run("which Xorg 2>/dev/null || which X 2>/dev/null")
        # X server may or may not be installed, so we just check if command succeeds
        assert result.exit_status == 0, f"Failed to check for X server: {result.stderr}"

    def test_wayland_libs(self, ssh):
        """Test Wayland-related libraries are present (nvidia-jetpack-wayland)."""
        result = ssh.run("ldconfig -p 2>/dev/null | grep -i wayland")
        assert result.exit_status == 0, f"Failed to check Wayland libs: {result.stderr}"
        # At least one wayland-related lib expected when wayland stack is installed
        assert "wayland" in result.stdout.lower(), "No Wayland libraries found (nvidia-jetpack-wayland may be missing)"

    def test_wayland_socket_or_server(self, ssh):
        """Test Wayland socket or compositor binary available (optional on headless)."""
        socket_result = ssh.run("ls /run/user/*/wayland-* 2>/dev/null")
        which_result = ssh.run("which weston 2>/dev/null || which Xwayland 2>/dev/null")
        has_socket = socket_result.exit_status == 0 and socket_result.stdout.strip()
        has_binary = which_result.exit_status == 0 and which_result.stdout.strip()
        if not (has_socket or has_binary):  #exists only when a user is logged into a graphical session
            pytest.skip("No Wayland socket or compositor binary (headless or wayland not running | only on graphical session)")
