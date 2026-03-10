"""Client-side validation for API filter values."""

import difflib

import click


def validate_filter_values(
    values: list[str],
    valid_set: set,
    aliases: dict,
    field_name: str,
) -> list[str]:
    """Validate filter values against known enums with fuzzy matching.

    Returns corrected values list. Unknown values are warned about but
    still included (soft validation) to support new API values.
    """
    resolved = []
    for v in values:
        v_stripped = v.strip()
        if not v_stripped:
            continue  # skip empty values

        v_lower = v_stripped.lower()

        # Exact match
        if v_lower in valid_set:
            resolved.append(v_lower)
            continue

        # Alias match
        if v_lower in aliases:
            corrected = aliases[v_lower]
            click.echo(f'Info: Mapped "{v_stripped}" → "{corrected}" for --{field_name}', err=True)
            resolved.append(corrected)
            continue

        # Fuzzy match (substring)
        substring_matches = [valid for valid in valid_set if v_lower in valid or valid in v_lower]
        if len(substring_matches) == 1:
            corrected = substring_matches[0]
            click.echo(f'Info: Mapped "{v_stripped}" → "{corrected}" for --{field_name}', err=True)
            resolved.append(corrected)
            continue

        # No match — soft validation: warn but still send
        suggestions = _get_closest_matches(v_lower, valid_set, n=3)
        click.echo(f'Warning: Unknown --{field_name} value: "{v_stripped}". Sending to API as-is.', err=True)
        if suggestions:
            suggestion_str = ", ".join(f'"{s}"' for s in suggestions)
            click.echo(f"  Did you mean: {suggestion_str}?", err=True)
        click.echo(f"  Known values: {', '.join(sorted(valid_set))}", err=True)
        resolved.append(v_lower)

    return resolved


def _get_closest_matches(query: str, candidates: set, n: int = 3) -> list[str]:
    """Return the n closest matches using edit distance."""
    return difflib.get_close_matches(query, candidates, n=n, cutoff=0.4)
