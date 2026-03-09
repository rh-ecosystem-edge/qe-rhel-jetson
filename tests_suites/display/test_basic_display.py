"""
Display tests for Jetson RPMs.

Known Issues
============

1. nvidia_drm Loading Behavior (NVIDIA-580 — RESOLVED)
   Issue: nvidia_drm is loaded via load-nvidia-drm.service which requires
          graphical.target. On multi-user.target the module is not auto-loaded.
   Resolution: Henry and Rupinder agreed that nvidia_drm loading should be
               inferred at runtime — load it if/when needed. It is NOT expected
               to auto-load on multi-user.target. This is not a bug.
   Henry: "the module loading should be inferred at runtime (e.g. load it
           if/when we need it), could also be an optional drm package tied
           to all the jetpack wayland and vulkan support packages"
   Rupinder: "ok, at runtime then, load a module if needed. Modify the test
              to first insert a module if not loaded already before running
              the display test case."
   Affected tests: test_display_by_drm
   Test logic:
     - graphical.target + nvidia_drm loaded     → expected, test DRM status
     - graphical.target + nvidia_drm NOT loaded  → fail (service should load it)
     - multi-user.target + nvidia_drm loaded     → test DRM status
     - multi-user.target + nvidia_drm NOT loaded → load on demand, test DRM status
   WARNING: Rupinder noted that loading nvidia_drm on multi-user.target with RHEL 9.7
            requires 'pd_ignore_unused' in kernel cmdline to avoid kernel hang.
   TODO: Henry noted nvidia_drm may be needed even without wayland/graphical target
         (e.g. for non-display workloads). Impact analysis needed — test workloads on
         multi-user.target with nvidia_drm loaded to verify stability and whether the
         module affects non-graphical workloads.

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

        result = ssh.run("ls -la /dev/dri/* || ls -la /dev/fb*", fail_on_rc=False)
        assert result.exit_status == 0, f"Failed to check display devices: {result.stderr}"

    def test_display_by_drm(self, ensure_pd_ignore_unused):
        """Test display sysfs entries and DRM connector status.
        Verifies nvidia_drm loading behavior based on systemd target, then checks
        /sys/class/drm/card*-*/status for display connection (see Known Issue #1)."""
        ssh = ensure_pd_ignore_unused
        
        # Step 1: Check systemd target
        target_result = ssh.run("systemctl get-default", fail_on_rc=False)
        assert target_result.exit_status == 0, f"Failed to get systemd target: {target_result.stderr}"
        systemd_target = target_result.stdout.strip()

        # Step 2: Check if nvidia_drm is loaded
        drm_mod = ssh.run("lsmod | grep nvidia_drm", fail_on_rc=False)
        drm_loaded = drm_mod.exit_status == 0
        print(f"drm_loaded: {drm_loaded}")

        # Step 3: Handle based on target + module state
        if systemd_target == "graphical.target" and not drm_loaded:
            # graphical.target should auto-load nvidia_drm via load-nvidia-drm.service
            assert False, (
                "nvidia_drm is NOT loaded on graphical.target — "
                "load-nvidia-drm.service should have loaded it"
            )

        if not drm_loaded:
            # multi-user.target: nvidia_drm is not auto-loaded, load on demand
            load_result = ssh.sudo("modprobe nvidia_drm", fail_on_rc=False)
            assert load_result.exit_status == 0, (
                f"Failed to load nvidia_drm on demand: {load_result.stderr}"
            )

        # Step 4: Test DRM connector status
        result = ssh.run("ls -1 /sys/class/drm/", fail_on_rc=False)
        assert result.exit_status == 0, f"Failed to access DRM sysfs: {result.stderr}"
        result = ssh.run("cat /sys/class/drm/card*-*/status", fail_on_rc=False)
        assert result.exit_status == 0, f"Failed to check display status: {result.stderr}"
        if "disconnected" in result.stdout.lower():
            warnings.warn(UserWarning("Display is not connected"))

    def test_x11_display(self, ssh):
        """Test X11 display is installed on the system.- Warn if not installed."""

        result = ssh.run("which Xorg || which X", fail_on_rc=False)
        if result.exit_status != 0:
            warnings.warn(UserWarning(
                "Xorg/X11 server is not installed — Xorg is not part of JetPack RPMs"
            ))

    def test_wayland_libs(self, ssh):
        """Test Wayland-related libraries are present (nvidia-jetpack-wayland).
        Checks that Wayland shared libraries are available via ldconfig. (come from the nvidia-jetpack-wayland RPM)"""

        result = ssh.run("ldconfig -p | grep -i wayland", fail_on_rc=False)
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
