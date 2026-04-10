# Bug: `prospects search --total` fails with 422 when combined with filters

## Summary

`explorium prospects search` returns a `422 Unprocessable Entity` error whenever `--total` is used alongside `--job-level`, `--department`, or `--page-size`. The same query works fine without `--total`.

## Severity

**High** — `--total` is the primary way users control result count in search. Without it, search is limited to a single default page, making filtered searches effectively broken for any workflow that needs a specific number of results.

## Steps to Reproduce

### 1. Works — no `--total`, no `--page-size`
```bash
explorium prospects search \
  -b "4f5c422f4d49a5a807eda27434231040" \
  --job-level vp \
  -o json
# ✅ Returns results
```

### 2. Fails — add `--total`
```bash
explorium prospects search \
  -b "4f5c422f4d49a5a807eda27434231040" \
  --job-level vp \
  --total 3 \
  -o json
# ❌ 422 Unprocessable Entity
```

### 3. Fails — use `--page-size` instead of `--total`
```bash
explorium prospects search \
  -b "4f5c422f4d49a5a807eda27434231040" \
  --job-level vp,cxo \
  --department engineering \
  --page-size 3 \
  -o json
# ❌ 422: "'size' must be greater than or equal to 'page_size'"
```

### 4. Fails — multiple business IDs via comma-separation with `--total`
```bash
explorium prospects search \
  --business-id "id1,id2,id3,id4,id5,id6,id7,id8,id9,id10,id11" \
  --job-level vp,cxo \
  --total 33 \
  -o csv
# ❌ 422 Unprocessable Entity
```

### 5. Fails — multiple business IDs via file with `--total`
```bash
explorium prospects search \
  -f companies_with_business_ids.csv \
  --job-level vp,cxo \
  --department engineering \
  --total 33 \
  -o csv
# ❌ 422 Unprocessable Entity
```

## Root Cause

The API requires `size >= page_size` in the request body. When the CLI translates `--total` and/or `--page-size` into API parameters, it either:

- Doesn't set `size` at all (leaving it at a default that is lower than the computed `page_size`), or
- Computes `size` and `page_size` in a way that violates the `size >= page_size` constraint

The one time the API returned a detailed error body, it explicitly said:
```json
{
  "detail": [
    {
      "loc": ["body", "__root__"],
      "msg": "'size' must be greater than or equal to 'page_size'",
      "type": "value_error"
    }
  ]
}
```

## Secondary Issue: Error Messages Swallowed

In most of the failing calls, the CLI only printed:
```
Error: API request failed: 422 Client Error: Unprocessable Entity for url:
https://api.explorium.ai/v1/prospects
Aborted!
```

The API response body (which contained the `size >= page_size` hint) was **not shown**. This made debugging significantly harder — I only discovered the actual constraint by accident on one specific call that happened to print the body.

## Expected Behavior

1. `--total 3` should work with any combination of filters (`--job-level`, `--department`, `--job-title`, etc.)
2. The CLI should ensure `size >= page_size` before sending the request — the user should never need to know about this internal API constraint
3. When the API returns a 422, the CLI should **always** print the full error response body

## Suggested Fix

1. Before sending a search request to the API, add a guard:
   ```
   if size < page_size:
       size = page_size
   ```
2. When `--total` is provided, derive both `size` and `page_size` from it such that the constraint is always satisfied
3. Always include the API response body in error output for 4xx/5xx responses

## Impact

This bug forced a workaround of looping through business IDs one at a time in a Python script, bypassing the CLI entirely for the core search step. A workflow that should have been a single CLI command became ~30 lines of custom code and multiple minutes of trial-and-error debugging.
