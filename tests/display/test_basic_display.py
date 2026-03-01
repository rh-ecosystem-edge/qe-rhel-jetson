"""
Display tests for Jetson RPMs.
"""
import pytest
import warnings


class TestDisplay:
    """Test Display functionality on Jetson devices."""

    def test_display_devices(self, ssh):
        """Test display device nodes are present."""
        result = ssh.run("ls -la /dev/dri/* 2>/dev/null || ls -la /dev/fb* 2>/dev/null")
        # Check for framebuffer or DRM devices
        assert result.exit_status == 0, f"Failed to check display devices: {result.stderr}"

    def test_display_by_drm(self, ssh):
        """Test display sysfs entries and status"""
        # nvidia_drm is currently loaded via load-nvidia-drm.service (requires graphical.target).
        # On RPM-only setups using multi-user.target, nvidia_drm won't be loaded and

        # /sys/class/drm/card*-*/status won't exist. The root cause is initramfs composition
        # (dracut.conf add_drivers+=) — bootc includes it in initramfs, RPM-only does not.

        # The nvidia-jetson-sidecar team confirmed nvidia_drm should load by default
        # regardless of target. Once the RPM/dracut config is updated, this warning
        # will no longer trigger and the test will pass on both setups.
        #TODO: Once the RPM/dracut config is updated, this warning will no longer trigger and the test will pass on both setups.
        drm_mod = ssh.run("lsmod | grep nvidia_drm")
        if drm_mod.exit_status != 0:
            warnings.warn(UserWarning(
                "nvidia_drm module is not loaded — currently depends on graphical.target "
                "via load-nvidia-drm.service. The RPM dracut config should be updated to "
                "load nvidia_drm by default (add to dracut.conf add_drivers+= or "
                "/etc/modules-load.d/nvidia-load.conf)"
            ))
            return
        # Check that DRM class exists
        result = ssh.run("ls -1 /sys/class/drm/ 2>/dev/null")
        assert result.exit_status == 0, f"Failed to access DRM sysfs: {result.stderr}"
        # Check that the status is connected
        result = ssh.run("cat /sys/class/drm/card*-*/status")
        assert result.exit_status == 0, f"Failed to check display status: {result.stderr}"
        if "disconnected" in result.stdout.lower():
             warnings.warn(UserWarning("Display is not connected"))
             # TODO: Try to connect the display for more display testing like xrandr, resolution, etc.

    def test_x11_display(self, ssh):
        """Test X11 display if available."""
        result = ssh.run("which Xorg 2>/dev/null || which X 2>/dev/null")
        # Xorg is NOT a JetPack RPM — it's installed in bootc Containerfiles only to
        # ease internal testing and will be removed from production images.
        # Its absence is expected on RPM-only setups and future production bootc images.
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "Xorg/X11 server is not installed — Xorg is not part of JetPack RPMs "
                "(installed in bootc for internal testing only, not in production images)"
            ))

    def test_wayland_libs(self, ssh):
        """Test Wayland-related libraries are present (nvidia-jetpack-wayland)."""
        # Wayland is the modern replacement for X11
        result = ssh.run("ldconfig -p 2>/dev/null | grep -i wayland")
        assert result.exit_status == 0, f"Failed to check Wayland libs: {result.stderr}"
        # At least one wayland-related lib expected when wayland stack is installed
        assert "wayland" in result.stdout.lower(), "No Wayland libraries found (nvidia-jetpack-wayland may be missing)"

    def test_wayland_socket_or_server(self, ssh):
        """Test Wayland socket or compositor binary available (optional on headless)."""
        socket_result = ssh.run("ls /run/user/*/wayland-* 2>/dev/null")
        which_result = ssh.run("which weston 2>/dev/null || which Xwayland 2>/dev/null || which xrandr 2>/dev/null")
        has_socket = socket_result.exit_status == 0 and socket_result.stdout.strip()
        has_binary = which_result.exit_status == 0 and which_result.stdout.strip()
        if not (has_socket or has_binary):  #exists only when a user is logged into a graphical session
            pytest.skip("No Wayland socket or compositor binary (headless or wayland not running | only on graphical session)")
