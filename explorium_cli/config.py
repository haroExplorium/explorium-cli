"""Configuration management for Explorium CLI."""

import os
from pathlib import Path
from typing import Any, Optional

import yaml
from dotenv import load_dotenv


# Default config directory and file
CONFIG_DIR = Path.home() / ".explorium"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Default configuration values
DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.explorium.ai/v1",
    "default_output": "json",
    "default_page_size": 100,
}


def ensure_config_dir() -> Path:
    """Ensure the config directory exists."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config(config_path: Optional[str] = None) -> dict[str, Any]:
    """
    Load configuration from file and environment.

    Priority (highest to lowest):
    1. Environment variables (EXPLORIUM_*)
    2. Config file specified by config_path
    3. Default config file (~/.explorium/config.yaml)
    4. Default values

    Args:
        config_path: Optional path to config file.

    Returns:
        Configuration dictionary.
    """
    # Load .env file if present
    load_dotenv()

    # Start with defaults
    config = DEFAULT_CONFIG.copy()

    # Load from config file
    file_path = Path(config_path) if config_path else CONFIG_FILE
    if file_path.exists():
        with open(file_path) as f:
            file_config = yaml.safe_load(f) or {}
            config.update(file_config)

    # Override with environment variables
    env_mappings = {
        "EXPLORIUM_API_KEY": "api_key",
        "EXPLORIUM_BASE_URL": "base_url",
        "EXPLORIUM_DEFAULT_OUTPUT": "default_output",
        "EXPLORIUM_PAGE_SIZE": "default_page_size",
    }

    for env_var, config_key in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value:
            if config_key == "default_page_size":
                config[config_key] = int(env_value)
            else:
                config[config_key] = env_value

    return config


def save_config(config: dict[str, Any], config_path: Optional[str] = None) -> Path:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save.
        config_path: Optional path to config file.

    Returns:
        Path to the saved config file.
    """
    ensure_config_dir()
    file_path = Path(config_path) if config_path else CONFIG_FILE

    with open(file_path, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    return file_path


def get_config_value(key: str, config_path: Optional[str] = None) -> Any:
    """Get a specific configuration value."""
    config = load_config(config_path)
    return config.get(key)


def set_config_value(
    key: str,
    value: Any,
    config_path: Optional[str] = None
) -> Path:
    """
    Set a specific configuration value and save.

    Args:
        key: Configuration key to set.
        value: Value to set.
        config_path: Optional path to config file.

    Returns:
        Path to the saved config file.
    """
    config = load_config(config_path)
    config[key] = value
    return save_config(config, config_path)


def init_config(api_key: str, config_path: Optional[str] = None) -> Path:
    """
    Initialize configuration with API key.

    Args:
        api_key: The Explorium API key.
        config_path: Optional path to config file.

    Returns:
        Path to the saved config file.
    """
    config = DEFAULT_CONFIG.copy()
    config["api_key"] = api_key
    return save_config(config, config_path)
