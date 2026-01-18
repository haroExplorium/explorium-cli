"""Output formatting utilities for Explorium CLI."""

import json
from typing import Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


console = Console()
error_console = Console(stderr=True)


def output(data: Any, format: str = "json", title: Optional[str] = None) -> None:
    """
    Output data in the specified format.

    Args:
        data: Data to output (dict or list).
        format: Output format ('json' or 'table').
        title: Optional title for table output.
    """
    if format == "json":
        output_json(data)
    elif format == "table":
        output_table(data, title=title)
    else:
        output_json(data)  # default to JSON


def output_json(data: Any) -> None:
    """Output data as formatted JSON."""
    json_str = json.dumps(data, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True)
    console.print(syntax)


def output_table(data: Any, title: Optional[str] = None) -> None:
    """
    Output data as a rich table.

    Args:
        data: Data to display. Can be a dict or list of dicts.
        title: Optional table title.
    """
    if data is None:
        console.print("[dim]No data[/dim]")
        return

    # Handle single dict (wrap in list)
    if isinstance(data, dict):
        # Check if it has a 'data' key (API response format)
        if "data" in data:
            data = data["data"]
        else:
            data = [data]

    if not isinstance(data, list):
        console.print("[dim]Cannot display as table[/dim]")
        output_json(data)
        return

    if not data:
        console.print("[dim]No results[/dim]")
        return

    # Create table
    table = Table(title=title, show_header=True, header_style="bold cyan")

    # Get columns from first item
    columns = list(data[0].keys())
    for col in columns:
        table.add_column(col, overflow="fold")

    # Add rows
    for row in data:
        values = []
        for col in columns:
            val = row.get(col, "")
            # Format complex values
            if isinstance(val, (dict, list)):
                val = json.dumps(val, default=str)
            elif val is None:
                val = ""
            else:
                val = str(val)
            # Truncate long values
            if len(val) > 50:
                val = val[:47] + "..."
            values.append(val)
        table.add_row(*values)

    console.print(table)


def output_error(message: str, details: Optional[dict] = None) -> None:
    """
    Output an error message.

    Args:
        message: Error message to display.
        details: Optional error details.
    """
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    if details:
        error_console.print(f"[dim]{json.dumps(details, indent=2)}[/dim]")


def output_success(message: str) -> None:
    """Output a success message."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def output_warning(message: str) -> None:
    """Output a warning message."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def output_info(message: str) -> None:
    """Output an info message."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


def format_business(business: dict) -> str:
    """Format a business record for display."""
    name = business.get("name", "Unknown")
    website = business.get("website", "")
    business_id = business.get("business_id", "")
    return f"{name} ({website}) [ID: {business_id}]"


def format_prospect(prospect: dict) -> str:
    """Format a prospect record for display."""
    first_name = prospect.get("first_name", "")
    last_name = prospect.get("last_name", "")
    title = prospect.get("job_title", "")
    prospect_id = prospect.get("prospect_id", "")
    return f"{first_name} {last_name} - {title} [ID: {prospect_id}]"
