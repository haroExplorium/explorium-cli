"""Business commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.utils import get_api, handle_api_call, output_options
from explorium_cli.formatters import output, output_error
from explorium_cli.api.client import APIError
from explorium_cli.pagination import paginated_fetch
from explorium_cli.batching import parse_csv_ids_with_rows, parse_csv_business_match_params, batched_enrich, batched_match, normalize_linkedin_url, read_input_file, merge_enrichment_results
from explorium_cli.match_utils import (
    business_match_options,
    resolve_business_id,
    validate_business_match_params,
    MatchError,
    LowConfidenceError,
)


def _handle_match_error(error: MatchError) -> None:
    """Handle match errors with user-friendly output."""
    output_error(error.message)
    raise click.Abort()


def _handle_low_confidence_error(error: LowConfidenceError) -> None:
    """Handle low confidence errors with suggestions."""
    output_error(error.message)
    click.echo("\nSuggestions (try --min-confidence to lower threshold):", err=True)
    for i, suggestion in enumerate(error.suggestions[:5], 1):
        confidence = suggestion.get("match_confidence", 0)
        name = suggestion.get("name", "Unknown")
        business_id = suggestion.get("business_id", "N/A")
        click.echo(f"  {i}. {name} (ID: {business_id}, confidence: {confidence:.2f})", err=True)
    raise click.Abort()


def _resolve_business_id_with_errors(
    businesses_api: BusinessesAPI,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> str:
    """Resolve business ID with proper error handling."""
    try:
        validate_business_match_params(business_id, name, domain, linkedin)
        return resolve_business_id(
            businesses_api,
            business_id=business_id,
            name=name,
            domain=domain,
            linkedin=linkedin,
            min_confidence=min_confidence
        )
    except ValueError as e:
        raise click.UsageError(str(e))
    except MatchError as e:
        _handle_match_error(e)
        raise  # Never reached, but makes type checker happy
    except LowConfidenceError as e:
        _handle_low_confidence_error(e)
        raise  # Never reached, but makes type checker happy


def _print_match_summary(result: dict, total_input: int) -> None:
    """Print match statistics to stderr."""
    meta = result.get("_match_meta")
    if meta:
        parts = [f"Matched: {meta['matched']}/{meta['total_input']}"]
        if meta["not_found"]:
            parts.append(f"Not found: {meta['not_found']}")
        if meta["errors"]:
            parts.append(f"Errors: {meta['errors']}")
        click.echo(" | ".join(parts), err=True)
        return
    # Fallback for backward compat
    matches = result.get("matched_businesses") or result.get("data", [])
    if isinstance(matches, list):
        matched = len(matches)
        failed = total_input - matched
        msg = f"Matched: {matched}/{total_input}"
        if failed > 0:
            msg += f", Failed: {failed}"
        click.echo(msg, err=True)


def _handle_search_error(error: APIError, industry_value: Optional[str] = None) -> None:
    """Handle search API errors with user-friendly messages."""
    msg = error.message or ""
    detail = error.response or {}

    # Check for linkedin_category validation error (invalid --industry value)
    is_industry_error = "linkedin_category" in msg
    if not is_industry_error and isinstance(detail, dict):
        detail_str = str(detail)
        is_industry_error = "linkedin_category" in detail_str

    if is_industry_error and industry_value:
        click.echo(
            f'Error: "{industry_value}" is not a valid industry category for --industry.',
            err=True,
        )
        click.echo("", err=True)
        click.echo(
            'Hint: --industry accepts LinkedIn industry categories (e.g., "Software Development",',
            err=True,
        )
        click.echo(
            '  "Financial Services", "Hospitals and Health Care").',
            err=True,
        )
        click.echo(
            f'  Try: explorium businesses autocomplete --query "{industry_value}"',
            err=True,
        )
    else:
        output_error(msg, detail if isinstance(detail, dict) else None)


@click.group()
@click.pass_context
def businesses(ctx: click.Context) -> None:
    """Business operations: match, search, enrich, events."""
    pass


@businesses.command()
@click.option("--name", "-n", help="Company name")
@click.option("--domain", "-d", help="Company domain/website")
@click.option("--linkedin", "-l", help="LinkedIn company URL")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="JSON or CSV file with businesses to match (extra CSV columns are ignored)"
)
@click.option("--summary", is_flag=True, help="Print match statistics to stderr")
@click.option("--ids-only", is_flag=True, help="Output only matched business IDs, one per line")
@output_options
@click.pass_context
def match(
    ctx: click.Context,
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    file,
    summary: bool,
    ids_only: bool,
) -> None:
    """Match businesses to get unique business IDs."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    if file:
        content, csv_mode = read_input_file(file)
        if csv_mode:
            businesses_to_match = parse_csv_business_match_params(content)
        else:
            businesses_to_match = json.load(content)
    elif name or domain or linkedin:
        businesses_to_match = [{
            "name": name,
            "domain": domain,
            "linkedin_url": normalize_linkedin_url(linkedin) if linkedin else linkedin
        }]
    else:
        raise click.UsageError(
            "Provide --name/--domain/--linkedin or --file"
        )

    try:
        result = batched_match(
            businesses_api.match,
            businesses_to_match,
            result_key="matched_businesses",
            id_key="business_id",
            entity_name="businesses",
            preserve_input=True,
        )
    except APIError as e:
        output_error(e.message, e.response)
        raise click.Abort()

    if summary and result:
        _print_match_summary(result, len(businesses_to_match))

    result.pop("_match_meta", None)

    output_format = ctx.obj["output"]

    if ids_only:
        records = result.get("matched_businesses") or result.get("data", [])
        if isinstance(records, list):
            for record in records:
                bid = record.get("business_id", "")
                if bid:
                    click.echo(bid)
    else:
        output_data = result
        if output_format in ("csv", "table"):
            records = result.get("matched_businesses") or result.get("data", [])
            if isinstance(records, list):
                output_data = records
        output(output_data, output_format, file_path=ctx.obj.get("output_file"))


@businesses.command()
@click.option("--country", help="Country codes (comma-separated)")
@click.option("--size", help="Company size ranges (comma-separated)")
@click.option("--revenue", help="Revenue ranges (comma-separated)")
@click.option("--industry", help="Industry categories (comma-separated)")
@click.option("--tech", help="Technologies (comma-separated)")
@click.option("--events", help="Event types (comma-separated)")
@click.option("--events-days", type=int, default=45, help="Days for event recency")
@click.option("--total", type=int, help="Total records to collect (auto-paginate)")
@click.option("--page", type=int, default=1, help="Page number (ignored if --total)")
@click.option("--page-size", type=int, default=100, help="Results per page")
@output_options
@click.pass_context
def search(
    ctx: click.Context,
    country: Optional[str],
    size: Optional[str],
    revenue: Optional[str],
    industry: Optional[str],
    tech: Optional[str],
    events: Optional[str],
    events_days: int,
    total: Optional[int],
    page: int,
    page_size: int
) -> None:
    """Search and filter businesses."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    filters = {}
    if country:
        filters["country_code"] = {"type": "includes", "values": country.split(",")}
    if size:
        filters["company_size"] = {"type": "includes", "values": size.split(",")}
    if revenue:
        filters["company_revenue"] = {"type": "includes", "values": revenue.split(",")}
    if industry:
        filters["linkedin_category"] = {"type": "includes", "values": industry.split(",")}
    if tech:
        filters["company_tech_stack_tech"] = {"type": "includes", "values": tech.split(",")}
    if events:
        filters["events"] = {
            "type": "includes",
            "values": events.split(","),
            "last_occurrence": events_days
        }

    if total:
        # Auto-paginate mode
        if total <= 0:
            raise click.UsageError("Total must be positive")
        try:
            result = paginated_fetch(
                businesses_api.search,
                total=total,
                page_size=page_size,
                filters=filters
            )
            output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
        except APIError as e:
            _handle_search_error(e, industry)
            raise click.Abort()
        except Exception as e:
            output_error(str(e))
            raise click.Abort()
    else:
        # Single page mode (existing behavior)
        try:
            result = businesses_api.search(
                filters,
                size=page_size,
                page_size=page_size,
                page=page
            )
            output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
        except APIError as e:
            _handle_search_error(e, industry)
            raise click.Abort()


@businesses.command()
@business_match_options
@output_options
@click.pass_context
def enrich(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with firmographics data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich, resolved_id)


@businesses.command("enrich-tech")
@business_match_options
@output_options
@click.pass_context
def enrich_tech(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with technographics data (tech stack)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_technographics, resolved_id)


@businesses.command("enrich-financial")
@business_match_options
@output_options
@click.pass_context
def enrich_financial(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with financial metrics data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_financial, resolved_id)


@businesses.command("enrich-funding")
@business_match_options
@output_options
@click.pass_context
def enrich_funding(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with funding and acquisition data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_funding, resolved_id)


@businesses.command("enrich-workforce")
@business_match_options
@output_options
@click.pass_context
def enrich_workforce(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with workforce trends data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_workforce, resolved_id)


@businesses.command("enrich-traffic")
@business_match_options
@output_options
@click.pass_context
def enrich_traffic(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with website traffic data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_traffic, resolved_id)


@businesses.command("enrich-social")
@business_match_options
@output_options
@click.pass_context
def enrich_social(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with social media (LinkedIn posts) data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_social, resolved_id)


@businesses.command("enrich-ratings")
@business_match_options
@output_options
@click.pass_context
def enrich_ratings(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with employee ratings data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_ratings, resolved_id)


@businesses.command("enrich-keywords")
@business_match_options
@click.option("--keywords", "-k", required=True, help="Keywords to search (comma-separated)")
@output_options
@click.pass_context
def enrich_keywords(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float,
    keywords: str
) -> None:
    """Search for keywords on a company's website."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    keywords_list = [k.strip() for k in keywords.split(",")]
    handle_api_call(ctx, businesses_api.enrich_keywords, resolved_id, keywords_list)


@businesses.command("enrich-challenges")
@business_match_options
@output_options
@click.pass_context
def enrich_challenges(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a public company with business challenges (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_challenges, resolved_id)


@businesses.command("enrich-competitive")
@business_match_options
@output_options
@click.pass_context
def enrich_competitive(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a public company with competitive landscape (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_competitive, resolved_id)


@businesses.command("enrich-strategic")
@business_match_options
@output_options
@click.pass_context
def enrich_strategic(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a public company with strategic insights (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_strategic, resolved_id)


@businesses.command("enrich-website-changes")
@business_match_options
@output_options
@click.pass_context
def enrich_website_changes(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with website changes data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_website_changes, resolved_id)


@businesses.command("enrich-webstack")
@business_match_options
@output_options
@click.pass_context
def enrich_webstack(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with webstack data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_webstack, resolved_id)


@businesses.command("enrich-hierarchy")
@business_match_options
@output_options
@click.pass_context
def enrich_hierarchy(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with company hierarchy data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_hierarchy, resolved_id)


@businesses.command("enrich-intent")
@business_match_options
@output_options
@click.pass_context
def enrich_intent(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Enrich a single business with Bombora intent data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.enrich_intent, resolved_id)


@businesses.command("bulk-enrich")
@click.option("--ids", help="Business IDs (comma-separated)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="CSV file with 'business_id' column (other columns are ignored)"
)
@click.option(
    "--match-file",
    type=click.File("r"),
    help="JSON file with match params (name, domain) to resolve IDs"
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.8,
    help="Minimum match confidence (0-1, default: 0.8)"
)
@click.option("--summary", is_flag=True, help="Print match/enrichment statistics to stderr")
@output_options
@click.pass_context
def bulk_enrich(
    ctx: click.Context,
    ids: Optional[str],
    file,
    match_file,
    min_confidence: float,
    summary: bool,
) -> None:
    """Bulk enrich multiple businesses (up to 50)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    business_ids = []
    file_id_to_input: dict = {}

    if file:
        business_ids, file_id_to_input = parse_csv_ids_with_rows(file, column_name="business_id")
    elif ids:
        business_ids = [id.strip() for id in ids.split(",")]
    elif match_file:
        # Read match params and resolve each to IDs
        match_params_list = json.load(match_file)
        match_failures = []
        total_to_match = len(match_params_list)

        click.echo(f"Matching {total_to_match} businesses...", err=True)

        for i, params in enumerate(match_params_list):
            try:
                resolved_id = resolve_business_id(
                    businesses_api,
                    name=params.get("name"),
                    domain=params.get("domain"),
                    linkedin=params.get("linkedin_url"),
                    min_confidence=min_confidence
                )
                business_ids.append(resolved_id)
            except (MatchError, LowConfidenceError) as e:
                match_failures.append((i, params, str(e)))
            except Exception as e:
                match_failures.append((i, params, f"Error: {e}"))

            if (i + 1) % 10 == 0 or (i + 1) == total_to_match:
                click.echo(f"  {i + 1}/{total_to_match} processed", err=True)

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

        click.echo(f"Matched: {len(business_ids)}/{total_to_match}, Failed: {len(match_failures)}", err=True)

        if not business_ids:
            raise click.UsageError("No businesses could be matched")
    else:
        raise click.UsageError("Provide --ids, --file, or --match-file")

    result = batched_enrich(
        businesses_api.bulk_enrich,
        business_ids,
        entity_name="businesses",
        id_key="business_id",
    )

    # Merge input columns from file if available
    if file_id_to_input:
        enriched_data = result.get("data", [])
        if isinstance(enriched_data, list):
            for row in enriched_data:
                bid = row.get("business_id", "")
                if bid in file_id_to_input:
                    for k, v in file_id_to_input[bid].items():
                        row[f"input_{k}"] = v

    output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))

    if summary and not match_file:
        click.echo(f"Enriched: {len(business_ids)} businesses", err=True)


def _resolve_business_enrichment_methods(types_str, businesses_api):
    """Parse comma-separated --types and return list of (label, api_method) pairs."""
    valid = {
        "firmographics": ("firmographics", businesses_api.bulk_enrich),
        "tech": ("tech", businesses_api.bulk_enrich_tech),
        "financial": ("financial", businesses_api.bulk_enrich_financial),
        "funding": ("funding", businesses_api.bulk_enrich_funding),
        "workforce": ("workforce", businesses_api.bulk_enrich_workforce),
        "traffic": ("traffic", businesses_api.bulk_enrich_traffic),
        "social": ("social", businesses_api.bulk_enrich_social),
        "ratings": ("ratings", businesses_api.bulk_enrich_ratings),
        "challenges": ("challenges", businesses_api.bulk_enrich_challenges),
        "competitive": ("competitive", businesses_api.bulk_enrich_competitive),
        "strategic": ("strategic", businesses_api.bulk_enrich_strategic),
        "website-changes": ("website-changes", businesses_api.bulk_enrich_website_changes),
        "webstack": ("webstack", businesses_api.bulk_enrich_webstack),
        "hierarchy": ("hierarchy", businesses_api.bulk_enrich_hierarchy),
        "intent": ("intent", businesses_api.bulk_enrich_intent),
    }
    requested = [t.strip().lower() for t in types_str.split(",")]

    if "all" in requested:
        requested = list(valid.keys())

    methods = []
    for t in requested:
        if t not in valid:
            valid_names = ", ".join(valid.keys())
            raise click.UsageError(
                f"Unknown enrichment type '{t}'. Valid: {valid_names}, all"
            )
        methods.append(valid[t])
    return methods


@businesses.command("enrich-file")
@click.option(
    "--file", "-f",
    required=True,
    type=click.File("r"),
    help="CSV or JSON file with businesses to match and enrich (extra CSV columns are ignored)"
)
@click.option(
    "--types",
    default="firmographics",
    help="Enrichment types, comma-separated: firmographics, tech, financial, funding, workforce, traffic, social, ratings, challenges, competitive, strategic, website-changes, webstack, hierarchy, intent, all"
)
@click.option(
    "--min-confidence",
    type=float,
    default=0.8,
    help="Minimum match confidence (0-1, default: 0.8)"
)
@click.option("--summary", is_flag=True, help="Print match/enrichment statistics to stderr")
@output_options
@click.pass_context
def enrich_file(
    ctx: click.Context,
    file,
    types: str,
    min_confidence: float,
    summary: bool,
) -> None:
    """Match businesses from a file and enrich in one pass.

    Reads CSV or JSON file with match parameters, resolves each to a
    business ID, then enriches all matched businesses.

    Use --types to select enrichment (comma-separated):
      firmographics, tech, financial, funding, workforce, traffic,
      social, ratings, challenges, competitive, strategic,
      website-changes, webstack, hierarchy, intent, all
    """
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    # Parse file (auto-detect CSV vs JSON)
    content, csv_mode = read_input_file(file)
    if csv_mode:
        match_params_list = parse_csv_business_match_params(content)
    else:
        match_params_list = json.load(content)

    # Resolve each to a business ID, tracking input params for later merge.
    # If the parsed row already contains a business_id, use it directly.
    business_ids = []
    id_to_input: dict = {}
    match_failures = []
    rows_to_match = []
    rows_with_id = []

    for i, params in enumerate(match_params_list):
        existing_id = params.get("business_id", "").strip() if isinstance(params.get("business_id"), str) else ""
        if existing_id:
            business_ids.append(existing_id)
            id_to_input[existing_id] = params
            rows_with_id.append(i)
        else:
            rows_to_match.append((i, params))

    if rows_with_id:
        click.echo(f"Using existing business_id for {len(rows_with_id)} rows", err=True)

    total_to_match = len(rows_to_match)
    if total_to_match > 0:
        click.echo(f"Matching {total_to_match} businesses...", err=True)

        for seq, (i, params) in enumerate(rows_to_match):
            try:
                resolved_id = resolve_business_id(
                    businesses_api,
                    name=params.get("name"),
                    domain=params.get("domain"),
                    linkedin=params.get("linkedin_url"),
                    min_confidence=min_confidence
                )
                business_ids.append(resolved_id)
                id_to_input[resolved_id] = params
            except (MatchError, LowConfidenceError) as e:
                match_failures.append((i, params, str(e)))
            except Exception as e:
                match_failures.append((i, params, f"Error: {e}"))

            if (seq + 1) % 10 == 0 or (seq + 1) == total_to_match:
                click.echo(f"  {seq + 1}/{total_to_match} processed", err=True)

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

    total_input = len(match_params_list)
    click.echo(f"Matched: {len(business_ids)}/{total_input}, Failed: {len(match_failures)}", err=True)

    if not business_ids:
        raise click.UsageError("No businesses could be matched from file")

    # Route to correct enrichment method(s)
    methods = _resolve_business_enrichment_methods(types.strip(), businesses_api)

    if len(methods) == 1:
        result = batched_enrich(methods[0][1], business_ids, entity_name="businesses", id_key="business_id")
    else:
        all_partials = []
        for label, api_method in methods:
            click.echo(f"Enriching {label}...", err=True)
            partial = batched_enrich(api_method, business_ids, entity_name="businesses", id_key="business_id")
            all_partials.append(partial.get("data", []))
        result = {"status": "success", "data": merge_enrichment_results(all_partials, "business_id")}

    # Merge original input columns into enrichment results
    enriched_data = result.get("data", [])
    if isinstance(enriched_data, list):
        for row in enriched_data:
            if not isinstance(row, dict):
                continue
            bid = row.get("business_id", "")
            if bid in id_to_input:
                for k, v in id_to_input[bid].items():
                    row[f"input_{k}"] = v

    output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))


@businesses.command()
@business_match_options
@output_options
@click.pass_context
def lookalike(
    ctx: click.Context,
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    min_confidence: float
) -> None:
    """Find similar companies."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    resolved_id = _resolve_business_id_with_errors(
        businesses_api, business_id, name, domain, linkedin, min_confidence
    )
    handle_api_call(ctx, businesses_api.lookalike, resolved_id)


@businesses.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option(
    "--field",
    type=click.Choice(["name", "industry", "tech"], case_sensitive=False),
    default="name",
    help="Field to autocomplete (default: name)"
)
@output_options
@click.pass_context
def autocomplete(ctx: click.Context, query: str, field: str) -> None:
    """Get autocomplete suggestions for company names, industries, or technologies."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    # Map friendly field names to API field names
    field_map = {"name": "company_name", "industry": "linkedin_category", "tech": "company_tech_stack_tech"}
    api_field = field_map.get(field, "company_name")
    handle_api_call(ctx, businesses_api.autocomplete, query, api_field)


# Events subgroup
@businesses.group()
@click.pass_context
def events(ctx: click.Context) -> None:
    """Business event operations."""
    pass


@events.command("list")
@click.option("--ids", required=True, help="Business IDs (comma-separated)")
@click.option("--events", "event_types", required=True, help="Event types (comma-separated)")
@output_options
@click.pass_context
def list_events(
    ctx: click.Context,
    ids: str,
    event_types: str
) -> None:
    """List events for businesses."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    business_ids = [id.strip() for id in ids.split(",")]
    types = [t.strip() for t in event_types.split(",")]

    handle_api_call(
        ctx,
        businesses_api.list_events,
        business_ids,
        types
    )


@events.command()
@click.option("--ids", required=True, help="Business IDs (comma-separated)")
@click.option("--events", "event_types", required=True, help="Event types (comma-separated)")
@click.option("--key", required=True, help="Enrollment key")
@output_options
@click.pass_context
def enroll(
    ctx: click.Context,
    ids: str,
    event_types: str,
    key: str
) -> None:
    """Enroll businesses for event monitoring."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    business_ids = [id.strip() for id in ids.split(",")]
    types = [t.strip() for t in event_types.split(",")]

    handle_api_call(
        ctx,
        businesses_api.enroll_events,
        business_ids,
        types,
        key
    )


@events.command()
@output_options
@click.pass_context
def enrollments(ctx: click.Context) -> None:
    """List event enrollments."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.list_enrollments)
