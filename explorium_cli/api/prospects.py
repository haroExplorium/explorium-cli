"""Prospect API client for Explorium."""

from typing import Any, Optional

from explorium_cli.api.client import ExploriumAPI


class ProspectsAPI:
    """API client for prospect-related endpoints."""

    def __init__(self, client: ExploriumAPI):
        """
        Initialize the Prospects API.

        Args:
            client: The base Explorium API client.
        """
        self.client = client

    def match(self, prospects: list[dict]) -> dict:
        """
        Match prospects to get unique prospect IDs.

        Args:
            prospects: List of prospect dicts with name, linkedin, etc.

        Returns:
            API response with matched prospects.
        """
        return self.client.post(
            "/prospects/match",
            json={"prospects_to_match": prospects}
        )

    def search(
        self,
        filters: dict,
        mode: str = "full",
        size: int = 100,
        page_size: int = 100,
        page: int = 1
    ) -> dict:
        """
        Search and filter prospects.

        Args:
            filters: Search filters (business_id, job_level, department, etc.).
            mode: Search mode ('full' or 'preview').
            size: Total number of results to return (max 60,000).
            page_size: Number of results per page (max 500).
            page: Page number.

        Returns:
            API response with matching prospects.
        """
        return self.client.post(
            "/prospects",
            json={
                "mode": mode,
                "size": size,
                "page_size": page_size,
                "page": page,
                "filters": filters
            }
        )

    def enrich_contacts(self, prospect_id: str) -> dict:
        """
        Enrich prospect contact information.

        Args:
            prospect_id: The prospect ID to enrich.

        Returns:
            API response with contact info (emails, phones).
        """
        return self.client.post(
            "/prospects/contacts_information/enrich",
            json={"prospect_id": prospect_id}
        )

    def enrich_social(self, prospect_id: str) -> dict:
        """
        Enrich prospect social media profiles (LinkedIn posts).

        Args:
            prospect_id: The prospect ID to enrich.

        Returns:
            API response with LinkedIn posts and activity.
        """
        return self.client.post(
            "/prospects/linkedin_posts/enrich",
            json={"prospect_id": prospect_id}
        )

    def enrich_profile(self, prospect_id: str) -> dict:
        """
        Enrich prospect professional profile.

        Args:
            prospect_id: The prospect ID to enrich.

        Returns:
            API response with professional profile.
        """
        return self.client.post(
            "/prospects/profiles/enrich",
            json={"prospect_id": prospect_id}
        )

    def bulk_enrich(
        self,
        prospect_ids: list[str],
        enrich_types: Optional[list[str]] = None
    ) -> dict:
        """
        Bulk enrich multiple prospects (up to 50) with contact information.

        Args:
            prospect_ids: List of prospect IDs to enrich.
            enrich_types: Optional list of enrichment types.

        Returns:
            API response with enriched prospects.
        """
        payload: dict[str, Any] = {"prospect_ids": prospect_ids}
        if enrich_types:
            payload["enrich_types"] = enrich_types

        return self.client.post("/prospects/contacts_information/bulk_enrich", json=payload)

    def bulk_enrich_profiles(self, prospect_ids: list[str]) -> dict:
        """
        Bulk enrich multiple prospects (up to 50) with professional profile data.

        Args:
            prospect_ids: List of prospect IDs to enrich.

        Returns:
            API response with enriched prospect profiles.
        """
        return self.client.post(
            "/prospects/profiles/bulk_enrich",
            json={"prospect_ids": prospect_ids}
        )

    def bulk_enrich_all(self, prospect_ids: list[str]) -> dict:
        """
        Bulk enrich multiple prospects (up to 50) with all available data
        (contacts, social, and profiles).

        Args:
            prospect_ids: List of prospect IDs to enrich.

        Returns:
            API response with fully enriched prospects.
        """
        return self.client.post(
            "/prospects/enrich/bulk",
            json={"prospect_ids": prospect_ids}
        )

    def autocomplete(self, query: str) -> dict:
        """
        Get autocomplete suggestions for prospect names.

        Args:
            query: Search query string.

        Returns:
            API response with autocomplete suggestions.
        """
        return self.client.get(
            "/prospects/autocomplete",
            params={"query": query}
        )

    def statistics(
        self,
        filters: dict,
        group_by: Optional[list[str]] = None
    ) -> dict:
        """
        Get aggregated prospect statistics.

        Args:
            filters: Filter criteria.
            group_by: Fields to group by.

        Returns:
            API response with aggregated statistics.
        """
        payload: dict[str, Any] = {"filters": filters}
        if group_by:
            payload["group_by"] = group_by

        return self.client.post("/prospects/statistics", json=payload)

    def list_events(
        self,
        prospect_ids: list[str],
        event_types: list[str]
    ) -> dict:
        """
        List events for prospects.

        Args:
            prospect_ids: List of prospect IDs.
            event_types: List of event types to filter.

        Returns:
            API response with prospect events.
        """
        payload: dict[str, Any] = {
            "prospect_ids": prospect_ids,
            "event_types": event_types
        }

        return self.client.post("/prospects/events", json=payload)

    def enroll_events(
        self,
        prospect_ids: list[str],
        event_types: list[str],
        enrollment_key: str
    ) -> dict:
        """
        Enroll prospects for event monitoring.

        Args:
            prospect_ids: List of prospect IDs to monitor.
            event_types: List of event types to subscribe to.
            enrollment_key: Unique key for this enrollment.

        Returns:
            API response confirming enrollment.
        """
        return self.client.post(
            "/prospects/events/enrollments",
            json={
                "prospect_ids": prospect_ids,
                "event_types": event_types,
                "enrollment_key": enrollment_key
            }
        )

    def list_enrollments(self) -> dict:
        """
        List all event enrollments.

        Returns:
            API response with enrollment list.
        """
        return self.client.get("/prospects/events/enrollments")
