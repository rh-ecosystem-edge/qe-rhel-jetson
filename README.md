# qe-rhel-jetson
Repository for QE Jetson effort, includes automation of python tests and deploying Beaker machine

## Jetson Structure
- HARDWARE ACCELERATORS: GPU (CUDA), DLA (AI), PVA (Vision), Video Enc/Dec
- INTERFACES: CSI Camera, USBs, PCIe, Ethernet, CAN bus, Display
- SOFTWARE FRAMEWORKS: GStreamer (MultiMedia), TensorRT (AI), VPI (Vision)

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

! For step by step Integration with Beaker (for Jetson testing)
Read qe-rhel-jetson/beaker/README.md

Tests can be configured via environment variables:

- `JETSON_HOST`: Hostname or IP address of the Jetson device name
- `JETSON_USERNAME`: SSH username
- `JETSON_PASSWORD`: SSH password, OR `JETSON_KEY_PATH` : SSH key path e.g. ~/.ssh/id_rsa (use when auth is key-based)
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