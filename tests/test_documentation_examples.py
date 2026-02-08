"""
Tests for all CLI examples documented in CLI_DOCUMENTATION.md

This test file verifies that every command-line example in the documentation
is valid and executes correctly (with mocked API calls).
"""

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import yaml
from click.testing import CliRunner

from explorium_cli.main import cli


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def config_file(tmp_path: Path) -> Path:
    """Create a config file with API key."""
    config_dir = tmp_path / ".explorium"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "api_key": "test_api_key",
        "base_url": "https://api.explorium.ai/v1",
        "default_output": "json",
        "default_page_size": 100
    }))
    return config_file


@pytest.fixture
def mock_businesses_api():
    """Mock BusinessesAPI for all business commands."""
    with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
        mock_instance = MagicMock()
        mock_instance.match.return_value = {
            "status": "success",
            "matched_businesses": [{"business_id": "8adce3ca1cef0c986b22310e369a0793", "name": "Test Company"}]
        }
        mock_instance.search.return_value = {
            "status": "success",
            "data": [{"business_id": "id1", "name": "Company A"}],
            "meta": {"page": 1, "total": 1}
        }
        mock_instance.enrich.return_value = {
            "status": "success",
            "data": {"business_id": "id1", "name": "Company A", "revenue": "10M"}
        }
        mock_instance.bulk_enrich.return_value = {
            "status": "success",
            "data": [{"business_id": "id1"}, {"business_id": "id2"}]
        }
        mock_instance.lookalike.return_value = {
            "status": "success",
            "data": [{"business_id": "similar1", "similarity_score": 0.9}]
        }
        mock_instance.autocomplete.return_value = {
            "status": "success",
            "data": [{"name": "Starbucks", "business_id": "id1"}]
        }
        mock_instance.list_events.return_value = {
            "status": "success",
            "data": [{"event_type": "new_funding_round", "date": "2024-01-15"}]
        }
        mock_instance.enroll_events.return_value = {"status": "success"}
        mock_instance.list_enrollments.return_value = {
            "status": "success",
            "data": [{"key": "my_key", "business_id": {"values": ["id1"]}}]
        }
        MockAPI.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_prospects_api():
    """Mock ProspectsAPI for all prospect commands."""
    with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
        mock_instance = MagicMock()
        mock_instance.match.return_value = {
            "status": "success",
            "matched_prospects": [{"prospect_id": "prospect_001", "first_name": "John", "last_name": "Doe"}]
        }
        mock_instance.search.return_value = {
            "status": "success",
            "data": [{"prospect_id": "prospect_001", "job_title": "VP Engineering"}],
            "meta": {"page": 1, "total": 1}
        }
        mock_instance.bulk_enrich.return_value = {
            "status": "success",
            "data": [{"prospect_id": "prospect_001"}]
        }
        mock_instance.enrich_contacts.return_value = {
            "status": "success",
            "data": {"prospect_id": "prospect_001", "email": "john@company.com"}
        }
        mock_instance.enrich_social.return_value = {
            "status": "success",
            "data": {"prospect_id": "prospect_001", "linkedin": "https://linkedin.com/in/johndoe"}
        }
        mock_instance.enrich_profile.return_value = {
            "status": "success",
            "data": {"prospect_id": "prospect_001", "job_title": "VP Engineering"}
        }
        mock_instance.statistics.return_value = {
            "status": "success",
            "data": {"total": 100, "by_department": {"Engineering": 50}}
        }
        mock_instance.list_events.return_value = {
            "status": "success",
            "data": [{"event_type": "prospect_changed_company"}]
        }
        mock_instance.enroll_events.return_value = {"status": "success"}
        mock_instance.list_enrollments.return_value = {
            "status": "success",
            "data": [{"key": "my_key", "prospect_ids": ["prospect_001"]}]
        }
        MockAPI.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_webhooks_api():
    """Mock WebhooksAPI for all webhook commands."""
    with patch("explorium_cli.commands.webhooks.WebhooksAPI") as MockAPI:
        mock_instance = MagicMock()
        mock_instance.create.return_value = {
            "status": "success",
            "data": {"partner_id": "my_partner", "webhook_url": "https://myapp.com/webhook"}
        }
        mock_instance.get.return_value = {
            "status": "success",
            "data": {"partner_id": "my_partner", "webhook_url": "https://myapp.com/webhook"}
        }
        mock_instance.update.return_value = {"status": "success"}
        mock_instance.delete.return_value = {"status": "success"}
        MockAPI.return_value = mock_instance
        yield mock_instance


# =============================================================================
# Global Options Tests
# =============================================================================

class TestGlobalOptions:
    """Tests for global CLI options from documentation."""

    def test_help_option(self, runner: CliRunner):
        """Test: explorium --help"""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Explorium" in result.output

    def test_businesses_help(self, runner: CliRunner):
        """Test: explorium businesses --help"""
        result = runner.invoke(cli, ["businesses", "--help"])
        assert result.exit_code == 0

    def test_businesses_search_help(self, runner: CliRunner):
        """Test: explorium businesses search --help"""
        result = runner.invoke(cli, ["businesses", "search", "--help"])
        assert result.exit_code == 0

    def test_table_output_option(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium -o table businesses search --country us"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0

    def test_custom_config_option(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium -c /path/to/config.yaml businesses search --country us"""
        result = runner.invoke(cli, [
            "-c", str(config_file),
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0


# =============================================================================
# Config Command Tests
# =============================================================================

class TestConfigCommands:
    """Tests for config commands from documentation."""

    def test_config_init_basic(self, runner: CliRunner, tmp_path: Path):
        """Test: explorium config init --api-key 'sk_live_abc123xyz'"""
        config_file = tmp_path / "config.yaml"
        result = runner.invoke(cli, [
            "config", "init",
            "--api-key", "sk_live_abc123xyz",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0
        assert config_file.exists()

    def test_config_init_short_form(self, runner: CliRunner, tmp_path: Path):
        """Test: explorium config init -k 'sk_live_abc123xyz'"""
        config_file = tmp_path / "config.yaml"
        result = runner.invoke(cli, [
            "config", "init",
            "-k", "sk_live_abc123xyz",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0

    def test_config_init_custom_path(self, runner: CliRunner, tmp_path: Path):
        """Test: explorium config init -k 'key' --config-path ~/my-project/explorium.yaml"""
        config_file = tmp_path / "my-project" / "explorium.yaml"
        config_file.parent.mkdir(parents=True)
        result = runner.invoke(cli, [
            "config", "init",
            "-k", "sk_live_abc123xyz",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0

    def test_config_show(self, runner: CliRunner, config_file: Path):
        """Test: explorium config show"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "config", "show",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0
        assert "api_key" in result.output

    def test_config_set_default_output(self, runner: CliRunner, config_file: Path):
        """Test: explorium config set default_output table"""
        result = runner.invoke(cli, [
            "config", "set", "default_output", "table",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0

    def test_config_set_page_size(self, runner: CliRunner, config_file: Path):
        """Test: explorium config set default_page_size 50"""
        result = runner.invoke(cli, [
            "config", "set", "default_page_size", "50",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0

    def test_config_set_api_key(self, runner: CliRunner, config_file: Path):
        """Test: explorium config set api_key 'sk_live_new_key_here'"""
        result = runner.invoke(cli, [
            "config", "set", "api_key", "sk_live_new_key_here",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0

    def test_config_set_base_url(self, runner: CliRunner, config_file: Path):
        """Test: explorium config set base_url 'https://api.explorium.ai/v2'"""
        result = runner.invoke(cli, [
            "config", "set", "base_url", "https://api.explorium.ai/v2",
            "--config-path", str(config_file)
        ])
        assert result.exit_code == 0


# =============================================================================
# Business Match Command Tests
# =============================================================================

class TestBusinessMatchExamples:
    """Tests for businesses match command examples from documentation."""

    def test_match_by_name_and_domain(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses match --name 'Starbucks' --domain 'starbucks.com'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Starbucks",
            "--domain", "starbucks.com"
        ])
        mock_businesses_api.match.assert_called_once_with([{
            "name": "Starbucks",
            "domain": "starbucks.com",
            "linkedin_url": None
        }])
        assert result.exit_code == 0

    def test_match_by_name_only(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses match --name 'Microsoft Corporation'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Microsoft Corporation"
        ])
        mock_businesses_api.match.assert_called_once_with([{
            "name": "Microsoft Corporation",
            "domain": None,
            "linkedin_url": None
        }])

    def test_match_by_domain_only(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses match --domain 'salesforce.com'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--domain", "salesforce.com"
        ])
        mock_businesses_api.match.assert_called_once_with([{
            "name": None,
            "domain": "salesforce.com",
            "linkedin_url": None
        }])

    def test_match_by_linkedin(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses match --linkedin 'https://linkedin.com/company/starbucks'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--linkedin", "https://linkedin.com/company/starbucks"
        ])
        mock_businesses_api.match.assert_called_once_with([{
            "name": None,
            "domain": None,
            "linkedin_url": "https://linkedin.com/company/starbucks"
        }])

    def test_match_from_file(self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path):
        """Test: explorium businesses match -f companies.json"""
        companies_file = tmp_path / "companies.json"
        companies_file.write_text(json.dumps([
            {"name": "Starbucks", "website": "starbucks.com"},
            {"name": "Microsoft", "website": "microsoft.com"},
            {"name": "Salesforce", "website": "salesforce.com"}
        ]))

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "-f", str(companies_file)
        ])
        mock_businesses_api.match.assert_called_once()

    def test_match_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses match --name 'Apple' --domain 'apple.com' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "match",
            "--name", "Apple",
            "--domain", "apple.com"])
        mock_businesses_api.match.assert_called_once()


# =============================================================================
# Business Search Command Tests
# =============================================================================

class TestBusinessSearchExamples:
    """Tests for businesses search command examples from documentation."""

    def test_search_us_companies(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}},
            size=100,
            page=1
        )
        assert result.exit_code == 0

    def test_search_multiple_countries(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country 'us,ca,gb'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us,ca,gb"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us", "ca", "gb"]}},
            size=100,
            page=1
        )

    def test_search_by_size(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --size '51-200'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--size", "51-200"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_size": {"values": ["51-200"]}},
            size=100,
            page=1
        )

    def test_search_multiple_sizes(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --size '51-200,201-500,501-1000'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--size", "51-200,201-500,501-1000"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_size": {"values": ["51-200", "201-500", "501-1000"]}},
            size=100,
            page=1
        )

    def test_search_by_revenue(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --revenue '10M-50M'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--revenue", "10M-50M"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_revenue": {"values": ["10M-50M"]}},
            size=100,
            page=1
        )

    def test_search_by_tech(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --tech 'Python'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--tech", "Python"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_tech_stack_tech": {"values": ["Python"]}},
            size=100,
            page=1
        )

    def test_search_multiple_techs(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --tech 'Python,React,AWS'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--tech", "Python,React,AWS"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_tech_stack_tech": {"values": ["Python", "React", "AWS"]}},
            size=100,
            page=1
        )

    def test_search_by_industry(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --industry 'Software,Technology'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--industry", "Software,Technology"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"linkedin_category": {"values": ["Software", "Technology"]}},
            size=100,
            page=1
        )

    def test_search_with_events(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --events 'new_funding_round'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--events", "new_funding_round"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "events": {"values": ["new_funding_round"], "last_occurrence": 45}},
            size=100,
            page=1
        )

    def test_search_with_multiple_events(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --events 'new_funding_round,new_product,ipo_announcement' --events-days 30"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--events", "new_funding_round,new_product,ipo_announcement",
            "--events-days", "30"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "events": {"values": ["new_funding_round", "new_product", "ipo_announcement"], "last_occurrence": 30}},
            size=100,
            page=1
        )

    def test_search_combined_filters(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: Combined filters search"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--size", "51-200,201-500",
            "--revenue", "5M-10M,10M-50M",
            "--tech", "Python,AWS",
            "--events", "new_funding_round",
            "--events-days", "60"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {
                "country_code": {"values": ["us"]},
                "company_size": {"values": ["51-200", "201-500"]},
                "company_revenue": {"values": ["5M-10M", "10M-50M"]},
                "company_tech_stack_tech": {"values": ["Python", "AWS"]},
                "events": {"values": ["new_funding_round"], "last_occurrence": 60}
            },
            size=100,
            page=1
        )

    def test_search_with_pagination(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --page 1 --page-size 25"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--page", "1",
            "--page-size", "25"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}},
            size=25,
            page=1
        )

    def test_search_page_2(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --page 2 --page-size 25"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--page", "2",
            "--page-size", "25"
        ])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}},
            size=25,
            page=2
        )

    def test_search_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses search --country us --size '51-200' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "search",
            "--country", "us",
            "--size", "51-200"])
        mock_businesses_api.search.assert_called_once_with(
            {"country_code": {"values": ["us"]}, "company_size": {"values": ["51-200"]}},
            size=100,
            page=1
        )


# =============================================================================
# Business Enrich Command Tests
# =============================================================================

class TestBusinessEnrichExamples:
    """Tests for businesses enrich command examples from documentation."""

    def test_enrich_single_business(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses enrich --id '8adce3ca1cef0c986b22310e369a0793'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "enrich",
            "--id", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.enrich.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")

    def test_enrich_short_form(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses enrich -i '8adce3ca1cef0c986b22310e369a0793'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "enrich",
            "-i", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.enrich.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")

    def test_enrich_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses enrich --id 'id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "enrich",
            "--id", "8adce3ca1cef0c986b22310e369a0793"])
        mock_businesses_api.enrich.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")


# =============================================================================
# Business Bulk Enrich Command Tests
# =============================================================================

class TestBusinessBulkEnrichExamples:
    """Tests for businesses bulk-enrich command examples from documentation."""

    def test_bulk_enrich_by_ids(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses bulk-enrich --ids 'id1,id2,id3'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "--ids", "id1,id2,id3"
        ])
        mock_businesses_api.bulk_enrich.assert_called_once_with(["id1", "id2", "id3"])

    def test_bulk_enrich_from_file(self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path):
        """Test: explorium businesses bulk-enrich -f business_ids.csv"""
        ids_file = tmp_path / "business_ids.csv"
        ids_file.write_text("business_id\n8adce3ca1cef0c986b22310e369a0793\n7bdef4ab2deg1d097c33421f480b1894\n6cegh5bc3efh2e108d44532g591c2905")

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "-f", str(ids_file)
        ])
        mock_businesses_api.bulk_enrich.assert_called_once()

    def test_bulk_enrich_auto_batches_over_50(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test that bulk-enrich auto-batches over 50 IDs."""
        mock_businesses_api.bulk_enrich.side_effect = [
            {"status": "success", "data": []},
            {"status": "success", "data": []}
        ]
        ids = ",".join([f"id{i}" for i in range(51)])
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "--ids", ids
        ])
        # Should succeed with auto-batching (2 batches: 50 + 1)
        assert result.exit_code == 0
        assert mock_businesses_api.bulk_enrich.call_count == 2


# =============================================================================
# Business Lookalike Command Tests
# =============================================================================

class TestBusinessLookalikeExamples:
    """Tests for businesses lookalike command examples from documentation."""

    def test_lookalike_basic(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike --id '8adce3ca1cef0c986b22310e369a0793'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")

    def test_lookalike_short_form(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike -i 'id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "lookalike",
            "-i", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")

    def test_lookalike_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike --id 'id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793"])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793")


# =============================================================================
# Business Autocomplete Command Tests
# =============================================================================

class TestBusinessAutocompleteExamples:
    """Tests for businesses autocomplete command examples from documentation."""

    def test_autocomplete_star(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses autocomplete --query 'star'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "autocomplete",
            "--query", "star"
        ])
        mock_businesses_api.autocomplete.assert_called_once_with("star")

    def test_autocomplete_short_form(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses autocomplete -q 'micro'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "autocomplete",
            "-q", "micro"
        ])
        mock_businesses_api.autocomplete.assert_called_once_with("micro")

    def test_autocomplete_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses autocomplete --query 'sales' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "autocomplete",
            "--query", "sales"])
        mock_businesses_api.autocomplete.assert_called_once_with("sales")


# =============================================================================
# Business Events Command Tests
# =============================================================================

class TestBusinessEventsExamples:
    """Tests for businesses events command examples from documentation."""

    def test_events_list_single_business(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1' --events 'new_funding_round'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "8adce3ca1cef0c986b22310e369a0793",
            "--events", "new_funding_round"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["8adce3ca1cef0c986b22310e369a0793"],
            ["new_funding_round"]
        )

    def test_events_list_multiple_businesses(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1,id2,id3' --events 'new_funding_round'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1,id2,id3",
            "--events", "new_funding_round"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["id1", "id2", "id3"],
            ["new_funding_round"]
        )

    def test_events_list_with_multiple_event_types(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1,id2' --events 'new_funding_round,new_product'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1,id2",
            "--events", "new_funding_round,new_product"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["id1", "id2"],
            ["new_funding_round", "new_product"]
        )

    def test_events_list_combined(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: Combined events list with filters and table output"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "events", "list",
            "--ids", "id1,id2",
            "--events", "new_funding_round,merger_and_acquisitions"])
        mock_businesses_api.list_events.assert_called_once()

    def test_events_enroll_funding_ipo(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events enroll --ids 'id' --events 'new_funding_round,ipo_announcement' --key 'my_key'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "enroll",
            "--ids", "8adce3ca1cef0c986b22310e369a0793",
            "--events", "new_funding_round,ipo_announcement",
            "--key", "my_monitoring_key"
        ])
        mock_businesses_api.enroll_events.assert_called_once_with(
            ["8adce3ca1cef0c986b22310e369a0793"],
            ["new_funding_round", "ipo_announcement"],
            "my_monitoring_key"
        )

    def test_events_enroll_multiple_businesses(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events enroll --ids 'id1,id2,id3' --events 'new_funding_round,new_product,new_partnership' --key 'key'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "enroll",
            "--ids", "id1,id2,id3",
            "--events", "new_funding_round,new_product,new_partnership",
            "--key", "product_launch_alerts"
        ])
        mock_businesses_api.enroll_events.assert_called_once()

    def test_events_enroll_hiring_signals(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events enroll for hiring signals"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "enroll",
            "--ids", "id1,id2",
            "--events", "hiring_in_engineering_department,increase_in_engineering_department",
            "--key", "engineering_growth_signals"
        ])
        mock_businesses_api.enroll_events.assert_called_once()

    def test_events_enrollments(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events enrollments"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "enrollments"
        ])
        mock_businesses_api.list_enrollments.assert_called_once()

    def test_events_enrollments_table(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events enrollments -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "events", "enrollments"])
        mock_businesses_api.list_enrollments.assert_called_once()


# =============================================================================
# Prospect Match Command Tests
# =============================================================================

class TestProspectMatchExamples:
    """Tests for prospects match command examples from documentation."""

    def test_match_by_name_and_business(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects match --first-name 'John' --last-name 'Doe' --company-name 'Acme'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--company-name", "Acme Corp"
        ])
        mock_prospects_api.match.assert_called_once_with([{
            "full_name": "John Doe",
            "company_name": "Acme Corp"
        }])

    def test_match_by_linkedin(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects match --linkedin 'https://linkedin.com/in/johndoe'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--linkedin", "https://linkedin.com/in/johndoe"
        ])
        # API expects 'linkedin' field, not 'linkedin_url'
        mock_prospects_api.match.assert_called_once_with([{
            "linkedin": "https://linkedin.com/in/johndoe"
        }])

    def test_match_by_name_only_rejected(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: name-only match is rejected — must provide company, email, or linkedin."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "Jane",
            "--last-name", "Smith"
        ])
        assert result.exit_code != 0
        assert "Cannot match by name alone" in (result.output + result.stderr)

    def test_match_by_name_and_company(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects match --first-name 'Jane' --last-name 'Smith' --company-name 'Acme'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "Jane",
            "--last-name", "Smith",
            "--company-name", "Acme"
        ])
        mock_prospects_api.match.assert_called_once_with([{
            "full_name": "Jane Smith",
            "company_name": "Acme"
        }])

    def test_match_from_file(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects match -f prospects.json"""
        prospects_file = tmp_path / "prospects.json"
        prospects_file.write_text(json.dumps([
            {"first_name": "John", "last_name": "Doe", "linkedin_url": "https://linkedin.com/in/johndoe"},
            {"first_name": "Jane", "last_name": "Smith", "business_id": "8adce3ca1cef0c986b22310e369a0793"},
            {"first_name": "Bob", "last_name": "Johnson"}
        ]))

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "-f", str(prospects_file)
        ])
        mock_prospects_api.match.assert_called_once()

    def test_match_with_table_output(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects match --first-name 'John' --last-name 'Doe' --company-name 'Acme' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--company-name", "Acme"])
        mock_prospects_api.match.assert_called_once()


# =============================================================================
# Prospect Search Command Tests
# =============================================================================

class TestProspectSearchExamples:
    """Tests for prospects search command examples from documentation."""

    def test_search_all_prospects_at_company(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["8adce3ca1cef0c986b22310e369a0793"]}},
            size=100,
            page=1
        )

    def test_search_multiple_companies(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id1,id2,id3'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1,id2,id3"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1", "id2", "id3"]}},
            size=100,
            page=1
        )

    def test_search_by_job_level_single(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --job-level 'cxo'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--job-level", "cxo"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "job_level": {"values": ["cxo"]}},
            size=100,
            page=1
        )

    def test_search_by_job_level_multiple(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --job-level 'cxo,vp,director'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--job-level", "cxo,vp,director"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "job_level": {"values": ["cxo", "vp", "director"]}},
            size=100,
            page=1
        )

    def test_search_by_department_single(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --department 'Engineering'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--department", "Engineering"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "job_department": {"values": ["Engineering"]}},
            size=100,
            page=1
        )

    def test_search_by_department_multiple(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --department 'Engineering,Product,Sales'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--department", "Engineering,Product,Sales"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "job_department": {"values": ["Engineering", "Product", "Sales"]}},
            size=100,
            page=1
        )

    def test_search_by_job_title(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --job-title 'Software Engineer'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--job-title", "Software Engineer"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "job_title": {"values": ["Software Engineer"], "include_related_job_titles": True}},
            size=100,
            page=1
        )

    def test_search_with_has_email(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --has-email"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--has-email"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "has_email": {"value": True}},
            size=100,
            page=1
        )

    def test_search_with_has_phone(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --has-phone"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--has-phone"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "has_phone_number": {"value": True}},
            size=100,
            page=1
        )

    def test_search_with_has_email_and_phone(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --has-email --has-phone"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--has-email",
            "--has-phone"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "has_email": {"value": True}, "has_phone_number": {"value": True}},
            size=100,
            page=1
        )

    def test_search_by_experience_min(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --experience-min 60"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--experience-min", "60"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "experience_min": {"value": 60}},
            size=100,
            page=1
        )

    def test_search_by_experience_range(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --experience-min 24 --experience-max 60"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--experience-min", "24",
            "--experience-max", "60"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "experience_min": {"value": 24}, "experience_max": {"value": 60}},
            size=100,
            page=1
        )

    def test_search_by_role_tenure_max(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --role-tenure-max 12"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--role-tenure-max", "12"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "role_tenure_max": {"value": 12}},
            size=100,
            page=1
        )

    def test_search_by_country(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --country 'us'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--country", "us"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}, "country_code": {"values": ["us"]}},
            size=100,
            page=1
        )

    def test_search_combined_filters(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: Combined prospect search filters"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "search",
            "--business-id", "id1",
            "--job-level", "cxo,vp,director",
            "--department", "Engineering",
            "--has-email"])
        mock_prospects_api.search.assert_called_once_with(
            {
                "business_id": {"values": ["id1"]},
                "job_level": {"values": ["cxo", "vp", "director"]},
                "job_department": {"values": ["Engineering"]},
                "has_email": {"value": True}
            },
            size=100,
            page=1
        )

    def test_search_with_pagination(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects search --business-id 'id' --page 1 --page-size 25"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "search",
            "--business-id", "id1",
            "--page", "1",
            "--page-size", "25"
        ])
        mock_prospects_api.search.assert_called_once_with(
            {"business_id": {"values": ["id1"]}},
            size=25,
            page=1
        )


# =============================================================================
# Prospect Bulk Enrich Command Tests
# =============================================================================

class TestProspectBulkEnrichExamples:
    """Tests for prospects bulk-enrich command examples from documentation."""

    def test_bulk_enrich_by_ids(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'prospect_id1,prospect_id2,prospect_id3'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "prospect_id1,prospect_id2,prospect_id3"
        ])
        mock_prospects_api.bulk_enrich.assert_called_once_with(
            ["prospect_id1", "prospect_id2", "prospect_id3"]
        )

    def test_bulk_enrich_from_file(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects bulk-enrich -f prospect_ids.csv"""
        ids_file = tmp_path / "prospect_ids.csv"
        ids_file.write_text("prospect_id\nprospect_id1\nprospect_id2\nprospect_id3")

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "-f", str(ids_file)
        ])
        mock_prospects_api.bulk_enrich.assert_called_once()

    def test_bulk_enrich_with_types_contacts(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'contacts'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "contacts"
        ])
        mock_prospects_api.bulk_enrich.assert_called_once_with(
            ["id1", "id2"]
        )

    def test_bulk_enrich_with_types_profile(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'profile'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "profile"
        ])
        mock_prospects_api.bulk_enrich_profiles.assert_called_once_with(
            ["id1", "id2"]
        )

    def test_bulk_enrich_with_types_all(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'all'
        'all' expands to contacts + profile (two separate API calls)."""
        mock_prospects_api.bulk_enrich_profiles.return_value = {
            "status": "success", "data": [{"prospect_id": "id1"}]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "all"
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()
        mock_prospects_api.bulk_enrich_profiles.assert_called_once()

    def test_bulk_enrich_types_comma_separated(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'contacts,profile'"""
        mock_prospects_api.bulk_enrich_profiles.return_value = {
            "status": "success", "data": [{"prospect_id": "id1", "job_title": "VP"}]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "contacts,profile"
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()
        mock_prospects_api.bulk_enrich_profiles.assert_called_once()

    def test_bulk_enrich_types_invalid_in_list(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1' --types 'contacts,bogus' raises error"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1",
            "--types", "contacts,bogus"
        ])
        assert result.exit_code != 0
        assert "Unknown enrichment type 'bogus'" in result.output or "Unknown enrichment type 'bogus'" in result.stderr


# =============================================================================
# Prospect Autocomplete Command Tests
# =============================================================================

class TestProspectAutocompleteExamples:
    """Tests for prospects autocomplete command examples from documentation."""

    def test_autocomplete_john(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects autocomplete --query 'john'"""
        mock_prospects_api.autocomplete = MagicMock(return_value={"status": "success", "data": []})
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "autocomplete",
            "--query", "john"
        ])
        # Command should execute without error

    def test_autocomplete_short_form(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects autocomplete -q 'smith'"""
        mock_prospects_api.autocomplete = MagicMock(return_value={"status": "success", "data": []})
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "autocomplete",
            "-q", "smith"
        ])


# =============================================================================
# Prospect Statistics Command Tests
# =============================================================================

class TestProspectStatisticsExamples:
    """Tests for prospects statistics command examples from documentation."""

    def test_statistics_by_department(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects statistics --business-id 'id' --group-by 'department'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "statistics",
            "--business-id", "id1",
            "--group-by", "department"
        ])
        mock_prospects_api.statistics.assert_called_once()

    def test_statistics_by_job_level(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects statistics --business-id 'id' --group-by 'job_level'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "statistics",
            "--business-id", "id1",
            "--group-by", "job_level"
        ])
        mock_prospects_api.statistics.assert_called_once()

    def test_statistics_multiple_groups(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects statistics --business-id 'id' --group-by 'department,job_level'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "statistics",
            "--business-id", "id1",
            "--group-by", "department,job_level"
        ])
        mock_prospects_api.statistics.assert_called_once()

    def test_statistics_multiple_companies(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects statistics --business-id 'id1,id2,id3' --group-by 'country'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "statistics",
            "--business-id", "id1,id2,id3",
            "--group-by", "country"
        ])
        mock_prospects_api.statistics.assert_called_once()

    def test_statistics_with_table_output(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects statistics --business-id 'id' --group-by 'department' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "statistics",
            "--business-id", "id1",
            "--group-by", "department"])
        mock_prospects_api.statistics.assert_called_once()


# =============================================================================
# Prospect Enrich Command Tests
# =============================================================================

class TestProspectEnrichExamples:
    """Tests for prospects enrich command examples from documentation."""

    def test_enrich_contacts(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich contacts --id 'prospect_id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "contacts",
            "--id", "prospect_id"
        ])
        mock_prospects_api.enrich_contacts.assert_called_once_with("prospect_id")

    def test_enrich_contacts_short_form(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich contacts -i 'prospect_id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "contacts",
            "-i", "prospect_id"
        ])
        mock_prospects_api.enrich_contacts.assert_called_once_with("prospect_id")

    def test_enrich_contacts_table_output(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich contacts --id 'prospect_id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "enrich", "contacts",
            "--id", "prospect_id"])
        mock_prospects_api.enrich_contacts.assert_called_once_with("prospect_id")

    def test_enrich_social(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich social --id 'prospect_id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "social",
            "--id", "prospect_id"
        ])
        mock_prospects_api.enrich_social.assert_called_once_with("prospect_id")

    def test_enrich_social_table_output(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich social -i 'prospect_id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "enrich", "social",
            "-i", "prospect_id"])
        mock_prospects_api.enrich_social.assert_called_once_with("prospect_id")

    def test_enrich_profile(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich profile --id 'prospect_id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "profile",
            "--id", "prospect_id"
        ])
        mock_prospects_api.enrich_profile.assert_called_once_with("prospect_id")

    def test_enrich_profile_table_output(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects enrich profile -i 'prospect_id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "enrich", "profile",
            "-i", "prospect_id"])
        mock_prospects_api.enrich_profile.assert_called_once_with("prospect_id")


# =============================================================================
# Prospect Events Command Tests
# =============================================================================

class TestProspectEventsExamples:
    """Tests for prospects events command examples from documentation."""

    def test_events_list_single_prospect(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'prospect_id1' --events 'prospect_changed_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "prospect_id1",
            "--events", "prospect_changed_company"
        ])
        mock_prospects_api.list_events.assert_called_once_with(
            ["prospect_id1"],
            ["prospect_changed_company"]
        )

    def test_events_list_multiple_prospects(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'id1,id2,id3' --events 'prospect_changed_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "id1,id2,id3",
            "--events", "prospect_changed_company"
        ])
        mock_prospects_api.list_events.assert_called_once_with(
            ["id1", "id2", "id3"],
            ["prospect_changed_company"]
        )

    def test_events_list_with_event_filter(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'id1' --events 'prospect_changed_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "id1",
            "--events", "prospect_changed_company"
        ])
        mock_prospects_api.list_events.assert_called_once()

    def test_events_list_multiple_event_types(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'id1' --events 'prospect_changed_role,prospect_changed_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "id1",
            "--events", "prospect_changed_role,prospect_changed_company"
        ])
        mock_prospects_api.list_events.assert_called_once()

    def test_events_list_combined(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: Combined prospect events list"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "events", "list",
            "--ids", "id1,id2",
            "--events", "prospect_changed_company"])
        mock_prospects_api.list_events.assert_called_once()

    def test_events_enroll_job_changes(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events enroll for job changes"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "enroll",
            "--ids", "prospect_id1,prospect_id2",
            "--events", "prospect_changed_role,prospect_changed_company",
            "--key", "job_change_alerts"
        ])
        mock_prospects_api.enroll_events.assert_called_once_with(
            ["prospect_id1", "prospect_id2"],
            ["prospect_changed_role", "prospect_changed_company"],
            "job_change_alerts"
        )

    def test_events_enroll_anniversaries(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events enroll for anniversaries"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "enroll",
            "--ids", "id1,id2,id3",
            "--events", "prospect_job_start_anniversary",
            "--key", "anniversary_alerts"
        ])
        mock_prospects_api.enroll_events.assert_called_once()

    def test_events_enrollments(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events enrollments"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "enrollments"
        ])
        mock_prospects_api.list_enrollments.assert_called_once()

    def test_events_enrollments_table(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events enrollments -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "events", "enrollments"])
        mock_prospects_api.list_enrollments.assert_called_once()


# =============================================================================
# Webhook Command Tests
# =============================================================================

class TestWebhookExamples:
    """Tests for webhook command examples from documentation."""

    def test_webhooks_create(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks create --partner-id 'my_company' --url 'https://myapp.com/webhook'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "create",
            "--partner-id", "my_company",
            "--url", "https://myapp.com/webhook"
        ])
        mock_webhooks_api.create.assert_called_once_with("my_company", "https://myapp.com/webhook")

    def test_webhooks_create_short_form(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks create -p 'acme_corp' -u 'https://api.acme.com/explorium/events'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "create",
            "-p", "acme_corp",
            "-u", "https://api.acme.com/explorium/events"
        ])
        mock_webhooks_api.create.assert_called_once_with("acme_corp", "https://api.acme.com/explorium/events")

    def test_webhooks_get(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks get --partner-id 'my_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "get",
            "--partner-id", "my_company"
        ])
        mock_webhooks_api.get.assert_called_once_with("my_company")

    def test_webhooks_get_short_form_table(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks get -p 'acme_corp' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "webhooks", "get",
            "-p", "acme_corp"])
        mock_webhooks_api.get.assert_called_once_with("acme_corp")

    def test_webhooks_update(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks update --partner-id 'my_company' --url 'https://myapp.com/new-webhook'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "update",
            "--partner-id", "my_company",
            "--url", "https://myapp.com/new-webhook"
        ])
        mock_webhooks_api.update.assert_called_once_with("my_company", "https://myapp.com/new-webhook")

    def test_webhooks_update_short_form(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks update -p 'acme_corp' -u 'https://api.acme.com/v2/explorium/events'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "update",
            "-p", "acme_corp",
            "-u", "https://api.acme.com/v2/explorium/events"
        ])
        mock_webhooks_api.update.assert_called_once_with("acme_corp", "https://api.acme.com/v2/explorium/events")

    def test_webhooks_delete(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks delete --partner-id 'my_company'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "delete",
            "--partner-id", "my_company"
        ])
        mock_webhooks_api.delete.assert_called_once_with("my_company")

    def test_webhooks_delete_short_form(self, runner: CliRunner, config_file: Path, mock_webhooks_api):
        """Test: explorium webhooks delete -p 'acme_corp'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "delete",
            "-p", "acme_corp"
        ])
        mock_webhooks_api.delete.assert_called_once_with("acme_corp")


# =============================================================================
# Workflow Example Tests
# =============================================================================

class TestWorkflowExamples:
    """Tests for complete workflow examples from documentation."""

    def test_workflow_research_target_company(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """Test: Example 1 - Research a Target Company workflow"""
        # Step 1: Find the company
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Acme Corp",
            "--domain", "acme.com"
        ])
        assert mock_businesses_api.match.called

        # Step 2: Get company details
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "enrich",
            "--id", "8adce3ca1cef0c986b22310e369a0793"])
        assert mock_businesses_api.enrich.called

        # Step 3: Check recent company events
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "events", "list",
            "--ids", "8adce3ca1cef0c986b22310e369a0793",
            "--events", "new_funding_round"])
        assert mock_businesses_api.list_events.called

        # Step 4: Find similar companies
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793"])
        assert mock_businesses_api.lookalike.called

    def test_workflow_build_prospect_list(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """Test: Example 2 - Build a Prospect List workflow"""
        # Step 1: Find engineering leaders with email
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "search",
            "--business-id", "8adce3ca1cef0c986b22310e369a0793",
            "--job-level", "cxo,vp,director",
            "--department", "Engineering",
            "--has-email"])
        assert mock_prospects_api.search.called

        # Step 2: Get contact info
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "contacts",
            "--id", "prospect_id_1"
        ])
        assert mock_prospects_api.enrich_contacts.called

        # Step 3: Get social profiles
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich", "social",
            "--id", "prospect_id_1"
        ])
        assert mock_prospects_api.enrich_social.called

    def test_workflow_event_monitoring(
        self, runner: CliRunner, config_file: Path,
        mock_businesses_api, mock_prospects_api, mock_webhooks_api
    ):
        """Test: Example 3 - Set Up Event Monitoring workflow"""
        # Step 1: Create webhook endpoint
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "webhooks", "create",
            "--partner-id", "my_sales_app",
            "--url", "https://myapp.com/webhook"
        ])
        assert mock_webhooks_api.create.called

        # Step 2: Enroll target companies for business events
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "enroll",
            "--ids", "id1,id2,id3",
            "--events", "new_funding_round,new_product,hiring_in_engineering_department",
            "--key", "target_accounts_q1"
        ])
        assert mock_businesses_api.enroll_events.called

        # Step 3: Enroll key contacts for job changes
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "enroll",
            "--ids", "prospect1,prospect2,prospect3",
            "--events", "prospect_changed_role,prospect_changed_company",
            "--key", "key_contacts_q1"
        ])
        assert mock_prospects_api.enroll_events.called

        # Step 4: View active enrollments
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "events", "enrollments"])
        assert mock_businesses_api.list_enrollments.called

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "events", "enrollments"])
        assert mock_prospects_api.list_enrollments.called

    def test_workflow_market_research(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """Test: Example 5 - Market Research Query workflow"""
        # Find US tech companies with specific criteria
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "search",
            "--country", "us",
            "--size", "51-200,201-500",
            "--revenue", "5M-10M,10M-50M",
            "--tech", "Python",
            "--page-size", "100"
        ])
        assert mock_businesses_api.search.called

        # Filter to those with recent funding
        mock_businesses_api.search.reset_mock()
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "search",
            "--country", "us",
            "--size", "51-200,201-500",
            "--revenue", "5M-10M,10M-50M",
            "--tech", "Python",
            "--events", "new_funding_round",
            "--events-days", "90"])
        assert mock_businesses_api.search.called


# =============================================================================
# Prospect Enrich-File Command Tests
# =============================================================================

class TestProspectEnrichFileExamples:
    """Tests for prospects enrich-file command."""

    def test_enrich_file_csv(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file -f prospects.csv"""
        csv_file = tmp_path / "prospects.csv"
        csv_file.write_text("first_name,last_name,company_name\nJohn,Doe,Acme Corp\nJane,Smith,Beta Inc")

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(csv_file)
        ])
        assert result.exit_code == 0
        assert mock_prospects_api.match.called
        mock_prospects_api.bulk_enrich.assert_called_once()

    def test_enrich_file_json(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file -f prospects.json"""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([
            {"full_name": "John Doe", "company_name": "Acme Corp"},
            {"linkedin": "https://linkedin.com/in/janesmith"}
        ]))

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file)
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()

    def test_enrich_file_types_profile(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file -f file.json --types profile"""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([{"full_name": "John Doe", "company_name": "Acme"}]))

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }
        mock_prospects_api.bulk_enrich_profiles.return_value = {
            "status": "success", "data": [{"prospect_id": "p1"}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file),
            "--types", "profile"
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich_profiles.assert_called_once()

    def test_enrich_file_types_all(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file -f file.json --types all
        'all' expands to contacts + profile (two separate API calls)."""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([{"full_name": "John Doe", "company_name": "Acme"}]))

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }
        mock_prospects_api.bulk_enrich_profiles.return_value = {
            "status": "success", "data": [{"prospect_id": "p1"}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file),
            "--types", "all"
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()
        mock_prospects_api.bulk_enrich_profiles.assert_called_once()

    def test_enrich_file_match_failures_still_enriches(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test that partial match failures don't abort — successful matches still enrich."""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([
            {"full_name": "John Doe", "company_name": "Acme Corp"},
            {"full_name": "Unknown Person", "company_name": "Nowhere Inc"},
            {"full_name": "Jane Smith", "company_name": "Beta Inc"}
        ]))

        # First and third calls succeed, second fails (empty matches triggers MatchError)
        mock_prospects_api.match.side_effect = [
            {"matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]},
            {"matched_prospects": []},
            {"matched_prospects": [{"prospect_id": "p3", "match_confidence": 0.90}]},
        ]

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file)
        ])
        assert result.exit_code == 0
        # Should have enriched the 2 successful matches
        mock_prospects_api.bulk_enrich.assert_called_once()
        call_args = mock_prospects_api.bulk_enrich.call_args[0][0]
        assert len(call_args) == 2
        assert "p1" in call_args
        assert "p3" in call_args
        # Should have warning in stderr
        assert "1 match failures" in result.stderr

    def test_enrich_file_types_comma_separated(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file -f file.json --types contacts,profile calls both APIs."""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([{"full_name": "John Doe", "company_name": "Acme"}]))

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }
        mock_prospects_api.bulk_enrich_profiles.return_value = {
            "status": "success", "data": [{"prospect_id": "p1", "job_title": "VP"}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file),
            "--types", "contacts,profile"
        ])
        assert result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()
        mock_prospects_api.bulk_enrich_profiles.assert_called_once()

    def test_enrich_file_types_invalid_in_list(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects enrich-file --types contacts,bogus raises error."""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([{"full_name": "John Doe", "company_name": "Acme"}]))

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file),
            "--types", "contacts,bogus"
        ])
        assert result.exit_code != 0
        assert "Unknown enrichment type 'bogus'" in result.output or "Unknown enrichment type 'bogus'" in result.stderr


# =============================================================================
# Business Enrich-File Command Tests
# =============================================================================

class TestBusinessEnrichFileExamples:
    """Tests for businesses enrich-file command."""

    def test_enrich_file_csv(self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path):
        """Test: explorium businesses enrich-file -f companies.csv"""
        csv_file = tmp_path / "companies.csv"
        csv_file.write_text("name,domain\nStarbucks,starbucks.com\nMicrosoft,microsoft.com")

        mock_businesses_api.match.return_value = {
            "matched_businesses": [{"business_id": "b1", "match_confidence": 0.95}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "enrich-file",
            "-f", str(csv_file)
        ])
        assert result.exit_code == 0
        assert mock_businesses_api.match.called
        mock_businesses_api.bulk_enrich.assert_called_once()

    def test_enrich_file_json(self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path):
        """Test: explorium businesses enrich-file -f companies.json"""
        json_file = tmp_path / "companies.json"
        json_file.write_text(json.dumps([
            {"name": "Starbucks", "domain": "starbucks.com"},
            {"name": "Microsoft", "domain": "microsoft.com"}
        ]))

        mock_businesses_api.match.return_value = {
            "matched_businesses": [{"business_id": "b1", "match_confidence": 0.95}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "enrich-file",
            "-f", str(json_file)
        ])
        assert result.exit_code == 0
        mock_businesses_api.bulk_enrich.assert_called_once()


# =============================================================================
# Feature 8: Strip full_name when linkedin/email present without company_name
# =============================================================================

class TestFeature8FullNameStripping:
    """Tests for Feature 8: full_name stripping when strong identifiers present."""

    def test_match_linkedin_without_company_strips_fullname(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """When linkedin is present without company_name, full_name should be stripped."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--linkedin", "https://linkedin.com/in/johndoe"
        ])
        assert result.exit_code == 0
        mock_prospects_api.match.assert_called_once_with([{
            "linkedin": "https://linkedin.com/in/johndoe"
        }])

    def test_match_email_without_company_strips_fullname(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """When email is present without company_name, full_name should be stripped."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--email", "john@acme.com"
        ])
        assert result.exit_code == 0
        mock_prospects_api.match.assert_called_once_with([{
            "email": "john@acme.com"
        }])

    def test_match_linkedin_with_company_includes_fullname(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """When linkedin AND company_name are present, full_name should be included."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--linkedin", "https://linkedin.com/in/johndoe",
            "--company-name", "Acme Corp"
        ])
        assert result.exit_code == 0
        mock_prospects_api.match.assert_called_once_with([{
            "full_name": "John Doe",
            "linkedin": "https://linkedin.com/in/johndoe",
            "company_name": "Acme Corp"
        }])

    def test_match_name_only_rejected(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """Name-only match is rejected — must provide company, email, or linkedin."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "Jane",
            "--last-name", "Smith"
        ])
        assert result.exit_code != 0
        assert "Cannot match by name alone" in (result.output + result.stderr)

    def test_match_name_with_company_includes_fullname(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """When company is present, full_name should be included."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "Jane",
            "--last-name", "Smith",
            "--company-name", "Acme"
        ])
        assert result.exit_code == 0
        mock_prospects_api.match.assert_called_once_with([{
            "full_name": "Jane Smith",
            "company_name": "Acme"
        }])


# =============================================================================
# Feature 9: Global --output-file flag
# =============================================================================

class TestFeature9OutputFile:
    """Tests for Feature 9: --output-file global flag."""

    def test_global_output_file_option_exists(self, runner: CliRunner):
        """Test that --output-file is shown in --help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "--output-file" in result.output

    def test_output_json_to_file(
        self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path
    ):
        """Test that --output-file writes clean JSON to file."""
        out_file = tmp_path / "output.json"
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "--output-file", str(out_file),
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "data" in data
        # Stderr should have confirmation
        assert "Output written to" in result.stderr

    def test_output_csv_to_file(
        self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path
    ):
        """Test that --output-file with -o csv writes CSV to file."""
        out_file = tmp_path / "output.csv"
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "csv",
            "--output-file", str(out_file),
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0
        assert out_file.exists()
        content = out_file.read_text()
        assert "business_id" in content  # CSV header
        assert "Output written to" in result.stderr

    def test_output_file_no_ansi(
        self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path
    ):
        """Test that file output contains no ANSI escape codes."""
        out_file = tmp_path / "output.json"
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "--output-file", str(out_file),
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0
        content = out_file.read_text()
        assert "\033[" not in content  # No ANSI escape codes

    def test_output_file_table_falls_back_to_json(
        self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path
    ):
        """Test that table format with --output-file falls back to JSON."""
        out_file = tmp_path / "output.json"
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "--output-file", str(out_file),
            "businesses", "search", "--country", "us"
        ])
        assert result.exit_code == 0
        data = json.loads(out_file.read_text())
        assert isinstance(data, dict)


# =============================================================================
# Feature 10: --summary flag
# =============================================================================

class TestFeature10Summary:
    """Tests for Feature 10: --summary flag for match/enrichment stats."""

    def test_prospect_match_with_summary(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """Test that --summary prints match stats to stderr."""
        mock_prospects_api.match.return_value = {
            "status": "success",
            "matched_prospects": [
                {"prospect_id": "p1", "match_confidence": 0.95}
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--company-name", "Acme",
            "--summary"
        ])
        assert result.exit_code == 0
        assert "Matched: 1/1" in result.stderr

    def test_business_match_with_summary(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """Test that businesses match --summary prints stats to stderr."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Starbucks",
            "--summary"
        ])
        assert result.exit_code == 0
        assert "Matched:" in result.stderr

    def test_prospect_enrich_file_with_summary(
        self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path
    ):
        """Test that enrich-file --summary prints match-phase stats."""
        json_file = tmp_path / "prospects.json"
        json_file.write_text(json.dumps([
            {"full_name": "John Doe", "company_name": "Acme Corp"},
            {"full_name": "Unknown Person", "company_name": "Nowhere Inc"},
            {"full_name": "Jane Smith", "company_name": "Beta Inc"}
        ]))

        mock_prospects_api.match.side_effect = [
            {"matched_prospects": [{"prospect_id": "p1", "match_confidence": 0.95}]},
            {"matched_prospects": []},
            {"matched_prospects": [{"prospect_id": "p3", "match_confidence": 0.90}]},
        ]

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "enrich-file",
            "-f", str(json_file),
            "--summary"
        ])
        assert result.exit_code == 0
        assert "Matched: 2/3, Failed: 1" in result.stderr

    def test_business_bulk_enrich_with_summary(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """Test that bulk-enrich --summary with --ids prints enrichment count."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "--ids", "id1,id2,id3",
            "--summary"
        ])
        assert result.exit_code == 0
        assert "Enriched: 3 businesses" in result.stderr


# =============================================================================
# Feature 6 & 7 Tests: Pipeable Match Output + Subcommand --format
# =============================================================================

class TestMatchPipeableOutput:
    """Tests for Feature 6: match output directly usable by bulk-enrich."""

    def test_match_csv_output_has_prospect_id_column(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """Match with CSV output should produce flat records with prospect_id column."""
        mock_prospects_api.match.return_value = {
            "matched_prospects": [
                {"prospect_id": "p1", "first_name": "John", "last_name": "Doe"},
                {"prospect_id": "p2", "first_name": "Jane", "last_name": "Smith"},
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--email", "john@example.com",
            "--format", "csv",
        ])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        header = lines[0]
        assert "prospect_id" in header
        assert "p1" in lines[1]
        assert "p2" in lines[2]

    def test_match_csv_output_has_business_id_column(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """Match with CSV output should produce flat records with business_id column."""
        mock_businesses_api.match.return_value = {
            "matched_businesses": [
                {"business_id": "b1", "name": "Acme Corp"},
                {"business_id": "b2", "name": "Globex Inc"},
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Acme",
            "--format", "csv",
        ])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        header = lines[0]
        assert "business_id" in header
        assert "b1" in lines[1]
        assert "b2" in lines[2]

    def test_match_ids_only_prospects(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """--ids-only should print just prospect IDs, one per line."""
        mock_prospects_api.match.return_value = {
            "matched_prospects": [
                {"prospect_id": "p1", "first_name": "John"},
                {"prospect_id": "p2", "first_name": "Jane"},
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--email", "john@example.com",
            "--ids-only",
        ])
        assert result.exit_code == 0
        ids = result.output.strip().split("\n")
        assert ids == ["p1", "p2"]

    def test_match_ids_only_businesses(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """--ids-only should print just business IDs, one per line."""
        mock_businesses_api.match.return_value = {
            "matched_businesses": [
                {"business_id": "b1", "name": "Acme"},
                {"business_id": "b2", "name": "Globex"},
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "match",
            "--name", "Acme",
            "--ids-only",
        ])
        assert result.exit_code == 0
        ids = result.output.strip().split("\n")
        assert ids == ["b1", "b2"]

    def test_match_csv_to_bulk_enrich_pipeline(
        self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path
    ):
        """End-to-end: match CSV output should be parseable by bulk-enrich --file."""
        # Step 1: match produces CSV with prospect_id column
        mock_prospects_api.match.return_value = {
            "matched_prospects": [
                {"prospect_id": "p1", "first_name": "John"},
                {"prospect_id": "p2", "first_name": "Jane"},
            ]
        }
        match_result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--email", "john@example.com",
            "--format", "csv",
        ])
        assert match_result.exit_code == 0

        # Step 2: Write match CSV to a file
        csv_file = tmp_path / "match_output.csv"
        csv_file.write_text(match_result.output)

        # Step 3: bulk-enrich reads the CSV
        mock_prospects_api.bulk_enrich.return_value = {
            "status": "success",
            "data": [{"prospect_id": "p1", "email": "john@co.com"}]
        }
        enrich_result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--file", str(csv_file),
        ])
        assert enrich_result.exit_code == 0
        mock_prospects_api.bulk_enrich.assert_called_once()
        call_args = mock_prospects_api.bulk_enrich.call_args[0][0]
        assert "p1" in call_args
        assert "p2" in call_args


class TestSubcommandFormatOption:
    """Tests for Feature 7: subcommand-level --format option."""

    def test_format_overrides_global_output(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """--format csv on subcommand should override -o json."""
        mock_prospects_api.match.return_value = {
            "matched_prospects": [
                {"prospect_id": "p1", "first_name": "John"},
            ]
        }
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "json",
            "prospects", "match",
            "--email", "john@example.com",
            "--format", "csv",
        ])
        assert result.exit_code == 0
        # CSV output starts with header row, not JSON brace
        assert result.output.strip().startswith("first_name") or "prospect_id" in result.output.split("\n")[0]

    def test_format_on_bulk_enrich(
        self, runner: CliRunner, config_file: Path, mock_prospects_api
    ):
        """--format csv should work on bulk-enrich."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "json",
            "prospects", "bulk-enrich",
            "--ids", "p1,p2",
            "--format", "csv",
        ])
        assert result.exit_code == 0
        assert "prospect_id" in result.output.split("\n")[0]

    def test_format_on_enrich_file(
        self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path
    ):
        """--format csv should work on enrich-file."""
        # Create a CSV input file
        csv_file = tmp_path / "prospects.csv"
        csv_file.write_text("full_name,company_name\nJohn Doe,Acme Corp\n")

        mock_prospects_api.match.return_value = {
            "matched_prospects": [{"prospect_id": "p1"}]
        }
        mock_prospects_api.bulk_enrich.return_value = {
            "status": "success",
            "data": [{"prospect_id": "p1", "email": "john@acme.com"}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "json",
            "prospects", "enrich-file",
            "--file", str(csv_file),
            "--format", "csv",
        ])
        assert result.exit_code == 0
        assert "prospect_id" in result.output.split("\n")[0]

    def test_format_on_business_bulk_enrich(
        self, runner: CliRunner, config_file: Path, mock_businesses_api
    ):
        """--format csv should work on businesses bulk-enrich."""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "json",
            "businesses", "bulk-enrich",
            "--ids", "b1,b2",
            "--format", "csv",
        ])
        assert result.exit_code == 0
        assert "business_id" in result.output.split("\n")[0]

    def test_format_on_business_enrich_file(
        self, runner: CliRunner, config_file: Path, mock_businesses_api, tmp_path: Path
    ):
        """--format csv should work on businesses enrich-file."""
        csv_file = tmp_path / "businesses.csv"
        csv_file.write_text("name,domain\nAcme Corp,acme.com\n")

        mock_businesses_api.match.return_value = {
            "matched_businesses": [{"business_id": "b1"}]
        }
        mock_businesses_api.bulk_enrich.return_value = {
            "status": "success",
            "data": [{"business_id": "b1", "revenue": "10M"}]
        }

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "json",
            "businesses", "enrich-file",
            "--file", str(csv_file),
            "--format", "csv",
        ])
        assert result.exit_code == 0
        assert "business_id" in result.output.split("\n")[0]
