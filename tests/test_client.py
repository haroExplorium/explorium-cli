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
                json=None,
                timeout=30
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
                json={"businesses_to_match": []},
                timeout=30
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
                json={"url": "https://new.url.com"},
                timeout=30
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
                json=None,
                timeout=30
            )
            assert result == {"status": "success", "data": []}


class TestExploriumAPIErrorHandling:
    """Tests for API error handling."""

    @pytest.fixture
    def api_client(self) -> ExploriumAPI:
        """Create an API client for testing with no retries."""
        return ExploriumAPI(api_key="test_key", max_retries=0)

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


class TestExploriumAPIRetry:
    """Tests for API retry mechanism."""

    def test_retry_on_500_error(self):
        """Test that 500 errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "Server error"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_retry_on_connection_error(self):
        """Test that connection errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[
                requests.exceptions.ConnectionError("Connection refused"),
                mock_response_success
            ]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_retry_on_timeout(self):
        """Test that timeout errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[
                requests.exceptions.Timeout("Request timed out"),
                mock_response_success
            ]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_no_retry_on_400_error(self):
        """Test that 400 errors do not trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 400
            assert mock_req.call_count == 1

    def test_max_retries_exceeded(self):
        """Test that error is raised after max retries exceeded."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"error": "Service unavailable"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 503
            assert mock_req.call_count == 3  # Initial + 2 retries

    def test_custom_retry_settings(self):
        """Test client with custom retry settings."""
        api = ExploriumAPI(
            api_key="test_key",
            max_retries=5,
            retry_delay=0.5,
            retry_backoff=3.0,
            timeout=60
        )
        assert api.max_retries == 5
        assert api.retry_delay == 0.5
        assert api.retry_backoff == 3.0
        assert api.timeout == 60

    def test_retry_on_rate_limit(self):
        """Test that 429 rate limit errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=1, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 429
        mock_response_fail.json.return_value = {"error": "Rate limited"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_retry_on_502_bad_gateway(self):
        """Test that 502 Bad Gateway errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=1, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 502
        mock_response_fail.json.return_value = {"error": "Bad Gateway"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_retry_on_422_unprocessable_entity(self):
        """Test that 422 Unprocessable Entity errors trigger retries (transient API issues)."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 422
        mock_response_fail.json.return_value = {"error": "Unprocessable Entity"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    @patch('time.sleep')
    def test_retry_on_422_with_backoff(self, mock_sleep):
        """Test that 422 retries use exponential backoff."""
        api = ExploriumAPI(
            api_key="test_key",
            max_retries=2,
            retry_delay=1.0,
            retry_backoff=2.0
        )

        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"error": "Unprocessable Entity"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 422

        # Verify exponential backoff delays: 1.0, 2.0
        assert mock_sleep.call_count == 2
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0

    def test_retry_on_504_gateway_timeout(self):
        """Test that 504 Gateway Timeout errors trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=1, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 504
        mock_response_fail.json.return_value = {"error": "Gateway Timeout"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 2

    def test_no_retry_on_401_unauthorized(self):
        """Test that 401 Unauthorized errors do not trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 401
            assert mock_req.call_count == 1

    def test_no_retry_on_403_forbidden(self):
        """Test that 403 Forbidden errors do not trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {"error": "Forbidden"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 403
            assert mock_req.call_count == 1

    def test_no_retry_on_404_not_found(self):
        """Test that 404 Not Found errors do not trigger retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=2, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Not found"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 404
            assert mock_req.call_count == 1

    def test_retry_post_request(self):
        """Test that POST requests also retry on server errors."""
        api = ExploriumAPI(api_key="test_key", max_retries=1, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 500
        mock_response_fail.json.return_value = {"error": "Server error"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "created"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.post("/businesses/match", json={"name": "Test"})
            assert result == {"status": "created"}
            assert mock_req.call_count == 2
            # Verify POST parameters are preserved on retry
            for call in mock_req.call_args_list:
                assert call[0][0] == "POST"
                assert call[1]["json"] == {"name": "Test"}

    def test_retry_preserves_request_parameters(self):
        """Test that retry preserves all request parameters."""
        api = ExploriumAPI(api_key="test_key", max_retries=1, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.json.return_value = {"error": "Service unavailable"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"data": []}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[mock_response_fail, mock_response_success]
        ) as mock_req:
            result = api.get("/businesses/autocomplete", params={"query": "test"})
            assert result == {"data": []}
            assert mock_req.call_count == 2
            # Verify params are preserved on retry
            for call in mock_req.call_args_list:
                assert call[1]["params"] == {"query": "test"}

    @patch('time.sleep')
    def test_exponential_backoff(self, mock_sleep):
        """Test that retry uses exponential backoff."""
        api = ExploriumAPI(
            api_key="test_key",
            max_retries=3,
            retry_delay=1.0,
            retry_backoff=2.0
        )

        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {"error": "Service unavailable"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response):
            with pytest.raises(APIError):
                api.get("/test")

        # Verify exponential backoff delays: 1.0, 2.0, 4.0
        assert mock_sleep.call_count == 3
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
        assert sleep_calls[2] == 4.0

    def test_retry_with_zero_max_retries(self):
        """Test that max_retries=0 means no retries."""
        api = ExploriumAPI(api_key="test_key", max_retries=0, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Server error"}
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error

        with patch.object(api.session, "request", return_value=mock_response) as mock_req:
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 500
            assert mock_req.call_count == 1  # Only initial request, no retries

    def test_retry_multiple_failures_then_success(self):
        """Test retry succeeds after multiple failures."""
        api = ExploriumAPI(api_key="test_key", max_retries=3, retry_delay=0.01)

        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503
        mock_response_fail.json.return_value = {"error": "Service unavailable"}
        http_error = requests.exceptions.HTTPError(response=mock_response_fail)
        mock_response_fail.raise_for_status.side_effect = http_error

        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {"status": "success"}
        mock_response_success.raise_for_status.return_value = None

        with patch.object(
            api.session,
            "request",
            side_effect=[
                mock_response_fail,
                mock_response_fail,
                mock_response_fail,
                mock_response_success
            ]
        ) as mock_req:
            result = api.get("/test")
            assert result == {"status": "success"}
            assert mock_req.call_count == 4  # Initial + 3 retries

    def test_unexpected_exception_wrapped_as_api_error(self):
        """Test that unexpected exceptions (e.g., JSONDecodeError) are wrapped as APIError."""
        api = ExploriumAPI(api_key="test_key", max_retries=0, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        # Simulate response.json() raising an unexpected error
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")

        with patch.object(api.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert "Unexpected error" in exc_info.value.message

    def test_raw_http_error_wrapped_as_api_error(self):
        """Test that a raw HTTPError that somehow bypasses specific handlers is wrapped."""
        api = ExploriumAPI(api_key="test_key", max_retries=0, retry_delay=0.01)

        mock_response = MagicMock()
        mock_response.status_code = 422

        # Simulate raise_for_status raising, but response.json() also failing
        http_error = requests.exceptions.HTTPError(response=mock_response)
        mock_response.raise_for_status.side_effect = http_error
        mock_response.json.return_value = {"error": "Unprocessable Entity"}

        with patch.object(api.session, "request", return_value=mock_response):
            with pytest.raises(APIError) as exc_info:
                api.get("/test")
            assert exc_info.value.status_code == 422
