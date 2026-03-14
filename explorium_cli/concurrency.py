"""Unified concurrency utility for Explorium CLI."""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def concurrent_map(
    fn: Callable,
    items: list,
    max_workers: int = 5,
    label: str = "items",
    show_progress: bool = True,
) -> list[tuple[bool, Any]]:
    """Apply *fn* to each item concurrently, returning results in input order.

    Args:
        fn: Callable that takes a single item and returns a result.
        items: List of items to process.
        max_workers: Maximum concurrent workers. When 1, runs sequentially.
        label: Name for progress messages (e.g. "prospects").
        show_progress: Whether to print progress to stderr.

    Returns:
        List of ``(success, result_or_exception)`` tuples in input order.
        ``success`` is True when *fn* returned normally, False when it raised.
    """
    if not items:
        return []

    total = len(items)
    results: list[tuple[bool, Any]] = [None] * total  # type: ignore[list-item]
    completed_count = 0
    lock = threading.Lock()

    def _report(idx: int) -> None:
        nonlocal completed_count
        completed_count += 1
        if show_progress:
            import click
            click.echo(
                f"  {completed_count}/{total} {label} processed",
                err=True,
            )

    # Sequential fast-path: no thread overhead
    if max_workers <= 1:
        for i, item in enumerate(items):
            try:
                result = fn(item)
                results[i] = (True, result)
            except Exception as exc:
                results[i] = (False, exc)
            _report(i)
        return results

    # Parallel execution
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_idx = {
            pool.submit(fn, item): i for i, item in enumerate(items)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                result = future.result()
                results[idx] = (True, result)
            except Exception as exc:
                results[idx] = (False, exc)
            with lock:
                _report(idx)

    return results
