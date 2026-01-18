"""Tests for the Webhooks API module."""

import pytest
from unittest.mock import MagicMock

from explorium_cli.api.client import ExploriumAPI
from explorium_cli.api.webhooks import WebhooksAPI


class TestWebhooksAPIInit:
    """Tests for WebhooksAPI initialization."""

    def test_init_with_client(self):
        """Test WebhooksAPI initializes with client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        api = WebhooksAPI(mock_client)
        assert api.client == mock_client


class TestWebhooksCreate:
    """Tests for webhook creation."""

    @pytest.fixture
    def api(self) -> WebhooksAPI:
        """Create a WebhooksAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return WebhooksAPI(mock_client)

    def test_create_webhook(self, api: WebhooksAPI):
        """Test creating a webhook."""
        partner_id = "my_partner"
        webhook_url = "https://myapp.com/webhook"

        api.create(partner_id, webhook_url)

        api.client.post.assert_called_once_with(
            "/webhooks",
            json={
                "partner_id": partner_id,
                "webhook_url": webhook_url
            }
        )

    def test_create_webhook_with_special_url(self, api: WebhooksAPI):
        """Test creating a webhook with special URL."""
        partner_id = "partner_123"
        webhook_url = "https://api.example.com/v1/webhook?token=abc123"

        api.create(partner_id, webhook_url)

        api.client.post.assert_called_once_with(
            "/webhooks",
            json={
                "partner_id": partner_id,
                "webhook_url": webhook_url
            }
        )


class TestWebhooksGet:
    """Tests for getting webhook configuration."""

    @pytest.fixture
    def api(self) -> WebhooksAPI:
        """Create a WebhooksAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return WebhooksAPI(mock_client)

    def test_get_webhook(self, api: WebhooksAPI):
        """Test getting a webhook."""
        partner_id = "my_partner"

        api.get(partner_id)

        api.client.get.assert_called_once_with("/webhooks/my_partner")

    def test_get_webhook_special_id(self, api: WebhooksAPI):
        """Test getting a webhook with special partner ID."""
        partner_id = "partner-123_test"

        api.get(partner_id)

        api.client.get.assert_called_once_with("/webhooks/partner-123_test")


class TestWebhooksUpdate:
    """Tests for updating webhook URL."""

    @pytest.fixture
    def api(self) -> WebhooksAPI:
        """Create a WebhooksAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return WebhooksAPI(mock_client)

    def test_update_webhook(self, api: WebhooksAPI):
        """Test updating a webhook URL."""
        partner_id = "my_partner"
        new_url = "https://newapp.com/webhook"

        api.update(partner_id, new_url)

        api.client.put.assert_called_once_with(
            "/webhooks/my_partner",
            json={"webhook_url": new_url}
        )


class TestWebhooksDelete:
    """Tests for deleting webhooks."""

    @pytest.fixture
    def api(self) -> WebhooksAPI:
        """Create a WebhooksAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return WebhooksAPI(mock_client)

    def test_delete_webhook(self, api: WebhooksAPI):
        """Test deleting a webhook."""
        partner_id = "my_partner"

        api.delete(partner_id)

        api.client.delete.assert_called_once_with("/webhooks/my_partner")


class TestWebhooksAPIIntegration:
    """Integration-style tests for WebhooksAPI."""

    @pytest.fixture
    def api(self) -> WebhooksAPI:
        """Create a WebhooksAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return WebhooksAPI(mock_client)

    def test_full_webhook_lifecycle(self, api: WebhooksAPI):
        """Test full webhook CRUD lifecycle."""
        partner_id = "test_partner"
        original_url = "https://original.com/hook"
        updated_url = "https://updated.com/hook"

        # Create
        api.create(partner_id, original_url)
        assert api.client.post.called

        # Get
        api.get(partner_id)
        assert api.client.get.called

        # Update
        api.update(partner_id, updated_url)
        assert api.client.put.called

        # Delete
        api.delete(partner_id)
        assert api.client.delete.called

    def test_webhook_url_formats(self, api: WebhooksAPI):
        """Test various webhook URL formats are accepted."""
        partner_id = "test"
        urls = [
            "https://example.com/webhook",
            "https://api.example.com/v1/hooks/incoming",
            "https://example.com/webhook?secret=abc",
            "https://example.com:8443/webhook",
        ]

        for url in urls:
            api.create(partner_id, url)

        assert api.client.post.call_count == len(urls)
