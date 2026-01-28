# Jetson RPM Tests

This directory contains pytest-based tests for Jetson RPMs using SSH connections via paramiko.

## Real Jetson Structure
┌─────────────────────────────────────────┐
│         Jetson SoC (System on Chip)     │
├─────────────────────────────────────────┤
│                                         │
│  HARDWARE ACCELERATORS:                 │
│  ┌──────────┐  ┌──────────┐  ┌──────┐   │
│  │   GPU    │  │   DLA    │  │ PVA  │   │
│  │ (CUDA)   │  │ (AI)     │  │(Vision│  │
│  └──────────┘  └──────────┘  └──────┘   │
│                                         │
│  ┌──────────┐                           │
│  │ Video    │                           │
│  │ Enc/Dec  │                           │
│  └──────────┘                           │
│                                         │
│  INTERFACES:                            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐.   │
│  │ CSI  │ │ USB  │ │ PCIe │ │ Eth  │.   │
│  │Camera│ │      │ │      │ │      │.   │
│  └──────┘ └──────┘ └──────┘ └──────┘.   │
│                                         │
│  ┌──────┐  ┌──────┐                     │
│  │ CAN  │  │Display│                    │
│  │ Bus  │  │      │                     │
│  └──────┘  └──────┘                     │
│                                         │
│  SOFTWARE FRAMEWORKS:                   │
│  ┌──────────┐ ┌──────────┐              │
│  │GStreamer │ │ TensorRT │              │
│  │(Multimedia)│(AI)      │              │
│  └──────────┘ └──────────┘              │
│                                         │
│  ┌──────────┐                           │
│  │   VPI    │                           │
│  │(Vision)  │                           │
│  └──────────┘                           │
│                                         │
└─────────────────────────────────────────┘

## Reposetory Tests Structure

```
infra-tests/            # SSH infrastructure
├── ssh_client.py       # SSHConnection class using paramiko
└── __init__.py

tests/
├── conftest.py         # Shared pytest fixtures (Import ssh_client.py and set Variables)
├── cuda/               # CUDA tests
├── dla/                # DLA tests
├── pva/                # PVA tests
├── video_enc_dec/      # Video Encoder/Decoder tests
├── usbs/               # USB tests
├── pcis/               # PCI tests
├── can_bus/            # CAN bus tests
├── csi_camera/         # CSI camera tests
├── display/            # Display tests
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
