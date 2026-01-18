"""Tests for the configuration module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from explorium_cli.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_CONFIG,
    ensure_config_dir,
    load_config,
    save_config,
    get_config_value,
    set_config_value,
    init_config,
)


class TestEnsureConfigDir:
    """Tests for ensure_config_dir function."""

    def test_creates_directory_if_not_exists(self, tmp_path: Path):
        """Test that config directory is created if it doesn't exist."""
        with patch("explorium_cli.config.CONFIG_DIR", tmp_path / ".explorium"):
            result = ensure_config_dir()
            assert result.exists()
            assert result.is_dir()

    def test_returns_existing_directory(self, tmp_path: Path):
        """Test that existing directory is returned without error."""
        config_dir = tmp_path / ".explorium"
        config_dir.mkdir(parents=True)

        with patch("explorium_cli.config.CONFIG_DIR", config_dir):
            result = ensure_config_dir()
            assert result == config_dir
            assert result.exists()


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_default_config_when_no_file(self, tmp_path: Path, clean_env):
        """Test loading default config when no config file exists."""
        config_file = tmp_path / "nonexistent.yaml"
        config = load_config(str(config_file))

        assert config["api_key"] == ""
        assert config["base_url"] == "https://api.explorium.ai/v1"
        assert config["default_output"] == "json"
        assert config["default_page_size"] == 100

    def test_load_config_from_file(self, temp_config_file: Path, clean_env):
        """Test loading config from file."""
        config = load_config(str(temp_config_file))

        assert config["api_key"] == "test_api_key_12345"
        assert config["base_url"] == "https://api.explorium.ai/v1"
        assert config["default_output"] == "json"
        assert config["default_page_size"] == 100

    def test_load_config_from_environment(self, tmp_path: Path, mock_env_vars):
        """Test loading config from environment variables."""
        config_file = tmp_path / "empty.yaml"
        config = load_config(str(config_file))

        assert config["api_key"] == "env_api_key_67890"
        assert config["base_url"] == "https://custom.api.com/v1"
        assert config["default_output"] == "table"
        assert config["default_page_size"] == 50

    def test_environment_overrides_file(self, temp_config_file: Path, mock_env_vars):
        """Test that environment variables override file config."""
        config = load_config(str(temp_config_file))

        # Environment should override file
        assert config["api_key"] == "env_api_key_67890"
        assert config["base_url"] == "https://custom.api.com/v1"

    def test_load_config_with_partial_file(self, tmp_path: Path, clean_env):
        """Test loading config when file has partial values."""
        config_file = tmp_path / "partial.yaml"
        with open(config_file, "w") as f:
            yaml.safe_dump({"api_key": "partial_key"}, f)

        config = load_config(str(config_file))

        assert config["api_key"] == "partial_key"
        assert config["base_url"] == "https://api.explorium.ai/v1"  # default
        assert config["default_output"] == "json"  # default

    def test_load_config_with_empty_file(self, tmp_path: Path, clean_env):
        """Test loading config when file is empty."""
        config_file = tmp_path / "empty.yaml"
        config_file.touch()

        config = load_config(str(config_file))

        # Should use defaults
        assert config == DEFAULT_CONFIG

    def test_load_config_default_path(self, tmp_path: Path, clean_env):
        """Test loading config from default path."""
        with patch("explorium_cli.config.CONFIG_FILE", tmp_path / "config.yaml"):
            config_file = tmp_path / "config.yaml"
            with open(config_file, "w") as f:
                yaml.safe_dump({"api_key": "default_path_key"}, f)

            config = load_config()
            assert config["api_key"] == "default_path_key"


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_file(self, tmp_path: Path):
        """Test that save_config creates config file."""
        config_file = tmp_path / ".explorium" / "config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path / ".explorium"):
            with patch("explorium_cli.config.CONFIG_FILE", config_file):
                result = save_config({"api_key": "saved_key"})

        assert result == config_file
        assert config_file.exists()

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["api_key"] == "saved_key"

    def test_save_config_custom_path(self, tmp_path: Path):
        """Test saving config to custom path."""
        config_file = tmp_path / "custom_config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            result = save_config({"api_key": "custom_key"}, str(config_file))

        assert result == config_file
        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["api_key"] == "custom_key"

    def test_save_config_overwrites_existing(self, tmp_path: Path):
        """Test that save_config overwrites existing file."""
        config_file = tmp_path / "config.yaml"

        # Create initial file
        with open(config_file, "w") as f:
            yaml.safe_dump({"api_key": "old_key"}, f)

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            save_config({"api_key": "new_key"}, str(config_file))

        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["api_key"] == "new_key"

    def test_save_config_creates_directory(self, tmp_path: Path):
        """Test that save_config creates directory if needed."""
        config_dir = tmp_path / ".explorium"
        config_file = config_dir / "config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", config_dir):
            with patch("explorium_cli.config.CONFIG_FILE", config_file):
                save_config({"api_key": "new_key"})

        assert config_dir.exists()
        assert config_file.exists()


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_get_existing_value(self, temp_config_file: Path, clean_env):
        """Test getting an existing config value."""
        value = get_config_value("api_key", str(temp_config_file))
        assert value == "test_api_key_12345"

    def test_get_nonexistent_value(self, temp_config_file: Path, clean_env):
        """Test getting a nonexistent config value returns None."""
        value = get_config_value("nonexistent_key", str(temp_config_file))
        assert value is None

    def test_get_default_value(self, tmp_path: Path, clean_env):
        """Test getting default value when no file exists."""
        config_file = tmp_path / "nonexistent.yaml"
        value = get_config_value("base_url", str(config_file))
        assert value == "https://api.explorium.ai/v1"


class TestSetConfigValue:
    """Tests for set_config_value function."""

    def test_set_new_value(self, temp_config_file: Path, clean_env):
        """Test setting a new config value."""
        set_config_value("new_key", "new_value", str(temp_config_file))

        with open(temp_config_file) as f:
            config = yaml.safe_load(f)
        assert config["new_key"] == "new_value"

    def test_update_existing_value(self, temp_config_file: Path, clean_env):
        """Test updating an existing config value."""
        set_config_value("api_key", "updated_key", str(temp_config_file))

        with open(temp_config_file) as f:
            config = yaml.safe_load(f)
        assert config["api_key"] == "updated_key"

    def test_set_preserves_other_values(self, temp_config_file: Path, clean_env):
        """Test that setting a value preserves other values."""
        set_config_value("new_key", "new_value", str(temp_config_file))

        with open(temp_config_file) as f:
            config = yaml.safe_load(f)
        assert config["api_key"] == "test_api_key_12345"  # preserved
        assert config["new_key"] == "new_value"  # added


class TestInitConfig:
    """Tests for init_config function."""

    def test_init_creates_config_with_api_key(self, tmp_path: Path):
        """Test that init_config creates config with API key."""
        config_file = tmp_path / "config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            result = init_config("my_api_key", str(config_file))

        assert result == config_file
        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert config["api_key"] == "my_api_key"
        assert config["base_url"] == "https://api.explorium.ai/v1"

    def test_init_uses_default_values(self, tmp_path: Path):
        """Test that init_config uses default values for other settings."""
        config_file = tmp_path / "config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            init_config("my_api_key", str(config_file))

        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert config["default_output"] == "json"
        assert config["default_page_size"] == 100

    def test_init_overwrites_existing_config(self, tmp_path: Path):
        """Test that init_config overwrites existing config."""
        config_file = tmp_path / "config.yaml"

        # Create existing config
        with open(config_file, "w") as f:
            yaml.safe_dump({"api_key": "old_key", "custom": "value"}, f)

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            init_config("new_api_key", str(config_file))

        with open(config_file) as f:
            config = yaml.safe_load(f)

        assert config["api_key"] == "new_api_key"
        assert "custom" not in config  # old custom value removed


class TestDefaultConfigConstants:
    """Tests for configuration constants."""

    def test_config_dir_is_in_home(self):
        """Test CONFIG_DIR is in home directory."""
        assert CONFIG_DIR == Path.home() / ".explorium"

    def test_config_file_is_in_config_dir(self):
        """Test CONFIG_FILE is in CONFIG_DIR."""
        assert CONFIG_FILE == CONFIG_DIR / "config.yaml"

    def test_default_config_has_required_keys(self):
        """Test DEFAULT_CONFIG has all required keys."""
        required_keys = ["api_key", "base_url", "default_output", "default_page_size"]
        for key in required_keys:
            assert key in DEFAULT_CONFIG

    def test_default_config_values(self):
        """Test DEFAULT_CONFIG has correct default values."""
        assert DEFAULT_CONFIG["api_key"] == ""
        assert DEFAULT_CONFIG["base_url"] == "https://api.explorium.ai/v1"
        assert DEFAULT_CONFIG["default_output"] == "json"
        assert DEFAULT_CONFIG["default_page_size"] == 100
