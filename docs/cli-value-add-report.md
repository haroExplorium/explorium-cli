# Explorium CLI: Value-Add Features Over Raw API

Everything the CLI adds on top of calling the Explorium API directly, ranked from most impactful to least.

---

## Tier 1: Game-Changers (Would require significant custom code to replicate)

### 1. Auto-Batching with Intelligent Retry
**Files:** `batching.py` — `batched_match()`, `batched_enrich()`

The API has strict batch size limits (50 items). The CLI automatically splits any input into 50-item batches and reassembles results. On top of that, it implements exponential backoff retry (3 attempts, 2x multiplier, 5s base) for HTTP 429/5xx and connection errors.

- Users send 500 IDs; CLI sends 10 batches of 50 silently
- Rate limiting (429) triggers automatic wait-and-retry
- Partial failures don't kill the whole operation — successful batches are preserved
- Color-coded progress: green checkmark per batch, yellow for retries, red for failures

### 2. Full Workflow Integration: `enrich-file` (Match + Enrich in One Command)
**Files:** `commands/businesses.py` — `enrich_file()`, `commands/prospects.py` — `enrich_file()`

The API requires two separate operations: first match names/domains to IDs, then enrich those IDs. The CLI's `enrich-file` command chains these automatically:

- Reads CSV/JSON with company names and domains
- Matches each to a business ID (with progress reporting)
- Enriches all matched IDs (batched automatically)
- Merges original input columns back into output (prefixed `input_`)
- Supports `--types firmographics,tech,financial` or `--types all` in one pass
- Detects rows with pre-existing IDs and skips match for those
- Reports match failures without stopping (shows which rows failed and why)

### 3. Auto-Pagination
**Files:** `pagination.py` — `paginated_fetch()`

The API returns one page at a time. The CLI's `--total` flag automatically fetches as many pages as needed to reach the target count:

- `--total 500` fetches 5 pages of 100 transparently
- Shows "Fetching page X/Y..." progress
- Stops early when API has fewer results than requested
- Trims to exact count requested
- Smart page_size clamping to avoid API 422 errors

### 4. Match-Based ID Resolution (Name/Domain/LinkedIn Instead of IDs)
**Files:** `match_utils.py` — `resolve_business_id()`, `resolve_prospect_id()`, `business_match_options`

The API requires opaque business/prospect IDs. The CLI adds `--name`, `--domain`, `--linkedin` to every enrichment and lookalike command:

- `explorium businesses enrich --name "Salesforce"` just works (CLI matches first, then enriches)
- Configurable confidence threshold (`--min-confidence 0.6`)
- Low-confidence matches show top 5 suggestions with scores and suggest `--min-confidence`
- No-match cases show clear error with the params that failed
- Works across all 15+ enrichment commands, lookalike, and events

### 5. Multi-Format Output (JSON / Table / CSV / File)
**Files:** `formatters.py` — `output()`, `output_json()`, `output_table()`, `output_csv()`

The API returns only JSON. The CLI renders results in three formats plus file export:

- **JSON**: Pretty-printed with syntax highlighting (monokai theme in terminal)
- **Table**: Rich tables with column wrapping, truncated long values, bold headers
- **CSV**: Automatic nested data flattening (`{"a": {"b": 1}}` becomes `a.b,1`; lists become `"tag1, tag2"`)
- **File**: `--output-file path` writes clean data (no ANSI codes)
- Format set globally (`-o csv`) or per-command; config file default supported

---

## Tier 2: Major Convenience (Would require moderate custom code)

### 6. Smart CSV Column Aliasing & Auto-Mapping
**Files:** `batching.py` — `_resolve_column_mapping()`, `BUSINESS_COLUMN_ALIASES`, `PROSPECT_COLUMN_ALIASES`

The API requires exact field names. The CLI accepts common variations:

- `company_name`, `company`, `name` all map to the `name` field
- `website`, `url`, `company_domain`, `site` all map to `domain`
- `linkedin_url`, `linkedin`, `company_linkedin` all map to `linkedin_url`
- Prospect columns similarly: `firstname`/`first_name`/`first`, `email`/`email_address`/`e-mail`, etc.
- Case-insensitive matching
- Error message lists all accepted aliases when no columns match

### 7. Parallel Multi-Company Prospect Search
**Files:** `parallel_search.py` — `parallel_prospect_search()`

The API searches one company at a time. The CLI's `--max-per-company` flag searches multiple companies in parallel:

- Fans out one search per business ID with configurable concurrency (default 5 threads)
- Deduplicates prospects that appear under multiple companies
- Per-company progress indicators (checkmark or X with error)
- Aggregated stats: min/max/avg prospects per company, error counts

### 8. Multi-Type Enrichment Merging
**Files:** `batching.py` — `merge_enrichment_results()`

The API returns separate result sets per enrichment type. When `enrich-file --types contacts,profile,social` is used, the CLI:

- Calls each enrichment API separately
- Merges results by entity ID into single rows
- Preserves all fields without overwriting non-null values
- Returns one unified dataset instead of three separate ones

### 9. Input Column Preservation in Enrichment
**Files:** `commands/businesses.py` (bulk_enrich, enrich_file), `commands/prospects.py` (same)

The API returns only enriched fields. The CLI merges original input columns back into enriched output:

- `input_name`, `input_domain`, `input_email` etc. appear alongside enriched data
- Enables CSV round-trips: input CSV in, get enriched CSV out with original columns intact
- Works with both `bulk-enrich` (from CSV with IDs) and `enrich-file` (from CSV with names/domains)

### 10. Summary Statistics & Progress Reporting
**Files:** `commands/businesses.py` — `_print_match_summary()`, `commands/prospects.py` — `_print_search_summary()`

The API returns raw data. The CLI's `--summary` flag provides operational intelligence:

- Match summaries: "Matched: 45/50 | Not found: 3 | Errors: 2"
- Prospect search summaries: country breakdown (top 10), job level distribution, company count, email/phone availability percentages
- All summary output goes to stderr so stdout stays clean for piping

---

## Tier 3: Nice-to-Have (Small but useful touches)

### 11. File Format Auto-Detection (CSV vs JSON)
**Files:** `batching.py` — `read_input_file()`, `is_csv_input()`

Detects input format automatically from file extension or content peek (first non-whitespace char `[`/`{` = JSON, else CSV). Works with stdin piping.

### 12. Stdin Piping Support
**Files:** All commands with `--file` / `-f`

Every file-accepting command works with `-f -` for stdin, enabling shell pipelines:
```
explorium businesses match -f companies.csv -o csv | explorium businesses bulk-enrich -f - -o csv
```

### 13. Helpful Error Messages & Guidance
**Files:** Multiple locations

- Invalid `--industry` value → suggests `explorium businesses autocomplete --query "..."`
- Low confidence match → shows top 5 alternatives with confidence scores
- Missing CSV columns → lists found columns and all accepted aliases
- Name-only prospect match → explains what additional fields are needed

### 14. LinkedIn URL Normalization
**Files:** `batching.py` — `normalize_linkedin_url()`

Automatically prepends `https://` to bare LinkedIn URLs. Applied during CSV parsing and match param building.

### 15. Flexible Enrichment Type Selection
**Files:** `commands/businesses.py` — `_resolve_business_enrichment_methods()`, `commands/prospects.py` — `_resolve_enrichment_methods()`

`--types` accepts comma-separated values (`firmographics,tech,financial`) or `all`. Validates against known types and shows valid options on typo.

### 16. Company Name Resolution for Prospect Search
**Files:** `commands/prospects.py` (search command)

`--company-name "Google"` auto-resolves to a business ID before searching. Shows resolution result ("Google → bus_123") or suggests autocomplete if not found.

### 17. Smart Filter Helper Flags
**Files:** `commands/prospects.py` (search command)

Convenience boolean and range flags that build complex API filter structures:
- `--has-email`, `--has-phone` → `{"type": "exists"}`
- `--experience-min 5 --experience-max 15` → `{"type": "range", ...}`

### 18. Pre-Existing ID Detection in enrich-file
**Files:** `commands/businesses.py`, `commands/prospects.py`

When CSV input already contains `business_id`/`prospect_id` columns, those rows skip the match step entirely. Shows "Using existing business_id for X rows".

### 19. Friendly Field Name Mapping for Autocomplete
**Files:** `commands/businesses.py`, `commands/prospects.py`

`--field name` maps to `company_name`, `--field industry` maps to `linkedin_category`, etc. Users don't need to know API field names.

### 20. Configurable Output Defaults
**Files:** `main.py`, `utils.py` — `output_options`

Global `-o` / `--output-file` can be set once, then overridden per-command. Persistent `default_output` in config file.

---

## Summary

| Tier | # Features | What they provide |
|------|-----------|-------------------|
| **Tier 1** | 5 | Core workflow automation — batching, pagination, ID resolution, output formatting, match+enrich integration |
| **Tier 2** | 5 | Major convenience — column aliasing, parallel search, enrichment merging, column preservation, statistics |
| **Tier 3** | 10 | Polish — format detection, piping, error guidance, URL normalization, filter helpers |

The CLI transforms the Explorium API from a "send JSON, get JSON" interface into a full data workflow tool. The top 5 features alone (auto-batching, enrich-file workflow, pagination, ID resolution, multi-format output) would each require 100+ lines of custom code to replicate.

---

## Detailed Feature Reference Tables

### Feature 1: Auto-Batching with Intelligent Retry

| Aspect | Exact Behavior |
|--------|----------------|
| **Batch size** | 50 items per API call (hardcoded default in `batched_match()` and `batched_enrich()`) |
| **Splitting** | Input of N items → ceil(N/50) sequential API calls, results merged into single list |
| **Retry count** | 3 retries per batch (`BATCH_RETRY_MAX = 3`) |
| **Retry delay** | Starts at 5 seconds, doubles each retry (`BATCH_RETRY_BASE_DELAY = 5.0`, `BATCH_RETRY_BACKOFF = 2.0`) → 5s, 10s, 20s |
| **Retryable HTTP codes** | 429 (rate limit), 500, 502, 503, 504 (`RETRYABLE_STATUS_CODES`) |
| **Retryable exceptions** | `requests.ConnectionError`, `requests.Timeout`, any error with "connection", "timeout", "retries", or "name resolution" in message |
| **Non-retryable** | All 4xx errors except 429 (client errors like 400, 401, 403, 422) |
| **On batch failure** | For `batched_match`: aborts and raises `click.Abort()`, shows how many matched before error. For `batched_enrich`: skips failed batch, continues with remaining batches, reports failed count at end |
| **Progress output** | `✓` green on success, `⟳` yellow on retry (shows status code + wait time), `✗` red on failure. All to stderr |
| **Result merging** | `batched_match`: concatenates `matched_businesses`/`matched_prospects` lists. `batched_enrich`: concatenates `data` lists. Both return single combined dict |
| **ID injection** | `batched_enrich` injects entity ID into result records that don't already have it (when `id_key` set and batch size matches result count) |
| **Where used** | `businesses match`, `businesses bulk-enrich`, `businesses enrich-file`, `prospects match`, `prospects bulk-enrich`, `prospects enrich-file` |

### Feature 2: Full Workflow Integration (enrich-file)

| Aspect | Exact Behavior |
|--------|----------------|
| **Input parsing** | Reads file via `read_input_file()` → auto-detects CSV vs JSON. CSV parsed via `parse_csv_business_match_params()` / `parse_csv_prospect_match_params()`. JSON parsed via `json.load()` |
| **Pre-existing ID detection** | Scans each row for non-empty `business_id`/`prospect_id` column. Those rows skip match entirely. Prints "Using existing business_id for X rows" to stderr |
| **Match phase** | Calls `resolve_business_id()` / `resolve_prospect_id()` per row. Shows "Matching N businesses..." and progress every 10 rows ("X/N processed") |
| **Match failure handling** | Catches `MatchError`, `LowConfidenceError`, generic `Exception` per row. Accumulates failures. Shows first 5 failures with row data + error. Shows "...and N more" if >5 failures. Continues to enrich whatever matched |
| **Enrichment type routing** | `--types` parsed by `_resolve_business_enrichment_methods()` / `_resolve_enrichment_methods()`. Valid business types: firmographics, tech, financial, funding, workforce, traffic, social, ratings, challenges, competitive, strategic, website-changes, webstack, hierarchy, intent, all. Valid prospect types: contacts, profile, all |
| **Single vs multi-type** | Single type: one `batched_enrich()` call. Multiple types: iterates each method, collects partial results, calls `merge_enrichment_results()` to combine by entity ID |
| **Input column merge** | After enrichment, loops through `data` list. For each row with matching entity ID in `id_to_input` dict, adds every original column with `input_` prefix (e.g., `input_name`, `input_domain`) |
| **Output** | Passes merged result to `output()` with format from `ctx.obj["output"]` and optional `ctx.obj["output_file"]` |
| **Summary** | Prints "Matched: X/Y, Failed: Z" to stderr after match phase |
| **Where used** | `businesses enrich-file`, `prospects enrich-file` |

### Feature 3: Auto-Pagination

| Aspect | Exact Behavior |
|--------|----------------|
| **Trigger** | Activated when user passes `--total N` flag on search commands |
| **Page size clamping** | If `page_size > total`, sets `page_size = total` to avoid API 422 error ("size must be >= page_size") |
| **API call pattern** | Calls `api_method(size=total, page_size=page_size, page=N, **filters)`. `size` = total cap for API, `page_size` = per-page count, `page` = incrementing page number |
| **Stop conditions** | 1) `len(all_results) >= total`, 2) API returns empty `data`, 3) API returns fewer results than `current_size` (end of data), 4) `page > max_pages` |
| **Last page adjustment** | `current_size = min(page_size, remaining)` — requests only what's needed on final page |
| **Trimming** | After collection, trims to exactly `total` requested: `final_results = all_results[:total]` |
| **Progress** | Prints "Fetching page X/Y... ✓ (N records)" per page to stderr |
| **Error during pagination** | Re-raises the exception. If partial results collected, prints "Warning: Collected X of Y requested records (API error on page Z)" before raising |
| **Return value** | `{"status": "success", "data": [...], "meta": {"total_requested": N, "total_collected": N, "pages_fetched": N}}` |
| **--total vs --page** | When `--total` is set, the `--page` parameter is ignored — `paginated_fetch` always starts from page 1 |
| **Where used** | `businesses search --total`, `prospects search --total` |

### Feature 4: Match-Based ID Resolution

| Aspect | Exact Behavior |
|--------|----------------|
| **Added CLI options** | `--id`/`-i` (direct ID), `--name`/`-n`, `--domain`/`-d`, `--linkedin`/`-l`, `--min-confidence` (float, default 0.8). Added via `@business_match_options` / `@prospect_match_options` decorators |
| **Shortcut** | If `--id` is provided, returns it directly — no match API call |
| **Match param building** | Builds dict from provided flags: `{"name": ..., "domain": ..., "linkedin_url": normalize_linkedin_url(...)}`. Only includes non-None values |
| **API call** | Calls `api.match([match_params])` — wraps single params dict in a list |
| **Result extraction** | Checks `result.get("matched_businesses")` or `result.get("data", [])` for matches |
| **No match** | Raises `MatchError("No business matches found for: name=X, domain=Y")` — shows which params failed |
| **Low confidence** | If best match `match_confidence < min_confidence`, raises `LowConfidenceError` with all matches as suggestions |
| **Low confidence display** | Shows "Best match confidence (0.50) is below threshold (0.80). Found N potential match(es)." Then lists top 5: "1. Company Name (ID: xxx, confidence: 0.50)". Suggests "--min-confidence to lower threshold" |
| **Validation** | `validate_business_match_params()`: raises `ValueError("Provide --id or match parameters (--name, --domain, --linkedin)")` if all are None |
| **Prospect-specific** | Prospect validation also requires at least one of: `--id`, `--first-name`, `--last-name`, `--linkedin`, `--email` |
| **Commands using this** | `enrich`, `enrich-tech`, `enrich-financial`, `enrich-funding`, `enrich-workforce`, `enrich-traffic`, `enrich-social`, `enrich-ratings`, `enrich-keywords`, `enrich-challenges`, `enrich-competitive`, `enrich-strategic`, `enrich-website-changes`, `enrich-webstack`, `enrich-hierarchy`, `enrich-intent`, `lookalike` — all 17 single-entity commands |

### Feature 5: Multi-Format Output

| Aspect | Exact Behavior |
|--------|----------------|
| **JSON output** | `json.dumps(data, indent=2, default=str)`. If stdout is a TTY: renders with Rich `Syntax` (monokai theme, word_wrap=True). If piped: plain `print()` (no ANSI codes) |
| **Table output** | Creates Rich `Table(header_style="bold cyan")`. Columns from first row's keys, `overflow="fold"`. Complex values (dict/list) serialized to JSON string. Values > 50 chars truncated to 47 + "...". Empty data shows "[dim]No results[/dim]" |
| **CSV output** | Extracts `data` key from API response dicts. Checks first 5 rows for nested structures — if found, flattens all rows. Collects all unique keys across all rows, sorts alphabetically for consistent column order. Uses `csv.DictWriter` with `extrasaction='ignore'`. Remaining complex values (dict/list) become JSON strings. None becomes empty string |
| **Nested dict flattening** | `{"location": {"city": "SF", "state": "CA"}}` → `{"location.city": "SF", "location.state": "CA"}` (dot-separated) |
| **List flattening** | Scalar lists: `["tag1", "tag2"]` → `"tag1, tag2"` (comma-space joined). Dict lists: `[{"a": 1}, {"a": 2}]` → `{"field.0.a": 1, "field.1.a": 2}` (indexed). Mixed lists: serialized to JSON string. Empty lists: `""` |
| **File output** | `--output-file path`: writes to file instead of stdout. Table format falls back to JSON for file output. CSV files written with `newline=""`. Prints "Output written to: path" to stderr |
| **Format selection** | Global `-o`/`--output`/`--format` on root command sets `ctx.obj["output"]`. Per-command `@output_options` decorator adds same flags, overrides global when set. Config file `default_output` used as fallback |
| **Where used** | Every command that returns data — match, search, enrich (all types), bulk-enrich, enrich-file, lookalike, autocomplete, events list/enroll/enrollments, statistics |

### Feature 6: Smart CSV Column Aliasing

| Aspect | Exact Behavior |
|--------|----------------|
| **Business aliases** | `name` ← company_name, company, business_name. `domain` ← website, url, company_domain, company_website, site. `linkedin_url` ← linkedin, linkedin_company_url, company_linkedin |
| **Prospect aliases** | `first_name` ← firstname, first. `last_name` ← lastname, last, surname. `full_name` ← name, fullname, prospect_name. `email` ← email_address, e-mail, e_mail. `linkedin` ← linkedin_url, linkedin_profile. `company_name` ← company, employer, organization |
| **Matching** | Case-insensitive. Strips whitespace from column names. First CSV column matching a canonical name wins (no duplicates per canonical field) |
| **No-match error** | Raises `click.UsageError`: "No recognized business columns found in CSV.\nFound columns: foo, bar\nExpected columns (or aliases):\n  name (also: company_name, company, business_name)\n  domain (also: website, url, ...)" |
| **ID column detection** | Separately checks for `business_id`/`prospect_id` column (case-insensitive). If present and non-empty, included in output dict for skip-match optimization |
| **Where used** | `businesses match -f`, `businesses enrich-file -f`, `prospects match -f`, `prospects enrich-file -f` |

### Feature 7: Parallel Multi-Company Prospect Search

| Aspect | Exact Behavior |
|--------|----------------|
| **Trigger** | `prospects search --max-per-company N --business-id "id1,id2,id3"` or `--file` with business IDs |
| **Concurrency** | Default 5 threads (`ThreadPoolExecutor(max_workers=5)`). Not user-configurable |
| **ID deduplication** | Input business IDs deduplicated preserving order before fan-out |
| **Per-company search** | Each thread calls `paginated_fetch()` (if `total` set) or single-page `api_method()` with `business_id` filter injected per call. Other filters (job_level, department, etc.) shared across all calls |
| **Prospect deduplication** | Global `seen_prospect_ids` set. Prospects appearing under multiple companies are included only once (first occurrence wins) |
| **Progress** | Per company: `✓ bid_123: 15 found` (green) or `✗ bid_456: error message` (red). Shows duplicate removal: "5 duplicates removed". Summary: "Search complete: 45 prospects from 3 companies" |
| **Stats returned** | `_search_meta`: `companies_searched`, `concurrency`, `total_prospects`, `errors`, `min`/`max`/`avg` per company, `per_company` list with individual counts/errors |
| **Error handling** | Per-company errors don't stop other searches. Failed companies counted, error message stored in per_company stats |
| **Where used** | `prospects search --max-per-company` |

### Feature 8: Multi-Type Enrichment Merging

| Aspect | Exact Behavior |
|--------|----------------|
| **Trigger** | `--types firmographics,tech` or `--types all` on `enrich-file` commands |
| **Merge logic** | `merge_enrichment_results(all_partials, id_key)`: iterates through each partial result list. Groups by `entity_id` or `id_key` (e.g., `business_id`). For each entity, combines all key-value pairs from all partials |
| **Conflict resolution** | Non-null, non-empty values overwrite null/empty values. Later partials overwrite earlier ones for the same key |
| **Insertion order** | Preserves insertion order of entity IDs across all partials (first appearance determines position) |
| **Valid business types** | firmographics, tech, financial, funding, workforce, traffic, social, ratings, challenges, competitive, strategic, website-changes, webstack, hierarchy, intent (15 types) |
| **Valid prospect types** | contacts, profile (2 types) |
| **"all" expansion** | Business: all 15 types. Prospect: contacts + profile |
| **Invalid type error** | `click.UsageError("Unknown enrichment type 'xyz'. Valid: firmographics, tech, financial, ..., all")` |
| **Where used** | `businesses enrich-file --types`, `prospects enrich-file --types` |

### Feature 9: Input Column Preservation

| Aspect | Exact Behavior |
|--------|----------------|
| **How it works (bulk-enrich)** | `parse_csv_ids_with_rows()` reads CSV with ID column + all other columns. Returns `(ids_list, {id: row_dict})`. After enrichment, loops through `data` list, for each row finds matching ID in `file_id_to_input`, adds every original column prefixed with `input_` |
| **How it works (enrich-file)** | During match phase, stores `{resolved_id: original_params}` in `id_to_input`. After enrichment, same merge loop applies |
| **Prefix** | All input columns get `input_` prefix: `name` → `input_name`, `domain` → `input_domain`, `email` → `input_email` |
| **Excluded columns** | For bulk-enrich CSV: the ID column itself is excluded from `id_to_row` (avoids `input_business_id` duplication). For enrich-file: all original params included |
| **How it works (match)** | `batched_match(preserve_input=True)`: for each matched row at index j, merges `items[j]` dict with `input_` prefix. Only applied to `businesses match` and `prospects match` commands |
| **Where used** | `businesses bulk-enrich -f`, `businesses enrich-file`, `prospects bulk-enrich -f`, `prospects enrich-file`, `businesses match -f`, `prospects match -f` |

### Feature 10: Summary Statistics & Progress Reporting

| Aspect | Exact Behavior |
|--------|----------------|
| **Match summary (businesses & prospects)** | `--summary` flag. Output: "Matched: 45/50 \| Not found: 3 \| Errors: 2". Uses `_match_meta` dict from `batched_match()`. All to stderr |
| **Search summary (prospects only)** | `--summary` flag on `prospects search`. Computes from result data: Total prospects found, Country breakdown (top 10, sorted by count, shows "+N more" if >10), Job level distribution (all levels with counts), Companies represented (unique `business_id` count), Email availability (count + percentage), Phone availability (count + percentage) |
| **Parallel search summary** | Automatic after `--max-per-company` search. Shows: "Searched: N companies \| Concurrency: 5", "Results: N prospects total \| Per-company: min=X, max=Y, avg=Z \| Errors: N" |
| **Batch progress** | `batched_match`: "Batch 1/10: Matching 50 businesses..." per batch. `batched_enrich`: "Batch 1/10: Enriching 50 businesses..." or "Enriching 50 businesses..." for single batch |
| **Pagination progress** | "Fetching page 1/5... ✓ (100 records)" per page. Final: "Collected 500 records" |
| **enrich-file progress** | "Matching N businesses...", "X/N processed" every 10 rows, match failure warnings, "Matched: X/Y, Failed: Z", "Enriching [type]..." per enrichment type |
| **All output destination** | All progress/summary output goes to stderr (`err=True`), keeping stdout clean for data piping |

### Feature 11: File Format Auto-Detection

| Aspect | Exact Behavior |
|--------|----------------|
| **Extension check** | `.csv` → CSV mode. `.json` → JSON mode. Checked via `getattr(file, "name", "")` |
| **Content peek** | For stdin or unknown extension: reads first non-whitespace character. `[` or `{` → JSON. Anything else → CSV. Seeks back to start after peeking |
| **Wrapper** | `read_input_file()` reads all content into memory, wraps in `io.StringIO` with original filename preserved. Returns `(stringio, is_csv)` tuple |
| **Where used** | `businesses match -f`, `businesses enrich-file -f`, `prospects match -f`, `prospects enrich-file -f` |

### Feature 12: Stdin Piping Support

| Aspect | Exact Behavior |
|--------|----------------|
| **Mechanism** | Click's `type=click.File("r")` handles `-` as stdin automatically |
| **Format detection** | Works with `read_input_file()` content peek since stdin has no extension |
| **Pipeline example** | `explorium businesses match -f companies.csv -o csv 2>/dev/null \| explorium businesses bulk-enrich -f - -o csv` |
| **Where used** | Every command with `-f`/`--file` parameter: `match`, `bulk-enrich`, `enrich-file`, `search -f` (prospects) |

### Feature 13: Helpful Error Messages & Guidance

| Aspect | Exact Behavior |
|--------|----------------|
| **Invalid industry** | Detects "linkedin_category" in API error message or response. Shows: `Error: "X" is not a valid industry category for --industry.` + `Hint: --industry accepts LinkedIn industry categories (e.g., "Software Development", ...)` + `Try: explorium businesses autocomplete --query "X"` |
| **Low confidence match** | Shows confidence score vs threshold, lists up to 5 suggestions with name, ID, and confidence. Suggests `--min-confidence` flag |
| **No match found** | Shows "No business matches found for: name=X, domain=Y" with the exact params that failed |
| **Missing CSV columns** | Shows "No recognized business columns found in CSV.\nFound columns: col1, col2\nExpected columns (or aliases):\n  name (also: company_name, company, ...)" |
| **Name-only prospect match** | Warning to stderr: "Skipping 'John Doe' — name requires company_name, email, or linkedin for matching" |
| **Missing required options** | Click's built-in: "Error: Missing option '--query'" with usage hint |
| **API error display** | Shows `Error: message` in bold red + full response JSON in dim text (to stderr) |
| **Where used** | `businesses search` (industry), all match-based commands (confidence), CSV file commands (columns), `prospects match/enrich-file` (name-only) |

### Feature 14: LinkedIn URL Normalization

| Aspect | Exact Behavior |
|--------|----------------|
| **Logic** | If URL starts with `http://` or `https://` (case-insensitive): return as-is. Otherwise: prepend `https://`. Returns `None` unchanged |
| **Examples** | `linkedin.com/company/foo` → `https://linkedin.com/company/foo`. `www.linkedin.com/in/john` → `https://www.linkedin.com/in/john`. `https://linkedin.com/company/foo` → unchanged |
| **Where applied** | `parse_csv_business_match_params()` on linkedin_url column, `parse_csv_prospect_match_params()` on linkedin column, `resolve_business_id()` on `--linkedin` flag, `resolve_prospect_id()` on `--linkedin` flag, `businesses match --linkedin` in command handler |

### Feature 15: Flexible Enrichment Type Selection

| Aspect | Exact Behavior |
|--------|----------------|
| **Business types (15)** | firmographics → `bulk_enrich`, tech → `bulk_enrich_tech`, financial → `bulk_enrich_financial`, funding → `bulk_enrich_funding`, workforce → `bulk_enrich_workforce`, traffic → `bulk_enrich_traffic`, social → `bulk_enrich_social`, ratings → `bulk_enrich_ratings`, challenges → `bulk_enrich_challenges`, competitive → `bulk_enrich_competitive`, strategic → `bulk_enrich_strategic`, website-changes → `bulk_enrich_website_changes`, webstack → `bulk_enrich_webstack`, hierarchy → `bulk_enrich_hierarchy`, intent → `bulk_enrich_intent` |
| **Prospect types (2)** | contacts → `bulk_enrich`, profile → `bulk_enrich_profiles` |
| **"all"** | Expands to all types for that entity |
| **Default** | `firmographics` (businesses), `contacts` (prospects) |
| **Parsing** | Comma-separated, stripped, lowercased |
| **Error** | `click.UsageError("Unknown enrichment type 'xyz'. Valid: firmographics, tech, ..., all")` |
| **Where used** | `businesses enrich-file --types`, `prospects enrich-file --types` |

### Feature 16: Company Name Resolution for Prospect Search

| Aspect | Exact Behavior |
|--------|----------------|
| **Trigger** | `prospects search --company-name "Google" --company-name "Apple"` (multiple allowed) |
| **Resolution** | For each name: calls `BusinessesAPI.match([{"name": company_name}])`. Extracts `business_id` from first match. Adds to filters |
| **Success output** | `✓ 'Google' → bus_123abc` (green, to stderr) |
| **No match output** | `✗ No match for 'FooCorp'` (red) + `Hint: try 'explorium businesses autocomplete --query "FooCorp"'` |
| **Where used** | `prospects search --company-name` |

### Feature 17: Smart Filter Helper Flags

| Aspect | Exact Behavior |
|--------|----------------|
| **Boolean filters** | `--has-email` → `{"has_email": {"type": "exists"}}`. `--has-phone` → `{"has_phone_number": {"type": "exists"}}` |
| **Range filters** | `--experience-min 5 --experience-max 15` → `{"years_of_experience": {"type": "range", "min": 5, "max": 15}}`. `--role-tenure-min 2 --role-tenure-max 5` → `{"role_tenure": {"type": "range", "min": 2, "max": 5}}`. Only `min` or only `max` also accepted |
| **List filters** | `--country US,GB` → `{"country_code": {"type": "includes", "values": ["US", "GB"]}}`. Same pattern for `--size`, `--revenue`, `--industry`, `--tech`, `--job-level`, `--department`, `--job-title`, `--events` |
| **Where used** | `businesses search`, `prospects search` |

### Feature 18: Pre-Existing ID Detection

| Aspect | Exact Behavior |
|--------|----------------|
| **Detection** | Checks `params.get("business_id", "").strip()` / `params.get("prospect_id", "").strip()` for each parsed row |
| **Behavior** | Non-empty ID: added directly to `business_ids` list, original params stored in `id_to_input`. Row skipped during match phase |
| **Output** | "Using existing business_id for X rows" to stderr |
| **Mixed files** | Files with some rows having IDs and some without are handled correctly — ID rows skip match, non-ID rows go through match |
| **Where used** | `businesses enrich-file`, `prospects enrich-file` |

### Feature 19: Friendly Field Name Mapping for Autocomplete

| Aspect | Exact Behavior |
|--------|----------------|
| **Business autocomplete** | `--field name` → API field `company_name`. `--field industry` → `linkedin_category`. `--field tech` → `company_tech_stack_tech`. Default: `name` |
| **Prospect autocomplete** | `--field name` → `prospect_name`. `--field job-title` → `job_title`. `--field department` → `job_department`. Default: `name` |
| **Validation** | Click `type=click.Choice(["name", "industry", "tech"])` — invalid values rejected before API call |
| **Where used** | `businesses autocomplete --field`, `prospects autocomplete --field` |

### Feature 20: Configurable Output Defaults

| Aspect | Exact Behavior |
|--------|----------------|
| **Global flag** | `explorium -o csv ...` sets `ctx.obj["output"] = "csv"` for all commands in that invocation |
| **Per-command override** | `@output_options` decorator adds `-o`/`--output`/`--format` and `--output-file` to each leaf command. If set, overrides global value in `ctx.obj` before command runs |
| **Config file** | `default_output` key in `~/.explorium/config.yaml`. Used as fallback when neither global nor per-command flag is set |
| **File output** | Global `--output-file path` or per-command `--output-file path`. Writes clean data (no ANSI). Table format falls back to JSON for file output |
| **Where used** | Root `cli` group + every leaf command |
