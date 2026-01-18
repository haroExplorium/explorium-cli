"""Business commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.utils import get_api, handle_api_call


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
@click.option("--page", type=int, default=1, help="Page number")
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

    handle_api_call(
        ctx,
        businesses_api.search,
        filters,
        size=page_size,
        page=page
    )


@businesses.command()
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with firmographics data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich, business_id)


@businesses.command("enrich-tech")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_tech(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with technographics data (tech stack)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_technographics, business_id)


@businesses.command("enrich-financial")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_financial(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with financial metrics data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_financial, business_id)


@businesses.command("enrich-funding")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_funding(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with funding and acquisition data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_funding, business_id)


@businesses.command("enrich-workforce")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_workforce(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with workforce trends data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_workforce, business_id)


@businesses.command("enrich-traffic")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_traffic(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with website traffic data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_traffic, business_id)


@businesses.command("enrich-social")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_social(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with social media (LinkedIn posts) data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_social, business_id)


@businesses.command("enrich-ratings")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_ratings(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with employee ratings data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_ratings, business_id)


@businesses.command("enrich-keywords")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.option("--keywords", "-k", required=True, help="Keywords to search (comma-separated)")
@click.pass_context
def enrich_keywords(ctx: click.Context, business_id: str, keywords: str) -> None:
    """Search for keywords on a company's website."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    keywords_list = [k.strip() for k in keywords.split(",")]
    handle_api_call(ctx, businesses_api.enrich_keywords, business_id, keywords_list)


@businesses.command("enrich-challenges")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_challenges(ctx: click.Context, business_id: str) -> None:
    """Enrich a public company with business challenges (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_challenges, business_id)


@businesses.command("enrich-competitive")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_competitive(ctx: click.Context, business_id: str) -> None:
    """Enrich a public company with competitive landscape (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_competitive, business_id)


@businesses.command("enrich-strategic")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_strategic(ctx: click.Context, business_id: str) -> None:
    """Enrich a public company with strategic insights (from 10-K filings)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_strategic, business_id)


@businesses.command("enrich-website-changes")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_website_changes(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with website changes data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_website_changes, business_id)


@businesses.command("enrich-webstack")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_webstack(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with webstack data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_webstack, business_id)


@businesses.command("enrich-hierarchy")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_hierarchy(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with company hierarchy data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_hierarchy, business_id)


@businesses.command("enrich-intent")
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def enrich_intent(ctx: click.Context, business_id: str) -> None:
    """Enrich a single business with Bombora intent data."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.enrich_intent, business_id)


@businesses.command("bulk-enrich")
@click.option("--ids", help="Business IDs (comma-separated)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="File with business IDs (one per line)"
)
@click.pass_context
def bulk_enrich(ctx: click.Context, ids: Optional[str], file) -> None:
    """Bulk enrich multiple businesses (up to 50)."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)

    if file:
        business_ids = [line.strip() for line in file if line.strip()]
    elif ids:
        business_ids = [id.strip() for id in ids.split(",")]
    else:
        raise click.UsageError("Provide --ids or --file")

    if len(business_ids) > 50:
        raise click.UsageError("Maximum 50 businesses per bulk request")

    handle_api_call(ctx, businesses_api.bulk_enrich, business_ids)


@businesses.command()
@click.option("--id", "-i", "business_id", required=True, help="Business ID")
@click.pass_context
def lookalike(ctx: click.Context, business_id: str) -> None:
    """Find similar companies."""
    api = get_api(ctx)
    businesses_api = BusinessesAPI(api)
    handle_api_call(ctx, businesses_api.lookalike, business_id)


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
