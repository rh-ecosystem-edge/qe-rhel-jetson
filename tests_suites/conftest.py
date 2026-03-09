"""
Shared pytest configuration and fixtures for all tests.
This file imports SSHConnection from infra_tests/ssh_client.py and
collects hardware info from infra_tests/hardware_info.py for use in all tests.

Test tiers:
  - Basic tests (default): run with `pytest tests_suites/`
  - Extra tests: marked with @pytest.mark.extra, run with `pytest tests_suites/ --run-extra`
"""
import pytest
import os
import time
from pathlib import Path
import sys
import logging
from typing import Optional, Union, Dict, Any
import yaml
from infra_tests.ssh_client import SSHConnection
from infra_tests.hardware_info import collect as collect_hardware_info

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration - can be overridden via environment variables
JETSON_HOST = os.getenv("JETSON_HOST")
JETSON_USERNAME = os.getenv("JETSON_USERNAME")
JETSON_PASSWORD = os.getenv("JETSON_PASSWORD")
JETSON_KEY_PATH = os.getenv("JETSON_KEY_PATH")  # e.g. ~/.ssh/id_rsa or ~/.ssh/id_ed25519
JETSON_PORT = int(os.getenv("JETSON_PORT", "22"))
JETSON_TIMEOUT = int(os.getenv("JETSON_TIMEOUT", "60"))  # Connection timeout per attempt (seconds)

# Validate required environment variables (need either password or key path)
missing_vars = []
if not JETSON_HOST:
    missing_vars.append("JETSON_HOST")
if not JETSON_USERNAME:
    missing_vars.append("JETSON_USERNAME")
if not JETSON_PASSWORD and not JETSON_KEY_PATH:
    missing_vars.append("JETSON_PASSWORD or JETSON_KEY_PATH")

if missing_vars:
    error_msg = (f"Missing required environment variables: {', '.join(missing_vars)}\n")
    logger.error(error_msg)
    raise ValueError(error_msg)

# ---------------------------------------------------------------------------
# Hardware info variables (set by hardware_info_session fixture; use in tests)
# All are None by default if value not found.
# ---------------------------------------------------------------------------
RHEL_VERSION: Optional[float] = None
JETPACK_VERSION: Optional[Union[float, str]] = None  # str if X.Y.Z, float if X.Y
FIRMWARE_VERSION: Optional[Union[float, str]] = None  # str if X.Y.Z, float if X.Y
FIRMWARE_TYPE: Optional[str] = None
HARDWARE_MODEL_NAME: Optional[str] = None
KERNEL_VERSION: Optional[str] = None
CPU_ARCH: Optional[str] = None
BOOTC_AVAILABLE: bool = False
BOOTC_VERSION: Optional[Union[float, str]] = None  # str if X.Y.Z, float if X.Y
BOOTC_IMAGE_VERSION: Optional[Union[str]] = None
BOOTC_IMAGE_URL: Optional[str] = None

if JETSON_KEY_PATH: # key path provided, use key-based authentication
    key_path = os.path.expanduser(JETSON_KEY_PATH)
    if not os.path.exists(key_path):
        raise ValueError(
            f"SSH key file not found: {key_path}\n"
            f"Set JETSON_KEY_PATH to a valid SSH private key path."
        )
else: # no key path provided, use password authentication
    key_path = None

# ---------------------------------------------------------------------------
# Functions
# --------------------------------------------------------------------------- 

def _load_hardware_specs() -> Dict[str, Any]:
    """Load jetson_hardware_specs.yaml once."""
    path = Path(__file__).parent / "jetson_hardware_specs.yaml"
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Hardware specs must be a dictionary, got {type(data)}")
        return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {path}: {e}")
    except FileNotFoundError:
        raise ValueError(f"Hardware specs file not found: {path}")

def get_hardware_spec(hardware_model_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Return the expected-spec dict for the given hardware model name, or None if unknown.
    hardware_model_name comes from the device (dmidecode Product Name or devicetree model).
    """
    if not hardware_model_name:
        return None
    specs = _load_hardware_specs()
    name_lower = hardware_model_name.lower()
    for key in specs:
        if key.lower() in name_lower:
            spec = specs.get(key)
            if spec and not str(key).startswith("_"):
                return spec
    return None

def install_beaker_repo(ssh, rhel_version: Optional[float]):
    """
    Install Beaker repository on the Jetson.
    RHEL version is required to install the correct Beaker repository.
    Retries DNF operations up to 3 times to handle transient mirror failures.
    """
    logger.info("Checking Beaker repositories exist on the Jetson...")
    if rhel_version is None:
        raise ValueError("RHEL version not found, The environment is not a RHEL machine")

    main_rhel_version = str(rhel_version).split(".")[0]
    # declare commands to install Beaker repositories and EPEL release
    cmd_epel = f"dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-{main_rhel_version}.noarch.rpm -y"
    cmd_appstream = f"dnf config-manager --add-repo http://download.eng.rdu.redhat.com/released/rhel-{main_rhel_version}/RHEL-{main_rhel_version}/{rhel_version}.0/AppStream/aarch64/os/"
    cmd_baseos = f"dnf config-manager --add-repo http://download.eng.rdu.redhat.com/released/rhel-{main_rhel_version}/RHEL-{main_rhel_version}/{rhel_version}.0/BaseOS/aarch64/os/"
    
    result = ssh.sudo("dnf repolist | grep beaker- | wc -l")
    if result.exit_status == 0 and int(result.stdout.strip()) >= 12:
        logger.info("installing EPEL release for RHEL %s", rhel_version)
        ssh.sudo(cmd_epel)
    else:
      logger.info("installing Beaker repositories and EPEL release for RHEL %s", rhel_version)
      for attempt in range(1, 4):
          try:
              ssh.sudo(cmd_appstream)
              ssh.sudo(cmd_baseos)
              ssh.sudo(cmd_epel)
              break
          except Exception as e:
              if attempt < 3:
                  logger.warning("DNF operation failed (attempt %s/3): %s, retrying...", attempt, e)
                  time.sleep(5)
              else:
                  raise

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def hardware_info_session():
    """
    Collect hardware and system info from the Jetson via SSH at session start.
    Sets module-level variables and prints SETUP summary for each pytest run.
    """
    with SSHConnection(
        JETSON_HOST,
        JETSON_USERNAME,
        JETSON_PASSWORD or None,
        JETSON_PORT,
        JETSON_TIMEOUT,
        key_filename=key_path,
    ) as ssh:
        info = collect_hardware_info(ssh)

    # Set module-level variables so all tests can import them
    global RHEL_VERSION, JETPACK_VERSION, FIRMWARE_VERSION, FIRMWARE_TYPE
    global HARDWARE_MODEL_NAME, KERNEL_VERSION, CPU_ARCH
    global BOOTC_AVAILABLE, BOOTC_VERSION, BOOTC_IMAGE_URL, BOOTC_IMAGE_VERSION
    RHEL_VERSION = info.get("rhel_version")
    JETPACK_VERSION = info.get("jetpack_version")
    FIRMWARE_VERSION = info.get("firmware_version")
    FIRMWARE_TYPE = info.get("firmware_type")
    HARDWARE_MODEL_NAME = info.get("hardware_model_name")
    KERNEL_VERSION = info.get("kernel_version")
    CPU_ARCH = info.get("cpu_arch")
    BOOTC_AVAILABLE = info.get("bootc_available", False)
    BOOTC_VERSION = info.get("bootc_version")
    BOOTC_IMAGE_VERSION = info.get("bootc_image_version")
    BOOTC_IMAGE_URL = info.get("bootc_image_url")

    # Skip entire session if hardware model is not in Testing Matrix (jetson_hardware_specs.yaml)
    if get_hardware_spec(HARDWARE_MODEL_NAME) is None:
        pytest.skip(
            f"Hardware model not included in Testing Matrix: {HARDWARE_MODEL_NAME!r}. "
            "Add the device to tests_suites/jetson_hardware_specs.yaml to run tests."
        )

    # Print SETUP summary for each pytest run (values may be None if not found)
    fw_ver = f" {FIRMWARE_VERSION}" if FIRMWARE_VERSION is not None else ""
    print("\n" + "=" * 60)
    print("SETUP")
    print("=" * 60)
    print(f"1. RHEL version:          {RHEL_VERSION}")
    print(f"2. Jetpack Version:       {JETPACK_VERSION}")
    print(f"3. Firmware type/version: {FIRMWARE_TYPE}{fw_ver}")
    print(f"4. Hardware model name:   {HARDWARE_MODEL_NAME}")
    print(f"5. Bootc available:       {BOOTC_AVAILABLE}")
    print(f"6. Bootc image version:   {BOOTC_IMAGE_VERSION}")
    print(f"7. Bootc version:         {BOOTC_VERSION}")
    print(f"8. Bootc image URL:       {BOOTC_IMAGE_URL}")
    print("=" * 60 + "\n")
    yield


@pytest.fixture(scope="session", autouse=True)
def beaker_repo_session(hardware_info_session):
    """
    Install Beaker repositories on the Jetson after hardware info is collected.
    Depends on hardware_info_session to ensure RHEL_VERSION is available.
    """
    with SSHConnection(
        JETSON_HOST,
        JETSON_USERNAME,
        JETSON_PASSWORD or None,
        JETSON_PORT,
        JETSON_TIMEOUT,
        key_filename=key_path,
    ) as ssh:
        install_beaker_repo(ssh, RHEL_VERSION)
    yield

@pytest.fixture(scope="class")
def ssh():
    """
    SSH fixture that connects directly to Jetson.
    Can be configured via environment variables:
    - JETSON_HOST: Hostname or IP address
    - JETSON_USERNAME: SSH username
    - JETSON_PASSWORD: SSH password (optional if JETSON_KEY_PATH is set)
    - JETSON_KEY_PATH: Path to private key, e.g. ~/.ssh/id_rsa (use when auth is key-based)
    - JETSON_PORT: SSH port (default: 22)
    
    Note: This fixture depends on hardware_info fixture which collects
    hardware information at the beginning of the test session.
    """
    logger.info(
        "[conftest] Using JETSON_HOST=%s JETSON_PORT=%s JETSON_USERNAME=%s JETSON_TIMEOUT=%s",
        JETSON_HOST, JETSON_PORT, JETSON_USERNAME, JETSON_TIMEOUT,
    )
    key_path = os.path.expanduser(JETSON_KEY_PATH) if JETSON_KEY_PATH else None
    try:
        with SSHConnection(
            JETSON_HOST,
            JETSON_USERNAME,
            JETSON_PASSWORD or None,
            JETSON_PORT,
            JETSON_TIMEOUT,
            key_filename=key_path,
        ) as ssh:
            yield ssh
    except Exception as e:
        error_msg = (
            f"Failed to establish SSH connection to {JETSON_HOST}:{JETSON_PORT}\n"
            f"Error: {str(e)}\n"
            f"Please verify:\n"
            f"  - Environment variables are set correctly (JETSON_HOST, JETSON_USERNAME, JETSON_PASSWORD or JETSON_KEY_PATH)\n"
            f"  - For key-based auth, set JETSON_KEY_PATH=~/.ssh/id_rsa (or your private key path)\n"
            f"  - Host is reachable (try: ping {JETSON_HOST} or telnet {JETSON_HOST} {JETSON_PORT})\n"
            f"  - SSH service is running on the target\n"
            f"  - Credentials are correct\n"
            f"  - Firewall allows SSH connections\n"
            f"  - Network connectivity is available"
        )
        print(f"\n{error_msg}\n")
        logger.error(error_msg)
        raise


# ---------------------------------------------------------------------------
# Extra-tests support: @pytest.mark.extra tests are excluded by default.
# Run them with: pytest tests_suites/ --run-extra
# Or run ONLY extras: pytest tests_suites/ -m extra --run-extra
# ---------------------------------------------------------------------------

def pytest_addoption(parser):
    parser.addoption(
        "--run-extra",
        action="store_true",
        default=False,
        help="Run tests marked with @pytest.mark.extra (skipped by default)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-extra"):
        return  # --run-extra given: run everything
    skip_extra = pytest.mark.skip(reason="Extra test — use --run-extra to run")
    for item in items:
        if "extra" in item.keywords:
            item.add_marker(skip_extra)
