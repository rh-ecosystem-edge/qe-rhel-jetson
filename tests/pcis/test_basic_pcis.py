"""
PCI tests for Jetson RPMs.
Based on test_basic.py and test_basic_locally.py from edge-ai-image-pipelines.
"""
import warnings
import pytest
from tests import conftest as _conftest


class TestPCIs:
    """Test PCI functionality on Jetson devices."""

    def test_pcie(self, ssh):
        """Test PCI devices are present."""
        result = ssh.sudo("ls -1 /sys/bus/pci/devices/")
        assert result.exit_status == 0, f"Failed to list PCI devices: {result.stderr}"
        assert len(result.stdout.splitlines()) > 0, "No PCI devices found"

    def test_pci_spec(self, ssh):
        """Test PCI specification.
        
        Checks if PCIe slots have devices matching expected speeds and lanes.
        Slots may be unpopulated (no device connected), which is reported as a warning.
        The test passes if at least one expected PCIe configuration is found.
        """
        spec = _conftest.get_hardware_spec(_conftest.HARDWARE_MODEL_NAME)
        pcis_spec = spec.get("pcis")
        
        if not pcis_spec:
            pytest.skip("No PCIe specification defined for this hardware")
        
        ssh.sudo("dnf install pciutils -y", fail_on_rc=False)
        
        lspci_result = ssh.sudo("lspci -vv | grep -P 'LnkCap:'", fail_on_rc=False)
        lspci_output = lspci_result.stdout if lspci_result.exit_status == 0 else ""
        
        found_configs = []
        missing_configs = []
        
        for controller, values in pcis_spec.items():
            capable_speed = values.get("capable_speed")
            lanes = values.get("lanes")
            
            speed_match = capable_speed in lspci_output
            lane_pattern = f"Width x{lanes}"
            
            lines_with_speed = [line for line in lspci_output.splitlines() if capable_speed in line]
            lines_with_both = [line for line in lines_with_speed if lane_pattern in line]
            
            if lines_with_both:
                found_configs.append(f"{controller} ({capable_speed}, x{lanes})")
            else:
                missing_configs.append(f"{controller} ({capable_speed}, x{lanes})")
        
        if missing_configs:
            warnings.warn(
                UserWarning(
                    f"PCIe slots may be unpopulated or devices negotiated different speeds. "
                    f"Missing: {', '.join(missing_configs)}. "
                    f"Found: {', '.join(found_configs) if found_configs else 'none'}. "
                    f"This is expected if no device is plugged into the slot."
                )
            )
        
        expected_list = [
            f"{k} ({v.get('capable_speed')}, x{v.get('lanes')})" 
            for k, v in pcis_spec.items()
        ]
        assert len(found_configs) > 0 or len(pcis_spec) == 0, (
            f"No PCIe devices found matching any expected configuration. "
            f"Expected: {', '.join(expected_list)}. "
            f"Check if PCIe slots have devices connected."
        )
