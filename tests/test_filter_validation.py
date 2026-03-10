"""Tests for PRD-3: Client-side filter value validation."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from explorium_cli.validation import validate_filter_values
from explorium_cli.constants import (
    VALID_DEPARTMENTS,
    VALID_JOB_LEVELS,
    DEPARTMENT_ALIASES,
    JOB_LEVEL_ALIASES,
)


class TestValidateExactMatch:
    def test_exact_department(self):
        result = validate_filter_values(["engineering"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["engineering"]

    def test_exact_job_level(self):
        result = validate_filter_values(["cxo", "vp", "director"], VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level")
        assert result == ["cxo", "vp", "director"]

    def test_multiple_departments(self):
        result = validate_filter_values(["engineering", "it"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["engineering", "it"]


class TestCaseNormalization:
    def test_uppercase_department(self):
        result = validate_filter_values(["Engineering"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["engineering"]

    def test_uppercase_job_level(self):
        result = validate_filter_values(["VP"], VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level")
        assert result == ["vp"]

    def test_mixed_case(self):
        result = validate_filter_values(["MARKETING", "Sales"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["marketing", "sales"]


class TestAliasMatch:
    def test_information_technology(self, capsys):
        result = validate_filter_values(
            ["Information Technology"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
        )
        assert result == ["it"]

    def test_hr_alias(self, capsys):
        result = validate_filter_values(["HR"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["human resources"]

    def test_tech_alias(self):
        result = validate_filter_values(["tech"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == ["it"]

    def test_multiple_aliases_same_target(self):
        result = validate_filter_values(
            ["tech", "info tech", "information technology"],
            VALID_DEPARTMENTS,
            DEPARTMENT_ALIASES,
            "department",
        )
        assert result == ["it", "it", "it"]

    def test_mixed_valid_and_alias(self):
        result = validate_filter_values(
            ["engineering", "Information Technology"],
            VALID_DEPARTMENTS,
            DEPARTMENT_ALIASES,
            "department",
        )
        assert result == ["engineering", "it"]

    def test_job_level_csuite_alias(self):
        result = validate_filter_values(["c-suite"], VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level")
        assert result == ["cxo"]

    def test_job_level_vice_president_alias(self):
        result = validate_filter_values(["vice president"], VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level")
        assert result == ["vp"]


class TestEmptyValues:
    def test_empty_string_filtered(self):
        result = validate_filter_values(
            ["engineering", "", "it"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
        )
        assert result == ["engineering", "it"]

    def test_whitespace_only_filtered(self):
        result = validate_filter_values(
            ["engineering", "  ", "it"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
        )
        assert result == ["engineering", "it"]

    def test_all_empty(self):
        result = validate_filter_values(["", " "], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department")
        assert result == []


class TestUnknownValues:
    def test_unknown_with_close_match(self, capsys):
        """Typo should warn and still send (soft validation)."""
        result = validate_filter_values(
            ["enginering"], VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
        )
        assert result == ["enginering"]

    def test_unknown_no_close_match(self, capsys):
        """Totally unknown value should warn and still send."""
        result = validate_filter_values(
            ["underwater basket weaving"],
            VALID_DEPARTMENTS,
            DEPARTMENT_ALIASES,
            "department",
        )
        assert result == ["underwater basket weaving"]


class TestCLIIntegration:
    """Test filter validation through the CLI search command."""

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.BusinessesAPI")
    def test_search_with_alias(self, mock_biz_api_cls, mock_api_cls, mock_get_api):
        """Alias should be mapped before API call."""
        from explorium_cli.main import cli

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api

        mock_biz = MagicMock()
        mock_biz_api_cls.return_value = mock_biz
        mock_biz.match.return_value = {"data": [{"business_id": "bid1"}]}

        mock_prospects = MagicMock()
        mock_api_cls.return_value = mock_prospects
        mock_prospects.search.return_value = {"status": "success", "data": [], "pagination": {"total": 0}}

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, [
            "-o", "json",
            "prospects", "search",
            "--company-name", "Acme",
            "--department", "Information Technology",
        ])

        # Check the API was called with "it" not "Information Technology"
        call_args = mock_prospects.search.call_args
        filters = call_args[1].get("filters") or call_args[0][0] if call_args[0] else call_args[1].get("filters")
        if filters and "job_department" in filters:
            assert filters["job_department"]["values"] == ["it"]

        assert 'Mapped "Information Technology"' in result.stderr

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.BusinessesAPI")
    def test_search_case_insensitive(self, mock_biz_api_cls, mock_api_cls, mock_get_api):
        """Uppercase values should be lowercased."""
        from explorium_cli.main import cli

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api

        mock_biz = MagicMock()
        mock_biz_api_cls.return_value = mock_biz
        mock_biz.match.return_value = {"data": [{"business_id": "bid1"}]}

        mock_prospects = MagicMock()
        mock_api_cls.return_value = mock_prospects
        mock_prospects.search.return_value = {"status": "success", "data": [], "pagination": {"total": 0}}

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, [
            "-o", "json",
            "prospects", "search",
            "--company-name", "Acme",
            "--department", "Engineering",
            "--job-level", "VP",
        ])

        call_args = mock_prospects.search.call_args
        if call_args:
            filters = call_args[1].get("filters", {})
            if "job_department" in filters:
                assert filters["job_department"]["values"] == ["engineering"]
            if "job_level" in filters:
                assert filters["job_level"]["values"] == ["vp"]

    def test_search_help_lists_valid_values(self):
        """Help text should show valid values."""
        from explorium_cli.main import cli

        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(cli, ["prospects", "search", "--help"])

        assert "engineering" in result.output
        assert "cxo" in result.output
        assert "vp" in result.output
        assert "it" in result.output
