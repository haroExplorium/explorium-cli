"""Tests for the formatters module."""

import json
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from explorium_cli.formatters import (
    output,
    output_json,
    output_csv,
    output_table,
    output_error,
    output_success,
    output_warning,
    output_info,
    format_business,
    format_prospect,
    _flatten_dict,
    _should_flatten,
)


class TestOutputFunction:
    """Tests for the main output function."""

    def test_output_json_format(self):
        """Test output with JSON format."""
        data = {"key": "value"}
        with patch("explorium_cli.formatters.output_json") as mock_json:
            output(data, format="json")
            mock_json.assert_called_once_with(data)

    def test_output_table_format(self):
        """Test output with table format."""
        data = [{"key": "value"}]
        with patch("explorium_cli.formatters.output_table") as mock_table:
            output(data, format="table", title="Test")
            mock_table.assert_called_once_with(data, title="Test")

    def test_output_default_is_json(self):
        """Test output defaults to JSON."""
        data = {"key": "value"}
        with patch("explorium_cli.formatters.output_json") as mock_json:
            output(data)
            mock_json.assert_called_once_with(data)

    def test_output_unknown_format_falls_back_to_json(self):
        """Test output with unknown format falls back to JSON."""
        data = {"key": "value"}
        with patch("explorium_cli.formatters.output_json") as mock_json:
            output(data, format="unknown")
            mock_json.assert_called_once_with(data)


class TestOutputJson:
    """Tests for JSON output."""

    def test_output_json_dict_tty(self):
        """Test JSON output with dictionary when stdout is a TTY."""
        data = {"name": "test", "value": 123}
        with patch("explorium_cli.formatters.sys") as mock_sys, \
             patch("explorium_cli.formatters.console") as mock_console:
            mock_sys.stdout.isatty.return_value = True
            output_json(data)
            mock_console.print.assert_called_once()

    def test_output_json_list_tty(self):
        """Test JSON output with list when stdout is a TTY."""
        data = [{"id": 1}, {"id": 2}]
        with patch("explorium_cli.formatters.sys") as mock_sys, \
             patch("explorium_cli.formatters.console") as mock_console:
            mock_sys.stdout.isatty.return_value = True
            output_json(data)
            mock_console.print.assert_called_once()

    def test_output_json_nested_tty(self):
        """Test JSON output with nested data when stdout is a TTY."""
        data = {"nested": {"deep": {"value": "test"}}}
        with patch("explorium_cli.formatters.sys") as mock_sys, \
             patch("explorium_cli.formatters.console") as mock_console:
            mock_sys.stdout.isatty.return_value = True
            output_json(data)
            mock_console.print.assert_called_once()

    def test_output_json_plain_when_piped(self, capsys):
        """Test JSON output is plain (no ANSI) when stdout is piped."""
        data = {"name": "test", "value": 123}
        with patch("explorium_cli.formatters.sys") as mock_sys:
            mock_sys.stdout.isatty.return_value = False
            output_json(data)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed == data


class TestOutputTable:
    """Tests for table output."""

    def test_output_table_with_list(self):
        """Test table output with list of dicts."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()

    def test_output_table_with_dict_containing_data(self):
        """Test table output with API response format."""
        data = {
            "status": "success",
            "data": [
                {"name": "Alice", "age": 30}
            ]
        }
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()

    def test_output_table_with_single_dict(self):
        """Test table output with single dict."""
        data = {"name": "Alice", "age": 30}
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()

    def test_output_table_with_empty_list(self):
        """Test table output with empty list."""
        data = []
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0][0]
            assert "No results" in args

    def test_output_table_with_none(self):
        """Test table output with None."""
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(None)
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0][0]
            assert "No data" in args

    def test_output_table_with_title(self):
        """Test table output with title."""
        data = [{"name": "Alice"}]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data, title="Test Title")
            mock_console.print.assert_called_once()

    def test_output_table_truncates_long_values(self):
        """Test that long values are truncated."""
        data = [{"name": "A" * 100}]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()

    def test_output_table_handles_nested_values(self):
        """Test that nested values are JSON-ified."""
        data = [{"name": "Alice", "metadata": {"key": "value"}}]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()

    def test_output_table_handles_none_values(self):
        """Test that None values are handled."""
        data = [{"name": "Alice", "email": None}]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_table(data)
            mock_console.print.assert_called_once()


class TestOutputMessages:
    """Tests for message output functions."""

    def test_output_error(self):
        """Test error message output."""
        with patch("explorium_cli.formatters.error_console") as mock_console:
            output_error("Test error")
            mock_console.print.assert_called()
            args = mock_console.print.call_args[0][0]
            assert "Error" in args
            assert "Test error" in args

    def test_output_error_with_details(self):
        """Test error message with details."""
        with patch("explorium_cli.formatters.error_console") as mock_console:
            output_error("Test error", details={"code": "ERR001"})
            assert mock_console.print.call_count == 2

    def test_output_success(self):
        """Test success message output."""
        with patch("explorium_cli.formatters.console") as mock_console:
            output_success("Test success")
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0][0]
            assert "Success" in args
            assert "Test success" in args

    def test_output_warning(self):
        """Test warning message output."""
        with patch("explorium_cli.formatters.console") as mock_console:
            output_warning("Test warning")
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0][0]
            assert "Warning" in args
            assert "Test warning" in args

    def test_output_info(self):
        """Test info message output."""
        with patch("explorium_cli.formatters.console") as mock_console:
            output_info("Test info")
            mock_console.print.assert_called_once()
            args = mock_console.print.call_args[0][0]
            assert "Info" in args
            assert "Test info" in args


class TestFormatFunctions:
    """Tests for format helper functions."""

    def test_format_business_full_data(self):
        """Test formatting business with all data."""
        business = {
            "name": "Starbucks",
            "website": "starbucks.com",
            "business_id": "abc123"
        }
        result = format_business(business)
        assert "Starbucks" in result
        assert "starbucks.com" in result
        assert "abc123" in result

    def test_format_business_missing_data(self):
        """Test formatting business with missing data."""
        business = {"name": "Test Company"}
        result = format_business(business)
        assert "Test Company" in result
        assert "Unknown" not in result

    def test_format_business_empty_dict(self):
        """Test formatting empty business dict."""
        result = format_business({})
        assert "Unknown" in result

    def test_format_prospect_full_data(self):
        """Test formatting prospect with all data."""
        prospect = {
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "VP Engineering",
            "prospect_id": "prospect123"
        }
        result = format_prospect(prospect)
        assert "John" in result
        assert "Doe" in result
        assert "VP Engineering" in result
        assert "prospect123" in result

    def test_format_prospect_missing_data(self):
        """Test formatting prospect with missing data."""
        prospect = {"first_name": "John"}
        result = format_prospect(prospect)
        assert "John" in result

    def test_format_prospect_empty_dict(self):
        """Test formatting empty prospect dict."""
        result = format_prospect({})
        assert "ID:" in result


class TestFlattenDict:
    """Tests for _flatten_dict function."""

    def test_flat_dict_unchanged(self):
        d = {"a": 1, "b": "hello"}
        assert _flatten_dict(d) == {"a": 1, "b": "hello"}

    def test_nested_dict(self):
        d = {"a": {"b": 1}}
        assert _flatten_dict(d) == {"a.b": 1}

    def test_deeply_nested(self):
        d = {"a": {"b": {"c": 42}}}
        assert _flatten_dict(d) == {"a.b.c": 42}

    def test_simple_list_joined(self):
        d = {"tags": ["tech", "saas"]}
        assert _flatten_dict(d) == {"tags": "tech, saas"}

    def test_list_of_dicts_expanded(self):
        d = {"emails": [{"addr": "a@b.com"}, {"addr": "c@d.com"}]}
        assert _flatten_dict(d) == {"emails.0.addr": "a@b.com", "emails.1.addr": "c@d.com"}

    def test_empty_list(self):
        d = {"items": []}
        assert _flatten_dict(d) == {"items": ""}

    def test_none_values(self):
        d = {"a": None, "b": 1}
        assert _flatten_dict(d) == {"a": None, "b": 1}

    def test_mixed_nesting(self):
        d = {
            "name": "John",
            "address": {"city": "NY", "zip": "10001"},
            "tags": ["dev", "python"],
        }
        result = _flatten_dict(d)
        assert result == {
            "name": "John",
            "address.city": "NY",
            "address.zip": "10001",
            "tags": "dev, python",
        }


class TestShouldFlatten:
    """Tests for _should_flatten function."""

    def test_flat_data_returns_false(self):
        data = [{"a": 1, "b": "hello"}, {"a": 2, "b": "world"}]
        assert _should_flatten(data) is False

    def test_nested_dict_returns_true(self):
        data = [{"a": 1, "b": {"c": 2}}]
        assert _should_flatten(data) is True

    def test_list_value_returns_true(self):
        data = [{"a": 1, "b": [1, 2, 3]}]
        assert _should_flatten(data) is True

    def test_empty_data_returns_false(self):
        assert _should_flatten([]) is False

    def test_non_dict_rows_returns_false(self):
        assert _should_flatten(["a", "b"]) is False


class TestCsvFlatOutput:
    """Tests for flat CSV output with nested data."""

    def test_output_csv_flattens_nested(self, capsys):
        """CSV output flattens nested dicts."""
        data = [{"name": "John", "address": {"city": "NY"}}]
        output_csv(data)
        captured = capsys.readouterr()
        assert "address.city" in captured.out
        assert "NY" in captured.out
        assert "{" not in captured.out

    def test_output_csv_flat_data_unchanged(self, capsys):
        """CSV output for flat data works normally."""
        data = [{"name": "John", "age": 30}]
        output_csv(data)
        captured = capsys.readouterr()
        assert "name" in captured.out
        assert "John" in captured.out
