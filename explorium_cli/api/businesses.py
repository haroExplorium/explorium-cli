"""Business API client for Explorium."""

from typing import Any

from explorium_cli.api.client import ExploriumAPI


class BusinessesAPI:
    """API client for business-related endpoints."""

    def __init__(self, client: ExploriumAPI):
        """
        Initialize the Businesses API.

        Args:
            client: The base Explorium API client.
        """
        self.client = client

    def match(self, businesses: list[dict]) -> dict:
        """
        Match businesses to get unique business IDs.

        Args:
            businesses: List of business dicts with name, website, linkedin_company_url.

        Returns:
            API response with matched businesses.
        """
        return self.client.post(
            "/businesses/match",
            json={"businesses_to_match": businesses}
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
        Search and filter businesses.

        Args:
            filters: Search filters (country, size, revenue, etc.).
            mode: Search mode ('full' or 'preview').
            size: Total number of results to return (max 60,000).
            page_size: Number of results per page (max 500).
            page: Page number.

        Returns:
            API response with matching businesses.
        """
        return self.client.post(
            "/businesses",
            json={
                "mode": mode,
                "size": size,
                "page_size": page_size,
                "page": page,
                "filters": filters
            }
        )

    def enrich(self, business_id: str) -> dict:
        """
        Enrich a single business with firmographics data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with enriched business data.
        """
        return self.client.post(
            "/businesses/firmographics/enrich",
            json={"business_id": business_id}
        )

    def enrich_technographics(self, business_id: str) -> dict:
        """
        Enrich a single business with technographics data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with tech stack data.
        """
        return self.client.post(
            "/businesses/technographics/enrich",
            json={"business_id": business_id}
        )

    def enrich_financial(self, business_id: str) -> dict:
        """
        Enrich a single business with financial metrics data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with financial indicators.
        """
        return self.client.post(
            "/businesses/financial_indicators/enrich",
            json={"business_id": business_id}
        )

    def enrich_funding(self, business_id: str) -> dict:
        """
        Enrich a single business with funding and acquisition data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with funding and acquisition info.
        """
        return self.client.post(
            "/businesses/funding_and_acquisition/enrich",
            json={"business_id": business_id}
        )

    def enrich_workforce(self, business_id: str) -> dict:
        """
        Enrich a single business with workforce trends data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with workforce trends.
        """
        return self.client.post(
            "/businesses/workforce_trends/enrich",
            json={"business_id": business_id}
        )

    def enrich_traffic(self, business_id: str) -> dict:
        """
        Enrich a single business with website traffic data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with website traffic metrics.
        """
        return self.client.post(
            "/businesses/website_traffic/enrich",
            json={"business_id": business_id}
        )

    def enrich_social(self, business_id: str) -> dict:
        """
        Enrich a single business with social media (LinkedIn posts) data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with LinkedIn posts.
        """
        return self.client.post(
            "/businesses/linkedin_posts/enrich",
            json={"business_id": business_id}
        )

    def enrich_ratings(self, business_id: str) -> dict:
        """
        Enrich a single business with employee ratings data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with company ratings by employees.
        """
        return self.client.post(
            "/businesses/company_ratings_by_employees/enrich",
            json={"business_id": business_id}
        )

    def enrich_keywords(self, business_id: str, keywords: list[str]) -> dict:
        """
        Enrich a single business with website keyword search data.

        Args:
            business_id: The business ID to enrich.
            keywords: List of keywords to search for.

        Returns:
            API response with keyword search results.
        """
        return self.client.post(
            "/businesses/company_website_keywords/enrich",
            json={
                "business_id": business_id,
                "parameters": {"keywords": keywords}
            }
        )

    def enrich_challenges(self, business_id: str) -> dict:
        """
        Enrich a public company with business challenges data (from 10-K filings).

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with business challenges.
        """
        return self.client.post(
            "/businesses/pc_business_challenges_10k/enrich",
            json={"business_id": business_id}
        )

    def enrich_competitive(self, business_id: str) -> dict:
        """
        Enrich a public company with competitive landscape data (from 10-K filings).

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with competitive landscape.
        """
        return self.client.post(
            "/businesses/pc_competitive_landscape_10k/enrich",
            json={"business_id": business_id}
        )

    def enrich_strategic(self, business_id: str) -> dict:
        """
        Enrich a public company with strategic insights data (from 10-K filings).

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with strategic insights.
        """
        return self.client.post(
            "/businesses/pc_strategy_10k/enrich",
            json={"business_id": business_id}
        )

    def enrich_website_changes(self, business_id: str) -> dict:
        """
        Enrich a single business with website changes data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with website changes.
        """
        return self.client.post(
            "/businesses/website_changes/enrich",
            json={"business_id": business_id}
        )

    def enrich_webstack(self, business_id: str) -> dict:
        """
        Enrich a single business with webstack data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with webstack info.
        """
        return self.client.post(
            "/businesses/webstack/enrich",
            json={"business_id": business_id}
        )

    def enrich_hierarchy(self, business_id: str) -> dict:
        """
        Enrich a single business with company hierarchy data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with company hierarchy.
        """
        return self.client.post(
            "/businesses/company_hierarchies/enrich",
            json={"business_id": business_id}
        )

    def enrich_intent(self, business_id: str) -> dict:
        """
        Enrich a single business with Bombora intent data.

        Args:
            business_id: The business ID to enrich.

        Returns:
            API response with intent signals.
        """
        return self.client.post(
            "/businesses/bombora_intent/enrich",
            json={"business_id": business_id}
        )

    def bulk_enrich(self, business_ids: list[str]) -> dict:
        """
        Bulk enrich multiple businesses (up to 50).

        Args:
            business_ids: List of business IDs to enrich.

        Returns:
            API response with enriched businesses.
        """
        return self.client.post(
            "/businesses/firmographics/bulk_enrich",
            json={"business_ids": business_ids}
        )

    def _bulk_enrich_endpoint(self, endpoint: str, business_ids: list[str]) -> dict:
        """Call a bulk enrichment endpoint."""
        return self.client.post(endpoint, json={"business_ids": business_ids})

    def bulk_enrich_tech(self, business_ids: list[str]) -> dict:
        """Bulk enrich technographics."""
        return self._bulk_enrich_endpoint("/businesses/technographics/bulk_enrich", business_ids)

    def bulk_enrich_financial(self, business_ids: list[str]) -> dict:
        """Bulk enrich financial indicators."""
        return self._bulk_enrich_endpoint("/businesses/financial_indicators/bulk_enrich", business_ids)

    def bulk_enrich_funding(self, business_ids: list[str]) -> dict:
        """Bulk enrich funding data."""
        return self._bulk_enrich_endpoint("/businesses/funding_and_acquisition/bulk_enrich", business_ids)

    def bulk_enrich_workforce(self, business_ids: list[str]) -> dict:
        """Bulk enrich workforce trends."""
        return self._bulk_enrich_endpoint("/businesses/workforce_trends/bulk_enrich", business_ids)

    def bulk_enrich_traffic(self, business_ids: list[str]) -> dict:
        """Bulk enrich website traffic."""
        return self._bulk_enrich_endpoint("/businesses/website_traffic/bulk_enrich", business_ids)

    def bulk_enrich_social(self, business_ids: list[str]) -> dict:
        """Bulk enrich LinkedIn posts."""
        return self._bulk_enrich_endpoint("/businesses/linkedin_posts/bulk_enrich", business_ids)

    def bulk_enrich_ratings(self, business_ids: list[str]) -> dict:
        """Bulk enrich employee ratings."""
        return self._bulk_enrich_endpoint("/businesses/company_ratings_by_employees/bulk_enrich", business_ids)

    def bulk_enrich_challenges(self, business_ids: list[str]) -> dict:
        """Bulk enrich 10-K challenges."""
        return self._bulk_enrich_endpoint("/businesses/pc_business_challenges_10k/bulk_enrich", business_ids)

    def bulk_enrich_competitive(self, business_ids: list[str]) -> dict:
        """Bulk enrich 10-K competitive landscape."""
        return self._bulk_enrich_endpoint("/businesses/pc_competitive_landscape_10k/bulk_enrich", business_ids)

    def bulk_enrich_strategic(self, business_ids: list[str]) -> dict:
        """Bulk enrich 10-K strategic insights."""
        return self._bulk_enrich_endpoint("/businesses/pc_strategy_10k/bulk_enrich", business_ids)

    def bulk_enrich_website_changes(self, business_ids: list[str]) -> dict:
        """Bulk enrich website changes."""
        return self._bulk_enrich_endpoint("/businesses/website_changes/bulk_enrich", business_ids)

    def bulk_enrich_webstack(self, business_ids: list[str]) -> dict:
        """Bulk enrich webstack."""
        return self._bulk_enrich_endpoint("/businesses/webstack/bulk_enrich", business_ids)

    def bulk_enrich_hierarchy(self, business_ids: list[str]) -> dict:
        """Bulk enrich company hierarchy."""
        return self._bulk_enrich_endpoint("/businesses/company_hierarchies/bulk_enrich", business_ids)

    def bulk_enrich_intent(self, business_ids: list[str]) -> dict:
        """Bulk enrich Bombora intent."""
        return self._bulk_enrich_endpoint("/businesses/bombora_intent/bulk_enrich", business_ids)

    def lookalike(self, business_id: str) -> dict:
        """
        Find similar companies.

        Args:
            business_id: The business ID to find lookalikes for.

        Returns:
            API response with similar businesses.
        """
        return self.client.post(
            "/businesses/lookalikes/enrich",
            json={"business_id": business_id}
        )

    def autocomplete(self, query: str, field: str = "company_name") -> dict:
        """
        Get autocomplete suggestions for company names.

        Args:
            query: Search query string.
            field: Field to autocomplete (default: company_name).

        Returns:
            API response with autocomplete suggestions.
        """
        return self.client.get(
            "/businesses/autocomplete",
            params={"query": query, "field": field}
        )

    def list_events(
        self,
        business_ids: list[str],
        event_types: list[str]
    ) -> dict:
        """
        List events for businesses.

        Args:
            business_ids: List of business IDs.
            event_types: List of event types to filter.

        Returns:
            API response with business events.
        """
        payload: dict[str, Any] = {
            "business_ids": business_ids,
            "event_types": event_types
        }

        return self.client.post("/businesses/events", json=payload)

    def enroll_events(
        self,
        business_ids: list[str],
        event_types: list[str],
        enrollment_key: str
    ) -> dict:
        """
        Enroll businesses for event monitoring.

        Args:
            business_ids: List of business IDs to monitor.
            event_types: List of event types to subscribe to.
            enrollment_key: Unique key for this enrollment.

        Returns:
            API response confirming enrollment.
        """
        return self.client.post(
            "/businesses/events/enrollments",
            json={
                "business_ids": business_ids,
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
        return self.client.get("/businesses/events/enrollments")
