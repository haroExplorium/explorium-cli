"""Research orchestration: fan out company research with concurrency control."""

import asyncio
import csv
import io
import json
from typing import Any, TextIO

import click

from explorium_cli.ai_client import polish_prompt, research_company
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

    # Polish prompt
    if no_polish:
        polished = prompt
        click.echo("Skipping prompt polish (--no-polish)", err=True)
    else:
        click.echo("Polishing prompt with Sonnet...", err=True)
        polished = await polish_prompt(prompt)
        if verbose:
            click.echo(f"Polished prompt:\n{polished}", err=True)
        else:
            click.echo("Prompt polished.", err=True)

    # Fan out research
    semaphore = asyncio.Semaphore(threads)
    total = len(records)
    completed = 0
    errors = 0

    async def _research_one(idx: int, record: dict) -> dict[str, str]:
        nonlocal completed, errors
        company = record.get(company_col, "").strip()
        domain = record.get(domain_col, "").strip() if domain_col else ""

        if not company:
            result = {"answer": "", "reasoning": "No company name", "confidence": "low"}
        else:
            async with semaphore:
                try:
                    result = await research_company(
                        polished, company, domain, max_searches
                    )
                except Exception as e:
                    errors += 1
                    if verbose:
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
