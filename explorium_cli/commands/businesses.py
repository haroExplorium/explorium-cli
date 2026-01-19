"""Business commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.utils import get_api, handle_api_call
from explorium_cli.formatters import output, output_error
from explorium_cli.pagination import paginated_fetch
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
    help="JSON file with businesses to match"
)
@click.pass_context
def match(
    ctx: click.Context,
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str],
    file
) -> None:
    """Match businesses to get unique business IDs."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    if file:
        businesses_to_match = json.load(file)
    elif name or domain or linkedin:
        businesses_to_match = [{
            "name": name,
            "domain": domain,
            "linkedin_url": linkedin
        }]
    else:
        raise click.UsageError(
            "Provide --name/--domain/--linkedin or --file"
        )

    handle_api_call(ctx, businesses_api.match, businesses_to_match)


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
        filters["country_code"] = {"values": country.split(",")}
    if size:
        filters["company_size"] = {"values": size.split(",")}
    if revenue:
        filters["company_revenue"] = {"values": revenue.split(",")}
    if industry:
        filters["linkedin_category"] = {"values": industry.split(",")}
    if tech:
        filters["company_tech_stack_tech"] = {"values": tech.split(",")}
    if events:
        filters["events"] = {
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
            output(result, ctx.obj["output"])
        except Exception as e:
            output_error(str(e))
            raise click.Abort()
    else:
        # Single page mode (existing behavior)
        handle_api_call(
            ctx,
            businesses_api.search,
            filters,
            size=page_size,
            page=page
        )


@businesses.command()
@business_match_options
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
    help="File with business IDs (one per line)"
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
@click.pass_context
def bulk_enrich(
    ctx: click.Context,
    ids: Optional[str],
    file,
    match_file,
    min_confidence: float
) -> None:
    """Bulk enrich multiple businesses (up to 50)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    business_ids = []

    if file:
        business_ids = [line.strip() for line in file if line.strip()]
    elif ids:
        business_ids = [id.strip() for id in ids.split(",")]
    elif match_file:
        # Read match params and resolve each to IDs
        match_params_list = json.load(match_file)
        match_failures = []

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

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

        if not business_ids:
            raise click.UsageError("No businesses could be matched")
    else:
        raise click.UsageError("Provide --ids, --file, or --match-file")

    if len(business_ids) > 50:
        raise click.UsageError("Maximum 50 businesses per bulk request")

    handle_api_call(ctx, businesses_api.bulk_enrich, business_ids)


@businesses.command()
@business_match_options
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
@click.pass_context
def autocomplete(ctx: click.Context, query: str) -> None:
    """Get autocomplete suggestions for company names."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.autocomplete, query)


# Events subgroup
@businesses.group()
@click.pass_context
def events(ctx: click.Context) -> None:
    """Business event operations."""
    pass


@events.command("list")
@click.option("--ids", required=True, help="Business IDs (comma-separated)")
@click.option("--events", "event_types", required=True, help="Event types (comma-separated)")
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
@click.pass_context
def enrollments(ctx: click.Context) -> None:
    """List event enrollments."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.list_enrollments)
