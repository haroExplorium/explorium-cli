"""Tests for the base API client."""

import pytest
import requests
from unittest.mock import MagicMock, patch, Mock

from explorium_cli.api.client import ExploriumAPI, APIError


class TestExploriumAPIInit:
    """Tests for ExploriumAPI initialization."""

    def test_init_with_api_key(self):
        """Test client initializes with API key."""
        api = ExploriumAPI(api_key="test_key")
        assert api.api_key == "test_key"
        assert api.base_url == "https://api.explorium.ai/v1"

    def test_init_with_custom_base_url(self):
        """Test client initializes with custom base URL."""
        api = ExploriumAPI(api_key="test_key", base_url="https://custom.api.com/v1")
        assert api.base_url == "https://custom.api.com/v1"

    def test_init_sets_headers(self):
        """Test client sets correct headers."""
        api = ExploriumAPI(api_key="test_key")
        assert api.session.headers["API_KEY"] == "test_key"
        assert api.session.headers["Content-Type"] == "application/json"


class TestExploriumAPIRequests:
    """Tests for ExploriumAPI request methods."""

    @pytest.fixture
    def api_client(self) -> ExploriumAPI:
        """Create an API client for testing."""
        return ExploriumAPI(api_key="test_key")

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock response."""
        response = MagicMock()
        response.json.return_value = {"status": "success", "data": []}
        response.raise_for_status.return_value = None
        return response

    def test_get_request(self, api_client: ExploriumAPI, mock_response: MagicMock):
        """Test GET request."""
        with patch.object(api_client.session, "request", return_value=mock_response) as mock_req:
            result = api_client.get("/businesses/autocomplete", params={"query": "test"})

            mock_req.assert_called_once_with(
                "GET",
                "https://api.explorium.ai/v1/businesses/autocomplete",
                params={"query": "test"},
                json=None
            )
            assert result == {"status": "success", "data": []}

    def test_post_request(self, api_client: ExploriumAPI, mock_response: MagicMock):
        """Test POST request."""
        with patch.object(api_client.session, "request", return_value=mock_response) as mock_req:
            result = api_client.post("/businesses/match", json={"businesses_to_match": []})

            mock_req.assert_called_once_with(
                "POST",
                "https://api.explorium.ai/v1/businesses/match",
                params=None,
                json={"businesses_to_match": []}
            )
            assert result == {"status": "success", "data": []}

    def test_put_request(self, api_client: ExploriumAPI, mock_response: MagicMock):
        """Test PUT request."""
        with patch.object(api_client.session, "request", return_value=mock_response) as mock_req:
            result = api_client.put("/webhooks/partner1", json={"url": "https://new.url.com"})

            mock_req.assert_called_once_with(
                "PUT",
                "https://api.explorium.ai/v1/webhooks/partner1",
                params=None,
                json={"url": "https://new.url.com"}
            )
            assert result == {"status": "success", "data": []}

    def test_delete_request(self, api_client: ExploriumAPI, mock_response: MagicMock):
        """Test DELETE request."""
        with patch.object(api_client.session, "request", return_value=mock_response) as mock_req:
            result = api_client.delete("/webhooks/partner1")

            mock_req.assert_called_once_with(
                "DELETE",
                "https://api.explorium.ai/v1/webhooks/partner1",
                params=None,
                json=None
            )
            assert result == {"status": "success", "data": []}


class TestExploriumAPIErrorHandling:
    """Tests for API error handling."""

    @pytest.fixture
    def api_client(self) -> ExploriumAPI:
        """Create an API client for testing."""
        return ExploriumAPI(api_key="test_key")

    def test_http_error_with_json_response(self, api_client: ExploriumAPI):
        """Test handling HTTP error with JSON error response."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": {"message": "Bad request"}}

        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api_client.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert exc_info.value.status_code == 400
            assert exc_info.value.response == {"error": {"message": "Bad request"}}

    def test_http_error_without_json_response(self, api_client: ExploriumAPI):
        """Test handling HTTP error when response is not JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")

        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api_client.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert exc_info.value.status_code == 500
            assert exc_info.value.response is None

    def test_connection_error(self, api_client: ExploriumAPI):
        """Test handling connection error."""
        with patch.object(
            api_client.session,
            "request",
            side_effect=requests.exceptions.ConnectionError("Connection refused")
        ):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert "Request failed" in exc_info.value.message

    def test_timeout_error(self, api_client: ExploriumAPI):
        """Test handling timeout error."""
        with patch.object(
            api_client.session,
            "request",
            side_effect=requests.exceptions.Timeout("Request timed out")
        ):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert "Request failed" in exc_info.value.message

    def test_unauthorized_error(self, api_client: ExploriumAPI):
        """Test handling 401 unauthorized error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}}

        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api_client.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert exc_info.value.status_code == 401

    def test_not_found_error(self, api_client: ExploriumAPI):
        """Test handling 404 not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}

        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api_client.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/businesses/invalid_id")

            assert exc_info.value.status_code == 404

    def test_rate_limit_error(self, api_client: ExploriumAPI):
        """Test handling 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": {"code": "RATE_LIMIT", "message": "Too many requests"}}

        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api_client.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api_client.get("/test")

            assert exc_info.value.status_code == 429


class TestAPIError:
    """Tests for APIError exception class."""

    def test_api_error_with_all_params(self):
        """Test APIError with all parameters."""
        error = APIError(
            message="Test error",
            status_code=400,
            response={"error": "details"}
        )
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.response == {"error": "details"}
        assert str(error) == "Test error"

    def test_api_error_with_message_only(self):
        """Test APIError with message only."""
        error = APIError(message="Test error")
        assert error.message == "Test error"
        assert error.status_code is None
        assert error.response is None

    def test_api_error_is_exception(self):
        """Test APIError is an Exception."""
        error = APIError(message="Test error")
        assert isinstance(error, Exception)

    def test_api_error_can_be_raised(self):
        """Test APIError can be raised and caught."""
        with pytest.raises(APIError) as exc_info:
            raise APIError("Test error", status_code=500)

        assert exc_info.value.status_code == 500
