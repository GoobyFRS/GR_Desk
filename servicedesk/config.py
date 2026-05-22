"""Configuration loading utilities."""

from __future__ import annotations

from pathlib import Path

import yaml

from servicedesk.types import BrandingDict, ConfigDict, NavbarDict


def load_config(path: Path) -> ConfigDict:
    """Load application configuration from YAML file.

    Args:
        path: Path to configuration.yml file.

    Returns:
        Configuration dictionary.

    Raises:
        FileNotFoundError: If configuration file does not exist.
    """
    assert path is not None, "Configuration path cannot be None"

    if not path.exists():
        return _default_config()

    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert isinstance(config, dict), "Configuration must be a dictionary"
    return config


def load_branding(path: Path) -> BrandingDict:
    """Load branding configuration from YAML file.

    Args:
        path: Path to branding.yml file.

    Returns:
        Branding configuration dictionary.
    """
    assert path is not None, "Branding path cannot be None"

    if not path.exists():
        return _default_branding()

    with open(path, encoding="utf-8") as f:
        branding: BrandingDict = yaml.safe_load(f)

    assert isinstance(branding, dict), "Branding must be a dictionary"
    return branding


def load_navbar(path: Path) -> NavbarDict:
    """Load navigation bar configuration from YAML file.

    Args:
        path: Path to navbar YAML file.

    Returns:
        Navbar configuration dictionary.
    """
    assert path is not None, "Navbar path cannot be None"

    if not path.exists():
        return {"navbar": {"links": []}}

    with open(path, encoding="utf-8") as f:
        navbar: NavbarDict = yaml.safe_load(f)

    assert isinstance(navbar, dict), "Navbar must be a dictionary"
    return navbar


def load_titles(path: Path) -> list[str]:
    """Load employee titles from YAML file.

    Args:
        path: Path to employee_titles.yml file.

    Returns:
        List of job titles.
    """
    assert path is not None, "Titles path cannot be None"

    if not path.exists():
        return ["Support Technician"]

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Titles file must contain a dictionary"
    titles = data.get("titles", [])
    assert isinstance(titles, list), "Titles must be a list"
    return titles


def load_business_units(path: Path) -> list[str]:
    """Load business units from YAML file.

    Args:
        path: Path to business_units.yml file.

    Returns:
        List of business units.
    """
    assert path is not None, "Business units path cannot be None"

    if not path.exists():
        return ["Support"]

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Business units file must contain a dictionary"
    units = data.get("business_units", [])
    assert isinstance(units, list), "Business units must be a list"
    return units


def load_service_types(path: Path) -> list[str]:
    """Load service types from YAML file.

    Args:
        path: Path to service_types.yml file.

    Returns:
        List of service types.
    """
    assert path is not None, "Service types path cannot be None"

    if not path.exists():
        return ["Game Server", "Web Hosting", "VPS", "Other"]

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert isinstance(data, dict), "Service types file must contain a dictionary"
    types = data.get("service_types", [])
    assert isinstance(types, list), "Service types must be a list"
    return types


def _default_config() -> ConfigDict:
    """Return default configuration.

    Returns:
        Default configuration dictionary.
    """
    return {
        "app": {"name": "Service Desk", "debug": False, "log_level": "INFO"},
        "server": {"host": "0.0.0.0", "port": 5000, "workers": 2},
        "data": {"path": "data"},
        "tickets": {
            "queues": ["support", "escalation", "billing"],
            "statuses": ["new", "in_progress", "on_hold", "resolved", "cancelled"],
            "default_queue": "support",
            "default_status": "new",
        },
    }


def _default_branding() -> BrandingDict:
    """Return default branding configuration.

    Returns:
        Default branding dictionary.
    """
    return {
        "brand": {"name": "Service Desk", "tagline": "IT Service Management"},
        "colors": {"primary": "#2563eb", "background": "#f8fafc"},
    }
