"""Base API client for Explorium."""

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


class ExploriumAPI:
    """Base API client for Explorium endpoints."""

    BASE_URL = "https://api.explorium.ai/v1"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        Initialize the Explorium API client.

        Args:
            api_key: The API key for authentication.
            base_url: Optional custom base URL.
        """
        self.api_key = api_key
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "API_KEY": api_key,
            "Content-Type": "application/json",
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        **kwargs: Any
    ) -> dict:
        """
        Make an API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint (without base URL).
            params: Query parameters.
            json: JSON body for POST/PUT requests.
            **kwargs: Additional arguments for requests.

        Returns:
            JSON response as dictionary.

        Raises:
            APIError: If the request fails.
        """
        url = f"{self.base_url}{endpoint}"

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
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")

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
