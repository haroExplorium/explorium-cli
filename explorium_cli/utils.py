"""Utility functions for Explorium CLI."""

import functools

import click

from explorium_cli.api.client import ExploriumAPI, APIError
from explorium_cli.formatters import output, output_error


def get_api(ctx: click.Context) -> ExploriumAPI:
    """Get the API client from context, raising error if not configured."""
    api = ctx.obj.get("api")
    if not api:
        raise click.ClickException(
            "API key not configured. Run 'explorium config init --api-key YOUR_KEY'"
        )
    return api


def handle_api_call(ctx: click.Context, func, *args, **kwargs):
    """Execute an API call with error handling and output formatting."""
    try:
        result = func(*args, **kwargs)
        output(result, ctx.obj["output"], file_path=ctx.obj.get("output_file"))
        return result
    except APIError as e:
        output_error(e.message, e.response)
        raise click.Abort()


def output_options(f):
    """Add -o/--output/--format and --output-file to a leaf command.

    When provided, these override the global -o and --output-file set on the
    root ``explorium`` command.  The override is applied to ``ctx.obj`` before
    the wrapped command function runs, so existing code that reads
    ``ctx.obj["output"]`` and ``ctx.obj["output_file"]`` works without changes.
    """
    @click.option(
        "--output-file", "cmd_output_file",
        type=click.Path(),
        default=None,
        help="Write output to file instead of stdout",
    )
    @click.option(
        "-o", "--output", "--format", "cmd_output",
        type=click.Choice(["json", "table", "csv"]),
        default=None,
        help="Output format (json, table, csv)",
    )
    @functools.wraps(f)
    def wrapper(*args, cmd_output=None, cmd_output_file=None, **kwargs):
        ctx = click.get_current_context()
        if cmd_output is not None:
            ctx.obj["output"] = cmd_output
        if cmd_output_file is not None:
            ctx.obj["output_file"] = cmd_output_file
        return f(*args, **kwargs)
    return wrapper
