"""
Shared pytest configuration and fixtures for all tests.
This file imports SSHConnection from infra-tests/ssh_client.py.
"""
import pytest
import os
from pathlib import Path
import sys
import importlib.util
import logging
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import SSHConnection from infra-tests/ssh_client.py
# Since Python can't import from directories with hyphens (two or more words), we use importlib
ssh_client_path = project_root / "infra-tests" / "ssh_client.py"
spec = importlib.util.spec_from_file_location("ssh_client", ssh_client_path)
ssh_client_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssh_client_module)
SSHConnection = ssh_client_module.SSHConnection

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
JETSON_PORT = int(os.getenv("JETSON_PORT", "22"))
JETSON_TIMEOUT = int(os.getenv("JETSON_TIMEOUT", "60"))  # Connection timeout per attempt (seconds)

# Validate required environment variables
missing_vars = []
if not JETSON_HOST:
    missing_vars.append("JETSON_HOST")
if not JETSON_USERNAME:
    missing_vars.append("JETSON_USERNAME")
if not JETSON_PASSWORD:
    missing_vars.append("JETSON_PASSWORD")

if missing_vars:
    error_msg = (
        f"Missing required environment variables: {', '.join(missing_vars)}\n"
        f"Please export the following variables before running pytest:\n"
        f"  export JETSON_HOST=<hostname_or_ip>\n"
        f"  export JETSON_USERNAME=<username>\n"
        f"  export JETSON_PASSWORD=<password>\n"
        f"  export JETSON_PORT=<port>  # Optional, defaults to 22\n"
        f"  export JETSON_TIMEOUT=<timeout>  # Optional, defaults to 30 seconds"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)

@pytest.fixture(scope="class")
def ssh():
    """
    SSH fixture that connects directly to Jetson.
    Can be configured via environment variables:
    - JETSON_HOST: Hostname or IP address
    - JETSON_USERNAME: SSH username
    - JETSON_PASSWORD: SSH password
    - JETSON_PORT: SSH port (default: 22)
    
    Note: This fixture depends on hardware_info fixture which collects
    hardware information at the beginning of the test session.
    """
    logger.info(
        "[conftest] Using JETSON_HOST=%s JETSON_PORT=%s JETSON_USERNAME=%s JETSON_TIMEOUT=%s",
        JETSON_HOST, JETSON_PORT, JETSON_USERNAME, JETSON_TIMEOUT,
    )
    try:
        with SSHConnection(JETSON_HOST, JETSON_USERNAME, JETSON_PASSWORD, JETSON_PORT, JETSON_TIMEOUT) as ssh:
            yield ssh
    except Exception as e:
        error_msg = (
            f"Failed to establish SSH connection to {JETSON_HOST}:{JETSON_PORT}\n"
            f"Error: {str(e)}\n"
            f"Please verify:\n"
            f"  - Environment variables are set correctly (JETSON_HOST, JETSON_USERNAME, JETSON_PASSWORD)\n"
            f"  - Host is reachable (try: ping {JETSON_HOST} or telnet {JETSON_HOST} {JETSON_PORT})\n"
            f"  - SSH service is running on the target\n"
            f"  - Credentials are correct\n"
            f"  - Firewall allows SSH connections\n"
            f"  - Network connectivity is available"
        )
        print(f"\n{error_msg}\n")
        logger.error(error_msg)
        raise
