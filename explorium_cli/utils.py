"""Utility functions for Explorium CLI."""

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
        output(result, ctx.obj["output"])
        return result
    except APIError as e:
        output_error(e.message, e.response)
        raise click.Abort()
