"""Tests for the Businesses API module."""

import pytest
from unittest.mock import MagicMock, patch

from explorium_cli.api.client import ExploriumAPI
from explorium_cli.api.businesses import BusinessesAPI


class TestBusinessesAPIInit:
    """Tests for BusinessesAPI initialization."""

    def test_init_with_client(self):
        """Test BusinessesAPI initializes with client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        api = BusinessesAPI(mock_client)
        assert api.client == mock_client


class TestBusinessesMatch:
    """Tests for business match endpoint."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_match_single_business(self, api: BusinessesAPI):
        """Test matching a single business."""
        businesses = [{"name": "Starbucks", "website": "starbucks.com"}]
        api.match(businesses)

        api.client.post.assert_called_once_with(
            "/businesses/match",
            json={"businesses_to_match": businesses}
        )

    def test_match_multiple_businesses(self, api: BusinessesAPI):
        """Test matching multiple businesses."""
        businesses = [
            {"name": "Company A", "website": "companya.com"},
            {"name": "Company B", "website": "companyb.com"}
        ]
        api.match(businesses)

        api.client.post.assert_called_once_with(
            "/businesses/match",
            json={"businesses_to_match": businesses}
        )

    def test_match_with_linkedin(self, api: BusinessesAPI):
        """Test matching with LinkedIn URL."""
        businesses = [{"linkedin_company_url": "https://linkedin.com/company/test"}]
        api.match(businesses)

        api.client.post.assert_called_once()


class TestBusinessesSearch:
    """Tests for business search endpoint."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_search_basic(self, api: BusinessesAPI):
        """Test basic search."""
        filters = {"country": ["us"]}
        api.search(filters)

        api.client.post.assert_called_once_with(
            "/businesses",
            json={
                "mode": "full",
                "size": 100,
                "page_size": 100,
                "page": 1,
                "filters": filters
            }
        )

    def test_search_with_pagination(self, api: BusinessesAPI):
        """Test search with pagination."""
        filters = {"country": ["us"]}
        api.search(filters, size=500, page_size=50, page=2)

        api.client.post.assert_called_once_with(
            "/businesses",
            json={
                "mode": "full",
                "size": 500,
                "page_size": 50,
                "page": 2,
                "filters": filters
            }
        )

    def test_search_preview_mode(self, api: BusinessesAPI):
        """Test search in preview mode."""
        filters = {"country": ["us"]}
        api.search(filters, mode="preview")

        api.client.post.assert_called_once_with(
            "/businesses",
            json={
                "mode": "preview",
                "size": 100,
                "page_size": 100,
                "page": 1,
                "filters": filters
            }
        )

    def test_search_complex_filters(self, api: BusinessesAPI):
        """Test search with complex filters."""
        filters = {
            "country": ["us", "ca"],
            "employee_count": ["51-200", "201-500"],
            "revenue": ["10M-50M"],
            "technologies": ["Python", "React"]
        }
        api.search(filters)

        api.client.post.assert_called_once()
        call_args = api.client.post.call_args
        assert call_args[1]["json"]["filters"] == filters


class TestBusinessesEnrich:
    """Tests for business enrichment endpoints."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_enrich_single(self, api: BusinessesAPI):
        """Test single business enrichment."""
        business_id = "abc123"
        api.enrich(business_id)

        api.client.post.assert_called_once_with(
            "/businesses/firmographics/enrich",
            json={"business_id": business_id}
        )

    def test_bulk_enrich(self, api: BusinessesAPI):
        """Test bulk business enrichment."""
        business_ids = ["id1", "id2", "id3"]
        api.bulk_enrich(business_ids)

        api.client.post.assert_called_once_with(
            "/businesses/firmographics/bulk_enrich",
            json={"business_ids": business_ids}
        )

    def test_bulk_enrich_max_50(self, api: BusinessesAPI):
        """Test bulk enrichment with 50 IDs (max limit)."""
        business_ids = [f"id{i}" for i in range(50)]
        api.bulk_enrich(business_ids)

        api.client.post.assert_called_once()
        call_args = api.client.post.call_args
        assert len(call_args[1]["json"]["business_ids"]) == 50


class TestBusinessesLookalike:
    """Tests for business lookalike endpoint."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_lookalike_basic(self, api: BusinessesAPI):
        """Test basic lookalike search."""
        business_id = "abc123"
        api.lookalike(business_id)

        api.client.post.assert_called_once_with(
            "/businesses/lookalikes/enrich",
            json={"business_id": business_id}
        )


class TestBusinessesAutocomplete:
    """Tests for business autocomplete endpoint."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_autocomplete(self, api: BusinessesAPI):
        """Test autocomplete."""
        query = "star"
        api.autocomplete(query)

        api.client.get.assert_called_once_with(
            "/businesses/autocomplete",
            params={"query": query, "field": "company_name"}
        )


class TestBusinessesEvents:
    """Tests for business events endpoints."""

    @pytest.fixture
    def api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return BusinessesAPI(mock_client)

    def test_list_events(self, api: BusinessesAPI):
        """Test listing events."""
        business_ids = ["id1", "id2"]
        event_types = ["new_funding_round", "new_product"]
        api.list_events(business_ids, event_types)

        api.client.post.assert_called_once_with(
            "/businesses/events",
            json={"business_ids": business_ids, "event_types": event_types}
        )

    def test_enroll_events(self, api: BusinessesAPI):
        """Test enrolling for event monitoring."""
        business_ids = ["id1", "id2"]
        event_types = ["new_funding_round"]
        enrollment_key = "my_enrollment"

        api.enroll_events(business_ids, event_types, enrollment_key)

        api.client.post.assert_called_once_with(
            "/businesses/events/enrollments",
            json={
                "business_ids": business_ids,
                "event_types": event_types,
                "enrollment_key": enrollment_key
            }
        )

    def test_list_enrollments(self, api: BusinessesAPI):
        """Test listing enrollments."""
        api.list_enrollments()

        api.client.get.assert_called_once_with("/businesses/events/enrollments")
