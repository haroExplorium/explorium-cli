"""Output formatting utilities for Explorium CLI."""

import csv
import io
import json
import sys
from typing import Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


console = Console()
error_console = Console(stderr=True)


def _flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Recursively flatten nested dicts.

    - Nested dicts: {"a": {"b": 1}} -> {"a.b": 1}
    - Lists of scalars: {"tags": ["tech", "saas"]} -> {"tags": "tech, saas"}
    - Lists of dicts: {"emails": [{"addr": "a@b"}]} -> {"emails.0.addr": "a@b"}
    - Empty lists: {"items": []} -> {"items": ""}
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep).items())
        elif isinstance(v, list):
            if not v:
                items.append((new_key, ""))
            elif all(isinstance(i, dict) for i in v):
                for idx, item in enumerate(v):
                    items.extend(_flatten_dict(item, f"{new_key}{sep}{idx}", sep).items())
            elif any(isinstance(i, (dict, list)) for i in v):
                items.append((new_key, json.dumps(v, default=str)))
            else:
                items.append((new_key, ", ".join(str(i) for i in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def _should_flatten(data: list[dict]) -> bool:
    """Check first 5 rows for any nested dict/list values."""
    for row in data[:5]:
        if isinstance(row, dict):
            for v in row.values():
                if isinstance(v, (dict, list)):
                    return True
    return False


def output(data: Any, format: str = "json", title: Optional[str] = None, file_path: Optional[str] = None) -> None:
    """
    Output data in the specified format.

    Args:
        data: Data to output (dict or list).
        format: Output format ('json', 'table', or 'csv').
        title: Optional title for table output.
        file_path: Optional file path to write clean output to.
    """
    if file_path:
        # For table format with file output, fall back to JSON
        write_format = "json" if format == "table" else format
        _write_to_file(data, write_format, file_path)
        return

    if format == "json":
        output_json(data)
    elif format == "table":
        output_table(data, title=title)
    elif format == "csv":
        output_csv(data)
    else:
        output_json(data)  # default to JSON


def output_json(data: Any) -> None:
    """Output data as formatted JSON."""
    json_str = json.dumps(data, indent=2, default=str)
    if sys.stdout.isatty():
        syntax = Syntax(json_str, "json", theme="monokai", word_wrap=True)
        console.print(syntax)
    else:
        print(json_str)


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


def output_csv(data: Any) -> None:
    """
    Output data as CSV.

    Args:
        data: Data to output. Can be a dict (with 'data' key) or list of dicts.
    """
    if data is None:
        return

    # Handle API response format (extract 'data' key)
    if isinstance(data, dict):
        if "data" in data:
            data = data["data"]
        else:
            data = [data]

    if not isinstance(data, list):
        # Can't convert non-list to CSV, fall back to JSON
        output_json(data)
        return

    if not data:
        return

    # Flatten nested structures for usable CSV output
    if _should_flatten(data):
        data = [_flatten_dict(row) if isinstance(row, dict) else row for row in data]

    # Get all unique keys across all rows for headers
    all_keys: set[str] = set()
    for row in data:
        if isinstance(row, dict):
            all_keys.update(row.keys())

    if not all_keys:
        return

    # Sort keys for consistent column order
    fieldnames = sorted(all_keys)

    # Write CSV to string buffer, then print
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()

    for row in data:
        if isinstance(row, dict):
            # Convert any remaining complex values to JSON strings
            processed_row = {}
            for key, val in row.items():
                if isinstance(val, (dict, list)):
                    processed_row[key] = json.dumps(val, default=str)
                elif val is None:
                    processed_row[key] = ""
                else:
                    processed_row[key] = val
            writer.writerow(processed_row)

    print(output.getvalue(), end="")


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


def _write_to_file(data: Any, format: str, file_path: str) -> None:
    """Write clean data to a file (no Rich/ANSI formatting).

    Args:
        data: Data to write.
        format: 'json' or 'csv'.
        file_path: Destination file path.
    """
    import click as _click

    if format == "csv":
        # Normalize data for CSV
        rows = data
        if isinstance(rows, dict):
            rows = rows.get("data", [rows])
        if not isinstance(rows, list):
            # Can't write non-list as CSV, fall back to JSON
            format = "json"

        if format == "csv" and isinstance(rows, list) and rows:
            # Flatten nested structures for usable CSV output
            if _should_flatten(rows):
                rows = [_flatten_dict(row) if isinstance(row, dict) else row for row in rows]

            all_keys: set[str] = set()
            for row in rows:
                if isinstance(row, dict):
                    all_keys.update(row.keys())
            fieldnames = sorted(all_keys)

            with open(file_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    if isinstance(row, dict):
                        processed = {}
                        for key, val in row.items():
                            if isinstance(val, (dict, list)):
                                processed[key] = json.dumps(val, default=str)
                            elif val is None:
                                processed[key] = ""
                            else:
                                processed[key] = val
                        writer.writerow(processed)

            _click.echo(f"Output written to: {file_path}", err=True)
            return

    # Default: write JSON
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
        f.write("\n")

    _click.echo(f"Output written to: {file_path}", err=True)
