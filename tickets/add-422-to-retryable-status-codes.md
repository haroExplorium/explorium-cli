# Add HTTP 422 to retryable status codes in API client

**Type:** Bug Fix
**Priority:** Medium
**Component:** explorium-cli

---

## Description

The CLI's HTTP client (`explorium_cli/api/client.py`) retries failed API requests with exponential backoff for status codes `{429, 500, 502, 503, 504}`, plus `ConnectionError` and `Timeout`. HTTP 422 (Unprocessable Entity) is currently treated as a non-retryable client error and fails immediately.

In practice, the Explorium API can return transient 422 errors — for example, during `prospects enrich-file`, the bulk enrich endpoint returned a 422 that resolved on its own when the same request was made minutes later via `prospects bulk-enrich`. This is likely caused by eventual consistency or temporary server-side state issues.

## Steps to Reproduce

1. Run `explorium prospects enrich-file -f <file> --types contacts`
2. The match phase succeeds (88/88 matched)
3. The enrich phase calls `POST /v1/prospects/contacts_information/bulk_enrich`
4. API returns `422 Unprocessable Entity`
5. CLI aborts immediately with no retry

## Expected Behavior

The request should be retried up to 3 times with exponential backoff (1s → 2s → 4s) before failing.

## Proposed Fix

In `explorium_cli/api/client.py` line 24, add `422` to `RETRYABLE_STATUS_CODES`:

```python
# Before
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# After
RETRYABLE_STATUS_CODES = {422, 429, 500, 502, 503, 504}
```

## Trade-off

Genuine (permanent) 422 validation errors will now retry 3 times before failing, adding ~7 seconds of delay. This is acceptable overhead.

## Acceptance Criteria

- [ ] 422 added to `RETRYABLE_STATUS_CODES`
- [ ] Existing tests in `tests/test_client.py` pass
- [ ] New test case: verify 422 triggers retry with backoff
