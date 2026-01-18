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
            "data": [{"business_id": "8adce3ca1cef0c986b22310e369a0793", "name": "Test Company"}]
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
            "data": [{"prospect_id": "prospect_001", "first_name": "John", "last_name": "Doe"}]
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
        """Test: explorium businesses bulk-enrich -f business_ids.txt"""
        ids_file = tmp_path / "business_ids.txt"
        ids_file.write_text("8adce3ca1cef0c986b22310e369a0793\n7bdef4ab2deg1d097c33421f480b1894\n6cegh5bc3efh2e108d44532g591c2905")

        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "-f", str(ids_file)
        ])
        mock_businesses_api.bulk_enrich.assert_called_once()

    def test_bulk_enrich_max_50_limit(self, runner: CliRunner, config_file: Path):
        """Test that bulk-enrich enforces 50 ID limit."""
        ids = ",".join([f"id{i}" for i in range(51)])
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "bulk-enrich",
            "--ids", ids
        ])
        # Should fail with error about max 50
        assert result.exit_code != 0


# =============================================================================
# Business Lookalike Command Tests
# =============================================================================

class TestBusinessLookalikeExamples:
    """Tests for businesses lookalike command examples from documentation."""

    def test_lookalike_default_size(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike --id '8adce3ca1cef0c986b22310e369a0793'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793", 100)

    def test_lookalike_custom_size(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike --id 'id' --size 50"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793",
            "--size", "50"
        ])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793", 50)

    def test_lookalike_short_form(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike -i 'id' --size 25"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "lookalike",
            "-i", "8adce3ca1cef0c986b22310e369a0793",
            "--size", "25"
        ])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793", 25)

    def test_lookalike_with_table_output(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses lookalike --id 'id' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793"])
        mock_businesses_api.lookalike.assert_called_once_with("8adce3ca1cef0c986b22310e369a0793", 100)


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
        """Test: explorium businesses events list --ids 'id1'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["8adce3ca1cef0c986b22310e369a0793"],
            event_types=None,
            days=45
        )

    def test_events_list_multiple_businesses(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1,id2,id3'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1,id2,id3"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["id1", "id2", "id3"],
            event_types=None,
            days=45
        )

    def test_events_list_with_event_filter(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1,id2' --events 'new_funding_round'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1,id2",
            "--events", "new_funding_round"
        ])
        mock_businesses_api.list_events.assert_called_once_with(
            ["id1", "id2"],
            event_types=["new_funding_round"],
            days=45
        )

    def test_events_list_multiple_event_types(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1' --events 'new_funding_round,new_product,ipo_announcement'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1",
            "--events", "new_funding_round,new_product,ipo_announcement"
        ])
        mock_businesses_api.list_events.assert_called_once()

    def test_events_list_custom_days(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: explorium businesses events list --ids 'id1' --days 60"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "businesses", "events", "list",
            "--ids", "id1",
            "--days", "60"
        ])
        mock_businesses_api.list_events.assert_called_once()

    def test_events_list_combined(self, runner: CliRunner, config_file: Path, mock_businesses_api):
        """Test: Combined events list with filters and table output"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "events", "list",
            "--ids", "id1,id2",
            "--events", "new_funding_round,merger_and_acquisitions",
            "--days", "90"])
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
        """Test: explorium prospects match --first-name 'John' --last-name 'Doe' --business-id 'id'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe",
            "--business-id", "8adce3ca1cef0c986b22310e369a0793"
        ])
        mock_prospects_api.match.assert_called_once_with([{
            "first_name": "John",
            "last_name": "Doe",
            "business_id": "8adce3ca1cef0c986b22310e369a0793"
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

    def test_match_by_name_only(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects match --first-name 'Jane' --last-name 'Smith'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "match",
            "--first-name", "Jane",
            "--last-name", "Smith"
        ])
        mock_prospects_api.match.assert_called_once_with([{
            "first_name": "Jane",
            "last_name": "Smith"
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
        """Test: explorium prospects match --first-name 'John' --last-name 'Doe' -o table"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "match",
            "--first-name", "John",
            "--last-name", "Doe"])
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
            ["prospect_id1", "prospect_id2", "prospect_id3"],
            None
        )

    def test_bulk_enrich_from_file(self, runner: CliRunner, config_file: Path, mock_prospects_api, tmp_path: Path):
        """Test: explorium prospects bulk-enrich -f prospect_ids.txt"""
        ids_file = tmp_path / "prospect_ids.txt"
        ids_file.write_text("prospect_id1\nprospect_id2\nprospect_id3")

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
            ["id1", "id2"],
            ["contacts"]
        )

    def test_bulk_enrich_with_types_contacts_social(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'contacts,social'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "contacts,social"
        ])
        mock_prospects_api.bulk_enrich.assert_called_once_with(
            ["id1", "id2"],
            ["contacts", "social"]
        )

    def test_bulk_enrich_with_all_types(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects bulk-enrich --ids 'id1,id2' --types 'contacts,social,profile'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "bulk-enrich",
            "--ids", "id1,id2",
            "--types", "contacts,social,profile"
        ])
        mock_prospects_api.bulk_enrich.assert_called_once()


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
        """Test: explorium prospects events list --ids 'prospect_id1'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "prospect_id1"
        ])
        mock_prospects_api.list_events.assert_called_once_with(
            ["prospect_id1"],
            event_types=None,
            days=45
        )

    def test_events_list_multiple_prospects(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'id1,id2,id3'"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "id1,id2,id3"
        ])
        mock_prospects_api.list_events.assert_called_once_with(
            ["id1", "id2", "id3"],
            event_types=None,
            days=45
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

    def test_events_list_custom_days(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: explorium prospects events list --ids 'id1' --days 90"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "prospects", "events", "list",
            "--ids", "id1",
            "--days", "90"
        ])
        mock_prospects_api.list_events.assert_called_once()

    def test_events_list_combined(self, runner: CliRunner, config_file: Path, mock_prospects_api):
        """Test: Combined prospect events list"""
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "prospects", "events", "list",
            "--ids", "id1,id2",
            "--events", "prospect_changed_company",
            "--days", "60"])
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
            "--days", "90"])
        assert mock_businesses_api.list_events.called

        # Step 4: Find similar companies
        result = runner.invoke(cli, [
            "--config", str(config_file),
            "-o", "table",
            "businesses", "lookalike",
            "--id", "8adce3ca1cef0c986b22310e369a0793",
            "--size", "20"])
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
