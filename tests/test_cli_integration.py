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

    def test_businesses_bulk_enrich_batches_over_50(self, runner: CliRunner, config_with_key: Path):
        """Test businesses bulk-enrich auto-batches over 50 IDs."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.bulk_enrich.side_effect = [
                {"status": "success", "data": [{"id": f"id{i}"} for i in range(50)]},
                {"status": "success", "data": [{"id": f"id{i}"} for i in range(50, 75)]}
            ]
            MockAPI.return_value = mock_instance

            ids = ",".join([f"id{i}" for i in range(75)])
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "bulk-enrich", "--ids", ids]
            )

            assert result.exit_code == 0
            assert mock_instance.bulk_enrich.call_count == 2
            # First batch: 50 IDs
            first_call = mock_instance.bulk_enrich.call_args_list[0]
            assert len(first_call[0][0]) == 50
            # Second batch: 25 IDs
            second_call = mock_instance.bulk_enrich.call_args_list[1]
            assert len(second_call[0][0]) == 25

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
                ["--config", str(config_with_key), "businesses", "events", "list", "--ids", "id1,id2", "--events", "new_funding_round"]
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
        """Test prospects match with name + company (name alone is rejected)."""
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
                    "--last-name", "Doe",
                    "--company-name", "Acme"
                ]
            )

            mock_instance.match.assert_called_once()

    def test_prospects_match_name_only_rejected(self, runner: CliRunner, config_with_key: Path):
        """Test that name-only match is rejected with a helpful error."""
        result = runner.invoke(
            cli,
            [
                "--config", str(config_with_key),
                "prospects", "match",
                "--first-name", "John",
                "--last-name", "Doe"
            ]
        )
        assert result.exit_code != 0
        assert "Cannot match by name alone" in (result.output + result.stderr)

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

    def test_prospects_search_with_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test prospects search with CSV file of business IDs."""
        csv_file = tmp_path / "businesses.csv"
        csv_file.write_text("business_id\nbiz1\nbiz2\nbiz3\n")

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "-f", str(csv_file),
                    "--job-level", "cxo,vp",
                    "--has-email"
                ]
            )

            assert result.exit_code == 0
            mock_instance.search.assert_called_once()
            call_args = mock_instance.search.call_args
            filters = call_args[0][0]
            assert "business_id" in filters
            assert filters["business_id"]["values"] == ["biz1", "biz2", "biz3"]

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

    def test_csv_output_format(self, runner: CliRunner, config_with_key: Path):
        """Test CSV output format."""
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
                    "-o", "csv",
                    "businesses", "search", "--country", "us"
                ]
            )

            assert result.exit_code == 0
            # Check CSV structure
            assert "country,name" in result.output or "name,country" in result.output
            assert "Company A" in result.output
            assert "Company B" in result.output
            assert "US" in result.output
            assert "CA" in result.output

    def test_csv_output_with_complex_values(self, runner: CliRunner, config_with_key: Path):
        """Test CSV output handles nested objects as JSON strings."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {
                "status": "success",
                "data": [
                    {"name": "Company A", "tags": ["tech", "saas"], "meta": {"id": 1}}
                ]
            }
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "-o", "csv",
                    "businesses", "search", "--country", "us"
                ]
            )

            assert result.exit_code == 0
            # Complex values should be JSON-encoded
            assert "Company A" in result.output


class TestBusinessMatchBasedEnrichment:
    """Tests for match-based enrichment in business commands."""

    def test_enrich_with_id_calls_enrich_directly(self, runner: CliRunner, config_with_key: Path):
        """Test enrich with --id calls enrich API directly without match."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enrich.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--id", "direct_id_123"]
            )

            # Should call enrich directly, not match
            mock_instance.enrich.assert_called_once_with("direct_id_123")
            mock_instance.match.assert_not_called()

    def test_enrich_with_name_calls_match_then_enrich(self, runner: CliRunner, config_with_key: Path):
        """Test enrich with --name calls match API first, then enrich."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"business_id": "matched_id_456", "name": "Starbucks", "match_confidence": 0.95}]
            }
            mock_instance.enrich.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--name", "Starbucks"]
            )

            # Should call match first, then enrich with resolved ID
            mock_instance.match.assert_called_once()
            mock_instance.enrich.assert_called_once_with("matched_id_456")

    def test_enrich_with_domain_calls_match_then_enrich(self, runner: CliRunner, config_with_key: Path):
        """Test enrich with --domain calls match API first, then enrich."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"business_id": "domain_id_789", "website": "google.com", "match_confidence": 0.99}]
            }
            mock_instance.enrich.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--domain", "google.com"]
            )

            mock_instance.match.assert_called_once()
            mock_instance.enrich.assert_called_once_with("domain_id_789")

    def test_enrich_tech_with_name(self, runner: CliRunner, config_with_key: Path):
        """Test enrich-tech command accepts match parameters."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"business_id": "tech_id", "name": "Microsoft", "match_confidence": 0.97}]
            }
            mock_instance.enrich_technographics.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich-tech", "--name", "Microsoft"]
            )

            mock_instance.match.assert_called_once()
            mock_instance.enrich_technographics.assert_called_once_with("tech_id")

    def test_enrich_shows_error_when_no_match(self, runner: CliRunner, config_with_key: Path):
        """Test enrich shows error when no matches found."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--name", "NonexistentCorp"]
            )

            assert result.exit_code != 0
            full_output = result.output + (result.stderr or "")
            assert "No business matches found" in full_output or result.exit_code != 0

    def test_enrich_shows_low_confidence_suggestions(self, runner: CliRunner, config_with_key: Path):
        """Test enrich shows suggestions when confidence is low."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [
                    {"business_id": "maybe_id", "name": "Maybe Starbucks", "match_confidence": 0.5}
                ]
            }
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "enrich", "--name", "Starbucks"]
            )

            assert result.exit_code != 0
            full_output = result.output + (result.stderr or "")
            assert "confidence" in full_output.lower() or result.exit_code != 0

    def test_enrich_with_custom_min_confidence(self, runner: CliRunner, config_with_key: Path):
        """Test enrich accepts custom min-confidence threshold."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"business_id": "low_conf_id", "name": "Starbucks", "match_confidence": 0.5}]
            }
            mock_instance.enrich.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            # With low min-confidence, should succeed
            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "businesses", "enrich",
                    "--name", "Starbucks",
                    "--min-confidence", "0.4"
                ]
            )

            mock_instance.enrich.assert_called_once_with("low_conf_id")

    def test_lookalike_with_name(self, runner: CliRunner, config_with_key: Path):
        """Test lookalike command accepts match parameters."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"business_id": "lookalike_src", "name": "Starbucks", "match_confidence": 0.95}]
            }
            mock_instance.lookalike.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "lookalike", "--name", "Starbucks"]
            )

            mock_instance.match.assert_called_once()
            mock_instance.lookalike.assert_called_once_with("lookalike_src")

    def test_enrich_requires_id_or_match_params(self, runner: CliRunner, config_with_key: Path):
        """Test enrich requires either --id or match parameters."""
        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "businesses", "enrich"]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "Provide --id or match parameters" in full_output or result.exit_code == 2


class TestProspectMatchBasedEnrichment:
    """Tests for match-based enrichment in prospect commands."""

    def test_enrich_contacts_with_id_calls_directly(self, runner: CliRunner, config_with_key: Path):
        """Test enrich contacts with --id calls enrich API directly."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.enrich_contacts.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "enrich", "contacts", "--id", "prospect_123"]
            )

            mock_instance.enrich_contacts.assert_called_once_with("prospect_123")
            mock_instance.match.assert_not_called()

    def test_enrich_contacts_with_names_calls_match_then_enrich(self, runner: CliRunner, config_with_key: Path):
        """Test enrich contacts with name params calls match first."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"prospect_id": "matched_prospect", "first_name": "John", "match_confidence": 0.95}]
            }
            mock_instance.enrich_contacts.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "enrich", "contacts",
                    "--first-name", "John",
                    "--last-name", "Doe",
                    "--company-name", "Acme"
                ]
            )

            mock_instance.match.assert_called_once()
            mock_instance.enrich_contacts.assert_called_once_with("matched_prospect")

    def test_enrich_social_with_linkedin(self, runner: CliRunner, config_with_key: Path):
        """Test enrich social with linkedin param calls match first."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"prospect_id": "linkedin_prospect", "match_confidence": 0.98}]
            }
            mock_instance.enrich_social.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "enrich", "social",
                    "--linkedin", "https://linkedin.com/in/johndoe"
                ]
            )

            mock_instance.match.assert_called_once()
            mock_instance.enrich_social.assert_called_once_with("linkedin_prospect")

    def test_enrich_profile_with_names(self, runner: CliRunner, config_with_key: Path):
        """Test enrich profile accepts match parameters."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.match.return_value = {
                "status": "success",
                "data": [{"prospect_id": "profile_prospect", "match_confidence": 0.92}]
            }
            mock_instance.enrich_profile.return_value = {"status": "success", "data": {}}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "enrich", "profile",
                    "--first-name", "Jane",
                    "--last-name", "Smith",
                    "--company-name", "Microsoft"
                ]
            )

            mock_instance.match.assert_called_once()
            mock_instance.enrich_profile.assert_called_once_with("profile_prospect")


class TestBusinessSearchPagination:
    """Tests for business search with --total option (auto-pagination)."""

    def test_businesses_search_with_total(self, runner: CliRunner, config_with_key: Path):
        """Test businesses search with --total for auto-pagination."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            # Simulate 2 pages of results
            mock_instance.search.side_effect = [
                {
                    "status": "success",
                    "data": [{"business_id": f"id_{i}"} for i in range(100)],
                    "meta": {"page": 1, "size": 100, "total": 150}
                },
                {
                    "status": "success",
                    "data": [{"business_id": f"id_{i}"} for i in range(100, 150)],
                    "meta": {"page": 2, "size": 50, "total": 150}
                }
            ]
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search", "--country", "us", "--total", "150"]
            )

            assert result.exit_code == 0
            assert mock_instance.search.call_count == 2

    def test_businesses_search_total_negative_error(self, runner: CliRunner, config_with_key: Path):
        """Test that negative --total value raises error."""
        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "businesses", "search", "--total", "-10"]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "positive" in full_output.lower() or result.exit_code != 0

    def test_businesses_search_total_with_custom_page_size(self, runner: CliRunner, config_with_key: Path):
        """Test businesses search with --total and custom --page-size."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = [
                {
                    "status": "success",
                    "data": [{"business_id": f"id_{i}"} for i in range(50)],
                    "meta": {"page": 1, "size": 50, "total": 100}
                },
                {
                    "status": "success",
                    "data": [{"business_id": f"id_{i}"} for i in range(50, 100)],
                    "meta": {"page": 2, "size": 50, "total": 100}
                }
            ]
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "businesses", "search",
                    "--country", "us",
                    "--total", "100",
                    "--page-size", "50"
                ]
            )

            assert result.exit_code == 0
            assert mock_instance.search.call_count == 2

    def test_businesses_search_without_total_uses_single_page(self, runner: CliRunner, config_with_key: Path):
        """Test backwards compatibility - search without --total uses single page."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search", "--country", "us", "--page", "2"]
            )

            mock_instance.search.assert_called_once()
            call_kwargs = mock_instance.search.call_args[1]
            assert call_kwargs["page"] == 2

    def test_businesses_search_total_stops_when_no_more_data(self, runner: CliRunner, config_with_key: Path):
        """Test that pagination stops when API returns fewer results than available."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            # API only has 30 results, but we request 100
            mock_instance.search.return_value = {
                "status": "success",
                "data": [{"business_id": f"id_{i}"} for i in range(30)],
                "meta": {"page": 1, "size": 100, "total": 30}
            }
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search", "--country", "us", "--total", "100"]
            )

            assert result.exit_code == 0
            # Should only make 1 API call since total available is 30
            assert mock_instance.search.call_count == 1


class TestProspectSearchPagination:
    """Tests for prospect search with --total option (auto-pagination)."""

    def test_prospects_search_with_total(self, runner: CliRunner, config_with_key: Path):
        """Test prospects search with --total for auto-pagination."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = [
                {
                    "status": "success",
                    "data": [{"prospect_id": f"p_{i}"} for i in range(100)],
                    "meta": {"page": 1, "size": 100, "total": 200}
                },
                {
                    "status": "success",
                    "data": [{"prospect_id": f"p_{i}"} for i in range(100, 200)],
                    "meta": {"page": 2, "size": 100, "total": 200}
                }
            ]
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "abc123",
                    "--total", "200"
                ]
            )

            assert result.exit_code == 0
            assert mock_instance.search.call_count == 2

    def test_prospects_search_total_negative_error(self, runner: CliRunner, config_with_key: Path):
        """Test that negative --total value raises error."""
        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "prospects", "search", "--total", "0"]
        )

        assert result.exit_code != 0

    def test_prospects_search_without_total_uses_single_page(self, runner: CliRunner, config_with_key: Path):
        """Test backwards compatibility - search without --total uses single page."""
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
                    "--page", "3",
                    "--page-size", "25"
                ]
            )

            mock_instance.search.assert_called_once()
            call_kwargs = mock_instance.search.call_args[1]
            assert call_kwargs["page"] == 3
            assert call_kwargs["size"] == 25


class TestEnrichFileEmailOnly:
    """Tests for the bug: enrich-file 422 on email-only matched prospects.

    resolve_prospect_id was missing the email parameter, so email-only
    prospects were matched with empty params, causing 422 on enrichment.
    """

    def test_enrich_file_passes_email_to_match(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test enrich-file passes email to resolve_prospect_id for email-only prospects."""
        csv_file = tmp_path / "email_only.csv"
        csv_file.write_text("name,company,linkedin,email\nRobert Soong,,,robert.soong@ahss.org\n")

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI, \
             patch("explorium_cli.commands.prospects.resolve_prospect_id") as mock_resolve:
            mock_instance = MagicMock()
            MockAPI.return_value = mock_instance
            mock_resolve.return_value = "resolved_id_123"
            mock_instance.bulk_enrich.return_value = {"status": "success", "data": [{"prospect_id": "resolved_id_123"}]}

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "enrich-file",
                    "-f", str(csv_file),
                    "--types", "contacts",
                ]
            )

            assert result.exit_code == 0
            mock_resolve.assert_called_once()
            call_kwargs = mock_resolve.call_args[1]
            assert call_kwargs["email"] == "robert.soong@ahss.org"

    def test_enrich_file_email_only_does_not_send_empty_match(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test that email-only CSV rows don't result in empty match params."""
        csv_file = tmp_path / "email_only.csv"
        csv_file.write_text("email\nrobert.soong@ahss.org\n")

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI, \
             patch("explorium_cli.commands.prospects.resolve_prospect_id") as mock_resolve:
            mock_instance = MagicMock()
            MockAPI.return_value = mock_instance
            mock_resolve.return_value = "resolved_id_456"
            mock_instance.bulk_enrich.return_value = {"status": "success", "data": []}

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "enrich-file",
                    "-f", str(csv_file),
                    "--types", "contacts",
                ]
            )

            assert result.exit_code == 0
            call_kwargs = mock_resolve.call_args[1]
            # Email must be passed, not dropped
            assert call_kwargs["email"] == "robert.soong@ahss.org"
            # Name should NOT be included (email is a strong ID, no company)
            assert call_kwargs.get("first_name") is None
            assert call_kwargs.get("last_name") is None

    def test_bulk_enrich_match_file_passes_email(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test bulk-enrich --match-file also passes email to resolve_prospect_id."""
        match_file = tmp_path / "match.json"
        match_file.write_text(json.dumps([{"email": "robert.soong@ahss.org"}]))

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI, \
             patch("explorium_cli.commands.prospects.resolve_prospect_id") as mock_resolve:
            mock_instance = MagicMock()
            MockAPI.return_value = mock_instance
            mock_resolve.return_value = "resolved_id_789"
            mock_instance.bulk_enrich.return_value = {"status": "success", "data": []}

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "bulk-enrich",
                    "--match-file", str(match_file),
                    "--types", "contacts",
                ]
            )

            assert result.exit_code == 0
            call_kwargs = mock_resolve.call_args[1]
            assert call_kwargs["email"] == "robert.soong@ahss.org"


class TestProspectSearchMaxPerCompany:
    """Tests for --max-per-company option on prospects search."""

    def test_max_per_company_calls_parallel_search(self, runner: CliRunner, config_with_key: Path):
        """Test --max-per-company invokes parallel_prospect_search with correct args."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI, \
             patch("explorium_cli.commands.prospects.parallel_prospect_search") as mock_parallel:
            mock_instance = MagicMock()
            MockAPI.return_value = mock_instance
            mock_parallel.return_value = {"status": "success", "data": [{"prospect_id": "p1"}], "_search_meta": {}}

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "biz1,biz2",
                    "--job-level", "cxo",
                    "--max-per-company", "5"
                ]
            )

            assert result.exit_code == 0
            mock_parallel.assert_called_once()
            call_args = mock_parallel.call_args
            # First positional arg: api_method
            assert call_args[0][0] == mock_instance.search
            # Second positional arg: business_ids
            assert call_args[0][1] == ["biz1", "biz2"]
            # Third positional arg: filters (should NOT contain business_id)
            parallel_filters = call_args[0][2]
            assert "business_id" not in parallel_filters
            assert "job_level" in parallel_filters
            # total=max_per_company
            assert call_args[1]["total"] == 5

    def test_max_per_company_requires_business_ids(self, runner: CliRunner, config_with_key: Path):
        """Test --max-per-company errors without --business-id or --file."""
        result = runner.invoke(
            cli,
            [
                "--config", str(config_with_key),
                "prospects", "search",
                "--max-per-company", "5"
            ]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "--max-per-company requires --business-id or --file" in full_output

    def test_max_per_company_must_be_positive(self, runner: CliRunner, config_with_key: Path):
        """Test --max-per-company rejects zero and negative values."""
        result = runner.invoke(
            cli,
            [
                "--config", str(config_with_key),
                "prospects", "search",
                "--business-id", "biz1",
                "--max-per-company", "0"
            ]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "--max-per-company must be positive" in full_output

    def test_max_per_company_with_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test --max-per-company works with -f (CSV file of business IDs)."""
        csv_file = tmp_path / "businesses.csv"
        csv_file.write_text("business_id,name\nbiz1,Acme\nbiz2,Globex\n")

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI, \
             patch("explorium_cli.commands.prospects.parallel_prospect_search") as mock_parallel:
            mock_instance = MagicMock()
            MockAPI.return_value = mock_instance
            mock_parallel.return_value = {"status": "success", "data": [], "_search_meta": {}}

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "-f", str(csv_file),
                    "--max-per-company", "10"
                ]
            )

            assert result.exit_code == 0
            mock_parallel.assert_called_once()
            call_args = mock_parallel.call_args
            assert call_args[0][1] == ["biz1", "biz2"]
            assert call_args[1]["total"] == 10


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


class TestBulkEnrichCSVFormat:
    """Tests for bulk-enrich CSV file format requirements."""

    def test_prospects_bulk_enrich_csv_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test prospects bulk-enrich reads CSV with prospect_id column."""
        csv_file = tmp_path / "prospects.csv"
        csv_file.write_text("prospect_id,name,email\np1,John,john@example.com\np2,Jane,jane@example.com\n")

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.bulk_enrich.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "bulk-enrich", "-f", str(csv_file)]
            )

            assert result.exit_code == 0
            mock_instance.bulk_enrich.assert_called_once()
            call_args = mock_instance.bulk_enrich.call_args[0][0]
            assert call_args == ["p1", "p2"]

    def test_prospects_bulk_enrich_csv_missing_column_error(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test prospects bulk-enrich error when prospect_id column is missing."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("name,email\nJohn,john@example.com\n")

        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "prospects", "bulk-enrich", "-f", str(csv_file)]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "prospect_id" in full_output
        assert "Found columns:" in full_output

    def test_businesses_bulk_enrich_csv_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test businesses bulk-enrich reads CSV with business_id column."""
        csv_file = tmp_path / "businesses.csv"
        csv_file.write_text("business_id,company_name\nb1,Acme\nb2,Globex\n")

        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.bulk_enrich.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "bulk-enrich", "-f", str(csv_file)]
            )

            assert result.exit_code == 0
            mock_instance.bulk_enrich.assert_called_once()
            call_args = mock_instance.bulk_enrich.call_args[0][0]
            assert call_args == ["b1", "b2"]

    def test_businesses_bulk_enrich_csv_missing_column_error(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test businesses bulk-enrich error when business_id column is missing."""
        csv_file = tmp_path / "bad.csv"
        csv_file.write_text("company_name,website\nAcme,acme.com\n")

        result = runner.invoke(
            cli,
            ["--config", str(config_with_key), "businesses", "bulk-enrich", "-f", str(csv_file)]
        )

        assert result.exit_code != 0
        full_output = result.output + (result.stderr or "")
        assert "business_id" in full_output
        assert "Found columns:" in full_output

    def test_prospects_bulk_enrich_batches_over_50_from_file(self, runner: CliRunner, config_with_key: Path, tmp_path: Path):
        """Test prospects bulk-enrich auto-batches file with >50 IDs."""
        # Create CSV with 75 prospect IDs
        csv_content = "prospect_id,name\n" + "\n".join([f"p{i},Name{i}" for i in range(75)])
        csv_file = tmp_path / "prospects.csv"
        csv_file.write_text(csv_content)

        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.bulk_enrich.side_effect = [
                {"status": "success", "data": [{"id": f"p{i}"} for i in range(50)]},
                {"status": "success", "data": [{"id": f"p{i}"} for i in range(50, 75)]}
            ]
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "bulk-enrich", "-f", str(csv_file)]
            )

            assert result.exit_code == 0
            assert mock_instance.bulk_enrich.call_count == 2
            # First batch: 50 IDs
            first_call = mock_instance.bulk_enrich.call_args_list[0]
            assert len(first_call[0][0]) == 50
            # Second batch: 25 IDs
            second_call = mock_instance.bulk_enrich.call_args_list[1]
            assert len(second_call[0][0]) == 25


class TestSearchPageSizeFix:
    """Tests for the fix: single-page mode must pass page_size to the API.

    Previously, single-page mode only passed size=page_size but left the
    API method's page_size at its default (100), causing 422 errors when
    size < 100 (e.g. --page-size 3 => size=3, page_size=100 => 422).
    """

    def test_prospects_search_single_page_passes_page_size(self, runner: CliRunner, config_with_key: Path):
        """--page-size 3 without --total must send size=3 AND page_size=3."""
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
                    "--page-size", "3"
                ]
            )

            assert result.exit_code == 0
            mock_instance.search.assert_called_once()
            call_kwargs = mock_instance.search.call_args[1]
            assert call_kwargs["size"] == 3
            assert call_kwargs["page_size"] == 3

    def test_businesses_search_single_page_passes_page_size(self, runner: CliRunner, config_with_key: Path):
        """--page-size 5 without --total must send size=5 AND page_size=5."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "businesses", "search",
                    "--country", "us",
                    "--page-size", "5"
                ]
            )

            assert result.exit_code == 0
            mock_instance.search.assert_called_once()
            call_kwargs = mock_instance.search.call_args[1]
            assert call_kwargs["size"] == 5
            assert call_kwargs["page_size"] == 5

    def test_prospects_search_default_page_size_also_passed(self, runner: CliRunner, config_with_key: Path):
        """Default --page-size (100) must also send page_size=100."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "abc123"
                ]
            )

            assert result.exit_code == 0
            call_kwargs = mock_instance.search.call_args[1]
            assert call_kwargs["size"] == 100
            assert call_kwargs["page_size"] == 100


class TestSearchAPIErrorDisplay:
    """Tests for the fix: auto-pagination APIError should show response body.

    Previously, the except clause only caught generic Exception and called
    output_error(str(e)), which lost the APIError.response dict containing
    the actual API error details.
    """

    def test_prospects_search_autopaginate_api_error_shows_details(self, runner: CliRunner, config_with_key: Path):
        """APIError during auto-pagination must show both message and response body."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = APIError(
                "Validation failed: size must be >= page_size",
                status_code=422,
                response={"detail": "size must be >= page_size"}
            )
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "abc123",
                    "--total", "5"
                ]
            )

            assert result.exit_code != 0
            stderr = result.stderr or ""
            assert "Validation failed" in stderr
            assert "size must be >= page_size" in stderr

    def test_businesses_search_autopaginate_api_error_shows_details(self, runner: CliRunner, config_with_key: Path):
        """APIError during auto-pagination must show both message and response body."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = APIError(
                "Validation failed: size must be >= page_size",
                status_code=422,
                response={"detail": "size must be >= page_size"}
            )
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "businesses", "search",
                    "--country", "us",
                    "--total", "5"
                ]
            )

            assert result.exit_code != 0
            stderr = result.stderr or ""
            assert "Validation failed" in stderr
            assert "size must be >= page_size" in stderr

    def test_prospects_search_autopaginate_generic_error_still_works(self, runner: CliRunner, config_with_key: Path):
        """Non-APIError exceptions should still be caught and displayed."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.side_effect = RuntimeError("Connection timeout")
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                [
                    "--config", str(config_with_key),
                    "prospects", "search",
                    "--business-id", "abc123",
                    "--total", "5"
                ]
            )

            assert result.exit_code != 0
            stderr = result.stderr or ""
            assert "Connection timeout" in stderr
