"""Batching utilities for bulk operations in Explorium CLI."""

import csv
import math
import time
from typing import Any, Callable, TextIO

import click


def normalize_linkedin_url(url: str | None) -> str | None:
    """Prepend https:// if scheme is missing. Handles linkedin.com and www.linkedin.com."""
    if not url:
        return url
    lower = url.lower()
    if lower.startswith("http://") or lower.startswith("https://"):
        return url
    return f"https://{url}"


# Column name aliases: canonical_name -> list of accepted alternatives
# Case-insensitive matching is applied during resolution.

BUSINESS_COLUMN_ALIASES: dict[str, list[str]] = {
    "name": ["company_name", "company", "business_name"],
    "domain": ["website", "url", "company_domain", "company_website", "site"],
    "linkedin_url": ["linkedin", "linkedin_company_url", "company_linkedin"],
}

PROSPECT_COLUMN_ALIASES: dict[str, list[str]] = {
    "first_name": ["firstname", "first"],
    "last_name": ["lastname", "last", "surname"],
    "full_name": ["name", "fullname", "prospect_name"],
    "email": ["email_address", "e-mail", "e_mail"],
    "linkedin": ["linkedin_url", "linkedin_profile"],
    "company_name": ["company", "employer", "organization"],
}


def _resolve_column_mapping(
    fieldnames: list[str],
    aliases: dict[str, list[str]],
) -> dict[str, str]:
    """Build a mapping from CSV column names to canonical field names.

    For each canonical field, checks if any CSV column matches the canonical
    name or one of its aliases (case-insensitive). First match wins.

    Args:
        fieldnames: The CSV header column names.
        aliases: Dict of canonical_name -> [alias1, alias2, ...].

    Returns:
        Dict of {csv_column_name: canonical_field_name} for recognized columns.
    """
    mapping: dict[str, str] = {}
    # Build a lowercase lookup: lower(alias) -> canonical_name
    lookup: dict[str, str] = {}
    for canonical, alt_names in aliases.items():
        for name in [canonical] + alt_names:
            lookup[name.lower()] = canonical

    for col in fieldnames:
        col_lower = col.strip().lower()
        if col_lower in lookup:
            canonical = lookup[col_lower]
            # Only map the first CSV column that matches each canonical name
            if canonical not in mapping.values():
                mapping[col] = canonical

    return mapping


def _validate_recognized_columns(
    fieldnames: list[str],
    aliases: dict[str, list[str]],
    entity_type: str,
) -> dict[str, str]:
    """Resolve column mapping and raise a helpful error if no columns are recognized.

    Args:
        fieldnames: The CSV header column names.
        aliases: Column alias definitions.
        entity_type: "business" or "prospect" (for error messages).

    Returns:
        The resolved column mapping.

    Raises:
        click.UsageError: If no CSV columns match any known field name or alias.
    """
    mapping = _resolve_column_mapping(fieldnames, aliases)

    if not mapping:
        expected_parts = []
        for canonical, alt_names in aliases.items():
            names = ", ".join([canonical] + alt_names)
            expected_parts.append(f"  {canonical} (also: {', '.join(alt_names)})")
        expected_str = "\n".join(expected_parts)

        raise click.UsageError(
            f"No recognized {entity_type} columns found in CSV.\n"
            f"Found columns: {', '.join(fieldnames)}\n"
            f"Expected columns (or aliases):\n{expected_str}"
        )

    return mapping


def _get_mapped_value(row: dict, canonical: str, mapping: dict[str, str]) -> str:
    """Get the stripped value for a canonical field from a CSV row using the column mapping."""
    for csv_col, mapped_canonical in mapping.items():
        if mapped_canonical == canonical:
            return row.get(csv_col, "").strip()
    return ""


def parse_csv_ids(file: TextIO, column_name: str) -> list[str]:
    """
    Parse IDs from a CSV file column.

    Column matching is case-insensitive, so 'prospect_id', 'Prospect_Id',
    and 'PROSPECT_ID' all match when column_name='prospect_id'.

    Args:
        file: File object to read from
        column_name: Name of the column containing IDs

    Returns:
        List of IDs from the specified column

    Raises:
        click.UsageError: If column not found in CSV or no IDs found
    """
    reader = csv.DictReader(file)

    if reader.fieldnames is None:
        raise click.UsageError("CSV file is empty or has no header row")

    # Case-insensitive column lookup
    col_lower_map = {col.strip().lower(): col for col in reader.fieldnames}
    actual_col = col_lower_map.get(column_name.lower())

    if actual_col is None:
        raise click.UsageError(
            f"CSV file must contain a '{column_name}' column. "
            f"Found columns: {', '.join(reader.fieldnames)}"
        )

    ids = [row[actual_col].strip() for row in reader if row.get(actual_col, "").strip()]

    if not ids:
        raise click.UsageError("No IDs found in file")

    return ids


def parse_csv_business_match_params(file: TextIO) -> list[dict]:
    """
    Parse business match parameters from a CSV file.

    Recognized columns (case-insensitive, with aliases):
      name      — also: company_name, company, business_name
      domain    — also: website, url, company_domain, company_website, site
      linkedin_url — also: linkedin, linkedin_company_url, company_linkedin

    Args:
        file: File object to read from

    Returns:
        List of dicts with match parameters for BusinessesAPI.match()

    Raises:
        click.UsageError: If no recognized columns or no valid rows found
    """
    reader = csv.DictReader(file)

    if reader.fieldnames is None:
        raise click.UsageError("CSV file is empty or has no header row")

    mapping = _validate_recognized_columns(
        list(reader.fieldnames), BUSINESS_COLUMN_ALIASES, "business"
    )

    businesses = []
    for row in reader:
        entry: dict[str, Any] = {}

        name_val = _get_mapped_value(row, "name", mapping)
        if name_val:
            entry["name"] = name_val

        domain_val = _get_mapped_value(row, "domain", mapping)
        if domain_val:
            entry["domain"] = domain_val

        linkedin_val = normalize_linkedin_url(_get_mapped_value(row, "linkedin_url", mapping))
        if linkedin_val:
            entry["linkedin_url"] = linkedin_val

        if entry:
            businesses.append(entry)

    if not businesses:
        raise click.UsageError("No valid business match rows found in CSV")

    return businesses


def parse_csv_prospect_match_params(file: TextIO) -> list[dict]:
    """
    Parse prospect match parameters from a CSV file.

    Recognized columns (case-insensitive, with aliases):
      first_name   — also: firstname, first
      last_name    — also: lastname, last, surname
      full_name    — also: name, fullname, prospect_name
      email        — also: email_address, e-mail, e_mail
      linkedin     — also: linkedin_url, linkedin_profile
      company_name — also: company, employer, organization

    Args:
        file: File object to read from

    Returns:
        List of dicts with match parameters for ProspectsAPI.match()

    Raises:
        click.UsageError: If no recognized columns or no valid rows found
    """
    reader = csv.DictReader(file)

    if reader.fieldnames is None:
        raise click.UsageError("CSV file is empty or has no header row")

    mapping = _validate_recognized_columns(
        list(reader.fieldnames), PROSPECT_COLUMN_ALIASES, "prospect"
    )

    prospects = []
    for row in reader:
        entry: dict[str, Any] = {}

        # Build full_name from first_name + last_name or from full_name column
        first_name = _get_mapped_value(row, "first_name", mapping)
        last_name = _get_mapped_value(row, "last_name", mapping)
        full_name = _get_mapped_value(row, "full_name", mapping)

        email_val = _get_mapped_value(row, "email", mapping)
        linkedin_val = normalize_linkedin_url(_get_mapped_value(row, "linkedin", mapping))
        company_val = _get_mapped_value(row, "company_name", mapping)

        # Strip full_name when a strong identifier (linkedin/email) is present
        # but company_name is absent — the API can't use the name without company context.
        has_strong_id = bool(linkedin_val or email_val)
        include_name = company_val or not has_strong_id

        if include_name:
            if full_name:
                entry["full_name"] = full_name
            elif first_name and last_name:
                entry["full_name"] = f"{first_name} {last_name}"
            elif first_name:
                entry["full_name"] = first_name
            elif last_name:
                entry["full_name"] = last_name

        if email_val:
            entry["email"] = email_val

        if linkedin_val:
            entry["linkedin"] = linkedin_val

        if company_val:
            entry["company_name"] = company_val

        if entry:
            has_only_name = (
                "full_name" in entry
                and "email" not in entry
                and "linkedin" not in entry
                and "company_name" not in entry
            )
            if has_only_name:
                click.echo(
                    f"Warning: Skipping '{entry.get('full_name')}' — "
                    f"name requires company_name, email, or linkedin for matching",
                    err=True,
                )
                continue
            prospects.append(entry)

    if not prospects:
        raise click.UsageError("No valid prospect match rows found in CSV")

    return prospects


def _build_match_meta(
    all_matched: list[dict], total_input: int, id_key: str, error_count: int = 0
) -> dict:
    """Build _match_meta dict with match statistics."""
    if id_key:
        found = sum(1 for r in all_matched if r.get(id_key))
        not_found = len(all_matched) - found
    else:
        found, not_found = len(all_matched), 0
    return {
        "total_input": total_input,
        "matched": found,
        "not_found": not_found,
        "errors": error_count,
    }


def batched_match(
    api_method: Callable[..., dict],
    items: list[dict],
    result_key: str,
    id_key: str = "",
    batch_size: int = 50,
    entity_name: str = "records",
    show_progress: bool = True,
    preserve_input: bool = False,
) -> dict:
    """
    Match items in batches, combining results.

    Args:
        api_method: The API match method (e.g., prospects_api.match)
        items: List of dicts with match parameters
        result_key: Key in API response containing match results
                    (e.g., "matched_prospects", "matched_businesses")
        id_key: Key in result rows that holds the entity ID (e.g., "prospect_id").
                When set, _match_meta tracks found vs not-found counts.
        batch_size: Max items per API call (default: 50)
        entity_name: Name for progress messages (e.g., "prospects")
        show_progress: Whether to show progress to stderr
        preserve_input: When True, merge input columns into result rows with input_ prefix.

    Returns:
        Combined response with all matched results and _match_meta statistics.
    """
    total = len(items)
    if total <= batch_size:
        if show_progress:
            click.echo(f"Matching {total} {entity_name}...", err=True)

        last_error = None
        delay = BATCH_RETRY_BASE_DELAY

        for retry_attempt in range(BATCH_RETRY_MAX + 1):
            try:
                result = api_method(items)
                matched = result.get(result_key) or result.get("data", [])
                if not isinstance(matched, list):
                    matched = []
                if preserve_input:
                    for j, match_row in enumerate(matched):
                        if j < len(items):
                            for k, v in items[j].items():
                                match_row[f"input_{k}"] = v
                result["_match_meta"] = _build_match_meta(matched, total, id_key)
                if show_progress:
                    click.echo(
                        click.style(f"  ✓ {len(matched)} matched", fg="green"),
                        err=True,
                    )
                return result

            except Exception as e:
                api_err = _wrap_as_api_error(e)
                last_error = api_err
                if _is_retryable_api_error(e) and retry_attempt < BATCH_RETRY_MAX:
                    if show_progress:
                        click.echo(
                            click.style(
                                f"  ⟳ Batch retry {retry_attempt + 1}/{BATCH_RETRY_MAX} "
                                f"after {api_err.status_code} (waiting {delay:.0f}s)...",
                                fg="yellow",
                            ),
                            err=True,
                        )
                    time.sleep(delay)
                    delay *= BATCH_RETRY_BACKOFF
                    continue
                raise api_err

        raise last_error

    num_batches = math.ceil(total / batch_size)
    all_matched: list[dict] = []
    error_count = 0

    for batch_num in range(num_batches):
        start = batch_num * batch_size
        end = min(start + batch_size, total)
        batch = items[start:end]

        if show_progress:
            click.echo(
                f"Batch {batch_num + 1}/{num_batches}: Matching {len(batch)} {entity_name}...",
                err=True
            )

        last_error = None
        delay = BATCH_RETRY_BASE_DELAY

        for retry_attempt in range(BATCH_RETRY_MAX + 1):
            try:
                result = api_method(batch)
                matched = result.get(result_key) or result.get("data", [])
                if isinstance(matched, list):
                    if preserve_input:
                        for j, match_row in enumerate(matched):
                            if j < len(batch):
                                for k, v in batch[j].items():
                                    match_row[f"input_{k}"] = v
                    all_matched.extend(matched)

                if show_progress:
                    click.echo(
                        click.style(f"  ✓ {len(matched)} matched", fg="green"),
                        err=True
                    )
                last_error = None
                break

            except Exception as e:
                api_err = _wrap_as_api_error(e)
                last_error = api_err
                if _is_retryable_api_error(e) and retry_attempt < BATCH_RETRY_MAX:
                    if show_progress:
                        click.echo(
                            click.style(
                                f"  ⟳ Batch retry {retry_attempt + 1}/{BATCH_RETRY_MAX} "
                                f"after {api_err.status_code} (waiting {delay:.0f}s)...",
                                fg="yellow",
                            ),
                            err=True,
                        )
                    time.sleep(delay)
                    delay *= BATCH_RETRY_BACKOFF
                    continue

                # Non-retryable or retries exhausted
                error_count += len(batch)
                if show_progress:
                    click.echo(
                        click.style(f"  ✗ Error: {api_err.message}", fg="red"),
                        err=True
                    )
                    if all_matched:
                        click.echo(
                            f"Matched {len(all_matched)} {entity_name} before error.",
                            err=True
                        )
                raise click.Abort()

        if last_error is not None:
            error_count += len(batch)
            if show_progress:
                click.echo(
                    click.style(f"  ✗ Error: {last_error.message}", fg="red"),
                    err=True,
                )
                if all_matched:
                    click.echo(
                        f"Matched {len(all_matched)} {entity_name} before error.",
                        err=True,
                    )
            raise click.Abort()

    if show_progress:
        click.echo(f"Matched {len(all_matched)}/{total} {entity_name} total", err=True)

    result_dict = {result_key: all_matched}
    result_dict["_match_meta"] = _build_match_meta(all_matched, total, id_key, error_count)
    return result_dict


BATCH_RETRY_MAX = 3
BATCH_RETRY_BASE_DELAY = 5.0
BATCH_RETRY_BACKOFF = 2.0


RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _is_retryable_api_error(error: Exception) -> bool:
    """Check if an error is retryable at the batch level.

    Handles both APIError (normal path) and raw requests.exceptions.HTTPError
    (in case the HTTP client fails to wrap the exception).
    """
    import requests
    from explorium_cli.api.client import APIError

    if isinstance(error, APIError) and error.status_code in RETRYABLE_STATUS_CODES:
        return True
    if isinstance(error, requests.exceptions.HTTPError):
        if error.response is not None:
            return error.response.status_code in RETRYABLE_STATUS_CODES
    return False


def _wrap_as_api_error(error: Exception) -> Any:
    """Wrap a raw exception as APIError if it isn't one already."""
    import requests
    from explorium_cli.api.client import APIError

    if isinstance(error, APIError):
        return error
    if isinstance(error, requests.exceptions.HTTPError):
        status_code = error.response.status_code if error.response is not None else None
        error_response = None
        try:
            error_response = error.response.json()
        except (ValueError, AttributeError):
            pass
        return APIError(
            f"API request failed: {error}",
            status_code=status_code,
            response=error_response,
        )
    return APIError(f"Unexpected error: {error}")


def batched_enrich(
    api_method: Callable[..., dict],
    ids: list[str],
    batch_size: int = 50,
    entity_name: str = "records",
    show_progress: bool = True,
    id_key: str = "",
    **api_kwargs: Any
) -> dict:
    """
    Enrich IDs in batches, combining results.

    Args:
        api_method: The API method to call (e.g., prospects_api.bulk_enrich)
        ids: List of IDs to enrich
        batch_size: Max IDs per API call (default: 50)
        entity_name: Name for progress messages (e.g., "prospects", "businesses")
        show_progress: Whether to show progress to stderr
        id_key: When set (e.g. "prospect_id"), inject the ID into each result
                record that doesn't already include it. Ensures CSV output
                contains the entity ID column.
        **api_kwargs: Additional keyword args passed to API method

    Returns:
        Combined response with all enriched data from all batches

    Raises:
        click.Abort: If any batch fails after all retries
    """
    total_ids = len(ids)
    num_batches = math.ceil(total_ids / batch_size)

    all_data: list[dict] = []
    successful_count = 0

    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_ids)
        batch_ids = ids[start_idx:end_idx]
        batch_count = len(batch_ids)

        if show_progress:
            if num_batches > 1:
                click.echo(
                    f"Batch {batch_num + 1}/{num_batches}: Enriching {batch_count} {entity_name}...",
                    err=True
                )
            else:
                click.echo(
                    f"Enriching {batch_count} {entity_name}...",
                    err=True
                )

        last_error = None
        delay = BATCH_RETRY_BASE_DELAY

        for retry_attempt in range(BATCH_RETRY_MAX + 1):
            try:
                result = api_method(batch_ids, **api_kwargs)

                # Extract data from response
                if isinstance(result, dict):
                    if "data" in result:
                        data = result["data"]
                        if isinstance(data, list):
                            # Inject entity ID into records that don't have it
                            if id_key and len(data) == len(batch_ids):
                                for j, record in enumerate(data):
                                    if isinstance(record, dict) and id_key not in record:
                                        record[id_key] = batch_ids[j]
                            all_data.extend(data)
                        else:
                            all_data.append(data)
                    else:
                        all_data.append(result)

                successful_count += batch_count

                if show_progress:
                    click.echo(
                        click.style(" done", fg="green"),
                        err=True
                    )
                last_error = None
                break

            except Exception as e:
                api_err = _wrap_as_api_error(e)
                last_error = api_err
                if _is_retryable_api_error(e) and retry_attempt < BATCH_RETRY_MAX:
                    if show_progress:
                        click.echo(
                            click.style(
                                f"  ⟳ Batch retry {retry_attempt + 1}/{BATCH_RETRY_MAX} "
                                f"after {api_err.status_code} (waiting {delay:.0f}s)...",
                                fg="yellow",
                            ),
                            err=True,
                        )
                    time.sleep(delay)
                    delay *= BATCH_RETRY_BACKOFF
                    continue

                # Non-retryable or retries exhausted
                if show_progress:
                    click.echo(
                        click.style(f" ✗ Error: {api_err.message}", fg="red"),
                        err=True
                    )
                    if successful_count > 0:
                        click.echo(
                            f"Enriched {successful_count} {entity_name} before error occurred.",
                            err=True
                        )
                raise click.Abort()

        if last_error is not None:
            if show_progress:
                click.echo(
                    click.style(f" ✗ Error: {last_error.message}", fg="red"),
                    err=True,
                )
                if successful_count > 0:
                    click.echo(
                        f"Enriched {successful_count} {entity_name} before error occurred.",
                        err=True,
                    )
            raise click.Abort()

    if show_progress:
        click.echo(f"Enriched {successful_count} {entity_name} total", err=True)

    # Return combined result in same format as single API call
    return {"status": "success", "data": all_data}
