"""Tests for batched_enrich id_key injection."""

import pytest
from unittest.mock import MagicMock

from explorium_cli.batching import batched_enrich


class TestBatchedEnrichIdKey:
    """Tests for id_key parameter in batched_enrich."""

    def test_injects_id_when_missing_from_response(self):
        """Test that entity ID is injected when API doesn't return it."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [
                {"email": "a@b.com"},
                {"email": "c@d.com"},
            ],
        }

        result = batched_enrich(
            mock_api,
            ids=["p1", "p2"],
            id_key="prospect_id",
            show_progress=False,
        )

        data = result["data"]
        assert data[0]["prospect_id"] == "p1"
        assert data[1]["prospect_id"] == "p2"

    def test_does_not_overwrite_existing_id(self):
        """Test that existing ID in API response is not overwritten."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [
                {"prospect_id": "existing_id", "email": "a@b.com"},
            ],
        }

        result = batched_enrich(
            mock_api,
            ids=["p1"],
            id_key="prospect_id",
            show_progress=False,
        )

        assert result["data"][0]["prospect_id"] == "existing_id"

    def test_no_injection_without_id_key(self):
        """Test backward compatibility: no injection when id_key is empty."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"email": "a@b.com"}],
        }

        result = batched_enrich(
            mock_api,
            ids=["p1"],
            show_progress=False,
        )

        assert "prospect_id" not in result["data"][0]

    def test_no_injection_when_count_mismatch(self):
        """Test that injection is skipped when result count doesn't match batch."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"email": "a@b.com"}],  # 1 result for 2 IDs
        }

        result = batched_enrich(
            mock_api,
            ids=["p1", "p2"],
            id_key="prospect_id",
            show_progress=False,
        )

        # Should not inject because count mismatch (1 != 2)
        assert "prospect_id" not in result["data"][0]

    def test_injection_works_across_batches(self):
        """Test that ID injection works correctly across multiple batches."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"email": "a@b.com"}, {"email": "c@d.com"}],
            },
            {
                "status": "success",
                "data": [{"email": "e@f.com"}],
            },
        ]

        result = batched_enrich(
            mock_api,
            ids=["p1", "p2", "p3"],
            batch_size=2,
            id_key="prospect_id",
            show_progress=False,
        )

        assert len(result["data"]) == 3
        assert result["data"][0]["prospect_id"] == "p1"
        assert result["data"][1]["prospect_id"] == "p2"
        assert result["data"][2]["prospect_id"] == "p3"

    def test_business_id_injection(self):
        """Test that id_key works with business_id too."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"name": "Acme Corp"}],
        }

        result = batched_enrich(
            mock_api,
            ids=["b1"],
            id_key="business_id",
            show_progress=False,
        )

        assert result["data"][0]["business_id"] == "b1"
