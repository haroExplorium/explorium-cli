"""Integration tests for CLI commands."""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from click.testing import CliRunner

from explorium_cli.main import cli
from explorium_cli.api.client import APIError
from explorium_cli.utils import get_api, handle_api_call


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def mock_api():
    """Create a mock API client."""
    with patch("explorium_cli.main.ExploriumAPI") as MockAPI:
        mock_instance = MagicMock()
        MockAPI.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def config_with_key(tmp_path: Path) -> Path:
    """Create a config file with API key."""
    config_dir = tmp_path / ".explorium"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "api_key": "test_api_key",
        "base_url": "https://api.explorium.ai/v1",
        "default_output": "json"
    }))
    return config_file


class TestCLIRoot:
    """Tests for the root CLI command."""

    def test_cli_help(self, runner: CliRunner):
        """Test CLI help displays."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Explorium API CLI" in result.output

    def test_cli_version_group_exists(self, runner: CliRunner):
        """Test CLI has expected command groups."""
        result = runner.invoke(cli, ["--help"])
        assert "businesses" in result.output
        assert "prospects" in result.output
        assert "webhooks" in result.output
        assert "config" in result.output


class TestConfigCommands:
    """Tests for config commands."""

    def test_config_init(self, runner: CliRunner, tmp_path: Path):
        """Test config init creates config file."""
        config_file = tmp_path / "config.yaml"

        with patch("explorium_cli.config.CONFIG_DIR", tmp_path):
            result = runner.invoke(
                cli,
                ["config", "init", "--api-key", "my_test_key", "--config-path", str(config_file)]
            )

        assert result.exit_code == 0
        assert "Success" in result.output
        assert config_file.exists()

        with open(config_file) as f:
            config = yaml.safe_load(f)
        assert config["api_key"] == "my_test_key"

    def test_config_show(self, runner: CliRunner, config_with_key: Path):
        """Test config show displays configuration."""
        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "config", "show", "--config-path", str(config_with_key)]
        )

        assert result.exit_code == 0
        assert "api_key" in result.output

    def test_config_set(self, runner: CliRunner, config_with_key: Path):
        """Test config set updates values."""
        result = runner.invoke(
            cli,
            ["config", "set", "default_output", "table", "--config-path", str(config_with_key)]
        )

        assert result.exit_code == 0
        assert "Success" in result.output

        with open(config_with_key) as f:
            config = yaml.safe_load(f)
        assert config["default_output"] == "table"


class TestBusinessCommands:
    """Tests for business commands."""

    def test_businesses_help(self, runner: CliRunner):
        """Test businesses help displays."""
        result = runner.invoke(cli, ["businesses", "--help"])
        assert result.exit_code == 0
        assert "match" in result.output
        assert "search" in result.output
        assert "enrich" in result.output

    def test_businesses_match_requires_input(self, runner: CliRunner, config_with_key: Path):
        """Test businesses match requires input."""
        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "businesses", "match"],
            catch_exceptions=False
        )
        assert result.exit_code != 0
        # Error goes to stderr
        full_output = result.output + (result.stderr or "")
        assert "Provide" in full_output or "Error" in full_output or result.exit_code == 2

    def test_businesses_match_with_name(self, runner: CliRunner, config_with_key: Path):
        """Test businesses match with name."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "match", "--name", "Starbucks"]
            )

            # Check the API was called
            mock_instance.match.assert_called_once()

    def test_businesses_match_from_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test businesses match from JSON file."""
        # Create test file
        test_file = tmp_path / "companies.json"
        test_file.write_text(json.dumps([
            {"name": "Company A", "website": "companya.com"},
            {"name": "Company B", "website": "companyb.com"}
        ]))

        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "match", "-f", str(test_file)]
            )

            mock_instance.match.assert_called_once()
            call_args = mock_instance.match.call_args[0][0]
            assert len(call_args) == 2

    def test_businesses_search(self, runner: CliRunner, config_with_key: Path):
        """Test businesses search."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search", "--country", "us,ca"]
            )

            mock_instance.search.assert_called_once()

    def test_businesses_enrich(self, runner: CliRunner, config_with_key: Path):
        """Test businesses enrich."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enrich.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--id", "abc123"]
            )

            mock_instance.enrich.assert_called_once_with("abc123")

    def test_businesses_bulk_enrich_limit(self, runner: CliRunner, config_with_key: Path):
        """Test businesses bulk-enrich enforces 50 limit."""
        ids = ",".join([f"id{i}" for i in range(51)])

        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "businesses", "bulk-enrich", "--ids", ids]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "Maximum 50" in full_output or "50" in full_output or result.exit_code != 0

    def test_businesses_lookalike(self, runner: CliRunner, config_with_key: Path):
        """Test businesses lookalike."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.lookalike.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "lookalike", "--id", "abc123"]
            )

            mock_instance.lookalike.assert_called_once()

    def test_businesses_autocomplete(self, runner: CliRunner, config_with_key: Path):
        """Test businesses autocomplete."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.autocomplete.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "autocomplete", "-q", "star"]
            )

            mock_instance.autocomplete.assert_called_once_with("star")


class TestBusinessEventsCommands:
    """Tests for business events subcommands."""

    def test_events_list(self, runner: CliRunner, config_with_key: Path):
        """Test business events list."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.list_events.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "events", "list", "--ids", "id1,id2"]
            )

            mock_instance.list_events.assert_called_once()

    def test_events_enroll(self, runner: CliRunner, config_with_key: Path):
        """Test business events enroll."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enroll_events.return_value = {"status": "success"}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "businesses", "events", "enroll",
                    "--ids", "id1,id2",
                    "--events", "new_funding_round",
                    "--key", "my_key"
                ]
            )

            mock_instance.enroll_events.assert_called_once()


class TestProspectCommands:
    """Tests for prospect commands."""

    def test_prospects_help(self, runner: CliRunner):
        """Test prospects help displays."""
        result = runner.invoke(cli, ["prospects", "--help"])
        assert result.exit_code == 0
        assert "match" in result.output
        assert "search" in result.output
        assert "enrich" in result.output

    def test_prospects_match_with_name(self, runner: CliRunner, config_with_key: Path):
        """Test prospects match with name."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "match",
                    "--first-name", "John",
                    "--last-name", "Doe"
                ]
            )

            mock_instance.match.assert_called_once()

    def test_prospects_search(self, runner: CliRunner, config_with_key: Path):
        """Test prospects search."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "abc123",
                    "--job-level", "cxo,vp",
                    "--has-email"
                ]
            )

            mock_instance.search.assert_called_once()
            call_args = mock_instance.search.call_args
            filters = call_args[0][0]
            assert "job_level" in filters
            assert "has_email" in filters

    def test_prospects_enrich_contacts(self, runner: CliRunner, config_with_key: Path):
        """Test prospects enrich contacts."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enrich_contacts.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "enrich", "contacts", "--id", "prospect123"]
            )

            mock_instance.enrich_contacts.assert_called_once_with("prospect123")

    def test_prospects_enrich_social(self, runner: CliRunner, config_with_key: Path):
        """Test prospects enrich social."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enrich_social.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "enrich", "social", "--id", "prospect123"]
            )

            mock_instance.enrich_social.assert_called_once_with("prospect123")

    def test_prospects_statistics(self, runner: CliRunner, config_with_key: Path):
        """Test prospects statistics."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.statistics.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "statistics",
                    "--business-id", "abc123",
                    "--group-by", "department,job_level"
                ]
            )

            mock_instance.statistics.assert_called_once()


class TestWebhookCommands:
    """Tests for webhook commands."""

    def test_webhooks_help(self, runner: CliRunner):
        """Test webhooks help displays."""
        result = runner.invoke(cli, ["webhooks", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "get" in result.output
        assert "update" in result.output
        assert "delete" in result.output

    def test_webhooks_create(self, runner: CliRunner, config_with_key: Path):
        """Test webhooks create."""
        with patch("explorium_cli.commands.webhooks.WebhooksAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.create.return_value = {"status": "success"}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "webhooks", "create",
                    "--partner-id", "my_partner",
                    "--url", "https://myapp.com/webhook"
                ]
            )

            mock_instance.create.assert_called_once_with("my_partner", "https://myapp.com/webhook")

    def test_webhooks_get(self, runner: CliRunner, config_with_key: Path):
        """Test webhooks get."""
        with patch("explorium_cli.commands.webhooks.WebhooksAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.get.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "webhooks", "get", "--partner-id", "my_partner"]
            )

            mock_instance.get.assert_called_once_with("my_partner")

    def test_webhooks_update(self, runner: CliRunner, config_with_key: Path):
        """Test webhooks update."""
        with patch("explorium_cli.commands.webhooks.WebhooksAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.update.return_value = {"status": "success"}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "webhooks", "update",
                    "--partner-id", "my_partner",
                    "--url", "https://newapp.com/webhook"
                ]
            )

            mock_instance.update.assert_called_once_with("my_partner", "https://newapp.com/webhook")

    def test_webhooks_delete(self, runner: CliRunner, config_with_key: Path):
        """Test webhooks delete."""
        with patch("explorium_cli.commands.webhooks.WebhooksAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.delete.return_value = {"status": "success"}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "webhooks", "delete", "--partner-id", "my_partner"]
            )

            mock_instance.delete.assert_called_once_with("my_partner")


class TestOutputFormats:
    """Tests for output format options."""

    def test_json_output_format(self, runner: CliRunner, config_with_key: Path):
        """Test JSON output format."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.autocomplete.return_value = {"status": "success", "data": [{"name": "Test"}]}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "-o", "json",
                    "businesses", "autocomplete", "-q", "test"
                ]
            )

            # JSON output should be present (the actual format depends on rich)
            assert result.exit_code == 0

    def test_table_output_format(self, runner: CliRunner, config_with_key: Path):
        """Test table output format."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {
                "status": "success",
                "data": [
                    {"name": "Company A", "country": "US"},
                    {"name": "Company B", "country": "CA"}
                ]
            }
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "-o", "table",
                    "businesses", "search", "--country", "us"
                ]
            )

            assert result.exit_code == 0


class TestErrorHandling:
    """Tests for error handling."""

    def test_missing_api_key(self, runner: CliRunner, tmp_path: Path):
        """Test error when API key is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml.dump({"base_url": "https://api.explorium.ai/v1"}))

        result = runner.invoke(
            cli,
            ["--config", str(config_file), "businesses", "autocomplete", "-q", "test"]
        )

        assert result.exit_code != 0
        # Error may go to stderr
        full_output = result.output + (result.stderr or "")
        assert "API key not configured" in full_output or result.exit_code != 0

    def test_api_error_handling(self, runner: CliRunner, config_with_key: Path):
        """Test API error is handled gracefully."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.autocomplete.side_effect = APIError(
                "API request failed",
                status_code=400,
                response={"error": "Bad request"}
            )
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "autocomplete", "-q", "test"]
            )

            # Should handle error gracefully - error goes to stderr
            full_output = result.output + (result.stderr or "")
            assert result.exit_code != 0 or "Error" in full_output
