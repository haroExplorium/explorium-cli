"""Base API client for Explorium."""

import time
import requests
from typing import Any, Optional


class APIError(Exception):
    """Exception raised for API errors."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[dict] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES = {422, 429, 500, 502, 503, 504}


class ExploriumAPI:
    """Base API client for Explorium endpoints."""

    BASE_URL = "https://api.explorium.ai/v1"

    def __init__(
        self,
        api_key: str,
        base_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        retry_backoff: float = 2.0,
        timeout: int = 30
    ):
        """
        Initialize the Explorium API client.

        Args:
            api_key: The API key for authentication.
            base_url: Optional custom base URL.
            max_retries: Maximum number of retry attempts (default: 3).
            retry_delay: Initial delay between retries in seconds (default: 1.0).
            retry_backoff: Multiplier for exponential backoff (default: 2.0).
            timeout: Request timeout in seconds (default: 30).
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_backoff = retry_backoff
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "API_KEY": api_key,
            "Content-Type": "application/json",
        })

    def _should_retry(self, exception: Exception) -> bool:
        """
        Determine if the request should be retried based on the exception.

        Args:
            exception: The exception that was raised.

        Returns:
            True if the request should be retried, False otherwise.
        """
        if isinstance(exception, requests.exceptions.HTTPError):
            if exception.response is not None:
                return exception.response.status_code in RETRYABLE_STATUS_CODES
        elif isinstance(exception, (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        )):
            return True
        return False

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        **kwargs: Any
    ) -> dict:
        """
        Make an API request with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (without base URL).
            params: Query parameters.
            json: JSON body for POST/PUT requests.
            **kwargs: Additional arguments for requests.

        Returns:
            JSON response as dictionary.

        Raises:
            APIError: If the request fails after all retries.
        """
        url = f"{self.base_url}{endpoint}"
        kwargs.setdefault("timeout", self.timeout)

        last_exception: Optional[Exception] = None
        delay = self.retry_delay

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    **kwargs
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                last_exception = e
                if not self._should_retry(e) or attempt >= self.max_retries:
                    error_response: Optional[dict] = None
                    try:
                        error_response = e.response.json()
                    except (ValueError, AttributeError):
                        pass
                    raise APIError(
                        f"API request failed: {e}",
                        status_code=e.response.status_code if e.response else None,
                        response=error_response
                    )

            except (
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as e:
                last_exception = e
                if attempt >= self.max_retries:
                    raise APIError(f"Request failed after {self.max_retries} retries: {e}")

            except requests.exceptions.RequestException as e:
                raise APIError(f"Request failed: {e}")

            except Exception as e:
                # Catch-all: wrap any unexpected exception as APIError
                # so callers only need to handle APIError
                raise APIError(f"Unexpected error: {e}")

            # Wait before retrying with exponential backoff
            time.sleep(delay)
            delay *= self.retry_backoff

        # This should not be reached, but just in case
        raise APIError(f"Request failed: {last_exception}")

    def get(self, endpoint: str, params: Optional[dict] = None, **kwargs: Any) -> dict:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params, **kwargs)

    def post(self, endpoint: str, json: Optional[dict] = None, **kwargs: Any) -> dict:
        """Make a POST request."""
        return self._request("POST", endpoint, json=json, **kwargs)

    def put(self, endpoint: str, json: Optional[dict] = None, **kwargs: Any) -> dict:
        """Make a PUT request."""
        return self._request("PUT", endpoint, json=json, **kwargs)

    def delete(self, endpoint: str, **kwargs: Any) -> dict:
        """Make a DELETE request."""
        return self._request("DELETE", endpoint, **kwargs)
