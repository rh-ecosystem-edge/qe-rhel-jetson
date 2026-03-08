# Plan: Ubuntu Reference Comparison for Jetson Hardware Specs

## Context

Developers suggested comparing RHEL test outputs against Ubuntu (NVIDIA's officially supported OS) to validate that hardware specs are correctly detected. The existing TODO in `tests_suites/pcis/test_basic_pcis.py:30` confirms this intent:
```python
#TODO will check the lanes and logical slots later according ubuntu kernel version
```

The goal is to establish Ubuntu as "ground truth" for hardware spec tests (PCIe, USB, CAN, Ethernet) and compare RHEL outputs against it.

## Critical Analysis: Why a VM Won't Work

**Hardware spec tests query kernel-level sysfs interfaces**, not userspace. A VM abstracts physical hardware and presents virtual devices instead:

| Test | What it queries | In a VM you'd see |
|------|----------------|-------------------|
| PCIe (`lspci -vv`) | Physical PCIe controllers with LnkCap speeds/widths | Virtual PCI (virtio-pci) with no real LnkCap data |
| USB (`lsusb -t`) | Physical USB controller topology (ports, speeds) | Emulated EHCI/xHCI with virtual topology |
| CAN (`ip link show type can`) | SoC-integrated CAN controller | Nothing (no CAN passthrough to VMs) |
| Ethernet (`nmcli device`) | Physical NIC (eqos/stmmac driver) | Virtual NIC (virtio-net) |

**PCIe passthrough (VFIO)** could theoretically expose real PCI devices to the VM, but:
- It removes the device from the RHEL host (defeating the purpose)
- Jetson's Tegra SoC may not have proper IOMMU group isolation for root complex passthrough
- You'd need to pass the root complex itself, not just endpoint devices, to see LnkCap values

**Container/chroot won't work either** -- they share the RHEL kernel, so `lspci`/`lsusb` output is identical to the host. You'd be comparing RHEL against RHEL.

**Bottom line**: Hardware enumeration comes from the **running kernel + device tree + firmware**, not from userspace. The only way to get real Ubuntu hardware outputs is to actually boot Ubuntu's L4T kernel on the device.

## What Already Exists as Ground Truth

The `tests_suites/jetson_hardware_specs.yaml` already serves as the Ubuntu reference -- its values come from [NVIDIA's official Jetson Orin specifications](https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/), which describe behavior under Ubuntu+JetPack (L4T). The PCIe and USB tests already compare RHEL outputs against these YAML values.

However, the YAML is incomplete:
- PCIe `logical_slots` assertion is commented out (the TODO above)
- No detailed `lspci -vv` device-level reference (BDF addresses, device names)
- No raw output reference to diff against

## Recommended Approach: Pre-Collected Reference Data

Since VM/container is not viable, the practical approach is a **one-time reference collection** system:

1. **When Ubuntu access becomes available** (temporary flash, second device, or lab setup), run a collection script that captures the exact same commands the RHEL tests use
2. **Store outputs as structured JSON** per device model in the repo
3. **During RHEL tests**, optionally load and compare against the stored reference (warnings, not failures)

This approach works because hardware specs are deterministic per device model -- collecting once is sufficient.

## Implementation

### Phase 1: Reference Collection Script

**New file: `reference/collect_reference.py`**

Standalone CLI script that SSHs into any Jetson device (Ubuntu or RHEL) and captures hardware outputs:

```
python reference/collect_reference.py \
  --host <IP> --username <user> --password <pass>
```

**Commands captured** (matching exactly what the tests run):

| Component | Commands | Parsed Output |
|-----------|----------|---------------|
| PCIe | `ls -1 /sys/bus/pci/devices/`, `lspci -vv` | Device count, list of `{bdf, speed, width}` from LnkCap lines |
| USB | `ls -1 /sys/bus/usb/devices/`, `lsusb -t` | Device count, list of `{bus, speed, ports, driver}` per controller |
| CAN | `ip -o link show type can` | Interface names and count |
| Ethernet | `nmcli -t -f DEVICE,TYPE device \| grep ethernet`, `lsmod` | Interface list, loaded driver names |

The script will:
- Reuse `SSHConnection` from `infra_tests/ssh_client.py`
- Reuse `collect()` from `infra_tests/hardware_info.py` for device model identification
- Auto-detect OS type via `/etc/os-release` (tag output as "ubuntu" or "rhel")
- Normalize outputs into typed values (integers, lists) -- not raw strings -- for robust comparison
- Derive model key using same matching logic as `conftest.get_hardware_spec()`
- Save to `reference/data/<model_key>/reference_data.json`

### Phase 2: Comparison Utilities

**New file: `reference/comparison.py`**

A `ReferenceData` class that:
- Loads reference JSON for a given device model
- Provides comparison methods (`compare_count`, `compare_set`, `compare_value`)
- Returns `ComparisonResult` objects that emit `UserWarning` on mismatch (non-fatal)
- Warns if reference data is stale (>90 days old) or from a different JetPack version

### Phase 3: Test Integration

**Modified file: `tests_suites/conftest.py`**

- Add session-scoped `ubuntu_reference` fixture that loads reference data if available
- Returns `None` if no reference data exists (tests proceed normally)
- Import `reference/comparison.py` via importlib (same pattern as `infra_tests/`)

**Modified files: `tests_suites/pcis/test_basic_pcis.py`, `tests_suites/usbs/test_basic_usbs.py`**

Add optional comparison after existing assertions:
```python
def test_pci_spec(self, ssh, ubuntu_reference):
    # ... existing assertions unchanged ...

    # Optional Ubuntu reference comparison
    if ubuntu_reference and ubuntu_reference.has_section("pcis"):
        ubuntu_reference.compare_count(
            "pcis", "device_count", len(devices),
            "PCI device count differs from Ubuntu reference"
        ).warn_if_mismatch()
```

Also uncomment and enable the `logical_slots` assertion in `test_pci_spec` using the YAML values that are already defined but unused.

### Phase 4: Enhance Existing YAML (No Ubuntu Needed)

Even without Ubuntu access, we can improve coverage **today** by uncommenting the logical_slots check in `test_pci_spec` (lines 31-37) -- the YAML already has `logical_slots` values defined for every device model. This is the most immediate win.

## Files to Create/Modify

| File | Action |
|------|--------|
| `reference/collect_reference.py` | Create -- collection script |
| `reference/comparison.py` | Create -- comparison utilities |
| `reference/data/.gitkeep` | Create -- empty dir for future reference data |
| `tests_suites/conftest.py` | Modify -- add `ubuntu_reference` fixture |
| `tests_suites/pcis/test_basic_pcis.py` | Modify -- uncomment logical_slots, add optional comparison |
| `tests_suites/usbs/test_basic_usbs.py` | Modify -- add optional comparison |

## Verification

1. **Without Ubuntu reference data**: Run `pytest tests_suites/pcis/ tests_suites/usbs/` -- tests pass as before, no comparison warnings
2. **With reference data**: Place a `reference_data.json` for the device model, run tests -- comparison warnings appear in output for any RHEL vs reference mismatches
3. **Collection script**: Run against any accessible Jetson device to verify it captures correct outputs
4. **Logical slots**: After uncommenting, verify `test_pci_spec` checks `logical_slots` counts

## Summary: Do You Need JetPack on Ubuntu?

**For hardware-only scope (PCIe, USB, CAN, Ethernet): No.** These are kernel-level queries that don't require NVIDIA's userspace stack. Plain Ubuntu with L4T kernel (which comes with the base Jetson firmware flash) is sufficient. However:

- The existing `jetson_hardware_specs.yaml` already captures these expected values from NVIDIA docs
- A VM or container **cannot** substitute for an actual Ubuntu boot
- The immediate win is uncommenting the `logical_slots` assertion that's already in the code
