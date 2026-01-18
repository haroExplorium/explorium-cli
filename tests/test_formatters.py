"""Tests for the formatters module."""

import json
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from explorium_cli.formatters import (
    output,
    output_json,
    output_table,
    output_error,
    output_success,
    output_warning,
    output_info,
    format_business,
    format_prospect,
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

    def test_output_json_dict(self):
        """Test JSON output with dictionary."""
        data = {"name": "test", "value": 123}
        with patch("explorium_cli.formatters.console") as mock_console:
            output_json(data)
            mock_console.print.assert_called_once()

    def test_output_json_list(self):
        """Test JSON output with list."""
        data = [{"id": 1}, {"id": 2}]
        with patch("explorium_cli.formatters.console") as mock_console:
            output_json(data)
            mock_console.print.assert_called_once()

    def test_output_json_nested(self):
        """Test JSON output with nested data."""
        data = {"nested": {"deep": {"value": "test"}}}
        with patch("explorium_cli.formatters.console") as mock_console:
            output_json(data)
            mock_console.print.assert_called_once()


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
