"""Webhook API client for Explorium."""

from explorium_cli.api.client import ExploriumAPI


class WebhooksAPI:
    """API client for webhook-related endpoints."""

    def __init__(self, client: ExploriumAPI):
        """
        Initialize the Webhooks API.

        Args:
            client: The base Explorium API client.
        """
        self.client = client

    def create(self, partner_id: str, webhook_url: str) -> dict:
        """
        Create/register a webhook.

        Args:
            partner_id: Unique partner identifier.
            webhook_url: URL to receive webhook notifications.

        Returns:
            API response confirming webhook creation.
        """
        return self.client.post(
            "/webhooks",
            json={
                "partner_id": partner_id,
                "webhook_url": webhook_url
            }
        )

    def get(self, partner_id: str) -> dict:
        """
        Get webhook configuration.

        Args:
            partner_id: The partner ID to get webhook for.

        Returns:
            API response with webhook configuration.
        """
        return self.client.get(f"/webhooks/{partner_id}")

    def update(self, partner_id: str, webhook_url: str) -> dict:
        """
        Update webhook URL.

        Args:
            partner_id: The partner ID to update.
            webhook_url: New webhook URL.

        Returns:
            API response confirming update.
        """
        return self.client.put(
            f"/webhooks/{partner_id}",
            json={"webhook_url": webhook_url}
        )

    def delete(self, partner_id: str) -> dict:
        """
        Delete a webhook.

        Args:
            partner_id: The partner ID to delete webhook for.

        Returns:
            API response confirming deletion.
        """
        return self.client.delete(f"/webhooks/{partner_id}")
