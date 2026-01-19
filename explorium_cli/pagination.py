"""Pagination utilities for Explorium CLI."""

import math
from typing import Callable

import click


def paginated_fetch(
    api_method: Callable,
    total: int,
    page_size: int = 100,
    show_progress: bool = True,
    **api_kwargs
) -> dict:
    """
    Fetch multiple pages of results up to total records.

    Args:
        api_method: The API method to call (e.g., businesses_api.search).
        total: Maximum total records to collect.
        page_size: Records per API call (default: 100).
        show_progress: Whether to show progress messages to stderr.
        **api_kwargs: Additional arguments to pass to API method.

    Returns:
        Combined response with all accumulated data and metadata.

    Raises:
        ValueError: If total is not positive.
    """
    if total <= 0:
        raise ValueError("Total must be positive")

    all_results: list = []
    page = 1
    pages_fetched = 0
    max_pages = math.ceil(total / page_size)

    while len(all_results) < total:
        # Adjust size for last page if needed
        remaining = total - len(all_results)
        current_size = min(page_size, remaining)

        if show_progress:
            click.echo(
                f"Fetching page {page}/{max_pages}...",
                err=True,
                nl=False
            )

        try:
            # Make API call
            # Pass size=total for APIs that use it as total cap (like Explorium)
            # Pass page_size for per-page count
            response = api_method(**api_kwargs, size=total, page_size=page_size, page=page)
        except Exception:
            if show_progress:
                click.echo(" x (error)", err=True)
            if all_results:
                click.echo(
                    f"Warning: Collected {len(all_results)} of {total} requested records "
                    f"(API error on page {page})",
                    err=True
                )
            raise

        # Extract data
        data = response.get("data", [])
        if not data:
            if show_progress:
                click.echo(f" ✓ (no more data)", err=True)
            break

        all_results.extend(data)
        pages_fetched += 1

        if show_progress:
            click.echo(f" ✓ ({len(all_results)} records)", err=True)

        # Check if API has more data
        # If we got fewer results than requested, we've reached the end
        if len(data) < current_size:
            break

        page += 1
        if page > max_pages:
            break

    # Trim to exact total requested
    final_results = all_results[:total]
    collected_count = len(final_results)

    if show_progress:
        click.echo(f"Collected {collected_count} records", err=True)

    # Return combined response
    return {
        "status": "success",
        "data": final_results,
        "meta": {
            "total_requested": total,
            "total_collected": collected_count,
            "pages_fetched": pages_fetched
        }
    }
