"""Match resolution utilities for Explorium CLI.

This module provides utilities for resolving business and prospect IDs
from match parameters (name, domain, linkedin, etc.) instead of requiring
explicit IDs.
"""

from typing import Optional

import click

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.api.prospects import ProspectsAPI


class MatchError(Exception):
    """Exception raised when no matches are found."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class LowConfidenceError(Exception):
    """Exception raised when match confidence is below threshold.

    Attributes:
        suggestions: List of match suggestions with their confidence scores.
        min_confidence: The minimum confidence threshold that was not met.
    """

    def __init__(self, suggestions: list, min_confidence: float):
        self.suggestions = suggestions
        self.min_confidence = min_confidence
        self.message = (
            f"Best match confidence ({suggestions[0]['match_confidence']:.2f}) "
            f"is below threshold ({min_confidence:.2f}). "
            f"Found {len(suggestions)} potential match(es)."
        )
        super().__init__(self.message)


def validate_business_match_params(
    business_id: Optional[str],
    name: Optional[str],
    domain: Optional[str],
    linkedin: Optional[str]
) -> None:
    """Validate that either ID or match params are provided.

    Args:
        business_id: The business ID.
        name: Company name.
        domain: Company domain/website.
        linkedin: LinkedIn company URL.

    Raises:
        ValueError: If neither ID nor match parameters are provided.
    """
    if not business_id and not name and not domain and not linkedin:
        raise ValueError(
            "Provide --id or match parameters (--name, --domain, --linkedin)"
        )


def validate_prospect_match_params(
    prospect_id: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    linkedin: Optional[str],
    company_name: Optional[str]
) -> None:
    """Validate that either ID or match params are provided.

    Args:
        prospect_id: The prospect ID.
        first_name: First name.
        last_name: Last name.
        linkedin: LinkedIn profile URL.
        company_name: Company name.

    Raises:
        ValueError: If neither ID nor match parameters are provided.
    """
    if not prospect_id and not first_name and not last_name and not linkedin:
        raise ValueError(
            "Provide --id or match parameters (--first-name, --last-name, --linkedin)"
        )


def resolve_business_id(
    api: BusinessesAPI,
    business_id: Optional[str] = None,
    name: Optional[str] = None,
    domain: Optional[str] = None,
    linkedin: Optional[str] = None,
    min_confidence: float = 0.8
) -> str:
    """Resolve a business ID from match parameters or return direct ID.

    If business_id is provided, returns it directly without calling the match API.
    Otherwise, builds match params and calls the match API to resolve the ID.

    Args:
        api: The BusinessesAPI instance.
        business_id: Direct business ID (if known).
        name: Company name for matching.
        domain: Company domain/website for matching.
        linkedin: LinkedIn company URL for matching.
        min_confidence: Minimum confidence threshold (default: 0.8).

    Returns:
        The resolved business ID.

    Raises:
        MatchError: If no matches are found.
        LowConfidenceError: If the best match confidence is below threshold.
    """
    # If ID provided, return it directly
    if business_id:
        return business_id

    # Build match params
    match_params = {}
    if name:
        match_params["name"] = name
    if domain:
        match_params["domain"] = domain
    if linkedin:
        match_params["linkedin_url"] = linkedin

    # Call match API
    result = api.match([match_params])

    # Check for matches - API returns "matched_businesses" or "data"
    matches = result.get("matched_businesses") or result.get("data", [])
    if not matches:
        params_str = ", ".join(f"{k}={v}" for k, v in match_params.items())
        raise MatchError(f"No business matches found for: {params_str}")

    # Get best match
    best_match = matches[0]

    # Check confidence if provided (API may not return it for all matches)
    confidence = best_match.get("match_confidence")
    if confidence is not None and confidence < min_confidence:
        raise LowConfidenceError(matches, min_confidence)

    return best_match["business_id"]


def resolve_prospect_id(
    api: ProspectsAPI,
    prospect_id: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    linkedin: Optional[str] = None,
    company_name: Optional[str] = None,
    min_confidence: float = 0.8
) -> str:
    """Resolve a prospect ID from match parameters or return direct ID.

    If prospect_id is provided, returns it directly without calling the match API.
    Otherwise, builds match params and calls the match API to resolve the ID.

    Args:
        api: The ProspectsAPI instance.
        prospect_id: Direct prospect ID (if known).
        first_name: First name for matching.
        last_name: Last name for matching.
        linkedin: LinkedIn profile URL for matching.
        company_name: Company name for matching.
        min_confidence: Minimum confidence threshold (default: 0.8).

    Returns:
        The resolved prospect ID.

    Raises:
        MatchError: If no matches are found.
        LowConfidenceError: If the best match confidence is below threshold.
    """
    # If ID provided, return it directly
    if prospect_id:
        return prospect_id

    # Build match params
    match_params = {}
    has_strong_id = bool(linkedin)
    include_name = company_name or not has_strong_id

    if include_name:
        if first_name and last_name:
            match_params["full_name"] = f"{first_name} {last_name}"
        elif first_name:
            match_params["full_name"] = first_name
        elif last_name:
            match_params["full_name"] = last_name

    if linkedin:
        match_params["linkedin"] = linkedin
    if company_name:
        match_params["company_name"] = company_name

    # Call match API
    result = api.match([match_params])

    # Check for matches - API returns "matched_prospects" or "data"
    matches = result.get("matched_prospects") or result.get("data", [])
    if not matches:
        params_str = ", ".join(f"{k}={v}" for k, v in match_params.items())
        raise MatchError(f"No prospect matches found for: {params_str}")

    # Get best match
    best_match = matches[0]

    # Check confidence if provided (API may not return it for all matches)
    confidence = best_match.get("match_confidence")
    if confidence is not None and confidence < min_confidence:
        raise LowConfidenceError(matches, min_confidence)

    return best_match["prospect_id"]


def business_match_options(f):
    """Click decorator that adds business match options to a command.

    Adds the following options:
    - --id / -i: Direct business ID
    - --name / -n: Company name for matching
    - --domain / -d: Company domain/website for matching
    - --linkedin / -l: LinkedIn company URL for matching
    - --min-confidence: Minimum confidence threshold (default: 0.8)
    """
    f = click.option(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum match confidence (0-1, default: 0.8)"
    )(f)
    f = click.option(
        "--linkedin", "-l",
        help="LinkedIn company URL (for matching)"
    )(f)
    f = click.option(
        "--domain", "-d",
        help="Company domain/website (for matching)"
    )(f)
    f = click.option(
        "--name", "-n",
        help="Company name (for matching)"
    )(f)
    f = click.option(
        "--id", "-i", "business_id",
        help="Business ID (skip matching if provided)"
    )(f)
    return f


def prospect_match_options(f):
    """Click decorator that adds prospect match options to a command.

    Adds the following options:
    - --id / -i: Direct prospect ID
    - --first-name: First name for matching
    - --last-name: Last name for matching
    - --linkedin / -l: LinkedIn profile URL for matching
    - --company-name: Company name for matching
    - --min-confidence: Minimum confidence threshold (default: 0.8)
    """
    f = click.option(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum match confidence (0-1, default: 0.8)"
    )(f)
    f = click.option(
        "--company-name",
        help="Company name (for matching)"
    )(f)
    f = click.option(
        "--linkedin", "-l",
        help="LinkedIn profile URL (for matching)"
    )(f)
    f = click.option(
        "--last-name",
        help="Last name (for matching)"
    )(f)
    f = click.option(
        "--first-name",
        help="First name (for matching)"
    )(f)
    f = click.option(
        "--id", "-i", "prospect_id",
        help="Prospect ID (skip matching if provided)"
    )(f)
    return f
