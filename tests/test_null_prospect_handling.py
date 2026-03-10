"""Tests for PRD-1: Graceful null prospect ID handling in batch enrichment."""

import csv
import io
import tempfile

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, call

from explorium_cli.batching import batched_enrich


class TestBatchedEnrichNullGuard:
    """Test defensive null filtering in batched_enrich()."""

    def test_filters_null_ids(self, capsys):
        """Null and empty IDs should be filtered before API call."""
        mock_api = MagicMock(return_value={
            "status": "success",
            "data": [
                {"prospect_id": "id1", "email": "a@b.com"},
                {"prospect_id": "id3", "email": "c@d.com"},
            ],
        })

        result = batched_enrich(mock_api, ["id1", None, "id3", ""])
        assert len(result["data"]) == 2
        # API should only be called with valid IDs
        mock_api.assert_called_once()
        called_ids = mock_api.call_args[0][0]
        assert called_ids == ["id1", "id3"]

    def test_all_null_ids(self):
        """All null/empty IDs should return empty result without calling API."""
        mock_api = MagicMock()
        result = batched_enrich(mock_api, [None, None, ""])
        assert result == {"status": "success", "data": []}
        mock_api.assert_not_called()

    def test_no_nulls_no_warning(self, capsys):
        """No filtering warning when all IDs are valid."""
        mock_api = MagicMock(return_value={
            "status": "success",
            "data": [
                {"prospect_id": "id1"},
                {"prospect_id": "id2"},
            ],
        })
        result = batched_enrich(mock_api, ["id1", "id2"])
        assert len(result["data"]) == 2
        mock_api.assert_called_once_with(["id1", "id2"])


class TestEnrichFilePartialMatch:
    """Test enrich-file with partial match results."""

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.resolve_prospect_id")
    @patch("explorium_cli.commands.prospects.batched_enrich")
    def test_partial_match_enriches_valid_only(
        self, mock_batch, mock_resolve, mock_api_cls, mock_get_api
    ):
        """Only matched prospects should be sent for enrichment."""
        from explorium_cli.main import cli

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api
        mock_prospects = MagicMock()
        mock_api_cls.return_value = mock_prospects

        # 3 of 5 match; 2 fail
        from explorium_cli.commands.prospects import MatchError
        call_count = 0
        def resolve_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count in (2, 4):
                raise MatchError("No match found")
            return f"pid{call_count}"

        mock_resolve.side_effect = resolve_side_effect
        mock_batch.return_value = {
            "status": "success",
            "data": [
                {"prospect_id": "pid1", "email": "a@b.com"},
                {"prospect_id": "pid3", "email": "c@d.com"},
                {"prospect_id": "pid5", "email": "e@f.com"},
            ],
        }

        # Create temp CSV
        csv_content = "first_name,last_name,company_name\nAlice,Smith,Acme\nBob,Jones,Beta\nCarol,White,Gamma\nDave,Brown,Delta\nEve,Black,Epsilon\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "json",
                "prospects", "enrich-file",
                "-f", f.name,
                "--types", "contacts",
                "--summary",
            ])

        # batched_enrich called with 3 valid IDs only
        assert mock_batch.called
        called_ids = mock_batch.call_args[0][1]
        assert len(called_ids) == 3
        assert None not in called_ids

        # Output should contain enriched + unenrichable rows
        assert "Match phase: 3 matched / 2 not found" in result.stderr

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.resolve_prospect_id")
    def test_all_unmatched_no_enrichment(self, mock_resolve, mock_api_cls, mock_get_api):
        """If all matches fail, enrichment should not be called."""
        from explorium_cli.main import cli
        from explorium_cli.commands.prospects import MatchError

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api
        mock_api_cls.return_value = MagicMock()

        mock_resolve.side_effect = MatchError("No match found")

        csv_content = "first_name,last_name,company_name\nAlice,Smith,Acme\nBob,Jones,Beta\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "json",
                "prospects", "enrich-file",
                "-f", f.name,
                "--types", "contacts",
            ])

        # Should output rows with input_ columns, not crash
        assert result.exit_code == 0
        assert "Match phase: 0 matched / 2 not found" in result.stderr

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.resolve_prospect_id")
    @patch("explorium_cli.commands.prospects.batched_enrich")
    def test_all_matched_no_warning(
        self, mock_batch, mock_resolve, mock_api_cls, mock_get_api
    ):
        """No filtering warning when all rows match."""
        from explorium_cli.main import cli

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api
        mock_api_cls.return_value = MagicMock()

        call_count = 0
        def resolve_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"pid{call_count}"

        mock_resolve.side_effect = resolve_side_effect
        mock_batch.return_value = {
            "status": "success",
            "data": [
                {"prospect_id": "pid1", "email": "a@b.com"},
                {"prospect_id": "pid2", "email": "c@d.com"},
            ],
        }

        csv_content = "first_name,last_name,company_name\nAlice,Smith,Acme\nBob,Jones,Beta\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "json",
                "prospects", "enrich-file",
                "-f", f.name,
                "--types", "contacts",
            ])

        assert "Match phase: 2 matched / 0 not found" in result.stderr
        assert "could not be matched" not in result.stderr

    @patch("explorium_cli.commands.prospects.get_api")
    @patch("explorium_cli.commands.prospects.ProspectsAPI")
    @patch("explorium_cli.commands.prospects.resolve_prospect_id")
    @patch("explorium_cli.commands.prospects.batched_enrich")
    def test_summary_breakdown(
        self, mock_batch, mock_resolve, mock_api_cls, mock_get_api
    ):
        """Summary should show match phase, enrich phase, and output breakdown."""
        from explorium_cli.main import cli
        from explorium_cli.commands.prospects import MatchError

        mock_api = MagicMock()
        mock_get_api.return_value = mock_api
        mock_api_cls.return_value = MagicMock()

        call_count = 0
        def resolve_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:
                raise MatchError("No match found")
            return f"pid{call_count}"

        mock_resolve.side_effect = resolve_side_effect
        mock_batch.return_value = {
            "status": "success",
            "data": [
                {"prospect_id": "pid1", "email": "a@b.com"},
                {"prospect_id": "pid2", "email": "c@d.com"},
            ],
        }

        csv_content = "first_name,last_name,company_name\nAlice,Smith,Acme\nBob,Jones,Beta\nCarol,White,Gamma\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "json",
                "prospects", "enrich-file",
                "-f", f.name,
                "--types", "contacts",
                "--summary",
            ])

        assert "Match phase: 2 matched / 1 not found" in result.stderr
        assert "Enrich phase: 2 enriched" in result.stderr
        assert "Output: 3 total rows (2 enriched + 1 match-only)" in result.stderr
