"""Main CLI entry point for Explorium."""

import click

from explorium_cli.config import load_config
from explorium_cli.api.client import ExploriumAPI


@click.group()
@click.option(
    "--config", "-c",
    help="Path to config file",
    type=click.Path(exists=False)
)
@click.option(
    "--output", "-o",
    type=click.Choice(["json", "table"]),
    default=None,
    help="Output format (default: json)"
)
@click.pass_context
def cli(ctx: click.Context, config: str, output: str) -> None:
    """Explorium API CLI - interact with all Explorium endpoints."""
    ctx.ensure_object(dict)

    # Load configuration
    cfg = load_config(config)
    ctx.obj["config"] = cfg

    # Set output format (CLI option > config > default)
    ctx.obj["output"] = output or cfg.get("default_output", "json")

    # Create API client if we have an API key
    if cfg.get("api_key"):
        ctx.obj["api"] = ExploriumAPI(
            api_key=cfg["api_key"],
            base_url=cfg.get("base_url")
        )


# Import and register command groups (must be after cli definition)
from explorium_cli.commands.config_cmd import config_group
from explorium_cli.commands.businesses import businesses
from explorium_cli.commands.prospects import prospects
from explorium_cli.commands.webhooks import webhooks

cli.add_command(config_group, name="config")
cli.add_command(businesses)
cli.add_command(prospects)
cli.add_command(webhooks)


if __name__ == "__main__":
    cli()
