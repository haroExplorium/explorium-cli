"""Research commands for Explorium CLI."""

import asyncio
import sys

import click

from explorium_cli.formatters import output
from explorium_cli.research import load_records, run_research


@click.group()
def research():
    """AI-powered company research using web search."""
    pass


@research.command()
@click.option(
    "-f", "--file",
    "input_file",
    required=True,
    type=click.File("r"),
    help="Input CSV or JSON file with company records",
)
@click.option(
    "--prompt", "-p",
    required=True,
    help="Research question to answer for each company",
)
@click.option(
    "--threads", "-t",
    default=10,
    show_default=True,
    help="Max concurrent research tasks",
)
@click.option(
    "--max-searches",
    default=5,
    show_default=True,
    help="Max web searches per company",
)
@click.option(
    "--no-polish",
    is_flag=True,
    default=False,
    help="Skip prompt polishing with Sonnet",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    default=False,
    help="Show detailed progress and polished prompt",
)
@click.pass_context
def run(ctx, input_file, prompt, threads, max_searches, no_polish, verbose):
    """Research companies using AI + web search.

    Reads a CSV/JSON file, asks a question about each company using AI
    with web search, and outputs the original data with 3 new columns:
    research_answer, research_reasoning, research_confidence.

    Example:
        explorium research run -f companies.csv --prompt "Is this a B2B company?"
    """
    # Load records
    records = load_records(input_file)
    click.echo(f"Loaded {len(records)} records from input file", err=True)

    # Run async research
    results = asyncio.run(
        run_research(
            records=records,
            prompt=prompt,
            threads=threads,
            max_searches=max_searches,
            no_polish=no_polish,
            verbose=verbose,
        )
    )

    # Check for total/partial failure
    error_count = sum(
        1 for r in results
        if r.get("research_answer", "").startswith("Error:")
        or r.get("research_answer", "").startswith("Skipped:")
    )

    # Output using existing formatter
    fmt = ctx.obj.get("output", "json") if ctx.obj else "json"
    file_path = ctx.obj.get("output_file") if ctx.obj else None
    output(results, format=fmt, title="Research Results", file_path=file_path)

    if error_count == len(results):
        click.echo(f"Error: All {len(results)} research tasks failed.", err=True)
        ctx.exit(1)
    elif error_count > 0:
        click.echo(f"Warning: {error_count}/{len(results)} research tasks failed.", err=True)
