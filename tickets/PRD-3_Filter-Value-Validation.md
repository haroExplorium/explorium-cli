# PRD: Client-Side Filter Value Validation for Prospect Search

**Author:** Claude (generated from pipeline analysis)
**Date:** 2026-03-10
**Status:** Draft
**Component:** `explorium-cli` — `prospects search`, `commands/prospects.py`, `parallel_search.py`
**Severity:** High — causes full batch failure of all company searches with no actionable error message

---

## 1. Problem Statement

The `prospects search` command accepts comma-separated filter values for `--department`, `--job-level`, `--job-title`, and similar fields. These values are split on commas, lowercased, and passed directly to the API without any client-side validation. When a value doesn't match the API's allowed enum, the API rejects the entire request with a verbose validation error.

In the observed pipeline run, using `--department "Engineering,Information Technology"` caused all 21 company searches to fail. The value `"Information Technology"` is not in the API's enum — the correct value is `"it"`. The CLI did not catch this before making 21 API calls, each of which returned the same error:

```json
{"loc": ["body", "filters", "job_department", "values", 1],
 "msg": "value is not a valid enumeration member; permitted: 'administration', 'real estate', 'healthcare', ..."}
```

The error message lists all valid values, but only in the raw API response buried in stderr. The user sees 21 cross-marked failures with the full JSON error blob repeated for each company, then `Total prospects found: 0`.

### Impact

- 21 wasted API calls (one per company) that all fail identically.
- ~30 seconds of wall-clock time waiting for failures.
- The valid enum values are listed in the error but are hard to extract from the verbose JSON error format.
- The user has to guess the correct value (e.g., "Information Technology" → "it"), re-run, and wait again.
- The `--department` and `--job-level` flags have no help text listing valid values, so the user has no way to know valid values upfront.

---

## 2. Root Cause Analysis

### Current Code Path (`explorium_cli/commands/prospects.py`, lines 367–395)

The `search` subcommand constructs filters as a dict of `{field: {"type": "includes", "values": [...]}}` entries:

```python
# Lines 370-373
if job_level:
    filters["job_level"] = {"type": "includes", "values": job_level.split(",")}
if department:
    filters["job_department"] = {"type": "includes", "values": department.split(",")}
```

No validation occurs at this point. The raw strings are split on commas, trimmed, and passed through.

### Parallel Search Amplification (`parallel_search.py`, lines 54–78)

When `--max-per-company` is used (which it was in the pipeline), the CLI fans out one API call per company via `parallel_prospect_search()`. Each call includes the same invalid filter. This means the validation error is repeated N times (once per company), multiplying both the wasted API calls and the stderr noise.

Even without `--max-per-company`, a single search call with invalid filters fails — but the single-company case at least fails only once.

### Available Enum Values

The API's error response reveals the complete enum for `job_department`:

```
administration, real estate, healthcare, partnerships, c-suite, design,
human resources, engineering, education, strategy, product, sales, r&d,
retail, customer success, security, public service, creative, it, support,
marketing, trade, legal, operations, procurement, data, manufacturing,
logistics, finance
```

And for `job_level` (from the API documentation and autocomplete):

```
cxo, vp, director, manager, senior, entry, training, owner, partner, unpaid
```

These enums are stable — they change infrequently and are part of the API contract.

### No `--help` Guidance

The Click option definitions for `--department` and `--job-level` provide no indication of valid values:

```python
@click.option("--department", help="Filter by department")
@click.option("--job-level", help="Filter by job level")
```

Compare with `--country`, which at least suggests the format ("ISO 2-letter country code").

---

## 3. Proposed Solution

### 3.1 Client-Side Enum Validation with Fuzzy Matching

**Location:** `explorium_cli/commands/prospects.py`, `search` subcommand, between argument parsing and filter construction (line ~367).

**Behavior:** Define the known enum values as constants. Before constructing filters, validate each user-provided value against the enum. If a value doesn't match exactly, attempt fuzzy matching and suggest the closest valid value.

**Implementation:**

```python
# explorium_cli/constants.py (new file or added to existing)

VALID_DEPARTMENTS = {
    "administration", "real estate", "healthcare", "partnerships", "c-suite",
    "design", "human resources", "engineering", "education", "strategy",
    "product", "sales", "r&d", "retail", "customer success", "security",
    "public service", "creative", "it", "support", "marketing", "trade",
    "legal", "operations", "procurement", "data", "manufacturing",
    "logistics", "finance"
}

VALID_JOB_LEVELS = {
    "cxo", "vp", "director", "manager", "senior", "entry",
    "training", "owner", "partner", "unpaid"
}

# Common aliases that users are likely to type
DEPARTMENT_ALIASES = {
    "information technology": "it",
    "info tech": "it",
    "tech": "it",
    "technology": "it",
    "hr": "human resources",
    "cs": "customer success",
    "eng": "engineering",
    "mktg": "marketing",
    "ops": "operations",
    "mfg": "manufacturing",
    "research": "r&d",
    "research and development": "r&d",
    "dev": "engineering",
    "devops": "engineering",
    "infra": "it",
    "infrastructure": "it",
    "swe": "engineering",
    "software engineering": "engineering",
    "executive": "c-suite",
    "management": "c-suite",
    "supply chain": "logistics",
}

JOB_LEVEL_ALIASES = {
    "c-suite": "cxo",
    "c-level": "cxo",
    "chief": "cxo",
    "executive": "cxo",
    "vice president": "vp",
    "vice-president": "vp",
    "dir": "director",
    "mgr": "manager",
    "sr": "senior",
    "junior": "entry",
    "intern": "training",
    "founder": "owner",
}
```

**Validation function:**

```python
# explorium_cli/validation.py (new file)

def validate_filter_values(values: list[str], valid_set: set, aliases: dict, field_name: str) -> list[str]:
    """
    Validate filter values against known enums.
    Returns corrected values list.
    Raises click.UsageError if any value is unresolvable.
    """
    resolved = []
    for v in values:
        v_lower = v.strip().lower()

        # Exact match
        if v_lower in valid_set:
            resolved.append(v_lower)
            continue

        # Alias match
        if v_lower in aliases:
            corrected = aliases[v_lower]
            click.echo(f'Info: Mapped "{v}" → "{corrected}" for --{field_name}', err=True)
            resolved.append(corrected)
            continue

        # Fuzzy match (substring)
        substring_matches = [valid for valid in valid_set if v_lower in valid or valid in v_lower]
        if len(substring_matches) == 1:
            corrected = substring_matches[0]
            click.echo(f'Info: Mapped "{v}" → "{corrected}" for --{field_name}', err=True)
            resolved.append(corrected)
            continue

        # No match — fail with helpful error
        suggestions = _get_closest_matches(v_lower, valid_set, n=3)
        suggestion_str = ", ".join(f'"{s}"' for s in suggestions)
        raise click.UsageError(
            f'Invalid --{field_name} value: "{v}"\n'
            f'  Valid values: {", ".join(sorted(valid_set))}\n'
            f'  Did you mean: {suggestion_str}?'
        )

    return resolved


def _get_closest_matches(query: str, candidates: set, n: int = 3) -> list[str]:
    """Return the n closest matches using edit distance."""
    import difflib
    return difflib.get_close_matches(query, candidates, n=n, cutoff=0.4)
```

**Integration in search command:**

```python
# prospects.py, search subcommand, before filter construction

if department:
    dept_values = validate_filter_values(
        department.split(","), VALID_DEPARTMENTS, DEPARTMENT_ALIASES, "department"
    )
    filters["job_department"] = {"type": "includes", "values": dept_values}

if job_level:
    level_values = validate_filter_values(
        job_level.split(","), VALID_JOB_LEVELS, JOB_LEVEL_ALIASES, "job-level"
    )
    filters["job_level"] = {"type": "includes", "values": level_values}
```

### 3.2 Enhanced `--help` Text with Valid Values

**Location:** `explorium_cli/commands/prospects.py`, `search` Click option definitions.

**Changes:**

```python
@click.option(
    "--department",
    help="Filter by department (comma-separated). "
         "Valid: administration, c-suite, creative, customer success, data, "
         "design, education, engineering, finance, healthcare, human resources, "
         "it, legal, logistics, manufacturing, marketing, operations, "
         "partnerships, procurement, product, public service, r&d, "
         "real estate, retail, sales, security, strategy, support, trade"
)
@click.option(
    "--job-level",
    help="Filter by job level (comma-separated). "
         "Valid: cxo, vp, director, manager, senior, entry, training, "
         "owner, partner, unpaid"
)
```

### 3.3 Autocomplete Integration for Discovery

**Location:** `explorium_cli/commands/prospects.py`, shell completion support.

**Behavior:** For shells that support it (bash, zsh, fish), provide tab completion for `--department` and `--job-level` values using Click's `shell_complete` parameter:

```python
from click.shell_completion import CompletionItem

def complete_department(ctx, param, incomplete):
    return [CompletionItem(v) for v in sorted(VALID_DEPARTMENTS) if v.startswith(incomplete.lower())]

def complete_job_level(ctx, param, incomplete):
    return [CompletionItem(v) for v in sorted(VALID_JOB_LEVELS) if v.startswith(incomplete.lower())]

@click.option("--department", shell_complete=complete_department, ...)
@click.option("--job-level", shell_complete=complete_job_level, ...)
```

### 3.4 Case Normalization

**Location:** `explorium_cli/commands/prospects.py`, filter construction.

**Behavior:** Always lowercase filter values before sending to the API. This prevents failures from trivial casing differences like "Engineering" vs "engineering" or "VP" vs "vp".

This is partially handled today (the comma-split values are used as-is from the user's input), but should be explicitly lowered:

```python
values = [v.strip().lower() for v in department.split(",")]
```

---

## 4. User Experience Examples

### Before (Current)

```
$ explorium prospects search --company-name "Acme" --department "Information Technology,Engineering"
  ✗ abc123: API request failed (HTTP unknown): https://api.explorium.ai/v1/prospects
  Reason: [{'loc': ['body', 'filters', 'job_department', 'values', 1], 'msg': "value is not a valid enumeration member; permitted: 'administration', 'real estate', ..."}]
Search complete: 0 prospects from 1 companies
```

### After (Proposed — Alias Match)

```
$ explorium prospects search --company-name "Acme" --department "Information Technology,Engineering"
Info: Mapped "Information Technology" → "it" for --department
  ✓ abc123: 15 found
Search complete: 15 prospects from 1 companies
```

### After (Proposed — Invalid Value, No Close Match)

```
$ explorium prospects search --company-name "Acme" --department "Underwater Basket Weaving"
Error: Invalid --department value: "underwater basket weaving"
  Valid values: administration, c-suite, creative, customer success, data, design, ...
  Did you mean: "education", "creative", "trade"?
```

### After (Proposed — Help Text)

```
$ explorium prospects search --help
  ...
  --department TEXT  Filter by department (comma-separated). Valid: administration,
                    c-suite, creative, customer success, data, design, education,
                    engineering, finance, healthcare, human resources, it, legal,
                    logistics, manufacturing, marketing, operations, partnerships,
                    procurement, product, public service, r&d, real estate, retail,
                    sales, security, strategy, support, trade
  --job-level TEXT   Filter by job level (comma-separated). Valid: cxo, vp, director,
                    manager, senior, entry, training, owner, partner, unpaid
```

---

## 5. Edge Cases and Constraints

| Scenario | Expected Behavior |
|----------|-------------------|
| Exact valid value ("engineering") | Passed through, no message |
| Valid value with wrong case ("Engineering") | Lowercased to "engineering", no message |
| Known alias ("Information Technology") | Mapped to "it" with info message |
| Unknown value with close match ("enginering") | Error with suggestion: "Did you mean: engineering?" |
| Unknown value with no close match ("xyz") | Error listing all valid values |
| Multiple values, one invalid ("engineering,xyz") | Error on "xyz" before any API call |
| Empty value after split ("engineering,,it") | Empty strings filtered out silently |
| API adds new enum value not in local list | Falls through to API validation; user gets API error as today. The constants file should be updated periodically. |
| `--job-title` filter (free text, not enum) | No validation — job titles are not enumerated. Pass through as-is. |
| `--country` filter | Validate against ISO 3166-1 alpha-2 codes (separate concern, same pattern) |

---

## 6. Maintaining the Enum List

The valid values are hardcoded in the CLI. If the API adds or removes enum values, the CLI must be updated. Mitigation strategies:

1. **Periodic sync:** The `explorium config` or a new `explorium update-enums` command fetches valid values from the API's metadata endpoint (if one exists) and updates a local cache file.
2. **Soft validation:** Instead of raising `UsageError` on unknown values, print a warning and proceed. If the API rejects it, the user sees both the warning and the API error. This prevents the CLI from blocking valid new values.
3. **Version pinning:** The constants file includes a `LAST_VERIFIED` date. If more than 90 days old, the CLI prints a reminder to update.

**Recommended approach for v1:** Hard validation with a fallback. If a value doesn't match the local enum or aliases, print a warning but still send it to the API. This way:
- Known bad values get caught with helpful suggestions.
- Unknown values that might be new API additions still get through.

```python
# In validate_filter_values(), instead of raising UsageError:
click.echo(f'Warning: Unknown --{field_name} value: "{v}". Sending to API as-is.', err=True)
click.echo(f'  Known values: {", ".join(sorted(valid_set))}', err=True)
resolved.append(v_lower)
```

---

## 7. Backward Compatibility

- **Exact valid values:** No behavior change.
- **Casing:** Values like "Engineering" that worked before (because the API is case-insensitive) continue to work. Values that were rejected by the API due to casing now get auto-lowered.
- **Aliases:** New behavior — values like "Information Technology" now succeed instead of failing. This is a strict improvement.
- **Invalid values:** New behavior — instead of 21 API failures, the user gets an immediate error with suggestions. This is a strict improvement.
- **Help text:** Additive — no existing behavior changes.
- **Shell completion:** Additive — only activates if user has completion configured.

---

## 8. Testing Requirements

### Unit Tests

1. **`test_validate_exact_match`** — "engineering" → ["engineering"], no output.
2. **`test_validate_case_normalization`** — "Engineering" → ["engineering"], no output.
3. **`test_validate_alias_match`** — "Information Technology" → ["it"], info message.
4. **`test_validate_multiple_values`** — "engineering,it" → ["engineering", "it"].
5. **`test_validate_mixed_valid_and_alias`** — "engineering,Information Technology" → ["engineering", "it"].
6. **`test_validate_unknown_with_suggestion`** — "enginering" → warning + suggestion "engineering".
7. **`test_validate_unknown_no_match`** — "xyz" → warning + list of all valid values.
8. **`test_validate_empty_values_filtered`** — "engineering,,it" → ["engineering", "it"].
9. **`test_validate_job_level_aliases`** — "c-suite" → ["cxo"], "vice president" → ["vp"].
10. **`test_validate_job_level_exact`** — "cxo,vp,director" → ["cxo", "vp", "director"].

### Integration Tests

11. **`test_search_with_alias_succeeds`** — Run `prospects search --department "Information Technology"`. Assert API receives `job_department: {"values": ["it"]}`. Assert results returned.
12. **`test_search_invalid_department_warns`** — Run `prospects search --department "xyz"`. Assert warning printed. Assert API call still made (soft validation).

---

## 9. Implementation Estimate

| Task | Effort |
|------|--------|
| Constants file with enums and aliases | 1 hour |
| Validation function with fuzzy matching | 2 hours |
| Integration in search command | 30 minutes |
| Enhanced help text | 30 minutes |
| Shell completion | 1 hour |
| Case normalization | 15 minutes |
| Unit tests (10 cases) | 3 hours |
| Integration tests (2 cases) | 1.5 hours |
| **Total** | **~10 hours** |

---

## 10. Success Metrics

- Zero API calls wasted on known-invalid filter values.
- Common aliases ("Information Technology" → "it", "HR" → "human resources") resolve automatically.
- Users can discover valid values via `--help` or shell completion without consulting API documentation.
- Unknown values produce an actionable error message with "did you mean?" suggestions within 0 seconds (no API round-trip).
