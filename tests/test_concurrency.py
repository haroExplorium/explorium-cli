"""Tests for concurrent_map function."""

import threading
import time
from unittest.mock import patch

import pytest

from explorium_cli.concurrency import concurrent_map


class TestConcurrentMap:
    """Tests for concurrent_map function."""

    # ── basic ───────────────────────────────────────────────────────

    def test_concurrent_map_basic(self):
        """All items processed, results returned in input order."""
        items = [1, 2, 3, 4, 5]
        results = concurrent_map(
            lambda x: x * 10, items, max_workers=3, show_progress=False,
        )

        assert len(results) == 5
        for i, (ok, value) in enumerate(results):
            assert ok is True
            assert value == items[i] * 10

    def test_concurrent_map_empty_list(self):
        """Empty input returns empty output with no errors."""
        results = concurrent_map(
            lambda x: x, [], max_workers=3, show_progress=False,
        )

        assert results == []

    def test_concurrent_map_single_item(self):
        """Single item is processed correctly."""
        results = concurrent_map(
            lambda x: x + 1, [42], max_workers=3, show_progress=False,
        )

        assert len(results) == 1
        assert results[0] == (True, 43)

    # ── failure handling ────────────────────────────────────────────

    def test_concurrent_map_partial_failure(self):
        """Items that raise are returned as (False, exception); others succeed."""
        def process(x):
            if x % 2 == 0:
                raise ValueError(f"bad: {x}")
            return x * 10

        items = [1, 2, 3, 4, 5]
        results = concurrent_map(
            process, items, max_workers=3, show_progress=False,
        )

        assert len(results) == 5
        # Odd items succeed
        assert results[0] == (True, 10)
        assert results[2] == (True, 30)
        assert results[4] == (True, 50)
        # Even items fail
        for idx in [1, 3]:
            ok, exc = results[idx]
            assert ok is False
            assert isinstance(exc, ValueError)

    def test_concurrent_map_total_failure(self):
        """When all items fail, every result is (False, exception)."""
        def always_fail(x):
            raise RuntimeError(f"fail {x}")

        items = [1, 2, 3]
        results = concurrent_map(
            always_fail, items, max_workers=3, show_progress=False,
        )

        assert len(results) == 3
        for ok, exc in results:
            assert ok is False
            assert isinstance(exc, RuntimeError)

    # ── concurrency control ─────────────────────────────────────────

    def test_concurrent_map_respects_max_workers(self):
        """No more than max_workers threads run the function simultaneously."""
        max_workers = 2
        lock = threading.Lock()
        active = [0]
        peak = [0]

        def tracked_fn(x):
            with lock:
                active[0] += 1
                if active[0] > peak[0]:
                    peak[0] = active[0]
            time.sleep(0.03)
            with lock:
                active[0] -= 1
            return x

        concurrent_map(
            tracked_fn, list(range(6)), max_workers=max_workers,
            show_progress=False,
        )

        assert peak[0] <= max_workers

    def test_concurrent_map_sequential_when_workers_1(self):
        """max_workers=1 processes items one at a time, in order."""
        lock = threading.Lock()
        active = [0]
        peak = [0]
        order = []

        def tracked_fn(x):
            with lock:
                active[0] += 1
                if active[0] > peak[0]:
                    peak[0] = active[0]
                order.append(x)
            time.sleep(0.01)
            with lock:
                active[0] -= 1
            return x

        items = [10, 20, 30, 40]
        results = concurrent_map(
            tracked_fn, items, max_workers=1, show_progress=False,
        )

        assert peak[0] == 1
        assert order == items
        assert all(ok for ok, _ in results)

    # ── ordering ────────────────────────────────────────────────────

    def test_concurrent_map_preserves_order(self):
        """Results match input order even when workers finish out of order."""
        def staggered_fn(x):
            # Lower values sleep longer so they finish last
            time.sleep(0.05 - x * 0.01)
            return x * 100

        items = [4, 3, 2, 1, 0]
        results = concurrent_map(
            staggered_fn, items, max_workers=5, show_progress=False,
        )

        for i, (ok, value) in enumerate(results):
            assert ok is True
            assert value == items[i] * 100

    # ── progress output ─────────────────────────────────────────────

    def test_concurrent_map_progress_output(self, capsys):
        """show_progress=True writes to stderr; False is silent."""
        items = [1, 2, 3]

        # With progress enabled
        concurrent_map(lambda x: x, items, show_progress=True, label="things")
        captured = capsys.readouterr()
        assert captured.err != ""  # something written to stderr

        # With progress disabled
        concurrent_map(lambda x: x, items, show_progress=False, label="things")
        captured = capsys.readouterr()
        assert captured.err == ""  # nothing written to stderr
