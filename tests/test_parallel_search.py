"""Tests for parallel multi-business prospect search."""

import time
from unittest.mock import MagicMock, patch

import pytest

from explorium_cli.parallel_search import parallel_prospect_search, print_search_summary


class TestParallelProspectSearch:
    """Tests for parallel_prospect_search function."""

    def _make_api(self, responses: dict[str, dict | Exception]):
        """Create a mock api_method that returns per-business-ID responses.

        Args:
            responses: mapping from business_id → API response dict, or an
                       Exception to raise for that ID.
        """
        def mock_search(filters, size=100, page_size=100, page=1):
            bid = filters["business_id"]["values"][0]
            resp = responses.get(bid)
            if isinstance(resp, Exception):
                raise resp
            return resp or {"data": []}
        return mock_search

    # ── basic fan-out ────────────────────────────────────────────────

    def test_single_id_returns_data(self):
        """Single business ID should still work through fan-out."""
        api = self._make_api({
            "bid1": {"data": [
                {"prospect_id": "p1", "name": "Alice", "business_id": "bid1"},
            ]}
        })

        result = parallel_prospect_search(
            api, ["bid1"], filters={}, show_progress=False,
        )

        assert len(result["data"]) == 1
        assert result["data"][0]["prospect_id"] == "p1"

    def test_multi_id_merges_results(self):
        """Results from multiple companies should be merged."""
        api = self._make_api({
            "bid1": {"data": [
                {"prospect_id": "p1", "business_id": "bid1"},
            ]},
            "bid2": {"data": [
                {"prospect_id": "p2", "business_id": "bid2"},
                {"prospect_id": "p3", "business_id": "bid2"},
            ]},
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2"], filters={}, show_progress=False,
        )

        ids = {r["prospect_id"] for r in result["data"]}
        assert ids == {"p1", "p2", "p3"}

    def test_deduplicates_by_prospect_id(self):
        """Same prospect appearing in multiple companies should be deduplicated."""
        api = self._make_api({
            "bid1": {"data": [
                {"prospect_id": "p1", "business_id": "bid1"},
            ]},
            "bid2": {"data": [
                {"prospect_id": "p1", "business_id": "bid2"},  # duplicate
                {"prospect_id": "p2", "business_id": "bid2"},
            ]},
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2"], filters={}, show_progress=False,
        )

        ids = [r["prospect_id"] for r in result["data"]]
        assert ids.count("p1") == 1
        assert "p2" in ids

    def test_deduplicates_business_ids(self):
        """Duplicate business IDs in input should be deduplicated."""
        call_count = {"n": 0}

        def mock_search(filters, size=100, page_size=100, page=1):
            call_count["n"] += 1
            bid = filters["business_id"]["values"][0]
            return {"data": [{"prospect_id": f"p-{bid}", "business_id": bid}]}

        result = parallel_prospect_search(
            mock_search, ["bid1", "bid1", "bid1"], filters={}, show_progress=False,
        )

        assert call_count["n"] == 1  # only 1 unique ID
        assert len(result["data"]) == 1

    # ── filters are passed through ───────────────────────────────────

    def test_filters_passed_to_each_call(self):
        """Shared filters should be sent with each per-company request."""
        received_filters = []

        def mock_search(filters, size=100, page_size=100, page=1):
            received_filters.append(dict(filters))
            return {"data": []}

        parallel_prospect_search(
            mock_search,
            ["bid1", "bid2"],
            filters={"job_level": {"values": ["vp", "cxo"]}},
            show_progress=False,
        )

        assert len(received_filters) == 2
        for f in received_filters:
            assert f["job_level"] == {"values": ["vp", "cxo"]}
            # Each should have its own business_id
            assert "business_id" in f

    def test_original_filters_not_mutated(self):
        """The caller's filters dict should not be modified."""
        original_filters = {"job_level": {"values": ["vp"]}}

        def mock_search(filters, size=100, page_size=100, page=1):
            return {"data": []}

        parallel_prospect_search(
            mock_search,
            ["bid1", "bid2"],
            filters=original_filters,
            show_progress=False,
        )

        assert "business_id" not in original_filters

    # ── error handling ───────────────────────────────────────────────

    def test_one_failure_does_not_abort_others(self):
        """A failing company should not prevent others from returning results."""
        api = self._make_api({
            "bid1": {"data": [
                {"prospect_id": "p1", "business_id": "bid1"},
            ]},
            "bid2": Exception("API error for bid2"),
            "bid3": {"data": [
                {"prospect_id": "p3", "business_id": "bid3"},
            ]},
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2", "bid3"], filters={}, show_progress=False,
        )

        ids = {r["prospect_id"] for r in result["data"]}
        assert "p1" in ids
        assert "p3" in ids
        meta = result["_search_meta"]
        assert meta["errors"] == 1
        assert meta["total_prospects"] == 2

    def test_all_failures_returns_empty(self):
        """If every company fails, return empty data with error count."""
        api = self._make_api({
            "bid1": Exception("fail1"),
            "bid2": Exception("fail2"),
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2"], filters={}, show_progress=False,
        )

        assert result["data"] == []
        meta = result["_search_meta"]
        assert meta["errors"] == 2
        assert meta["total_prospects"] == 0

    # ── concurrency ──────────────────────────────────────────────────

    def test_concurrency_limits_parallel_calls(self):
        """Concurrency should limit how many API calls run at once."""
        max_concurrent = {"current": 0, "peak": 0}
        import threading
        lock = threading.Lock()

        def mock_search(filters, size=100, page_size=100, page=1):
            with lock:
                max_concurrent["current"] += 1
                if max_concurrent["current"] > max_concurrent["peak"]:
                    max_concurrent["peak"] = max_concurrent["current"]
            time.sleep(0.05)  # simulate API latency
            with lock:
                max_concurrent["current"] -= 1
            bid = filters["business_id"]["values"][0]
            return {"data": [{"prospect_id": f"p-{bid}", "business_id": bid}]}

        result = parallel_prospect_search(
            mock_search,
            [f"bid{i}" for i in range(10)],
            filters={},
            concurrency=3,
            show_progress=False,
        )

        assert max_concurrent["peak"] <= 3
        assert len(result["data"]) == 10

    # ── total per-company semantics ──────────────────────────────────

    def test_total_applied_per_company(self):
        """--total should be passed per-company via paginated_fetch."""
        calls = []

        def mock_search(filters, size=100, page_size=100, page=1):
            bid = filters["business_id"]["values"][0]
            calls.append({"bid": bid, "size": size, "page_size": page_size})
            # Return more than total to test trimming
            return {"data": [
                {"prospect_id": f"p-{bid}-{i}", "business_id": bid}
                for i in range(5)
            ]}

        with patch("explorium_cli.parallel_search.paginated_fetch") as mock_pf:
            mock_pf.side_effect = lambda api_method, total, page_size, show_progress, **kw: (
                mock_search(kw["filters"], size=total, page_size=page_size)
            )

            result = parallel_prospect_search(
                mock_search,
                ["bid1", "bid2"],
                filters={},
                total=3,
                show_progress=False,
            )

        # paginated_fetch should be called once per company
        assert mock_pf.call_count == 2
        for call in mock_pf.call_args_list:
            assert call.kwargs.get("total") or call[1].get("total") == 3

    # ── metadata ─────────────────────────────────────────────────────

    def test_search_meta_structure(self):
        """_search_meta should contain expected fields."""
        api = self._make_api({
            "bid1": {"data": [
                {"prospect_id": "p1", "business_id": "bid1"},
                {"prospect_id": "p2", "business_id": "bid1"},
            ]},
            "bid2": {"data": [
                {"prospect_id": "p3", "business_id": "bid2"},
            ]},
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2"], filters={}, show_progress=False,
        )

        meta = result["_search_meta"]
        assert meta["companies_searched"] == 2
        assert meta["total_prospects"] == 3
        assert meta["errors"] == 0
        assert meta["min"] == 1
        assert meta["max"] == 2
        assert meta["avg"] == 1.5
        assert len(meta["per_company"]) == 2

    def test_empty_results_for_company(self):
        """A company returning 0 results should not error."""
        api = self._make_api({
            "bid1": {"data": []},
            "bid2": {"data": [
                {"prospect_id": "p1", "business_id": "bid2"},
            ]},
        })

        result = parallel_prospect_search(
            api, ["bid1", "bid2"], filters={}, show_progress=False,
        )

        assert len(result["data"]) == 1
        meta = result["_search_meta"]
        assert meta["errors"] == 0
        assert meta["min"] == 0


class TestPrintSearchSummary:
    """Tests for print_search_summary."""

    def test_prints_summary(self, capsys):
        meta = {
            "companies_searched": 5,
            "concurrency": 3,
            "total_prospects": 15,
            "errors": 1,
            "min": 1,
            "max": 5,
            "avg": 3.0,
            "per_company": [],
        }

        print_search_summary(meta)

        captured = capsys.readouterr()
        assert "5 companies" in captured.err
        assert "Concurrency: 3" in captured.err
        assert "15 prospects" in captured.err
        assert "Errors: 1" in captured.err
