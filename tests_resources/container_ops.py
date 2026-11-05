"""
General container build/run utilities for test suites.
Works with ANY Dockerfile (L4T, PyTorch, TensorRT, Ubuntu, etc.).

Key principle: Dockerfiles only COMPILE, never RUN tests.
Test execution happens via run_container() so each test gets individual pass/fail.
"""
import os
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# RHEL/Podman GPU flags (CDI-based, replaces Docker's --runtime nvidia)
PODMAN_GPU_FLAGS = "--device nvidia.com/gpu=all --group-add keep-groups --security-opt label=disable --net=host"

# Configurable L4T image. None means no compatible image is published for
# the detected host L4T version.
L4T_JETPACK_IMAGE: Optional[str] = os.getenv("L4T_JETPACK_IMAGE") or None

# NGC l4t-jetpack tags. Never select a different L4T major: its userspace and
# host CDI libraries may be incompatible.
PUBLISHED_L4T_JETPACK_TAGS = (
    "r36.4.0",
    "r36.3.0",
    "r36.2.0",
    "r35.4.1",
    "r35.3.1",
    "r35.2.1",
    "r35.1.0",
)


def _parse_l4t_tuple(version: str) -> tuple:
    parts = []
    for part in str(version).lstrip("rR").split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def resolve_l4t_jetpack_tag(l4t_version: str) -> Optional[str]:
    """Return the newest published tag on the host L4T major, or None."""
    wanted = _parse_l4t_tuple(l4t_version)
    exact = "r" + str(l4t_version).lstrip("rR")
    if exact in PUBLISHED_L4T_JETPACK_TAGS:
        return exact

    compatible = [
        (_parse_l4t_tuple(tag), tag)
        for tag in PUBLISHED_L4T_JETPACK_TAGS
        if _parse_l4t_tuple(tag)[0] == wanted[0]
        and _parse_l4t_tuple(tag) <= wanted
    ]
    return max(compatible)[1] if compatible else None


def get_l4t_jetpack_image() -> Optional[str]:
    """Return the configured image, evaluated at call time."""
    return L4T_JETPACK_IMAGE


def set_l4t_image_from_version(l4t_version: str) -> None:
    """Set an NGC image on the same L4T major as the detected host."""
    global L4T_JETPACK_IMAGE
    if "L4T_JETPACK_IMAGE" in os.environ:
        return

    tag = resolve_l4t_jetpack_tag(l4t_version)
    if tag is None:
        L4T_JETPACK_IMAGE = None
        logger.warning(
            "No published l4t-jetpack image matches host L4T %s. "
            "L4T container tests will skip unless L4T_JETPACK_IMAGE is set "
            "to a compatible image.",
            l4t_version,
        )
        return

    L4T_JETPACK_IMAGE = f"nvcr.io/nvidia/l4t-jetpack:{tag}"
    if tag == "r" + str(l4t_version).lstrip("rR"):
        logger.info("L4T_JETPACK_IMAGE auto-set to %s", L4T_JETPACK_IMAGE)
    else:
        logger.info(
            "L4T_JETPACK_IMAGE set to %s (same L4T major as host %s)",
            L4T_JETPACK_IMAGE,
            l4t_version,
        )

# Default building container image timeout in seconds (30 minutes)
DEFAULT_BUILD_TIMEOUT = 900
# Default running container timeout in seconds (10 minutes)
DEFAULT_RUN_TIMEOUT = 600

def build_container_image(ssh, dockerfile_path, image_tag, context_files=None,
                          build_args=None, timeout=DEFAULT_BUILD_TIMEOUT, suite_name="test"):
    """
    Build a container image from a Dockerfile on the remote device.

    Skips build if image with the same tag already exists on the device.
    The Dockerfile should only COMPILE/INSTALL — NOT run tests.

    Args:
        ssh: SSHConnection instance
        dockerfile_path: Local Path to Dockerfile to upload
        image_tag: Tag for the built image (e.g., "l4t-cuda-tests:r36.4.0-v12.9")
        context_files: Optional list of local Path objects to upload alongside Dockerfile
        build_args: Optional dict of build args (e.g., {"CUDA_SAMPLES_VERSION": "v12.9"})
        timeout: Build timeout in seconds (default is value in seconds of DEFAULT_BUILD_TIMEOUT)
        suite_name: Name prefix for temp dir (e.g., "cuda", "vpi") for easy identification

    Returns:
        image_tag (str) — the tag of the built (or existing) image
    """
    check = ssh.sudo(f"podman image exists {image_tag}", fail_on_rc=False)
    if check.exit_status == 0:
        logger.info("Image %s already exists, skipping build", image_tag)
        return image_tag

    tmp = ssh.run(f"mktemp -d /tmp/test-{suite_name}-XXXXXX").stdout.strip()
    ssh.put(dockerfile_path, f"{tmp}/Dockerfile")
    if context_files:
        for f in context_files:
            ssh.put(f, f"{tmp}/{f.name}")

    all_args = dict(build_args or {})
    if "L4T_JETPACK_IMAGE" not in all_args:
        l4t_image = get_l4t_jetpack_image()
        if l4t_image:
            all_args["L4T_JETPACK_IMAGE"] = l4t_image
    if "CACHEBUST" not in all_args:
        all_args["CACHEBUST"] = str(datetime.now().timestamp())
    args_str = " ".join(f"--build-arg {k}='{v}'" for k, v in all_args.items())

    cmd = f"podman build -t {image_tag} {PODMAN_GPU_FLAGS} {args_str} {tmp}"
    ssh.sudo(cmd, timeout=timeout)
    return image_tag


def run_container(ssh, image_tag, command="", timeout=DEFAULT_RUN_TIMEOUT, extra_flags=""):
    """
    Run a command in a container image via podman run --rm.
    Applies RHEL-specific GPU flags automatically.

    Args:
        ssh: SSHConnection instance
        image_tag: Image tag to run
        command: Command to execute inside the container
        timeout: Run timeout in seconds
        extra_flags: Additional podman run flags

    Returns:
        Result object with stdout, stderr, exit_status
    """
    cmd = f"podman run --rm {PODMAN_GPU_FLAGS} {extra_flags} {image_tag} {command}"
    return ssh.sudo(cmd, timeout=timeout, fail_on_rc=False)


def cleanup_container_image(ssh, image_tag):
    """Remove a built image to free disk space."""
    ssh.sudo(f"podman rmi -f {image_tag}", fail_on_rc=False)
