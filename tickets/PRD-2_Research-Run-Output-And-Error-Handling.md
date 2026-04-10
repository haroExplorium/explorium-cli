# PRD: Research Run Output Format and Error Handling

**Author:** Claude (generated from pipeline analysis)
**Date:** 2026-03-10
**Status:** Draft
**Component:** `explorium-cli` — `research run`, `research_cmd.py`, `research.py`, `ai_client.py`
**Severity:** High — breaks pipeline ergonomics and wastes API credits on known-bad keys

---

## 1. Problem Statement

The `research run` command has two distinct issues that compound in pipeline usage:

### 1.1 No Output Format or File Options

Every other CLI command supports `-o {json|table|csv}` and `--output-file PATH` as global options. `research run` is the exception — it ignores the global `--output` and `--output-file` flags entirely and always writes raw JSON to stdout. This is because `research_cmd.py` (lines 82–85) calls `json.dumps()` directly to stdout instead of routing through the shared `formatters.output()` function used by all other commands.

This breaks the fundamental pipeline pattern the CLI is built around:

```bash
# This works for every other command:
explorium businesses match -f input.csv -o csv --output-file matched.csv
explorium prospects search ... -o csv --output-file prospects.csv

# But this doesn't work:
explorium research run -f companies.csv -o csv --output-file researched.csv
# Error: No such option: -o
```

The user must redirect stdout (`> file.csv`) and gets raw JSON instead of flattened CSV, requiring manual post-processing with `jq` or Python to convert to CSV before piping into the next pipeline step.

### 1.2 No Fail-Fast on API Key Errors

When the Anthropic API key is invalid, expired, or has no credits, the `research run` command does not validate the key upfront. Instead, it proceeds through prompt polishing (which fails), and — when `--no-polish` is used — fans out all company research tasks concurrently. Each task independently hits the API, gets the same `400 invalid_request_error`, and writes the error message into the `research_answer` field:

```json
{
  "research_answer": "Error: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Your credit balance is too low...'}}",
  "research_reasoning": "",
  "research_confidence": "low"
}
```

In the observed run, this produced 21 identical API errors — one per company — consuming wall-clock time and producing zero usable research. The command exited with code 0 (success), making it invisible to pipeline orchestration that the entire step failed.

---

## 2. Root Cause Analysis

### Output Format Issue

**`research_cmd.py` (lines 18–86):** The `run` function is decorated with `@click.pass_context` but does not access `ctx.obj` for output format settings. It receives the research results as a Python list and dumps them directly:

```python
# Current implementation (line 82-85)
results = asyncio.run(run_research(...))
click.echo(json.dumps(results, indent=2, default=str))
```

Compare with other commands that use the shared output infrastructure:

```python
# How other commands output (e.g., prospects.py)
output(result, ctx.obj.get("output_format", "json"), ctx.obj.get("output_file"))
```

The `research run` command was likely added later and bypassed the established output pattern. The `run` Click command definition also lacks the inherited group options since it's registered differently.

### Error Handling Issue

**`research.py` (lines 122–153):** The per-company research is wrapped in a generic `try/except Exception` that catches all errors and writes them into the result dict:

```python
try:
    result = await research_company(polished, company, domain, max_searches)
except Exception as e:
    result = {"answer": f"Error: {e}", "reasoning": "", "confidence": "low"}
```

There is no distinction between transient errors (rate limits, timeouts) and permanent errors (invalid API key, no credits). A `400 invalid_request_error` about credit balance is permanent — no retry will fix it, and every subsequent company will fail identically.

**`ai_client.py` (lines 50–56):** The retry logic (`_call_with_retry`) retries on `anthropic.RateLimitError` and `anthropic.InternalServerError`, but `anthropic.BadRequestError` (HTTP 400) is not retried — it raises immediately. However, the caller in `research.py` catches all exceptions uniformly, so the immediate raise is wasted.

### Prompt Polishing Failure Mode

**`ai_client.py` (line 83):** `polish_prompt()` calls the Anthropic API with `claude-sonnet-4-5-20241022`. If this call fails with a credit/auth error, the exception propagates up to `run_research()` (line 110), which does have a `try/except` — but this one is not caught and crashes the entire command. This means:

- With polishing (default): The command crashes immediately on a bad API key (good fail-fast, but bad UX — raw traceback).
- With `--no-polish`: The command proceeds to fan out all research tasks, each failing individually (bad — wastes time and produces garbage output).

---

## 3. Proposed Solution

### 3.1 Integrate Standard Output Formatting

**Location:** `explorium_cli/commands/research_cmd.py`

**Changes:**

1. Register `research run` under the main CLI group so it inherits the `-o`/`--output`/`--output-file` global options.
2. Replace the direct `json.dumps` call with the shared `output()` function from `formatters.py`.

**Implementation:**

```python
# research_cmd.py - updated run function
@click.pass_context
def run(ctx, input_file, prompt, threads, max_searches, no_polish, verbose):
    ...
    results = asyncio.run(run_research(...))

    # Wrap in API-style response for formatter compatibility
    response = {"status": "success", "data": results}

    output_format = ctx.obj.get("output_format", "json")
    output_file = ctx.obj.get("output_file")
    output(response, output_format, output_file)
```

This immediately enables:

```bash
# CSV output with file path — matches every other command
explorium research run -f companies.csv --prompt "..." -o csv --output-file researched.csv

# Piping into next step
explorium research run -f companies.csv --prompt "..." -o csv 2>/dev/null \
  | explorium prospects search -f - --job-level cxo -o csv
```

**CSV Flattening:** The existing `output_csv()` in `formatters.py` (lines 151–210) already handles nested dict flattening and list expansion. The three research fields (`research_answer`, `research_reasoning`, `research_confidence`) are flat strings, so they'll appear as straightforward columns alongside the input fields.

### 3.2 Upfront API Key Validation

**Location:** `explorium_cli/research.py`, `run_research()`, before the polishing or research phases.

**Behavior:** Before starting any work, make a lightweight Anthropic API call to validate that the key is active and has credits. Use a minimal `messages.create` call with a trivial prompt and `max_tokens=1`:

```python
async def _validate_anthropic_key():
    """Quick check that the API key works before fanning out research tasks."""
    import anthropic
    client = anthropic.AsyncAnthropic()
    try:
        await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1,
            messages=[{"role": "user", "content": "hi"}]
        )
    except anthropic.AuthenticationError as e:
        raise click.UsageError(f"Anthropic API key is invalid: {e}")
    except anthropic.BadRequestError as e:
        if "credit balance" in str(e).lower():
            raise click.UsageError(f"Anthropic API key has no credits: {e}")
        raise
```

**Call site:** Insert at the top of `run_research()`, before `polish_prompt()`:

```python
async def run_research(records, prompt, threads=10, max_searches=5, no_polish=False, verbose=False):
    click.echo("Validating Anthropic API key...", err=True)
    await _validate_anthropic_key()
    # ... proceed with polishing and research
```

**Cost:** ~0.001 cents per validation call. Negligible compared to the cost of 21 failed research calls.

### 3.3 Fail-Fast on Permanent Errors During Research

**Location:** `explorium_cli/research.py`, `run_research()`, research fan-out loop (lines 122–153).

**Behavior:** Introduce a shared `asyncio.Event` that signals permanent failure. When any research task encounters a permanent error (auth, credits, invalid model), it sets the event. All other pending tasks check the event before starting and abort immediately.

```python
async def run_research(...):
    abort_event = asyncio.Event()
    abort_reason = None

    async def _research_one(record, semaphore):
        nonlocal abort_reason
        if abort_event.is_set():
            return {**record, "research_answer": f"Skipped: {abort_reason}",
                    "research_reasoning": "", "research_confidence": "low"}

        async with semaphore:
            try:
                result = await research_company(...)
                return {**record, **result}
            except anthropic.BadRequestError as e:
                abort_reason = str(e)
                abort_event.set()
                return {**record, "research_answer": f"Error: {e}",
                        "research_reasoning": "", "research_confidence": "low"}
            except Exception as e:
                return {**record, "research_answer": f"Error: {e}",
                        "research_reasoning": "", "research_confidence": "low"}
```

**Distinction between error types:**

| Error Type | HTTP Code | Behavior |
|-----------|-----------|----------|
| `BadRequestError` (credits, invalid key) | 400 | Set abort event; fail fast |
| `AuthenticationError` | 401 | Set abort event; fail fast |
| `RateLimitError` | 429 | Retry with backoff (existing behavior) |
| `InternalServerError` | 500+ | Retry with backoff (existing behavior) |
| `APIConnectionError` | N/A | Retry with backoff; abort after 3 failures |
| Other `Exception` | N/A | Log and continue (per-company failure) |

### 3.4 Non-Zero Exit Code on Research Failure

**Location:** `explorium_cli/commands/research_cmd.py`

**Behavior:** After research completes, check if all records have error answers. If so, exit with code 1.

```python
results = asyncio.run(run_research(...))
error_count = sum(1 for r in results if r.get("research_answer", "").startswith("Error:"))
if error_count == len(results):
    click.echo(f"Error: All {len(results)} research tasks failed.", err=True)
    ctx.exit(1)
elif error_count > 0:
    click.echo(f"Warning: {error_count}/{len(results)} research tasks failed.", err=True)
```

### 3.5 Polishing Error Handling

**Location:** `explorium_cli/research.py`, `run_research()`, line ~110.

**Current:** `polish_prompt()` failure raises an unhandled exception, producing a raw Python traceback.

**Proposed:** Catch the error, print a user-friendly message, and suggest `--no-polish`:

```python
try:
    polished = await polish_prompt(prompt)
except Exception as e:
    if no_polish:
        raise  # shouldn't happen, but safety
    click.echo(f"Warning: Prompt polishing failed ({e}). Falling back to raw prompt.", err=True)
    click.echo("Tip: Use --no-polish to skip this step.", err=True)
    polished = prompt  # fallback to unpolished prompt
```

---

## 4. Edge Cases and Constraints

| Scenario | Expected Behavior |
|----------|-------------------|
| Valid API key, all companies research successfully | No change from current behavior (except output format support) |
| Invalid API key, no `--no-polish` | Validation catches error before any work; clean error message + exit 1 |
| Invalid API key, with `--no-polish` | Validation catches error before any work; clean error message + exit 1 |
| Key runs out of credits mid-research (company 12 of 21) | Abort event set; companies 13–21 marked as skipped; partial results output; exit warning |
| Rate limiting during research | Existing retry logic handles this; no abort event set |
| Network timeout on one company | Retried; if all retries fail, that company marked as error; others continue |
| `-o csv` output with nested research fields | research_answer, research_reasoning, research_confidence are flat strings — no flattening needed |
| `--output-file` with JSON format | Works via existing `formatters.output()` |
| Piped output (`\| next_command`) | Works; warnings go to stderr; clean data to stdout |
| Empty input file | Existing `load_records()` raises `UsageError` — no change |

---

## 5. Backward Compatibility

- **Default output format:** JSON (unchanged). Existing scripts that parse JSON stdout will continue to work.
- **JSON structure:** Unchanged. The `data` wrapper in the response object is stripped by `output_csv()` when formatting as CSV.
- **Exit codes:** Changed from always-0 to 1-on-total-failure. Scripts that check exit codes will now correctly detect failures. Scripts that ignore exit codes are unaffected.
- **`--no-polish` behavior:** Unchanged for successful runs. On key failure, now fails fast instead of producing 21 error entries.
- **New flags:** `-o` and `--output-file` are additive; omitting them preserves current default behavior.

---

## 6. Testing Requirements

### Unit Tests

1. **`test_research_output_csv`** — Run research with mock AI responses. Assert CSV output has correct columns including input fields + research fields.
2. **`test_research_output_file`** — Assert `--output-file` writes to disk, stdout is empty.
3. **`test_research_validate_key_invalid`** — Mock `messages.create` to raise `AuthenticationError`. Assert `UsageError` raised with friendly message.
4. **`test_research_validate_key_no_credits`** — Mock `messages.create` to raise `BadRequestError` with "credit balance" message. Assert `UsageError`.
5. **`test_research_fail_fast_on_permanent_error`** — Mock first company to raise `BadRequestError`. Assert remaining companies are skipped (not called). Assert abort reason in their `research_answer`.
6. **`test_research_continues_on_transient_error`** — Mock one company to raise a generic `Exception`. Assert other companies still researched.
7. **`test_research_polish_fallback`** — Mock `polish_prompt` to raise `BadRequestError`. Assert raw prompt is used as fallback. Assert warning printed.
8. **`test_research_exit_code_all_failed`** — Mock all companies to fail. Assert exit code 1.
9. **`test_research_exit_code_partial`** — Mock some companies to fail. Assert exit code 0 with warning.

### Integration Tests

10. **`test_research_csv_pipeline`** — Run `research run -o csv` with a 3-company test file. Pipe output to `prospects search -f -`. Assert pipeline completes.
11. **`test_research_invalid_key_exits_quickly`** — Set invalid API key. Time the command. Assert it exits within 5 seconds (not N * timeout).

---

## 7. Implementation Estimate

| Task | Effort |
|------|--------|
| Integrate standard output formatting | 2 hours |
| Upfront API key validation | 1 hour |
| Fail-fast abort event mechanism | 2 hours |
| Non-zero exit code logic | 30 minutes |
| Polish fallback error handling | 30 minutes |
| Unit tests (9 cases) | 4 hours |
| Integration tests (2 cases) | 2 hours |
| **Total** | **~12 hours** |

---

## 8. Success Metrics

- `research run` supports `-o csv --output-file` identically to all other commands.
- Invalid API key detected within 3 seconds of command start, not after N failed company requests.
- Partial failure (some companies fail, others succeed) produces a correct mixed output with clear warning counts on stderr.
- Total failure exits with code 1, enabling pipeline orchestration to detect and handle the error.
