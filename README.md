# qe-rhel-jetson
Repository for QE Jetson effort, includes automation of python tests and deploying Beaker machine

## Jetson Structure
- HARDWARE ACCELERATORS: GPU (CUDA), DLA (AI), PVA (Vision), Video Enc/Dec
- INTERFACES: CSI Camera, USBs, PCIe, Ethernet, CAN bus, Display
- SOFTWARE FRAMEWORKS: GStreamer (MultiMedia), TensorRT (AI), VPI (Vision)

## Repository Structure

```
qe-rhel-jetson/
├── tests_suites/               # Pytest test suites (per hardware component)
│   ├── conftest.py             # Shared fixtures, hardware info, SSH setup
│   ├── jetson_hardware_specs.yaml  # Expected specs per device model
│   ├── cuda/                   # CUDA tests
│   ├── dla/                    # DLA (Deep Learning Accelerator) tests
│   ├── pva/                    # PVA (Programmable Vision Accelerator) tests
│   ├── video_enc_dec/          # Video Encoder/Decoder tests
│   ├── kmod/                   # Kernel module (nvidia-jetpack-kmod) tests
│   ├── pcis/                   # PCIe tests
│   ├── usbs/                   # USB tests
│   ├── can_bus/                # CAN bus tests
│   ├── csi_camera/             # CSI camera tests
│   ├── display/                # Display tests (DRM, Wayland, X11)
│   ├── ethernet/               # Ethernet tests
│   └── tools/                  # nvidia-jetpack-tools tests (nvpmodel, nvfancontrol)
│
├── infra_tests/                # SSH infrastructure
│   ├── ssh_client.py           # SSHConnection class (paramiko/fabric wrapper)
│   └── hardware_info.py        # Collect hardware/system info from device via SSH
│
├── tests_resources/            # Shared utilities for tests
│   └── device_ops.py           # Reboot, reconnect, kernel arg helpers
│
├── beaker/                     # Beaker reservation & deployment automation
│   ├── pybeaker/               # Python client for Beaker API
│   ├── scripts/                # CLI tools (reserve_jetson.py)
│   └── ansible/                # Ansible playbooks (bootc install, RPM install)
│
├── jumpstarter/                # Jumpstarter integration for hardware testing
│   └── wrapper.py              # Flash & test via Jumpstarter framework
│
└── .github/workflows/          # CI/CD - IN PROGRESS (Blocked by Firewall issues)
    └── beaker-test.yml         # Reserve Beaker machine, deploy, run tests 
```

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

### For step by step Integration with Beaker (Beaker reservation & deployment automation)
- Read qe-rhel-jetson/beaker/README.md

### For step by step Integration via Jumpstarter (Flash & test via Jumpstarter framework)
- Read qe-rhel-jetson/jumpstarter/README.md - COMING SOON

Tests can be configured via environment variables:

- `JETSON_HOST`: Hostname or IP address of the Jetson device name
- `JETSON_USERNAME`: SSH username
- `JETSON_PASSWORD`: SSH password, OR `JETSON_KEY_PATH` : SSH key path e.g. ~/.ssh/id_rsa (use when auth is key-based)
- `JETSON_PORT`: SSH port (default: 22)

## Running Tests

Run all tests:
```bash
pytest tests_suites/
```

Run tests for a specific component:
```bash
pytest tests_suites/cuda/
pytest tests_suites/dla/
pytest tests_suites/pva/
```