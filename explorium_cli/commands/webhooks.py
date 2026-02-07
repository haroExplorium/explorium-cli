"""Webhook commands for Explorium CLI."""

import click

from explorium_cli.api.webhooks import WebhooksAPI
from explorium_cli.utils import get_api, handle_api_call, output_options


@click.group()
@click.pass_context
def webhooks(ctx: click.Context) -> None:
    """Webhook management operations."""
    pass


@webhooks.command()
@click.option("--partner-id", "-p", required=True, help="Partner identifier")
@click.option("--url", "-u", required=True, help="Webhook URL")
@output_options
@click.pass_context
def create(ctx: click.Context, partner_id: str, url: str) -> None:
    """Register a new webhook."""
    api = get_api(ctx)
    webhooks_api = WebhooksAPI(api)
    handle_api_call(ctx, webhooks_api.create, partner_id, url)


@webhooks.command()
@click.option("--partner-id", "-p", required=True, help="Partner identifier")
@output_options
@click.pass_context
def get(ctx: click.Context, partner_id: str) -> None:
    """Get webhook configuration."""
    api = get_api(ctx)
    webhooks_api = WebhooksAPI(api)
    handle_api_call(ctx, webhooks_api.get, partner_id)


@webhooks.command()
@click.option("--partner-id", "-p", required=True, help="Partner identifier")
@click.option("--url", "-u", required=True, help="New webhook URL")
@output_options
@click.pass_context
def update(ctx: click.Context, partner_id: str, url: str) -> None:
    """Update webhook URL."""
    api = get_api(ctx)
    webhooks_api = WebhooksAPI(api)
    handle_api_call(ctx, webhooks_api.update, partner_id, url)


@webhooks.command()
@click.option("--partner-id", "-p", required=True, help="Partner identifier")
@output_options
@click.pass_context
def delete(ctx: click.Context, partner_id: str) -> None:
    """Delete a webhook."""
    api = get_api(ctx)
    webhooks_api = WebhooksAPI(api)
    handle_api_call(ctx, webhooks_api.delete, partner_id)
