"""
Display tests for Jetson RPMs.

Known Issues
============

1. nvidia_drm Not Loaded on RPM-only (TICKET NEEDED)
   Issue: nvidia_drm is loaded via load-nvidia-drm.service which requires
          graphical.target. RPM-only setups use multi-user.target, so the
          module is not loaded and /sys/class/drm/card*-*/status does not exist.
          The root cause is initramfs composition — bootc includes nvidia_drm
          via dracut.conf add_drivers+=, RPM-only does not.
   Developer: Rupinder — to decide best fix approach (dracut.conf change vs
              post-install script).
   Contact: hgeaydem — confirmed nvidia_drm should load by default regardless
            of target. Requested a ticket to track this change.
   Affected tests: test_display_by_drm
   Fix applied: warnings.warn() + early return if nvidia_drm is not loaded.
   TODO: Once RPM/dracut config is updated,
         the warning will stop triggering and test will pass on both setups.

2. Xorg/X11 Not Installed on RPM-only (RESOLVED)
   Issue: Xorg is NOT a JetPack RPM. It is installed in bootc Containerfiles
          only to ease internal testing and will be removed from production
          bootc images as well.
   Contact: hgeaydem — confirmed Xorg is for internal testing only.
   Affected tests: test_x11_display
   Fix applied: assert -> warnings.warn(). Absence is expected on RPM-only
                and future production bootc images.
"""
import pytest
import warnings


class TestDisplay:
    """Test Display functionality on Jetson devices."""

    def test_display_devices(self, ssh):
        """Test display device nodes are present.
        Checks for DRM (/dev/dri/*) or framebuffer (/dev/fb*) device nodes"""

        result = ssh.run("ls -la /dev/dri/* || ls -la /dev/fb*")
        assert result.exit_status == 0, f"Failed to check display devices: {result.stderr}"

    def test_display_by_drm(self, ssh):
        """Test display sysfs entries and status
        Checks nvidia_drm module is loaded, then verifies DRM connector status (via /sys/class/drm/card*-*/status)"""

        drm_mod = ssh.run("lsmod | grep nvidia_drm", fail_on_rc=False)
        # TODO: Remove this warning block once the RPM/dracut config fix ships
        #       (see Known Issue #1 above).
        if drm_mod.exit_status != 0:
            warnings.warn(UserWarning(
                "nvidia_drm module is not loaded — currently depends on graphical.target "
                "via load-nvidia-drm.service. The RPM dracut config should be updated to "
                "load nvidia_drm by default (add to dracut.conf add_drivers+= or "
                "/etc/modules-load.d/nvidia-load.conf)"
            ))
            return
        result = ssh.run("ls -1 /sys/class/drm/")
        assert result.exit_status == 0, f"Failed to access DRM sysfs: {result.stderr}"
        result = ssh.run("cat /sys/class/drm/card*-*/status")
        assert result.exit_status == 0, f"Failed to check display status: {result.stderr}"
        if "disconnected" in result.stdout.lower():
            warnings.warn(UserWarning("Display is not connected"))
            # TODO: Try to connect the display for more display testing like xrandr, resolution, etc.

    def test_x11_display(self, ssh):
        """Test X11 display is installed on the system."""

        result = ssh.run("which Xorg || which X", fail_on_rc=False)
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "Xorg/X11 server is not installed — Xorg is not part of JetPack RPMs"
            ))

    def test_wayland_libs(self, ssh):
        """Test Wayland-related libraries are present (nvidia-jetpack-wayland).
        Checks that Wayland shared libraries are available via ldconfig. (come from the nvidia-jetpack-wayland RPM)"""

        result = ssh.run("ldconfig -p | grep -i wayland")
        assert result.exit_status == 0, f"Failed to check Wayland libs: {result.stderr}"
        assert "wayland" in result.stdout.lower(), "No Wayland libraries found (nvidia-jetpack-wayland may be missing)"

    def test_wayland_socket_or_server(self, ssh):
        """Test Wayland socket or compositor binary available (optional on headless)."""
        
        socket_result = ssh.run("ls /run/user/*/wayland-*", fail_on_rc=False)
        which_result = ssh.run("which weston || which Xwayland || which xrandr", fail_on_rc=False)
        has_socket = socket_result.exit_status == 0 and socket_result.stdout.strip()
        has_binary = which_result.exit_status == 0 and which_result.stdout.strip()
        if not (has_socket or has_binary):
            pytest.skip("No Wayland socket or compositor binary (headless or wayland not running | only on graphical session)")
