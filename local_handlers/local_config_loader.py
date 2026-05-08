#!/usr/bin/env python3
"""Configuration loader for GR_Desk application.

This module provides centralized loading of YAML-based configuration
from core_configuration.yml. Configuration is loaded once and should be
cached in a singleton to avoid repeated file I/O.
"""

__all__ = ["load_core_config"]

import os
from typing import Any

import yaml

CONFIG_PATH: str = "./my_data/core_configuration.yml"


def load_core_config() -> dict[str, Any]:
    """Load and parse core configuration from YAML file.

    Reads the core_configuration.yml file from the configured path and
    returns the parsed YAML structure as a dictionary.

    Returns:
        A dictionary containing all configuration keys and values from
        core_configuration.yml.

    Raises:
        FileNotFoundError: If core_configuration.yml does not exist at
            the configured CONFIG_PATH.
    """
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"core_configuration.yml missing at {CONFIG_PATH}"
        )

    with open(CONFIG_PATH, "r") as config_file:
        return yaml.safe_load(config_file)