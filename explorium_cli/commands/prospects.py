"""Prospect commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.prospects import ProspectsAPI
from explorium_cli.utils import get_api, handle_api_call


@click.group()
@click.pass_context
def prospects(ctx: click.Context) -> None:
    """Prospect operations: match, search, enrich, events."""
    pass


@prospects.command()
@click.option("--first-name", help="First name")
@click.option("--last-name", help="Last name")
@click.option("--linkedin", "-l", help="LinkedIn profile URL")
@click.option("--company-name", help="Company name (required with first/last name)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="JSON file with prospects to match"
)
@click.pass_context
def match(
    ctx: click.Context,
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    file
) -> None:
    """Match prospects to get unique prospect IDs."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    if file:
        prospects_to_match = json.load(file)
    elif first_name or last_name or linkedin:
        prospect = {}
        # Combine first_name and last_name into full_name
        if first_name and last_name:
            prospect["full_name"] = f"{first_name} {last_name}"
        elif first_name:
            prospect["full_name"] = first_name
        elif last_name:
            prospect["full_name"] = last_name
        if linkedin:
            prospect["linkedin"] = linkedin
        if company_name:
            prospect["company_name"] = company_name
        prospects_to_match = [prospect]
    else:
        raise click.UsageError(
            "Provide --first-name/--last-name/--linkedin or --file"
        )

    handle_api_call(ctx, prospects_api.match, prospects_to_match)


@prospects.command()
@click.option("--business-id", "-b", help="Business IDs (comma-separated)")
@click.option("--job-level", help="Job levels (comma-separated: cxo,vp,director,manager,senior,entry)")
@click.option("--department", help="Departments (comma-separated)")
@click.option("--job-title", help="Job title keywords")
@click.option("--country", help="Country codes (comma-separated)")
@click.option("--has-email", is_flag=True, help="Only prospects with email")
@click.option("--has-phone", is_flag=True, help="Only prospects with phone")
@click.option("--experience-min", type=int, help="Min total experience (months)")
@click.option("--experience-max", type=int, help="Max total experience (months)")
@click.option("--role-tenure-min", type=int, help="Min current role tenure (months)")
@click.option("--role-tenure-max", type=int, help="Max current role tenure (months)")
@click.option("--page", type=int, default=1, help="Page number")
@click.option("--page-size", type=int, default=100, help="Results per page")
@click.pass_context
def search(
    ctx: click.Context,
    business_id: Optional[str],
    job_level: Optional[str],
    department: Optional[str],
    job_title: Optional[str],
    country: Optional[str],
    has_email: bool,
    has_phone: bool,
    experience_min: Optional[int],
    experience_max: Optional[int],
    role_tenure_min: Optional[int],
    role_tenure_max: Optional[int],
    page: int,
    page_size: int
) -> None:
    """Search and filter prospects."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    filters = {}
    if business_id:
        filters["business_id"] = {"values": business_id.split(",")}
    if job_level:
        filters["job_level"] = {"values": job_level.split(",")}
    if department:
        filters["job_department"] = {"values": department.split(",")}
    if job_title:
        filters["job_title"] = {"values": [job_title], "include_related_job_titles": True}
    if country:
        filters["country_code"] = {"values": country.split(",")}
    if has_email:
        filters["has_email"] = {"value": True}
    if has_phone:
        filters["has_phone_number"] = {"value": True}
    if experience_min is not None:
        filters["experience_min"] = {"value": experience_min}
    if experience_max is not None:
        filters["experience_max"] = {"value": experience_max}
    if role_tenure_min is not None:
        filters["role_tenure_min"] = {"value": role_tenure_min}
    if role_tenure_max is not None:
        filters["role_tenure_max"] = {"value": role_tenure_max}

    handle_api_call(
        ctx,
        prospects_api.search,
        filters,
        size=page_size,
        page=page
    )


# Enrich subgroup
@prospects.group()
@click.pass_context
def enrich(ctx: click.Context) -> None:
    """Prospect enrichment operations."""
    pass


@enrich.command()
@click.option("--id", "-i", "prospect_id", required=True, help="Prospect ID")
@click.pass_context
def contacts(ctx: click.Context, prospect_id: str) -> None:
    """Enrich prospect contact information (email, phone)."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.enrich_contacts, prospect_id)


@enrich.command()
@click.option("--id", "-i", "prospect_id", required=True, help="Prospect ID")
@click.pass_context
def social(ctx: click.Context, prospect_id: str) -> None:
    """Enrich prospect social media profiles."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.enrich_social, prospect_id)


@enrich.command()
@click.option("--id", "-i", "prospect_id", required=True, help="Prospect ID")
@click.pass_context
def profile(ctx: click.Context, prospect_id: str) -> None:
    """Enrich prospect professional profile."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.enrich_profile, prospect_id)


@prospects.command("bulk-enrich")
@click.option("--ids", help="Prospect IDs (comma-separated)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="File with prospect IDs (one per line)"
)
@click.option("--types", help="Enrichment types (comma-separated)")
@click.pass_context
def bulk_enrich(
    ctx: click.Context,
    ids: Optional[str],
    file,
    types: Optional[str]
) -> None:
    """Bulk enrich multiple prospects (up to 50)."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    if file:
        prospect_ids = [line.strip() for line in file if line.strip()]
    elif ids:
        prospect_ids = [id.strip() for id in ids.split(",")]
    else:
        raise click.UsageError("Provide --ids or --file")

    if len(prospect_ids) > 50:
        raise click.UsageError("Maximum 50 prospects per bulk request")

    enrich_types = types.split(",") if types else None
    handle_api_call(ctx, prospects_api.bulk_enrich, prospect_ids, enrich_types)


@prospects.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.pass_context
def autocomplete(ctx: click.Context, query: str) -> None:
    """Get autocomplete suggestions for prospect names."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.autocomplete, query)


@prospects.command()
@click.option("--business-id", "-b", required=True, help="Business IDs (comma-separated)")
@click.option("--group-by", help="Fields to group by (comma-separated)")
@click.pass_context
def statistics(
    ctx: click.Context,
    business_id: str,
    group_by: Optional[str]
) -> None:
    """Get aggregated prospect statistics."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    filters = {"business_ids": business_id.split(",")}
    groups = group_by.split(",") if group_by else None

    handle_api_call(ctx, prospects_api.statistics, filters, groups)


# Events subgroup
@prospects.group()
@click.pass_context
def events(ctx: click.Context) -> None:
    """Prospect event operations."""
    pass


@events.command("list")
@click.option("--ids", required=True, help="Prospect IDs (comma-separated)")
@click.option("--events", "event_types", required=True, help="Event types (comma-separated)")
@click.pass_context
def list_events(
    ctx: click.Context,
    ids: str,
    event_types: str
) -> None:
    """List events for prospects."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    prospect_ids = [id.strip() for id in ids.split(",")]
    types = [t.strip() for t in event_types.split(",")]

    handle_api_call(
        ctx,
        prospects_api.list_events,
        prospect_ids,
        types
    )


@events.command()
@click.option("--ids", required=True, help="Prospect IDs (comma-separated)")
@click.option("--events", "event_types", required=True, help="Event types (comma-separated)")
@click.option("--key", required=True, help="Enrollment key")
@click.pass_context
def enroll(
    ctx: click.Context,
    ids: str,
    event_types: str,
    key: str
) -> None:
    """Enroll prospects for event monitoring."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    prospect_ids = [id.strip() for id in ids.split(",")]
    types = [t.strip() for t in event_types.split(",")]

    handle_api_call(
        ctx,
        prospects_api.enroll_events,
        prospect_ids,
        types,
        key
    )


@events.command()
@click.pass_context
def enrollments(ctx: click.Context) -> None:
    """List event enrollments."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.list_enrollments)
