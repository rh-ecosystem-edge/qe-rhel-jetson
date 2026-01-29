# Jetson RPM Tests

This directory contains pytest-based tests for Jetson RPMs using SSH connections via paramiko.

## Jetson Structure
- HARDWARE ACCELERATORS: GPU (CUDA), DLA (AI), PVA (Vision), Video Enc/Dec
- INTERFACES: CSI Camera, USBs, PCIe, Ethernet, CAN bus, Display
- SOFTWARE FRAMEWORKS: GStreamer (MultiMedia), TensorRT (AI), VPI (Vision)

## Reposetory Tests Structure

```
infra-tests/            # SSH infrastructure
├── ssh_client.py       # SSHConnection class using paramiko
├── hardware_info.py    # Collect hardware and system information from a Jetson device via SSH.
└── __init__.py

tests/
├── conftest.py         # Shared pytest fixtures (Import ssh_client.py, hardware_info collect function and set global variables)
├── kmod/               # Kernel module (nvidia-jetpack-kmod)
├── cuda/               # CUDA tests
├── dla/                # DLA tests
├── pva/                # PVA tests
├── video_enc_dec/      # Video Encoder/Decoder tests
├── usbs/               # USB tests
├── pcis/               # PCI tests
├── can_bus/            # CAN bus tests
├── csi_camera/         # CSI camera tests
├── display/            # Display tests (X11, DRM/GBM, Wayland)
├── tools/              # nvidia-jetpack-tools tests (nvpmodel, nvfancontrol)
└── ethernet/           # Ethernet tests
```

## Configuration

Tests can be configured via environment variables:

- `JETSON_HOST`: Hostname or IP address of the Jetson device name
- `JETSON_USERNAME`: SSH username
- `JETSON_PASSWORD`: SSH password
- `JETSON_PORT`: SSH port (default: 22)

## Running Tests

Run all tests:
```bash
pytest tests/
```

Run tests for a specific component:
```bash
pytest tests/cuda/
pytest tests/dla/
pytest tests/pva/
```

Run only critical tests:
```bash
pytest -m critical tests/
```

Run with verbose output:
```bash
pytest -v tests/
```

## Requirements

Install required dependencies:
```bash
pip install pytest paramiko
```

## Test Markers

- `@pytest.mark.critical`: Critical tests that must pass
- `@pytest.mark.xfail`: Tests that are expected to fail on certain hardware

## How to Warn

for more information look at tests/WARNING_BEHAVIOR.md

## Hardware / System Variables (for developers)

When running pytest, the session collects hardware and system info from the Jetson via SSH and exposes the following variables to all tests. **All variables default to `None` if the value is not found.** You can import them from `conftest` and use them to skip or adapt tests by RHEL version, Jetpack, firmware, bootc, RPMs, etc.
e.g add this import in the beggining
```bash
from tests import conftest as _conftest
```
and use it _conftest.HARDWARE_MODEL_NAME

| Variable | Type | Description |
|----------|------|-------------|
| `RHEL_VERSION` | str or None | RHEL version string (e.g. from `/etc/redhat-release`). |
| `JETPACK_VERSION` | float, str, or None | Jetpack version: str if X.Y.Z (2 dots), float if X.Y (1 dot). |
| `FIRMWARE_VERSION` | float, str, or None | Firmware version: str if X.Y.Z (2 dots), float if X.Y (1 dot). |
| `FIRMWARE_TYPE` | str or None | Firmware type (e.g. `UEFI`, `BIOS`). |
| `HARDWARE_MODEL_NAME` | str or None | Hardware model name. |
| `KERNEL_VERSION` | str or None | Kernel version (e.g. `uname -r`). |
| `CPU_ARCH` | str or None | CPU architecture (e.g. `aarch64`, `x86_64`). |
| `BOOTC_AVAILABLE` | bool | Whether bootc / rpm-ostree is available (default False). |
| `BOOTC_VERSION` | float, str, or None | Bootc version: str if X.Y.Z, float if X.Y (only if bootc is available). |
| `BOOTC_IMAGE_VERSION` | str or None | Bootc image version, including last modify date (only if bootc is available). |
| `BOOTC_IMAGE_URL` | str or None | Bootc image URL including tag (only if bootc is available). |

**Example usage in a test:**

```python
from tests.conftest import RHEL_VERSION, JETPACK_VERSION, BOOTC_AVAILABLE, RPMS_AVAILABLE

def test_something():
    if not RPMS_AVAILABLE:
        pytest.skip("nvidia-jetpack: need all 23 RPMs installed with same version")
    # ...
```

At the start of each pytest run, a **SETUP** block is printed with: RHEL version, Jetpack version, firmware type and version, hardware model name, whether bootc is available, and whether the nvidia-jetpack RPM is available.
