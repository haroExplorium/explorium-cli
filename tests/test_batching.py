"""Tests for batching module — batched_enrich id_key injection."""

import pytest
from unittest.mock import MagicMock

from explorium_cli.batching import batched_enrich


class TestBatchedEnrichIdKey:
    """Tests for batched_enrich id_key parameter."""

    def test_injects_id_when_missing_from_response(self):
        """When API response records lack the ID, inject it from the input list."""
        api_method = MagicMock(return_value={
            "status": "success",
            "data": [
                {"data": {"emails": [{"address": "a@b.com"}]}},
                {"data": {"emails": [{"address": "c@d.com"}]}},
            ]
        })

        result = batched_enrich(
            api_method, ["p1", "p2"],
            entity_name="prospects",
            id_key="prospect_id",
            show_progress=False,
        )

        records = result["data"]
        assert len(records) == 2
        assert records[0]["prospect_id"] == "p1"
        assert records[1]["prospect_id"] == "p2"
        # Original data preserved
        assert records[0]["data"]["emails"][0]["address"] == "a@b.com"

    def test_does_not_overwrite_existing_id(self):
        """When API response already includes the ID, don't overwrite it."""
        api_method = MagicMock(return_value={
            "status": "success",
            "data": [
                {"prospect_id": "api_id_1", "data": {"emails": []}},
                {"prospect_id": "api_id_2", "data": {"emails": []}},
            ]
        })

        result = batched_enrich(
            api_method, ["input_id_1", "input_id_2"],
            entity_name="prospects",
            id_key="prospect_id",
            show_progress=False,
        )

        records = result["data"]
        assert records[0]["prospect_id"] == "api_id_1"
        assert records[1]["prospect_id"] == "api_id_2"

    def test_no_injection_without_id_key(self):
        """When id_key is not set, don't inject anything (backward compat)."""
        api_method = MagicMock(return_value={
            "status": "success",
            "data": [
                {"data": {"emails": []}},
            ]
        })

        result = batched_enrich(
            api_method, ["p1"],
            entity_name="prospects",
            show_progress=False,
        )

        records = result["data"]
        assert "prospect_id" not in records[0]

    def test_no_injection_when_count_mismatch(self):
        """When result count doesn't match input count, skip injection."""
        api_method = MagicMock(return_value={
            "status": "success",
            "data": [
                {"data": {"emails": []}},
            ]
        })

        result = batched_enrich(
            api_method, ["p1", "p2"],  # 2 IDs but 1 result
            entity_name="prospects",
            id_key="prospect_id",
            show_progress=False,
        )

        records = result["data"]
        assert len(records) == 1
        assert "prospect_id" not in records[0]

    def test_injection_works_across_batches(self):
        """ID injection works correctly across multiple batches."""
        api_method = MagicMock(side_effect=[
            {"status": "success", "data": [
                {"data": {"emails": []}},
                {"data": {"emails": []}},
            ]},
            {"status": "success", "data": [
                {"data": {"emails": []}},
            ]},
        ])

        result = batched_enrich(
            api_method, ["p1", "p2", "p3"],
            batch_size=2,
            entity_name="prospects",
            id_key="prospect_id",
            show_progress=False,
        )

        records = result["data"]
        assert len(records) == 3
        assert records[0]["prospect_id"] == "p1"
        assert records[1]["prospect_id"] == "p2"
        assert records[2]["prospect_id"] == "p3"

    def test_business_id_injection(self):
        """Works with business_id key too."""
        api_method = MagicMock(return_value={
            "status": "success",
            "data": [
                {"name": "Acme Corp", "revenue": "10M"},
            ]
        })

        result = batched_enrich(
            api_method, ["b1"],
            entity_name="businesses",
            id_key="business_id",
            show_progress=False,
        )

        records = result["data"]
        assert records[0]["business_id"] == "b1"
        assert records[0]["name"] == "Acme Corp"
