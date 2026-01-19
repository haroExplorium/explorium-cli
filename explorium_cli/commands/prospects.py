"""Prospect commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.prospects import ProspectsAPI
from explorium_cli.utils import get_api, handle_api_call
from explorium_cli.formatters import output, output_error
from explorium_cli.pagination import paginated_fetch
from explorium_cli.match_utils import (
    prospect_match_options,
    resolve_prospect_id,
    validate_prospect_match_params,
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
        first_name = suggestion.get("first_name", "")
        last_name = suggestion.get("last_name", "")
        prospect_id = suggestion.get("prospect_id", "N/A")
        click.echo(f"  {i}. {first_name} {last_name} (ID: {prospect_id}, confidence: {confidence:.2f})", err=True)
    raise click.Abort()


def _resolve_prospect_id_with_errors(
    prospects_api: ProspectsAPI,
    prospect_id: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    min_confidence: float
) -> str:
    """Resolve prospect ID with proper error handling."""
    try:
        validate_prospect_match_params(prospect_id, first_name, last_name, linkedin, company_name)
        return resolve_prospect_id(
            prospects_api,
            prospect_id=prospect_id,
            first_name=first_name,
            last_name=last_name,
            linkedin=linkedin,
            company_name=company_name,
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
@click.option("--total", type=int, help="Total records to collect (auto-paginate)")
@click.option("--page", type=int, default=1, help="Page number (ignored if --total)")
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
    total: Optional[int],
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

    if total:
        # Auto-paginate mode
        if total <= 0:
            raise click.UsageError("Total must be positive")
        try:
            result = paginated_fetch(
                prospects_api.search,
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
@prospect_match_options
@click.pass_context
def contacts(
    ctx: click.Context,
    prospect_id: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    min_confidence: float
) -> None:
    """Enrich prospect contact information (email, phone)."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    resolved_id = _resolve_prospect_id_with_errors(
        prospects_api, prospect_id, first_name, last_name, linkedin, company_name, min_confidence
    )
    handle_api_call(ctx, prospects_api.enrich_contacts, resolved_id)


@enrich.command()
@prospect_match_options
@click.pass_context
def social(
    ctx: click.Context,
    prospect_id: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    min_confidence: float
) -> None:
    """Enrich prospect social media profiles."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    resolved_id = _resolve_prospect_id_with_errors(
        prospects_api, prospect_id, first_name, last_name, linkedin, company_name, min_confidence
    )
    handle_api_call(ctx, prospects_api.enrich_social, resolved_id)


@enrich.command()
@prospect_match_options
@click.pass_context
def profile(
    ctx: click.Context,
    prospect_id: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    min_confidence: float
) -> None:
    """Enrich prospect professional profile."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    resolved_id = _resolve_prospect_id_with_errors(
        prospects_api, prospect_id, first_name, last_name, linkedin, company_name, min_confidence
    )
    handle_api_call(ctx, prospects_api.enrich_profile, resolved_id)


@prospects.command("bulk-enrich")
@click.option("--ids", help="Prospect IDs (comma-separated)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="File with prospect IDs (one per line)"
)
@click.option(
    "--match-file",
    type=click.File("r"),
    help="JSON file with match params (full_name, linkedin, company_name) to resolve IDs"
)
@click.option("--types", help="Enrichment types (comma-separated)")
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
    types: Optional[str],
    min_confidence: float
) -> None:
    """Bulk enrich multiple prospects (up to 50)."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    prospect_ids = []

    if file:
        prospect_ids = [line.strip() for line in file if line.strip()]
    elif ids:
        prospect_ids = [id.strip() for id in ids.split(",")]
    elif match_file:
        # Read match params and resolve each to IDs
        match_params_list = json.load(match_file)
        match_failures = []

        for i, params in enumerate(match_params_list):
            try:
                # Extract first_name and last_name from full_name if present
                full_name = params.get("full_name", "")
                first_name = None
                last_name = None
                if full_name:
                    parts = full_name.split(" ", 1)
                    first_name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else None

                resolved_id = resolve_prospect_id(
                    prospects_api,
                    first_name=first_name,
                    last_name=last_name,
                    linkedin=params.get("linkedin"),
                    company_name=params.get("company_name"),
                    min_confidence=min_confidence
                )
                prospect_ids.append(resolved_id)
            except (MatchError, LowConfidenceError) as e:
                match_failures.append((i, params, str(e)))

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

        if not prospect_ids:
            raise click.UsageError("No prospects could be matched")
    else:
        raise click.UsageError("Provide --ids, --file, or --match-file")

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
