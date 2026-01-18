"""Configuration commands for Explorium CLI."""

import click
import yaml

from explorium_cli.config import (
    init_config,
    load_config,
    set_config_value,
    CONFIG_FILE,
)
from explorium_cli.formatters import output_success, output_info


@click.group(name="config")
def config_group() -> None:
    """Configuration management commands."""
    pass


@config_group.command()
@click.option(
    "--api-key", "-k",
    required=True,
    help="Your Explorium API key"
)
@click.option(
    "--config-path",
    type=click.Path(),
    help="Custom config file path"
)
def init(api_key: str, config_path: str) -> None:
    """Initialize configuration with API key."""
    file_path = init_config(api_key, config_path)
    output_success(f"Configuration saved to {file_path}")


@config_group.command()
@click.option(
    "--config-path",
    type=click.Path(exists=True),
    help="Config file to show"
)
@click.pass_context
def show(ctx: click.Context, config_path: str) -> None:
    """Show current configuration."""
    config = ctx.obj.get("config") or load_config(config_path)

    # Mask API key for display
    display_config = config.copy()
    if display_config.get("api_key"):
        key = display_config["api_key"]
        if len(key) > 8:
            display_config["api_key"] = f"{key[:4]}...{key[-4:]}"
        else:
            display_config["api_key"] = "***"

    output_info(f"Config file: {config_path or CONFIG_FILE}")
    click.echo(yaml.dump(display_config, default_flow_style=False))


@config_group.command()
@click.argument("key")
@click.argument("value")
@click.option(
    "--config-path",
    type=click.Path(),
    help="Config file to modify"
)
def set(key: str, value: str, config_path: str) -> None:
    """Set a configuration value."""
    # Type conversion for known numeric values
    if key == "default_page_size":
        try:
            value = int(value)
        except ValueError:
            raise click.BadParameter(f"'{value}' is not a valid integer")

    file_path = set_config_value(key, value, config_path)
    output_success(f"Set {key} = {value} in {file_path}")
