"""
pybeaker - Python library for automating Beaker system reservations

This library provides:
- BeakerClient: HTTP API client for direct system operations
- JobBuilder: Fluent API for building Beaker job XML
- BeakerCLI: Wrapper for bkr command-line operations

Example:
    from pybeaker import BeakerClient, BeakerConfig
    
    client = BeakerClient(BeakerConfig(
        hub_url="https://beaker.example.com",
        auth_method="krbv",
    ))
    
    user = client.whoami()
    job_id = client.submit_job(job_xml)
"""

from .client import BeakerClient
from .job_builder import JobBuilder, Recipe, RecipeSet
from .cli import BeakerCLI
from .config import BeakerConfig

__version__ = "0.1.0"

__all__ = [
    "BeakerClient",
    "BeakerConfig",
    "BeakerCLI",
    "JobBuilder",
    "Recipe",
    "RecipeSet",
]

