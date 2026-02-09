"""
Common utilities for pybeaker scripts.

This module provides shared functionality for authentication and client setup.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import urllib3
urllib3.disable_warnings()

from pybeaker import BeakerClient, BeakerConfig


def get_beaker_client(require_hub_url: bool = True) -> BeakerClient:
    """Create a BeakerClient with authentication from environment variables.
    
    Environment variables:
        BEAKER_HUB_URL: Beaker server URL (required unless require_hub_url=False)
        BEAKER_SSL_VERIFY: Set to "false" to disable SSL verification
        
        Authentication (choose one method):
        
        Option 1 - Kerberos (default):
            BEAKER_AUTH_METHOD: Set to "krbv" (or leave unset)
            BEAKER_KRB_REALM: Kerberos realm (optional)
            Requires: valid Kerberos ticket (run 'kinit' first)
        
        Option 2 - Username/Password:
            BEAKER_AUTH_METHOD: Set to "password"
            BEAKER_USERNAME: Your Beaker username
            BEAKER_PASSWORD: Your Beaker password
    
    Args:
        require_hub_url: If True, exit with error if BEAKER_HUB_URL is not set
        
    Returns:
        Configured BeakerClient instance
    """
    hub_url = os.environ.get("BEAKER_HUB_URL")
    if require_hub_url and not hub_url:
        print("Error: BEAKER_HUB_URL environment variable required")
        print("Set it with: export BEAKER_HUB_URL='https://beaker.engineering.redhat.com'")
        sys.exit(1)
    
    # Determine authentication method
    auth_method = os.environ.get("BEAKER_AUTH_METHOD", "krbv").lower()
    
    config_kwargs = {
        "hub_url": hub_url,
        "auth_method": auth_method,
        "ssl_verify": os.environ.get("BEAKER_SSL_VERIFY", "true").lower() != "false",
    }
    
    if auth_method == "password":
        username = os.environ.get("BEAKER_USERNAME")
        password = os.environ.get("BEAKER_PASSWORD")
        if not username or not password:
            print("Error: BEAKER_USERNAME and BEAKER_PASSWORD required for password auth")
            print("Set them with:")
            print("  export BEAKER_USERNAME='your_username'")
            print("  export BEAKER_PASSWORD='your_password'")
            sys.exit(1)
        config_kwargs["username"] = username
        config_kwargs["password"] = password
        print(f"   Using password authentication as: {username}")
    else:
        config_kwargs["krb_realm"] = os.environ.get("BEAKER_KRB_REALM")
        print(f"   Using Kerberos authentication")
    
    return BeakerClient(BeakerConfig(**config_kwargs))


def get_hub_url() -> str:
    """Get Beaker hub URL from environment.
    
    Returns:
        Hub URL string
        
    Exits with error if not set.
    """
    hub_url = os.environ.get("BEAKER_HUB_URL")
    if not hub_url:
        print("Error: BEAKER_HUB_URL environment variable required")
        print("Set it with: export BEAKER_HUB_URL='https://beaker.engineering.redhat.com'")
        sys.exit(1)
    return hub_url

