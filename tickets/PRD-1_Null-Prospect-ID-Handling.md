# PRD: Graceful Null Prospect ID Handling in Batch Enrichment

**Author:** Claude (generated from pipeline analysis)
**Date:** 2026-03-10
**Status:** Draft
**Component:** `explorium-cli` — `prospects enrich-file`, `prospects bulk-enrich`, `batching.py`
**Severity:** Critical — causes silent total data loss in production pipelines

---

## 1. Problem Statement

When `prospects enrich-file` matches a batch of prospects, some rows inevitably fail to match (low confidence, ambiguous names, missing identifiers). These unmatched rows carry a `null` value in the `prospect_id` field. The current implementation passes the full list of IDs — including nulls — directly to the bulk enrichment API endpoints (`/prospects/contacts_information/bulk_enrich` and `/prospects/profiles/bulk_enrich`). The API rejects the entire batch if even one null ID is present, returning an HTTP validation error:

```json
[{"loc": ["body", "prospect_ids", 7], "msg": "none is not an allowed value", "type": "type_error.none.not_allowed"}]
```

Because the CLI batches prospects into groups of 50, a single null in a batch causes all 50 records in that batch to fail. In the observed pipeline run, 3 nulls spread across 2 batches caused 100% enrichment failure (0 out of 88 prospects enriched), despite 77 having valid IDs. The command reported `"status": "success", "data": []` — an empty successful result with no warning that valid records were silently dropped.

### Impact

- 77 successfully matched prospects lost all enrichment data.
- The pipeline appeared to succeed (exit code 0, valid JSON output).
- The user had to manually discover the issue, re-run matching separately, filter with Python, and call `bulk-enrich` on the clean subset — adding ~5 minutes of debugging and workaround scripting to every pipeline run.

---

## 2. Root Cause Analysis

### Current Code Path (`explorium_cli/commands/prospects.py`, lines 663–801)

1. `enrich-file` calls `resolve_prospect_id()` for each row. Unmatched rows get `None` as their `prospect_id`.
2. The full list of `(prospect_id, row_data)` pairs is passed to `batched_enrich()`.
3. `batched_enrich()` (`batching.py`, lines 721–852) splits IDs into chunks of 50 and calls `ProspectsAPI.bulk_enrich(batch_ids)`.
4. `bulk_enrich()` (`api/prospects.py`, lines 112–131) sends a POST with `{"prospect_ids": batch_ids}`.
5. The API validates all IDs and rejects the entire request if any ID is `None`.
6. The batch retry logic (`BATCH_RETRY_MAX=3`) retries the same invalid batch 3 times, then marks the batch as failed.
7. The failed batch's data is silently discarded — only a stderr message indicates failure.
8. The final output contains only successfully enriched records (in this case, zero).

### Why CSV Parsing Doesn't Catch This

`parse_csv_ids_with_rows()` (`batching.py`, line 229) does strip empty strings, but this code path is only used when `bulk-enrich` reads a CSV with an existing `prospect_id` column. In the `enrich-file` flow, IDs are resolved in-memory by `resolve_prospect_id()`, which returns `None` on failure — and the downstream code doesn't filter these out before batching.

---

## 3. Proposed Solution

### 3.1 Pre-Enrichment Null Filtering (Primary Fix)

**Location:** `explorium_cli/commands/prospects.py`, `enrich-file` subcommand, between the match loop (line ~764) and the enrichment call (line ~785).

**Behavior:** After the match phase completes, partition the results into two lists:

- `enrichable`: rows where `prospect_id` is not `None` and not empty string
- `unenrichable`: rows where `prospect_id` is `None` or empty

Pass only `enrichable` to `batched_enrich()`. After enrichment, merge the `unenrichable` rows back into the output with empty enrichment fields, preserving the input columns with the `input_` prefix so the user can see which rows failed matching.

**Pseudocode:**

```python
enrichable = [(pid, row) for pid, row in matched if pid]
unenrichable = [(pid, row) for pid, row in matched if not pid]

if unenrichable:
    click.echo(f"Warning: {len(unenrichable)} prospects could not be matched and will be excluded from enrichment.", err=True)

enriched = batched_enrich(enrichable, ...)

# Merge unenrichable rows back with empty enrichment fields
for _, row in unenrichable:
    enriched.append({f"input_{k}": v for k, v in row.items()})
```

### 3.2 Defensive Null Guard in `batched_enrich()` (Safety Net)

**Location:** `explorium_cli/batching.py`, `batched_enrich()`, line ~730 (before batch splitting).

**Behavior:** Filter out any `None` or empty-string IDs before constructing batches, regardless of how the function was called. Log a warning to stderr with the count of filtered IDs.

```python
original_count = len(ids)
ids = [id for id in ids if id and str(id).strip()]
filtered_count = original_count - len(ids)
if filtered_count > 0:
    click.echo(f"Warning: Filtered {filtered_count} null/empty IDs before enrichment.", err=True)
```

This ensures that even if a future caller passes nulls, the batch operation degrades gracefully rather than failing entirely.

### 3.3 Summary Output Enhancement

**Location:** `explorium_cli/commands/prospects.py`, `_print_match_summary()` and enrichment summary output.

**Current:** The summary prints `Matched: X/Y` but the subsequent `Enriched 0 prospects total (88 failed)` is misleading — it implies all 88 failed enrichment, when actually only 11 were unmatched and the rest were collateral damage.

**Proposed:** After enrichment, print a breakdown:

```
Match phase:  77 matched / 11 not found / 12 skipped (insufficient identifiers)
Enrich phase: 77 enriched / 0 failed (contacts: 77, profile: 77)
Output:       88 total rows (77 enriched + 11 match-only)
```

---

## 4. Edge Cases and Constraints

| Scenario | Expected Behavior |
|----------|-------------------|
| All prospects match successfully | No filtering needed; proceeds as today |
| All prospects fail matching | Warning printed; output contains only `input_` columns with no enrichment data |
| Mixed batch (some null, some valid) | Nulls filtered; valid IDs enriched; nulls appear in output with empty enrichment fields |
| `bulk-enrich` called with `--ids` containing empty values | Defensive guard in `batched_enrich()` filters them out |
| `bulk-enrich` called with `--file` CSV containing empty `prospect_id` rows | Existing `parse_csv_ids_with_rows()` already handles this — no change needed |
| Pipeline piping (stdout) | Warnings go to stderr; clean data to stdout; no behavioral change for pipes |

---

## 5. Backward Compatibility

- **Output schema:** Unchanged. The `input_` prefix columns and enrichment columns remain the same. Unenrichable rows simply have empty enrichment fields.
- **Exit code:** Unchanged. Exit 0 on success (even if some rows unenrichable). Exit 1 only on total failure (API down, auth error, etc.).
- **`--summary` flag:** Enhanced with more granular stats. Existing summary consumers that parse "Matched: X/Y" will still see that line.
- **Piped workflows:** No impact. Stderr warnings don't corrupt stdout CSV output.

---

## 6. Testing Requirements

### Unit Tests

1. **`test_batched_enrich_filters_null_ids`** — Pass a list containing `[valid_id, None, valid_id, ""]` to `batched_enrich()`. Assert only 2 IDs are sent to the API. Assert warning printed to stderr.
2. **`test_enrich_file_partial_match`** — Mock `resolve_prospect_id()` to return `None` for 3 of 10 rows. Assert enrichment is called with only 7 IDs. Assert output contains 10 rows (7 enriched + 3 with empty enrichment).
3. **`test_enrich_file_all_unmatched`** — Mock all matches to return `None`. Assert enrichment is never called. Assert output contains only `input_` columns.
4. **`test_enrich_file_all_matched`** — Mock all matches to succeed. Assert no filtering warning. Assert all rows enriched.

### Integration Tests

5. **End-to-end CSV pipeline** — Use a test CSV with 5 rows (3 matchable, 2 not). Run `enrich-file`. Assert output CSV has 5 rows, 3 with enrichment data, 2 with only input data.
6. **Pipe compatibility** — Run `enrich-file ... -o csv 2>/dev/null | wc -l` and assert correct row count.

---

## 7. Implementation Estimate

| Task | Effort |
|------|--------|
| Null filtering in `enrich-file` | 1 hour |
| Defensive guard in `batched_enrich()` | 30 minutes |
| Summary output enhancement | 1 hour |
| Unit tests (4 cases) | 2 hours |
| Integration tests (2 cases) | 1.5 hours |
| **Total** | **~6 hours** |

---

## 8. Success Metrics

- Zero silent data loss: every row in the input file appears in the output file, with or without enrichment.
- Enrichment rate matches match rate: if 77/88 match, 77/88 should be enriched (barring independent enrichment API errors).
- No behavior change for clean inputs (100% match rate).
