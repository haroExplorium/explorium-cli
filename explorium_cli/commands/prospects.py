"""Prospect commands for Explorium CLI."""

import json
from typing import Optional

import click

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.api.prospects import ProspectsAPI
from explorium_cli.utils import get_api, handle_api_call, output_options
from explorium_cli.formatters import output, output_error
from explorium_cli.api.client import APIError
from explorium_cli.pagination import paginated_fetch
from explorium_cli.parallel_search import parallel_prospect_search
from explorium_cli.constants import VALID_DEPARTMENTS, VALID_JOB_LEVELS, DEPARTMENT_ALIASES, JOB_LEVEL_ALIASES
from explorium_cli.validation import validate_filter_values
from explorium_cli.batching import parse_csv_ids, parse_csv_ids_with_rows, parse_csv_prospect_match_params, batched_enrich, batched_match, normalize_linkedin_url, read_input_file, merge_enrichment_results
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


def _resolve_enrichment_methods(types_str, prospects_api):
    """Parse comma-separated --types and return list of (label, api_method) pairs."""
    valid = {
        "contacts": ("contacts", prospects_api.bulk_enrich),
        "profile": ("profile", prospects_api.bulk_enrich_profiles),
    }
    requested = [t.strip().lower() for t in types_str.split(",")]

    # "all" expands to contacts + profile
    if "all" in requested:
        requested = ["contacts", "profile"]

    methods = []
    for t in requested:
        if t not in valid:
            raise click.UsageError(
                f"Unknown enrichment type '{t}'. Valid: contacts, profile, all"
            )
        methods.append(valid[t])
    return methods


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
    matches = result.get("matched_prospects") or result.get("data", [])
    if isinstance(matches, list):
        matched = len(matches)
        failed = total_input - matched
        msg = f"Matched: {matched}/{total_input}"
        if failed > 0:
            msg += f", Failed: {failed}"
        click.echo(msg, err=True)


def _print_search_summary(records: list) -> None:
    """Print aggregate search statistics to stderr."""
    total_count = len(records)
    click.echo(f"Summary:", err=True)
    click.echo(f"  Total prospects found: {total_count}", err=True)

    if not records:
        return

    # Country breakdown
    countries: dict = {}
    for r in records:
        c = r.get("country_name") or r.get("country_code") or r.get("country") or "Unknown"
        countries[c] = countries.get(c, 0) + 1
    if countries:
        sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{c} ({n})" for c, n in sorted_countries[:10]]
        if len(sorted_countries) > 10:
            parts.append(f"...+{len(sorted_countries) - 10} more")
        click.echo(f"  Countries: {', '.join(parts)}", err=True)

    # Job level breakdown
    levels: dict = {}
    for r in records:
        lv = r.get("job_level_main") or r.get("job_level") or "Unknown"
        levels[lv] = levels.get(lv, 0) + 1
    if levels:
        sorted_levels = sorted(levels.items(), key=lambda x: x[1], reverse=True)
        parts = [f"{lv} ({n})" for lv, n in sorted_levels]
        click.echo(f"  Job levels: {', '.join(parts)}", err=True)

    # Companies represented
    bids = {r.get("business_id") for r in records if r.get("business_id")}
    if bids:
        click.echo(f"  Companies represented: {len(bids)}", err=True)

    # Email/phone availability
    with_email = sum(1 for r in records if r.get("has_email") or r.get("email"))
    with_phone = sum(1 for r in records if r.get("has_phone_number") or r.get("phone"))
    if total_count > 0:
        email_pct = round(with_email / total_count * 100)
        phone_pct = round(with_phone / total_count * 100)
        click.echo(f"  With email: {with_email} ({email_pct}%)", err=True)
        click.echo(f"  With phone: {with_phone} ({phone_pct}%)", err=True)


class _OrderedGroup(click.Group):
    """A Click group that lists commands in definition order."""

    def list_commands(self, ctx):
        return list(self.commands)


@click.group(cls=_OrderedGroup)
@click.pass_context
def prospects(ctx: click.Context) -> None:
    """Prospect operations: match, search, enrich, events."""
    pass


@prospects.command()
@click.option("--first-name", help="First name")
@click.option("--last-name", help="Last name")
@click.option("--email", "-e", help="Email address")
@click.option("--linkedin", "-l", help="LinkedIn profile URL")
@click.option("--company-name", help="Company name (required with first/last name)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="JSON or CSV file with prospects to match (extra CSV columns are ignored)"
)
@click.option("--summary", is_flag=True, help="Print match statistics to stderr")
@click.option("--ids-only", is_flag=True, help="Output only matched prospect IDs, one per line")
@output_options
@click.pass_context
def match(
    ctx: click.Context,
    first_name: Optional[str],
    last_name: Optional[str],
    email: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str],
    file,
    summary: bool,
    ids_only: bool,
) -> None:
    """Match prospects to get unique prospect IDs.

    Match by email, LinkedIn URL, or full name + company name.
    Accepts a single prospect via flags or a CSV/JSON file for batch matching.
    """
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    if file:
        content, csv_mode = read_input_file(file)
        if csv_mode:
            prospects_to_match = parse_csv_prospect_match_params(content)
        else:
            prospects_to_match = json.load(content)
    elif first_name or last_name or email or linkedin:
        prospect = {}
        # Strip full_name when a strong identifier (linkedin/email) is present
        # but company_name is absent — the API can't use the name without company context.
        has_strong_id = bool(linkedin or email)
        include_name = company_name or not has_strong_id

        if include_name:
            if first_name and last_name:
                prospect["full_name"] = f"{first_name} {last_name}"
            elif first_name:
                prospect["full_name"] = first_name
            elif last_name:
                prospect["full_name"] = last_name
        if email:
            prospect["email"] = email
        if linkedin:
            prospect["linkedin"] = normalize_linkedin_url(linkedin)
        if company_name:
            prospect["company_name"] = company_name
        if prospect and list(prospect.keys()) == ["full_name"]:
            raise click.UsageError(
                "Cannot match by name alone. Also provide --company-name, --email, or --linkedin."
            )
        prospects_to_match = [prospect]
    else:
        raise click.UsageError(
            "Provide --first-name/--last-name/--email/--linkedin or --file"
        )

    try:
        result = batched_match(
            prospects_api.match,
            prospects_to_match,
            result_key="matched_prospects",
            id_key="prospect_id",
            entity_name="prospects",
            preserve_input=True,
            max_workers=ctx.obj.get("threads", 5),
        )
    except APIError as e:
        output_error(e.message, e.response)
        raise click.Abort()

    if summary and result:
        _print_match_summary(result, len(prospects_to_match))

    result.pop("_match_meta", None)

    if ids_only:
        records = result.get("matched_prospects") or result.get("data", [])
        if isinstance(records, list):
            for record in records:
                pid = record.get("prospect_id", "")
                if pid:
                    click.echo(pid)
    else:
        output_data = result
        if ctx.obj["output"] in ("csv", "table"):
            records = result.get("matched_prospects") or result.get("data", [])
            if isinstance(records, list):
                output_data = records
        output(output_data, ctx.obj["output"], file_path=ctx.obj.get("output_file"))


@prospects.command()
@click.option("--business-id", "-b", help="Business IDs (comma-separated)")
@click.option("--company-name", help="Company names to search (comma-separated, auto-resolves to business IDs)")
@click.option(
    "--file", "-f",
    type=click.File("r"),
    help="CSV file with 'business_id' column (other columns are ignored)"
)
@click.option("--job-level", help="Job levels (comma-separated). Valid: cxo, vp, director, manager, senior, entry, training, owner, partner, unpaid, president, advisor, freelancer, board member, founder, non-managerial, junior, vice president, senior manager")
@click.option("--department", help="Departments (comma-separated). Valid: administration, c-suite, creative, customer success, data, design, education, engineering, finance, healthcare, human resources, it, legal, logistics, manufacturing, marketing, operations, partnerships, procurement, product, public service, r&d, real estate, retail, sales, security, strategy, support, trade")
@click.option("--job-title", help="Job title keywords (includes related titles)")
@click.option("--country", help="Prospect country codes, comma-separated (ISO Alpha-2, e.g. US,GB)")
@click.option("--region", help="Prospect region codes, comma-separated (ISO 3166-2, e.g. us-ca,us-tx)")
@click.option("--city", help="Prospect city locations, comma-separated (e.g. 'New York, NY, US')")
@click.option("--has-email", is_flag=True, help="Only prospects with email")
@click.option("--has-phone", is_flag=True, help="Only prospects with phone")
@click.option("--has-website", is_flag=True, default=None, help="Only prospects with website")
@click.option("--experience-min", type=int, help="Min total experience (months)")
@click.option("--experience-max", type=int, help="Max total experience (months)")
@click.option("--role-tenure-min", type=int, help="Min current role tenure (months)")
@click.option("--role-tenure-max", type=int, help="Max current role tenure (months)")
@click.option("--company-size", "comp_size", help="Company size ranges, comma-separated (1-10,11-50,51-200,201-500,501-1000,1001-5000,5001-10000,10001+)")
@click.option("--company-revenue", "comp_revenue", help="Company revenue ranges, comma-separated (0-500K,500K-1M,...,10B-100B)")
@click.option("--company-country", help="Company HQ country codes, comma-separated (ISO Alpha-2)")
@click.option("--company-region", help="Company HQ region codes, comma-separated (ISO 3166-2)")
@click.option("--industry", help="LinkedIn industry categories, comma-separated")
@click.option("--google-category", help="Google business categories, comma-separated")
@click.option("--naics", help="NAICS industry codes, comma-separated (e.g. 23,5611)")
@click.option("--max-per-company", type=int, help="Max prospects per company (searches each company in parallel)")
@click.option("--total", type=int, help="Total records to collect (auto-paginate)")
@click.option("--page", type=int, default=1, help="Page number (ignored if --total)")
@click.option("--page-size", type=int, default=100, help="Results per page")
@click.option("--summary", is_flag=True, help="Print aggregate statistics to stderr")
@output_options
@click.pass_context
def search(
    ctx: click.Context,
    business_id: Optional[str],
    company_name: Optional[str],
    file,
    job_level: Optional[str],
    department: Optional[str],
    job_title: Optional[str],
    country: Optional[str],
    region: Optional[str],
    city: Optional[str],
    has_email: bool,
    has_phone: bool,
    has_website: Optional[bool],
    experience_min: Optional[int],
    experience_max: Optional[int],
    role_tenure_min: Optional[int],
    role_tenure_max: Optional[int],
    comp_size: Optional[str],
    comp_revenue: Optional[str],
    company_country: Optional[str],
    company_region: Optional[str],
    industry: Optional[str],
    google_category: Optional[str],
    naics: Optional[str],
    max_per_company: Optional[int],
    total: Optional[int],
    page: int,
    page_size: int,
    summary: bool,
) -> None:
    """Search and filter prospects."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    # Get business IDs from file, --business-id, or --company-name
    business_ids = []
    if file:
        business_ids = parse_csv_ids(file, column_name="business_id")
    elif business_id:
        business_ids = business_id.split(",")
    elif company_name:
        # Resolve company names to business IDs via match (concurrent)
        from explorium_cli.concurrency import concurrent_map
        businesses_api = BusinessesAPI(api)
        names = [n.strip() for n in company_name.split(",")]
        click.echo(f"Resolving {len(names)} company name(s) to business IDs...", err=True)
        max_workers = ctx.obj.get("threads", 5)

        def _resolve_name(name: str) -> tuple[str, str | None]:
            result = businesses_api.match([{"name": name}])
            matched = result.get("matched_businesses") or result.get("data", [])
            if isinstance(matched, list):
                for m in matched:
                    bid = m.get("business_id")
                    if bid:
                        return (name, bid)
            return (name, None)

        results = concurrent_map(
            _resolve_name, names,
            max_workers=max_workers, label="companies", show_progress=False,
        )
        for success, result_or_exc in results:
            if success:
                name, bid = result_or_exc
                if bid:
                    business_ids.append(bid)
                    click.echo(f"  ✓ '{name}' → {bid}", err=True)
                else:
                    click.echo(
                        f"  ✗ No match for '{name}'. Try: explorium businesses autocomplete --query \"{name}\"",
                        err=True,
                    )
            else:
                click.echo(f"  ✗ Error: {result_or_exc}", err=True)
        if not business_ids:
            raise click.UsageError(
                f"No businesses found matching the given name(s). "
                f"Try 'explorium businesses autocomplete --query \"...\"' to find similar names."
            )

    # Validate: only one category filter allowed
    category_count = sum(1 for v in [industry, google_category, naics] if v)
    if category_count > 1:
        raise click.UsageError(
            "Only one category filter allowed per request: --industry, --google-category, or --naics"
        )

    filters = {}
    if business_ids:
        filters["business_id"] = {"type": "includes", "values": business_ids}
    if job_level:
        level_values = validate_filter_values(
            job_level.split(","), VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level"
        )
        filters["job_level"] = {"type": "includes", "values": level_values}
    if department:
        dept_values = validate_filter_values(
            department.split(","), VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
        )
        filters["job_department"] = {"type": "includes", "values": dept_values}
    if job_title:
        filters["job_title"] = {"type": "any_match_phrase", "values": [job_title], "include_related_job_titles": True}
    if country:
        filters["country_code"] = {"type": "includes", "values": country.split(",")}
    if region:
        filters["region_country_code"] = {"type": "includes", "values": region.split(",")}
    if city:
        filters["city_region_country"] = {"type": "includes", "values": city.split(",")}
    if has_email:
        filters["has_email"] = {"type": "exists", "value": True}
    if has_phone:
        filters["has_phone_number"] = {"type": "exists", "value": True}
    if has_website is not None:
        filters["has_website"] = {"type": "exists", "value": True}
    if comp_size:
        filters["company_size"] = {"type": "includes", "values": comp_size.split(",")}
    if comp_revenue:
        filters["company_revenue"] = {"type": "includes", "values": comp_revenue.split(",")}
    if company_country:
        filters["company_country_code"] = {"type": "includes", "values": company_country.split(",")}
    if company_region:
        filters["company_region_country_code"] = {"type": "includes", "values": company_region.split(",")}
    if industry:
        filters["linkedin_category"] = {"type": "includes", "values": industry.split(",")}
    if google_category:
        filters["google_category"] = {"type": "includes", "values": google_category.split(",")}
    if naics:
        filters["naics_category"] = {"type": "includes", "values": naics.split(",")}
    if experience_min is not None or experience_max is not None:
        exp_filter: dict = {"type": "range"}
        if experience_min is not None:
            exp_filter["gte"] = experience_min
        if experience_max is not None:
            exp_filter["lte"] = experience_max
        filters["total_experience_months"] = exp_filter
    if role_tenure_min is not None or role_tenure_max is not None:
        tenure_filter: dict = {"type": "range"}
        if role_tenure_min is not None:
            tenure_filter["gte"] = role_tenure_min
        if role_tenure_max is not None:
            tenure_filter["lte"] = role_tenure_max
        filters["current_role_months"] = tenure_filter

    if max_per_company is not None:
        if not business_ids:
            raise click.UsageError("--max-per-company requires --business-id or --file")
        if max_per_company <= 0:
            raise click.UsageError("--max-per-company must be positive")
        parallel_filters = {k: v for k, v in filters.items() if k != "business_id"}
        try:
            result = parallel_prospect_search(
                prospects_api.search,
                business_ids,
                parallel_filters,
                total=max_per_company,
                page_size=page_size,
                concurrency=ctx.obj.get("threads", 5),
            )
            output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
            if summary:
                _print_search_summary(result.get("data", []))
        except APIError as e:
            output_error(e.message, e.response)
            raise click.Abort()
        except Exception as e:
            output_error(str(e))
            raise click.Abort()
    elif total:
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
            output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
            if summary:
                _print_search_summary(result.get("data", []))
        except APIError as e:
            output_error(e.message, e.response)
            raise click.Abort()
        except Exception as e:
            output_error(str(e))
            raise click.Abort()
    else:
        # Single page mode (existing behavior)
        result = handle_api_call(
            ctx,
            prospects_api.search,
            filters,
            size=page_size,
            page_size=page_size,
            page=page
        )
        if summary and result:
            records = result.get("data", [])
            if isinstance(records, list):
                _print_search_summary(records)


# Enrich subgroup
@prospects.group()
@click.pass_context
def enrich(ctx: click.Context) -> None:
    """Prospect enrichment operations."""
    pass


@enrich.command()
@prospect_match_options
@output_options
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
@output_options
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
@output_options
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
    help="CSV file with 'prospect_id' column (other columns are ignored)"
)
@click.option(
    "--match-file",
    type=click.File("r"),
    help="JSON file with match params (full_name, linkedin, company_name) to resolve IDs"
)
@click.option("--types", help="Enrichment types, comma-separated: contacts, profile, all (e.g. contacts,profile)")
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
    types: Optional[str],
    min_confidence: float,
    summary: bool,
) -> None:
    """Bulk enrich multiple prospects (up to 50).

    Use --types to select enrichment (comma-separated):
      contacts  — emails, phone numbers (default)
      profile   — professional profile, skills, experience
      all       — contacts + social + profiles combined

    Example: --types contacts,profile
    """
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    prospect_ids = []
    file_id_to_input: dict = {}

    if file:
        prospect_ids, file_id_to_input = parse_csv_ids_with_rows(file, column_name="prospect_id")
    elif ids:
        prospect_ids = [id.strip() for id in ids.split(",")]
    elif match_file:
        # Read match params and resolve each to IDs (concurrent)
        from explorium_cli.concurrency import concurrent_map
        match_params_list = json.load(match_file)
        match_failures = []
        total_to_match = len(match_params_list)
        max_workers = ctx.obj.get("threads", 5)

        click.echo(f"Matching {total_to_match} prospects...", err=True)

        def _resolve_one(params: dict) -> str:
            full_name = params.get("full_name", "")
            first_name = None
            last_name = None
            if full_name:
                parts = full_name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else None
            return resolve_prospect_id(
                prospects_api,
                first_name=first_name,
                last_name=last_name,
                linkedin=params.get("linkedin"),
                company_name=params.get("company_name"),
                email=params.get("email"),
                min_confidence=min_confidence,
            )

        results = concurrent_map(
            _resolve_one, match_params_list,
            max_workers=max_workers, label="prospects",
            show_progress=True,
        )
        for i, (success, result_or_exc) in enumerate(results):
            if success:
                prospect_ids.append(result_or_exc)
            else:
                match_failures.append((i, match_params_list[i], str(result_or_exc)))

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

        click.echo(f"Matched: {len(prospect_ids)}/{total_to_match}, Failed: {len(match_failures)}", err=True)

        if not prospect_ids:
            raise click.UsageError("No prospects could be matched")
    else:
        raise click.UsageError("Provide --ids, --file, or --match-file")

    enrich_type_str = types.strip() if types else "contacts"
    methods = _resolve_enrichment_methods(enrich_type_str, prospects_api)

    _mw = ctx.obj.get("threads", 5)
    if len(methods) == 1:
        result = batched_enrich(methods[0][1], prospect_ids, entity_name="prospects", id_key="prospect_id", max_workers=_mw)
    else:
        all_partials = []
        for label, api_method in methods:
            click.echo(f"Enriching {label}...", err=True)
            partial = batched_enrich(api_method, prospect_ids, entity_name="prospects", id_key="prospect_id", max_workers=_mw)
            all_partials.append(partial.get("data", []))
        result = {"status": "success", "data": merge_enrichment_results(all_partials, "prospect_id")}

    # Merge input columns from file if available
    if file_id_to_input:
        enriched_data = result.get("data", [])
        if isinstance(enriched_data, list):
            for row in enriched_data:
                pid = row.get("prospect_id", "")
                if pid in file_id_to_input:
                    for k, v in file_id_to_input[pid].items():
                        row[f"input_{k}"] = v

    output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))

    if summary and not match_file:
        click.echo(f"Enriched: {len(prospect_ids)} prospects", err=True)


@prospects.command("enrich-file")
@click.option(
    "--file", "-f",
    required=True,
    type=click.File("r"),
    help="CSV or JSON file with prospects to match and enrich (extra CSV columns are ignored)"
)
@click.option(
    "--types",
    default="contacts",
    help="Enrichment types, comma-separated: contacts, profile, all (e.g. contacts,profile)"
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
    """Match prospects from a file and enrich in one pass.

    Reads CSV or JSON file with match parameters, resolves each to a
    prospect ID, then bulk-enriches all matched prospects.

    Use --types to select enrichment (comma-separated):
      contacts  — emails, phone numbers (default)
      profile   — professional profile, skills, experience
      all       — contacts + social + profiles combined

    Example: --types contacts,profile
    """
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)

    # Parse file (auto-detect CSV vs JSON)
    content, csv_mode = read_input_file(file)
    if csv_mode:
        match_params_list = parse_csv_prospect_match_params(content)
    else:
        match_params_list = json.load(content)

    # Resolve each to a prospect ID, tracking input params for later merge.
    # If the parsed row already contains a prospect_id, use it directly.
    prospect_ids = []
    id_to_input: dict = {}
    match_failures = []
    rows_to_match = []
    rows_with_id = []

    for i, params in enumerate(match_params_list):
        existing_id = params.get("prospect_id", "").strip() if isinstance(params.get("prospect_id"), str) else ""
        if existing_id:
            prospect_ids.append(existing_id)
            id_to_input[existing_id] = params
            rows_with_id.append(i)
        else:
            rows_to_match.append((i, params))

    if rows_with_id:
        click.echo(f"Using existing prospect_id for {len(rows_with_id)} rows", err=True)

    total_to_match = len(rows_to_match)
    if total_to_match > 0:
        from explorium_cli.concurrency import concurrent_map
        max_workers = ctx.obj.get("threads", 5)
        click.echo(f"Matching {total_to_match} prospects...", err=True)

        def _resolve_one(item: tuple) -> tuple[int, dict, str]:
            i, params = item
            full_name = params.get("full_name", "")
            first_name = None
            last_name = None
            if full_name:
                parts = full_name.split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else None
            resolved_id = resolve_prospect_id(
                prospects_api,
                first_name=first_name or params.get("first_name"),
                last_name=last_name or params.get("last_name"),
                linkedin=params.get("linkedin"),
                company_name=params.get("company_name"),
                email=params.get("email"),
                min_confidence=min_confidence,
            )
            return (i, params, resolved_id)

        results = concurrent_map(
            _resolve_one, rows_to_match,
            max_workers=max_workers, label="prospects",
            show_progress=True,
        )
        for seq, (success, result_or_exc) in enumerate(results):
            if success:
                i, params, resolved_id = result_or_exc
                prospect_ids.append(resolved_id)
                id_to_input[resolved_id] = params
            else:
                i, params = rows_to_match[seq]
                match_failures.append((i, params, str(result_or_exc)))

        if match_failures:
            click.echo(f"Warning: {len(match_failures)} match failures:", err=True)
            for idx, params, error in match_failures[:5]:
                click.echo(f"  {idx}: {params} - {error}", err=True)
            if len(match_failures) > 5:
                click.echo(f"  ... and {len(match_failures) - 5} more", err=True)

    total_input = len(match_params_list)
    matched_count = len(prospect_ids)
    failed_count = len(match_failures)
    click.echo(f"Match phase: {matched_count} matched / {failed_count} not found", err=True)

    # Partition: enrichable (valid IDs) vs unenrichable (failed matches)
    unenrichable_rows = [(params, error) for _, params, error in match_failures]

    if not prospect_ids:
        # No matches at all — output unenrichable rows with input_ columns only
        output_data = []
        for params, _error in unenrichable_rows:
            output_data.append({f"input_{k}": v for k, v in params.items()})
        result = {"status": "success", "data": output_data}
        output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
        if summary:
            click.echo(f"Enrich phase: 0 enriched / 0 failed", err=True)
            click.echo(f"Output: {len(output_data)} total rows (0 enriched + {len(output_data)} match-only)", err=True)
        return

    # Route to correct enrichment method(s)
    methods = _resolve_enrichment_methods(types.strip(), prospects_api)
    _mw = ctx.obj.get("threads", 5)

    if len(methods) == 1:
        result = batched_enrich(methods[0][1], prospect_ids, entity_name="prospects", id_key="prospect_id", max_workers=_mw)
    else:
        all_partials = []
        for label, api_method in methods:
            click.echo(f"Enriching {label}...", err=True)
            partial = batched_enrich(api_method, prospect_ids, entity_name="prospects", id_key="prospect_id", max_workers=_mw)
            all_partials.append(partial.get("data", []))
        result = {"status": "success", "data": merge_enrichment_results(all_partials, "prospect_id")}

    # Merge original input columns into enrichment results
    enriched_data = result.get("data", [])
    if isinstance(enriched_data, list):
        for row in enriched_data:
            pid = row.get("prospect_id", "")
            if pid in id_to_input:
                for k, v in id_to_input[pid].items():
                    row[f"input_{k}"] = v

    # Append unenrichable rows with input_ columns and empty enrichment
    enriched_count = len(enriched_data) if isinstance(enriched_data, list) else 0
    if unenrichable_rows and isinstance(enriched_data, list):
        for params, _error in unenrichable_rows:
            enriched_data.append({f"input_{k}": v for k, v in params.items()})

    output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))

    if summary:
        unenrichable_count = len(unenrichable_rows)
        total_output = enriched_count + unenrichable_count
        click.echo(f"Enrich phase: {enriched_count} enriched / {matched_count - enriched_count} failed", err=True)
        click.echo(f"Output: {total_output} total rows ({enriched_count} enriched + {unenrichable_count} match-only)", err=True)


@prospects.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option(
    "--field",
    type=click.Choice(["name", "job-title", "department"], case_sensitive=False),
    default="name",
    help="Field to autocomplete (default: name)"
)
@output_options
@click.pass_context
def autocomplete(ctx: click.Context, query: str, field: str) -> None:
    """Get autocomplete suggestions for prospect names, job titles, or departments."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    # Map friendly field names to API field names
    field_map = {"name": "prospect_name", "job-title": "job_title", "department": "job_department"}
    api_field = field_map.get(field, "prospect_name")
    handle_api_call(ctx, prospects_api.autocomplete, query, api_field)


@prospects.command()
@click.option("--business-id", "-b", required=True, help="Business IDs (comma-separated)")
@click.option("--group-by", help="Fields to group by (comma-separated)")
@output_options
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
@output_options
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
@output_options
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
@output_options
@click.pass_context
def enrollments(ctx: click.Context) -> None:
    """List event enrollments."""
    api = get_api(ctx)
    prospects_api = ProspectsAPI(api)
    handle_api_call(ctx, prospects_api.list_enrollments)
