"""Tests for search filter options on businesses and prospects commands."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from explorium_cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


@pytest.fixture
def config_with_key(tmp_path: Path) -> Path:
    config_dir = tmp_path / ".explorium"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text(yaml.dump({
        "api_key": "test_api_key",
        "base_url": "https://api.explorium.ai/v1",
        "default_output": "json"
    }))
    return config_file


# =============================================================================
# Business Search Filters
# =============================================================================

class TestBusinessSearchFilters:
    """Tests for all business search filter options."""

    def _run_search(self, runner, config_with_key, extra_args):
        """Helper: run businesses search with given args, return filters dict."""
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search"] + extra_args,
            )
            assert result.exit_code == 0, f"CLI failed: {result.output}{result.stderr or ''}"
            mock_instance.search.assert_called_once()
            return mock_instance.search.call_args[0][0]  # filters dict

    def test_country_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--country", "US,GB"])
        assert filters["country_code"] == {"type": "includes", "values": ["US", "GB"]}

    def test_region_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--region", "us-ca,us-tx"])
        assert filters["region_country_code"] == {"type": "includes", "values": ["us-ca", "us-tx"]}

    def test_city_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--city", "San Francisco"])
        assert filters["city_region_country"] == {"type": "includes", "values": ["San Francisco"]}

    def test_size_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--size", "51-200,201-500"])
        assert filters["company_size"] == {"type": "includes", "values": ["51-200", "201-500"]}

    def test_revenue_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--revenue", "1M-5M,5M-10M"])
        assert filters["company_revenue"] == {"type": "includes", "values": ["1M-5M", "5M-10M"]}

    def test_company_age_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--company-age", "0-3,3-6"])
        assert filters["company_age"] == {"type": "includes", "values": ["0-3", "3-6"]}

    def test_locations_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--locations", "1,2-5"])
        assert filters["number_of_locations"] == {"type": "includes", "values": ["1", "2-5"]}

    def test_industry_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--industry", "Software Development"])
        assert filters["linkedin_category"] == {"type": "includes", "values": ["Software Development"]}

    def test_google_category_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--google-category", "Software Company"])
        assert filters["google_category"] == {"type": "includes", "values": ["Software Company"]}

    def test_naics_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--naics", "5611,541512"])
        assert filters["naics_category"] == {"type": "includes", "values": ["5611", "541512"]}

    def test_tech_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--tech", "JavaScript,AWS"])
        assert filters["company_tech_stack_tech"] == {"type": "includes", "values": ["JavaScript", "AWS"]}

    def test_tech_category_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--tech-category", "CRM,Marketing"])
        assert filters["company_tech_stack_category"] == {"type": "includes", "values": ["CRM", "Marketing"]}

    def test_keywords_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--keywords", "machine learning,AI"])
        assert filters["website_keywords"] == {"type": "any_match_phrase", "values": ["machine learning", "AI"]}

    def test_intent_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--intent", "Security:Cloud Security"])
        assert filters["business_intent_topics"] == {"type": "business_intent_topics", "topics": ["Security:Cloud Security"]}

    def test_intent_filter_with_level(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--intent", "Security:Cloud Security", "--intent-level", "high_intent"])
        assert filters["business_intent_topics"] == {
            "type": "business_intent_topics",
            "topics": ["Security:Cloud Security"],
            "topic_intent_level": "high_intent",
        }

    def test_events_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--events", "new_product,ipo_announcement"])
        assert filters["events"] == {
            "type": "includes",
            "values": ["new_product", "ipo_announcement"],
            "last_occurrence": 45,
        }

    def test_events_filter_custom_days(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--events", "new_product", "--events-days", "90"])
        assert filters["events"]["last_occurrence"] == 90

    def test_has_website_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--has-website"])
        assert filters["has_website"] == {"type": "exists", "value": True}

    def test_is_public_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--is-public"])
        assert filters["is_public_company"] == {"type": "exists", "value": True}

    def test_hq_only_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--hq-only"])
        assert filters["include_operating_locations"] == {"type": "exists", "value": False}

    def test_multiple_filters_combined(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, [
            "--country", "US",
            "--size", "201-500",
            "--tech", "Salesforce",
            "--has-website",
            "--hq-only",
        ])
        assert "country_code" in filters
        assert "company_size" in filters
        assert "company_tech_stack_tech" in filters
        assert "has_website" in filters
        assert "include_operating_locations" in filters

    def test_no_filters_passes_empty_dict(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, [])
        assert filters == {}


class TestBusinessSearchCategoryValidation:
    """Tests for mutually exclusive category filter validation."""

    def test_industry_and_google_category_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search",
                 "--industry", "Software", "--google-category", "Tech"],
            )
            assert result.exit_code != 0
            full = result.output + (result.stderr or "")
            assert "Only one category filter" in full

    def test_industry_and_naics_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search",
                 "--industry", "Software", "--naics", "5611"],
            )
            assert result.exit_code != 0

    def test_all_three_category_filters_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.businesses.BusinessesAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "businesses", "search",
                 "--industry", "Software", "--google-category", "Tech", "--naics", "5611"],
            )
            assert result.exit_code != 0


# =============================================================================
# Prospect Search Filters
# =============================================================================

class TestProspectSearchFilters:
    """Tests for all prospect search filter options."""

    def _run_search(self, runner, config_with_key, extra_args):
        """Helper: run prospects search with given args, return filters dict."""
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            mock_instance = MagicMock()
            mock_instance.search.return_value = {"status": "success", "data": []}
            MockAPI.return_value = mock_instance

            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "search",
                 "--business-id", "test_biz"] + extra_args,
            )
            assert result.exit_code == 0, f"CLI failed: {result.output}{result.stderr or ''}"
            mock_instance.search.assert_called_once()
            return mock_instance.search.call_args[0][0]  # filters dict

    def test_job_level_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--job-level", "cxo,vp"])
        assert filters["job_level"] == {"type": "includes", "values": ["cxo", "vp"]}

    def test_department_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--department", "engineering,sales"])
        assert filters["job_department"] == {"type": "includes", "values": ["engineering", "sales"]}

    def test_job_title_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--job-title", "CTO"])
        assert filters["job_title"] == {
            "type": "any_match_phrase",
            "values": ["CTO"],
            "include_related_job_titles": True,
        }

    def test_country_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--country", "US,GB"])
        assert filters["country_code"] == {"type": "includes", "values": ["US", "GB"]}

    def test_region_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--region", "us-ca,us-ny"])
        assert filters["region_country_code"] == {"type": "includes", "values": ["us-ca", "us-ny"]}

    def test_city_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--city", "New York"])
        assert filters["city_region_country"] == {"type": "includes", "values": ["New York"]}

    def test_has_email_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--has-email"])
        assert filters["has_email"] == {"type": "exists", "value": True}

    def test_has_phone_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--has-phone"])
        assert filters["has_phone_number"] == {"type": "exists", "value": True}

    def test_has_website_flag(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--has-website"])
        assert filters["has_website"] == {"type": "exists", "value": True}

    def test_experience_range_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--experience-min", "24", "--experience-max", "120"])
        assert filters["total_experience_months"] == {"type": "range", "gte": 24, "lte": 120}

    def test_experience_min_only(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--experience-min", "36"])
        assert filters["total_experience_months"] == {"type": "range", "gte": 36}

    def test_experience_max_only(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--experience-max", "60"])
        assert filters["total_experience_months"] == {"type": "range", "lte": 60}

    def test_role_tenure_range_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--role-tenure-min", "6", "--role-tenure-max", "24"])
        assert filters["current_role_months"] == {"type": "range", "gte": 6, "lte": 24}

    def test_company_size_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--company-size", "51-200,201-500"])
        assert filters["company_size"] == {"type": "includes", "values": ["51-200", "201-500"]}

    def test_company_revenue_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--company-revenue", "10M-25M"])
        assert filters["company_revenue"] == {"type": "includes", "values": ["10M-25M"]}

    def test_company_country_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--company-country", "US,GB"])
        assert filters["company_country_code"] == {"type": "includes", "values": ["US", "GB"]}

    def test_company_region_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--company-region", "us-ca"])
        assert filters["company_region_country_code"] == {"type": "includes", "values": ["us-ca"]}

    def test_industry_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--industry", "Software Development"])
        assert filters["linkedin_category"] == {"type": "includes", "values": ["Software Development"]}

    def test_google_category_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--google-category", "Software Company"])
        assert filters["google_category"] == {"type": "includes", "values": ["Software Company"]}

    def test_naics_filter(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, ["--naics", "5611"])
        assert filters["naics_category"] == {"type": "includes", "values": ["5611"]}

    def test_multiple_filters_combined(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, [
            "--job-level", "cxo",
            "--country", "US",
            "--has-email",
            "--company-size", "201-500",
            "--experience-min", "24",
        ])
        assert "job_level" in filters
        assert "country_code" in filters
        assert "has_email" in filters
        assert "company_size" in filters
        assert "total_experience_months" in filters
        assert "business_id" in filters  # always present from --business-id

    def test_business_id_always_included(self, runner, config_with_key):
        filters = self._run_search(runner, config_with_key, [])
        assert filters["business_id"] == {"type": "includes", "values": ["test_biz"]}


class TestProspectSearchCategoryValidation:
    """Tests for mutually exclusive category filter validation."""

    def test_industry_and_google_category_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "search",
                 "--business-id", "biz1",
                 "--industry", "Software", "--google-category", "Tech"],
            )
            assert result.exit_code != 0
            full = result.output + (result.stderr or "")
            assert "Only one category filter" in full

    def test_industry_and_naics_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "search",
                 "--business-id", "biz1",
                 "--industry", "Software", "--naics", "5611"],
            )
            assert result.exit_code != 0

    def test_all_three_category_filters_rejects(self, runner, config_with_key):
        with patch("explorium_cli.commands.prospects.ProspectsAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            result = runner.invoke(
                cli,
                ["--config", str(config_with_key), "prospects", "search",
                 "--business-id", "biz1",
                 "--industry", "Software", "--google-category", "Tech", "--naics", "5611"],
            )
            assert result.exit_code != 0
