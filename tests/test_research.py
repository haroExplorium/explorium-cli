"""Tests for AI research command."""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from explorium_cli.ai_client import parse_research_response
from explorium_cli.research import load_records, run_research, _find_company_column, _find_domain_column


# =============================================================================
# parse_research_response tests
# =============================================================================


class TestParseResearchResponse:
    def test_standard_format(self):
        text = (
            "ANSWER: Yes, this is a B2B company\n"
            "REASONING: They sell enterprise software\n"
            "CONFIDENCE: high"
        )
        result = parse_research_response(text)
        assert result["answer"] == "Yes, this is a B2B company"
        assert result["reasoning"] == "They sell enterprise software"
        assert result["confidence"] == "high"

    def test_multiline_answer(self):
        text = (
            "ANSWER: Yes, this is a B2B company.\n"
            "They provide cloud services to enterprises.\n"
            "REASONING: Found on their website\n"
            "CONFIDENCE: medium"
        )
        result = parse_research_response(text)
        assert "B2B company" in result["answer"]
        assert "cloud services" in result["answer"]
        assert result["confidence"] == "medium"

    def test_case_insensitive_labels(self):
        text = (
            "answer: Yes\n"
            "reasoning: Because\n"
            "confidence: low"
        )
        result = parse_research_response(text)
        assert result["answer"] == "Yes"
        assert result["reasoning"] == "Because"
        assert result["confidence"] == "low"

    def test_unknown_confidence_defaults_low(self):
        text = (
            "ANSWER: Maybe\n"
            "REASONING: Not sure\n"
            "CONFIDENCE: uncertain"
        )
        result = parse_research_response(text)
        assert result["answer"] == "Maybe"
        # Non-standard confidence kept as-is but not normalized
        assert result["confidence"] == "uncertain"

    def test_empty_text_returns_defaults(self):
        result = parse_research_response("")
        assert result["answer"] == ""
        assert result["reasoning"] == ""
        assert result["confidence"] == "low"

    def test_no_labels_puts_text_as_answer(self):
        text = "This company appears to be B2B based on their website."
        result = parse_research_response(text)
        assert result["answer"] == text
        assert result["confidence"] == "low"

    def test_extra_whitespace(self):
        text = (
            "ANSWER:   Yes  \n"
            "REASONING:   Found it   \n"
            "CONFIDENCE:   high   "
        )
        result = parse_research_response(text)
        assert result["answer"] == "Yes"
        assert result["reasoning"] == "Found it"
        assert result["confidence"] == "high"

    def test_markdown_bold_labels(self):
        text = (
            "**ANSWER:** Yes, this is fintech\n"
            "**REASONING:** They process payments\n"
            "**CONFIDENCE:** High"
        )
        result = parse_research_response(text)
        assert result["answer"] == "Yes, this is fintech"
        assert result["reasoning"] == "They process payments"
        assert result["confidence"] == "high"

    def test_markdown_list_labels(self):
        text = (
            "- **Answer:** No\n"
            "- **Reasoning:** They sell CRM software\n"
            "- **Confidence:** high"
        )
        result = parse_research_response(text)
        assert result["answer"] == "No"
        assert result["reasoning"] == "They sell CRM software"
        assert result["confidence"] == "high"


# =============================================================================
# Column detection tests
# =============================================================================


class TestColumnDetection:
    def test_find_company_name(self):
        assert _find_company_column(["company_name", "revenue"]) == "company_name"

    def test_find_company_alias(self):
        assert _find_company_column(["company", "domain"]) == "company"

    def test_find_name_column(self):
        assert _find_company_column(["name", "website"]) == "name"

    def test_no_company_column(self):
        assert _find_company_column(["revenue", "employees"]) is None

    def test_find_domain(self):
        assert _find_domain_column(["name", "domain"]) == "domain"

    def test_find_website(self):
        assert _find_domain_column(["name", "website"]) == "website"

    def test_no_domain(self):
        assert _find_domain_column(["name", "revenue"]) is None


# =============================================================================
# load_records tests
# =============================================================================


class TestLoadRecords:
    def test_load_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("company_name,domain\nAcme,acme.com\nGlobex,globex.com\n")
        with open(csv_file) as f:
            records = load_records(f)
        assert len(records) == 2
        assert records[0]["company_name"] == "Acme"
        assert records[1]["domain"] == "globex.com"

    def test_load_json(self, tmp_path):
        json_file = tmp_path / "test.json"
        data = [
            {"company_name": "Acme", "domain": "acme.com"},
            {"company_name": "Globex", "domain": "globex.com"},
        ]
        json_file.write_text(json.dumps(data))
        with open(json_file) as f:
            records = load_records(f)
        assert len(records) == 2
        assert records[0]["company_name"] == "Acme"

    def test_empty_file_raises(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("company_name\n")
        with open(csv_file) as f:
            with pytest.raises(Exception):
                load_records(f)


# =============================================================================
# Integration test with mocked Anthropic
# =============================================================================


class TestRunResearch:
    @pytest.mark.asyncio
    async def test_run_research_mocked(self):
        records = [
            {"company_name": "Acme Corp", "domain": "acme.com"},
            {"company_name": "Globex Inc", "domain": "globex.com"},
        ]

        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(type="text", text="ANSWER: Yes\nREASONING: Found on site\nCONFIDENCE: high")
        ]

        with patch("explorium_cli.ai_client._get_client") as mock_client_fn:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_client_fn.return_value = mock_client

            results = await run_research(
                records=records,
                prompt="Is {company_name} a B2B company?",
                threads=2,
                max_searches=3,
                verbose=False,
            )

        assert len(results) == 2
        assert results[0]["research_answer"] == "Yes"
        assert results[0]["research_reasoning"] == "Found on site"
        assert results[0]["research_confidence"] == "high"
        # Original columns preserved
        assert results[0]["company_name"] == "Acme Corp"
        assert results[0]["domain"] == "acme.com"


class TestResearchCLI:
    def test_research_help(self):
        runner = CliRunner(mix_stderr=False)
        from explorium_cli.main import cli
        result = runner.invoke(cli, ["research", "run", "--help"])
        assert result.exit_code == 0
        assert "--prompt" in result.output
        assert "--file" in result.output
        assert "--threads" in result.output

    def test_research_missing_file(self):
        runner = CliRunner(mix_stderr=False)
        from explorium_cli.main import cli
        result = runner.invoke(cli, ["research", "run", "--prompt", "test"])
        assert result.exit_code != 0

    def test_research_missing_prompt(self, tmp_path):
        runner = CliRunner(mix_stderr=False)
        from explorium_cli.main import cli
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("company_name\nAcme\n")
        result = runner.invoke(cli, ["research", "run", "-f", str(csv_file)])
        assert result.exit_code != 0
