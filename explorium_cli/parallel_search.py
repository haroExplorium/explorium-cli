"""Parallel fan-out search for multi-business prospect queries."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

import click

from explorium_cli.pagination import paginated_fetch


def parallel_prospect_search(
    api_method: Callable,
    business_ids: list[str],
    filters: dict,
    total: int | None = None,
    page_size: int = 100,
    concurrency: int = 5,
    show_progress: bool = True,
) -> dict:
    """
    Fan out one search per business ID, run in parallel, merge results.

    Args:
        api_method: The ProspectsAPI.search method.
        business_ids: List of business IDs to search across.
        filters: Shared filters (job_level, department, etc.) — must NOT
                 contain the ``business_id`` key; it is injected per-call.
        total: Max prospects per company.  None → single page (page_size).
        page_size: Results per API page.
        concurrency: Max parallel requests.
        show_progress: Print progress to stderr.

    Returns:
        Combined dict with ``data`` (deduplicated prospect list) and
        ``_search_meta`` with per-company stats.
    """
    # Deduplicate IDs, preserving order
    seen: set[str] = set()
    unique_ids: list[str] = []
    for bid in business_ids:
        bid = bid.strip()
        if bid and bid not in seen:
            seen.add(bid)
            unique_ids.append(bid)

    num_companies = len(unique_ids)
    if show_progress:
        click.echo(
            f"Searching {num_companies} companies (concurrency: {concurrency})...",
            err=True,
        )

    # ── worker function ──────────────────────────────────────────────
    def _search_one(bid: str) -> dict:
        """Search prospects for a single business ID. Returns a result dict."""
        per_company_filters = dict(filters)
        per_company_filters["business_id"] = {"values": [bid]}

        try:
            if total:
                result = paginated_fetch(
                    api_method,
                    total=total,
                    page_size=page_size,
                    show_progress=False,
                    filters=per_company_filters,
                )
            else:
                result = api_method(
                    filters=per_company_filters,
                    size=page_size,
                    page_size=page_size,
                    page=1,
                )
            data = result.get("data", [])
            return {"business_id": bid, "data": data, "error": None}
        except Exception as e:
            return {"business_id": bid, "data": [], "error": str(e)}

    # ── fan-out ──────────────────────────────────────────────────────
    all_prospects: list[dict] = []
    seen_prospect_ids: set[str] = set()
    per_company_stats: list[dict] = []
    error_count = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        future_to_bid = {
            pool.submit(_search_one, bid): bid for bid in unique_ids
        }

        for future in as_completed(future_to_bid):
            bid = future_to_bid[future]
            result = future.result()

            if result["error"]:
                error_count += 1
                per_company_stats.append(
                    {"business_id": bid, "count": 0, "error": result["error"]}
                )
                if show_progress:
                    click.echo(
                        click.style(f"  ✗ {bid}: {result['error']}", fg="red"),
                        err=True,
                    )
                continue

            # Deduplicate by prospect_id across companies
            new_rows = []
            for row in result["data"]:
                pid = row.get("prospect_id", "")
                if pid and pid in seen_prospect_ids:
                    continue
                if pid:
                    seen_prospect_ids.add(pid)
                new_rows.append(row)

            returned = len(new_rows)
            found = len(result["data"])
            per_company_stats.append(
                {"business_id": bid, "count": returned, "error": None}
            )
            all_prospects.extend(new_rows)

            if show_progress:
                msg = f"  ✓ {bid}: {found} found"
                if total and found > total:
                    msg += f", returning {total}"
                elif returned < found:
                    msg += f", {found - returned} duplicates removed"
                click.echo(click.style(msg, fg="green"), err=True)

    # ── summary ──────────────────────────────────────────────────────
    total_prospects = len(all_prospects)
    counts = [s["count"] for s in per_company_stats if s["error"] is None]

    meta: dict[str, Any] = {
        "companies_searched": num_companies,
        "concurrency": concurrency,
        "total_prospects": total_prospects,
        "errors": error_count,
        "per_company": per_company_stats,
    }
    if counts:
        meta["min"] = min(counts)
        meta["max"] = max(counts)
        meta["avg"] = round(sum(counts) / len(counts), 1)

    if show_progress:
        click.echo(
            f"Search complete: {total_prospects} prospects from "
            f"{num_companies} companies",
            err=True,
        )

    return {"status": "success", "data": all_prospects, "_search_meta": meta}


def print_search_summary(meta: dict) -> None:
    """Print search summary stats to stderr."""
    parts = [
        f"Searched: {meta['companies_searched']} companies",
        f"Concurrency: {meta['concurrency']}",
    ]
    click.echo(" | ".join(parts), err=True)

    parts2 = [f"Results: {meta['total_prospects']} prospects total"]
    if "min" in meta:
        parts2.append(
            f"Per-company: min={meta['min']}, max={meta['max']}, avg={meta['avg']}"
        )
    if meta["errors"]:
        parts2.append(f"Errors: {meta['errors']}")
    click.echo(" | ".join(parts2), err=True)
