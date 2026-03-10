"""Research orchestration: fan out company research with concurrency control."""

import asyncio
import csv
import io
import json
from typing import Any, TextIO

import click

from explorium_cli.ai_client import polish_prompt, research_company, validate_anthropic_key, is_permanent_error
from explorium_cli.batching import read_input_file


def load_records(file: TextIO) -> list[dict[str, str]]:
    """Load records from a CSV or JSON file.

    Returns:
        List of dicts, one per row/record.
    """
    wrapper, is_csv = read_input_file(file)

    if is_csv:
        reader = csv.DictReader(wrapper)
        records = [dict(row) for row in reader]
    else:
        data = json.load(wrapper)
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict) and "data" in data:
            records = data["data"]
        else:
            records = [data]

    if not records:
        raise click.UsageError("Input file contains no records")

    return records


def _find_company_column(fieldnames: list[str]) -> str | None:
    """Find the column most likely to contain company names."""
    aliases = [
        "company_name", "company", "name", "business_name",
        "organization", "employer", "company name",
    ]
    lower_map = {f.strip().lower(): f for f in fieldnames}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


def _find_domain_column(fieldnames: list[str]) -> str | None:
    """Find the column most likely to contain company domains."""
    aliases = [
        "domain", "website", "url", "company_domain",
        "company_website", "site",
    ]
    lower_map = {f.strip().lower(): f for f in fieldnames}
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    return None


async def run_research(
    records: list[dict[str, str]],
    prompt: str,
    threads: int = 10,
    max_searches: int = 5,
    no_polish: bool = False,
    verbose: bool = False,
) -> list[dict[str, str]]:
    """Run research across all records concurrently.

    Args:
        records: Input records (each must have a company name column).
        prompt: The user's research question.
        threads: Max concurrent research tasks.
        max_searches: Max web searches per company.
        no_polish: Skip prompt polishing with Sonnet.
        verbose: Print extra detail to stderr.

    Returns:
        Records with answer, reasoning, confidence columns appended.
    """
    # Detect company name and domain columns
    fieldnames = list(records[0].keys())
    company_col = _find_company_column(fieldnames)
    domain_col = _find_domain_column(fieldnames)

    if not company_col:
        raise click.UsageError(
            f"Could not find a company name column. "
            f"Found columns: {', '.join(fieldnames)}\n"
            f"Expected one of: company_name, company, name, business_name"
        )

    click.echo(f"Using column '{company_col}' for company names", err=True)
    if domain_col:
        click.echo(f"Using column '{domain_col}' for domains", err=True)

    # Validate API key before any work
    click.echo("Validating Anthropic API key...", err=True)
    try:
        await validate_anthropic_key()
    except RuntimeError as e:
        raise click.UsageError(str(e))

    # Polish prompt
    if no_polish:
        polished = prompt
        click.echo("Skipping prompt polish (--no-polish)", err=True)
    else:
        click.echo("Polishing prompt with Sonnet...", err=True)
        try:
            polished = await polish_prompt(prompt)
            if verbose:
                click.echo(f"Polished prompt:\n{polished}", err=True)
            else:
                click.echo("Prompt polished.", err=True)
        except Exception as e:
            click.echo(f"Warning: Prompt polishing failed ({e}). Falling back to raw prompt.", err=True)
            click.echo("Tip: Use --no-polish to skip this step.", err=True)
            polished = prompt

    # Fan out research with abort mechanism for permanent errors
    semaphore = asyncio.Semaphore(threads)
    total = len(records)
    completed = 0
    errors = 0
    abort_event = asyncio.Event()
    abort_reason = None

    async def _research_one(idx: int, record: dict) -> dict[str, str]:
        nonlocal completed, errors, abort_reason
        company = record.get(company_col, "").strip()
        domain = record.get(domain_col, "").strip() if domain_col else ""

        if abort_event.is_set():
            result = {"answer": f"Skipped: {abort_reason}", "reasoning": "", "confidence": "low"}
        elif not company:
            result = {"answer": "", "reasoning": "No company name", "confidence": "low"}
        else:
            async with semaphore:
                if abort_event.is_set():
                    result = {"answer": f"Skipped: {abort_reason}", "reasoning": "", "confidence": "low"}
                else:
                    try:
                        result = await research_company(
                            polished, company, domain, max_searches
                        )
                    except Exception as e:
                        errors += 1
                        if is_permanent_error(e):
                            abort_reason = str(e)
                            abort_event.set()
                            click.echo(
                                click.style(f"  Permanent error: {e}. Aborting remaining tasks.", fg="red"),
                                err=True,
                            )
                        elif verbose:
                            click.echo(
                                click.style(f"  Error researching '{company}': {e}", fg="red"),
                                err=True,
                            )
                        result = {"answer": f"Error: {e}", "reasoning": "", "confidence": "low"}

        completed += 1
        if completed % 5 == 0 or completed == total:
            click.echo(f"  Progress: {completed}/{total} companies researched", err=True)

        # Merge into original record
        merged = dict(record)
        merged["research_answer"] = result.get("answer", "")
        merged["research_reasoning"] = result.get("reasoning", "")
        merged["research_confidence"] = result.get("confidence", "")
        return merged

    tasks = [_research_one(i, rec) for i, rec in enumerate(records)]
    results = await asyncio.gather(*tasks)

    if errors:
        click.echo(
            click.style(f"Completed with {errors} error(s)", fg="yellow"),
            err=True,
        )
    else:
        click.echo(
            click.style(f"Research complete: {total} companies processed", fg="green"),
            err=True,
        )

    return list(results)
