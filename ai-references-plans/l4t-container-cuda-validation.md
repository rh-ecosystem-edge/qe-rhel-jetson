# Running CUDA Validation via L4T Container on RHEL 9.7 Bootc

## Context

Validate CUDA and JetPack components on a Jetson device running RHEL 9.7 bootc with JetPack 6.2.2 RPMs, using the NVIDIA L4T JetPack container and cuda-samples.

### Environment

| Component | Version | Notes |
|-----------|---------|-------|
| Host OS | RHEL 9.7 bootc | Deployed via Beaker, `graphical.target`, no monitor |
| JetPack RPMs (host) | 6.2.2 | L4T 36.5.0 userspace + kmod |
| UEFI firmware | 36.4.4 | SPI-flashed, 9.7 TP only (9.8+ will match userspace) |
| Kernel | 5.14.0-611.42.1.el9_7 | |
| L4T container | `r36.4.0` | From NGC (`nvcr.io/nvidia/l4t-jetpack`) |
| cuda-samples | v12.9 | From GitHub (`NVIDIA/cuda-samples`) |
| CUDA range | 12.x only | Jetson Orin Nano on RHEL + JetPack 6.2.2 supports CUDA 12 range only |

### Why L4T r36.4.0 Container Works on L4T 36.5.0 Host

The host runs L4T **36.5.0** drivers (JetPack 6.2.2 RPMs) but the latest available L4T container on NGC is **r36.4.0** (JetPack 6.1). This is a valid combination because:

1. **Forward compatibility**: The host driver (36.5.0) is **newer** than the container's userspace (36.4.0). NVIDIA's driver model guarantees that a newer host driver supports older userspace libraries — the same principle as running an older CUDA toolkit on a newer GPU driver.
2. **Same major L4T branch**: Both 36.4.0 and 36.5.0 are in the L4T R36 (JetPack 6.x) family, sharing the same kernel module ABI and device interface.
3. **CUDA version alignment**: Both ship CUDA 12.6, so there is no CUDA version mismatch between host driver and container toolkit.

If/when `nvcr.io/nvidia/l4t-jetpack:r36.5.0` becomes available on NGC, it would be the exact match and should be preferred.

### Why cuda-samples v12.9 Works with CUDA 12.6

The cuda-samples repository maintains backward compatibility within the same major CUDA version. v12.9 samples compile and run correctly against CUDA 12.6 toolkit — they use standard CUDA Runtime APIs that are stable across the CUDA 12.x range.

## Prerequisites

### 1. Verify CDI (Container Device Interface)

The host must have `nvidia-container-toolkit` configured so podman can expose GPU devices.

```bash
nvidia-ctk cdi list
```

Expected output:
```
INFO[0000] Found 2 CDI devices
nvidia.com/gpu=0
nvidia.com/gpu=all
```

If CDI devices are not listed, generate the spec:
```bash
sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
```

### 2. Clone cuda-samples on the Host

```bash
git clone --branch v12.9 --depth 1 https://github.com/NVIDIA/cuda-samples.git ${HOME}/cuda-samples
```

## Step-by-Step: Run CUDA from L4T Container

### Step 1 — Launch the L4T Container

No X11 or display flags are needed for headless CUDA validation. The `xhost +` and `-e DISPLAY` flags shown in NGC/Red Hat docs are only required for graphical samples.

```bash
podman run --rm -it \
  --device nvidia.com/gpu=all \
  --group-add keep-groups \
  --security-opt label=disable \
  --net=host \
  -v ${HOME}/cuda-samples:/cuda-samples \
  nvcr.io/nvidia/l4t-jetpack:r36.4.0
```

```bash
# Check CUDA version
  nvcc --version

  # Basic GPU query
  nvidia-smi   # or tegrastats
  ```

Flags explained:
| Flag | Purpose |
|------|---------|
| `--device nvidia.com/gpu=all` | Exposes all GPU devices via CDI (replaces `--runtime nvidia` used with Docker) |
| `--group-add keep-groups` | Preserves host group permissions for device access |
| `--security-opt label=disable` | Disables SELinux labeling (required on RHEL) |
| `--net=host` | Uses host networking (needed for some NVIDIA services) |
| `-v ${HOME}/cuda-samples:/cuda-samples` | Mounts cloned cuda-samples into the container |

### Step 2 — Install Build Dependencies Inside the Container

The L4T container is Ubuntu-based and does not include build tools by default:

```bash
apt-get update
apt-get install -y cmake pkg-config libglfw3 libglfw3-dev libdrm-dev
```

### Step 3 — Build and Run deviceQuery

```bash
cd /cuda-samples/Samples/1_Utilities/deviceQuery
mkdir build && cd build
cmake ..
make
./deviceQuery
```

<!-- TODO: paste deviceQuery output here -->

### Step 4 — Build and Run bandwidthTest

```bash
cd /cuda-samples/Samples/1_Utilities/bandwidthTest
mkdir build && cd build
cmake ..
make
./bandwidthTest
```

<!-- TODO: paste bandwidthTest output here -->

### Step 5 — Build and Run matrixMul

```bash
cd /cuda-samples/Samples/0_Introduction/matrixMul
mkdir build && cd build
cmake ..
make
./matrixMul
```

<!-- TODO: paste matrixMul output here -->

### Step 6 — Build and Run vectorAdd

```bash
cd /cuda-samples/Samples/0_Introduction/vectorAdd
mkdir build && cd build
cmake ..
make
./vectorAdd
```

<!-- TODO: paste vectorAdd output here -->

All samples follow the same pattern: `mkdir build && cd build && cmake .. && make && ./<binary>`.

### Validation Summary

| Sample | Result | Notes |
|--------|--------|-------|
| deviceQuery | <!-- TODO --> | |
| bandwidthTest | <!-- TODO --> | |
| matrixMul | <!-- TODO --> | |
| vectorAdd | <!-- TODO --> | |

### What This Validates

| What | How |
|------|-----|
| CUDA runtime | `deviceQuery` — confirms CUDA toolkit and driver communication |
| GPU memory subsystem | `bandwidthTest` — measures host-to-device, device-to-host, device-to-device bandwidth |
| GPU compute | `matrixMul`, `vectorAdd` — exercises CUDA cores with real computation |
| Driver compatibility | Running r36.4.0 userspace on r36.5.0 host drivers confirms forward compatibility |
| CUDA 12.x range | All samples use CUDA 12 APIs on Jetson Orin Nano hardware |

### Notes

- **Transient installs**: Any `apt-get install` inside the container is lost when the container exits (`--rm`). The cuda-samples binaries persist on the host via the `-v` mount.
- **Bootc image does not include xhost**: The `xorg-x11-server-utils` package is not in the bootc image. Install transiently if needed (see virtual display way above).

- **Why can't you run graphical samples with Virtual Display**:

  Xvfb doesn't support hardware GL. Xvfb provides a virtual display but no GPU-accelerated rendering.
  The samples requires real OpenGL-CUDA interop which won't work on a virtual framebuffer. This is expected for a headless Beaker machine.

#### FYI this is how setup virtual display

```bash
# On the host, before launching the container:
dnf install -y xorg-x11-server-Xvfb xorg-x11-server-utils
Xvfb :0 -screen 0 1024x768x24 &
export DISPLAY=:0
xhost +

# Then launch with display flags:
podman run --rm -it \
  --device nvidia.com/gpu=all \
  --group-add keep-groups \
  --security-opt label=disable \
  --net=host \
  -e DISPLAY=:0 \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v ${HOME}/cuda-samples:/cuda-samples \
  nvcr.io/nvidia/l4t-jetpack:r36.4.0
```

## References

- [NGC L4T JetPack Container](https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-jetpack)
- [Red Hat Developer — Validate Jetson GPU Support](https://developers.redhat.com/learning/learn:rhel:install-red-hat-device-edge-nvidia-jetson-orin-and-igx-orin/resource/resources:validate-jetson-gpu-support)
- [NVIDIA cuda-samples GitHub](https://github.com/NVIDIA/cuda-samples)
