"""Unit tests for the pagination utility module."""

import pytest
from unittest.mock import MagicMock, patch

from explorium_cli.pagination import paginated_fetch


class TestPaginatedFetch:
    """Tests for paginated_fetch function."""

    def test_single_page_fetch(self):
        """Test fetching when total fits in one page."""
        mock_api = MagicMock()
        # Return exactly what was requested (3 records) - signals no more data
        # since we got fewer than page_size (100)
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        }

        result = paginated_fetch(
            mock_api,
            total=3,
            page_size=100,
            show_progress=False,
            filters={"country": ["us"]}
        )

        assert mock_api.call_count == 1
        assert len(result["data"]) == 3
        assert result["meta"]["total_collected"] == 3
        assert result["meta"]["pages_fetched"] == 1

    def test_multiple_pages_fetch(self):
        """Test fetching across multiple pages."""
        mock_api = MagicMock()
        # Page 1: 100 results (full page)
        # Page 2: 100 results (full page)
        # Page 3: 50 results (less than page_size, signals end of data)
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100)],
            },
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100, 200)],
            },
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(200, 250)],
            }
        ]

        result = paginated_fetch(
            mock_api,
            total=250,
            page_size=100,
            show_progress=False,
            filters={"country": ["us"]}
        )

        assert mock_api.call_count == 3
        assert len(result["data"]) == 250
        assert result["meta"]["total_collected"] == 250
        assert result["meta"]["pages_fetched"] == 3

    def test_stops_when_no_more_data(self):
        """Test that fetching stops when API returns empty data."""
        mock_api = MagicMock()
        # API has 100 available but returns empty on page 2
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100)],
                "meta": {"page": 1, "size": 100, "total": 500}
            },
            {
                "status": "success",
                "data": [],
                "meta": {"page": 2, "size": 100, "total": 500}
            }
        ]

        result = paginated_fetch(
            mock_api,
            total=500,  # Request more than available
            page_size=100,
            show_progress=False,
            filters={}
        )

        # Should stop after getting empty response
        assert mock_api.call_count == 2
        assert len(result["data"]) == 100
        assert result["meta"]["total_collected"] == 100

    def test_stops_when_api_total_reached(self):
        """Test that fetching stops when API returns fewer results than requested."""
        mock_api = MagicMock()
        # API returns only 30 results when we asked for 100
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": str(i)} for i in range(30)],
            "meta": {"page": 1, "size": 30, "total": 30}
        }

        result = paginated_fetch(
            mock_api,
            total=100,  # Request more than available
            page_size=100,
            show_progress=False,
            filters={}
        )

        # Should stop after 1 call since we got fewer results than page_size
        assert mock_api.call_count == 1
        assert len(result["data"]) == 30
        assert result["meta"]["total_collected"] == 30

    def test_trims_to_exact_total(self):
        """Test that results are trimmed to exact total requested."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": str(i)} for i in range(100)],
            "meta": {"page": 1, "size": 100, "total": 100}
        }

        result = paginated_fetch(
            mock_api,
            total=50,  # Request less than page returns
            page_size=100,
            show_progress=False,
            filters={}
        )

        assert len(result["data"]) == 50
        assert result["meta"]["total_collected"] == 50
        assert result["meta"]["total_requested"] == 50

    def test_invalid_total_raises_error(self):
        """Test that negative or zero total raises ValueError."""
        mock_api = MagicMock()

        with pytest.raises(ValueError, match="Total must be positive"):
            paginated_fetch(mock_api, total=0, show_progress=False)

        with pytest.raises(ValueError, match="Total must be positive"):
            paginated_fetch(mock_api, total=-10, show_progress=False)

    def test_api_error_is_propagated(self):
        """Test that API errors are propagated after showing warning."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100)],  # Full page to continue
            },
            Exception("API Error")
        ]

        with pytest.raises(Exception, match="API Error"):
            paginated_fetch(
                mock_api,
                total=200,
                page_size=100,
                show_progress=False,
                filters={}
            )

    def test_passes_kwargs_to_api(self):
        """Test that kwargs are passed through to the API method."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}],
        }

        paginated_fetch(
            mock_api,
            total=1,
            page_size=50,
            show_progress=False,
            filters={"country": ["us"]},
            mode="preview"
        )

        # page_size is clamped to min(50, total=1) = 1
        mock_api.assert_called_once_with(
            filters={"country": ["us"]},
            mode="preview",
            size=1,         # total
            page_size=1,    # clamped to total
            page=1
        )

    def test_adjusts_last_page_size(self):
        """Test that size (total) and page_size are passed correctly."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100)],
            },
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(100, 150)],
            }
        ]

        paginated_fetch(
            mock_api,
            total=150,
            page_size=100,
            show_progress=False,
            filters={}
        )

        # Both calls should have size=150 (total) and page_size=100
        calls = mock_api.call_args_list
        assert calls[0][1]["size"] == 150      # total
        assert calls[0][1]["page_size"] == 100  # per page
        assert calls[1][1]["size"] == 150      # total
        assert calls[1][1]["page_size"] == 100  # per page

    @patch("explorium_cli.pagination.click.echo")
    def test_shows_progress(self, mock_echo):
        """Test that progress messages are shown when enabled."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}],
            "meta": {"page": 1, "size": 100, "total": 1}
        }

        paginated_fetch(
            mock_api,
            total=1,
            page_size=100,
            show_progress=True,
            filters={}
        )

        # Should have called echo for progress messages
        assert mock_echo.call_count >= 1

    @patch("explorium_cli.pagination.click.echo")
    def test_no_progress_when_disabled(self, mock_echo):
        """Test that no progress messages are shown when disabled."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}],
            "meta": {"page": 1, "size": 100, "total": 1}
        }

        paginated_fetch(
            mock_api,
            total=1,
            page_size=100,
            show_progress=False,
            filters={}
        )

        mock_echo.assert_not_called()

    def test_response_structure(self):
        """Test that the response has the expected structure."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}],
        }

        result = paginated_fetch(
            mock_api,
            total=1,
            page_size=100,
            show_progress=False,
            filters={}
        )

        assert "status" in result
        assert "data" in result
        assert "meta" in result
        assert result["status"] == "success"
        assert isinstance(result["data"], list)
        assert "total_requested" in result["meta"]
        assert "total_collected" in result["meta"]
        assert "pages_fetched" in result["meta"]

    def test_page_size_clamped_to_total(self):
        """Test that page_size is clamped to total to avoid API 422 error.

        Regression: `prospects search --total 3` sent size=3, page_size=100
        which the API rejected because size must be >= page_size.
        """
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        }

        result = paginated_fetch(
            mock_api,
            total=3,
            page_size=100,  # page_size > total
            show_progress=False,
            filters={"country": ["us"]}
        )

        # page_size should be clamped to 3 (total)
        call_kwargs = mock_api.call_args[1]
        assert call_kwargs["page_size"] == 3  # clamped from 100
        assert call_kwargs["size"] == 3       # total
        assert len(result["data"]) == 3

    def test_page_size_not_clamped_when_smaller(self):
        """Test that page_size is unchanged when already <= total."""
        mock_api = MagicMock()
        mock_api.return_value = {
            "status": "success",
            "data": [{"id": str(i)} for i in range(25)],
        }

        paginated_fetch(
            mock_api,
            total=50,
            page_size=25,  # page_size < total, no clamping
            show_progress=False,
            filters={}
        )

        call_kwargs = mock_api.call_args[1]
        assert call_kwargs["page_size"] == 25  # unchanged
        assert call_kwargs["size"] == 50       # total

    def test_custom_page_size(self):
        """Test fetching with custom page size."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(25)],
                "meta": {"page": 1, "size": 25, "total": 50}
            },
            {
                "status": "success",
                "data": [{"id": str(i)} for i in range(25, 50)],
                "meta": {"page": 2, "size": 25, "total": 50}
            }
        ]

        result = paginated_fetch(
            mock_api,
            total=50,
            page_size=25,
            show_progress=False,
            filters={}
        )

        assert mock_api.call_count == 2
        assert len(result["data"]) == 50
        assert result["meta"]["total_collected"] == 50
