"""Tests for the Prospects API module."""

import pytest
from unittest.mock import MagicMock

from explorium_cli.api.client import ExploriumAPI
from explorium_cli.api.prospects import ProspectsAPI


class TestProspectsAPIInit:
    """Tests for ProspectsAPI initialization."""

    def test_init_with_client(self):
        """Test ProspectsAPI initializes with client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        api = ProspectsAPI(mock_client)
        assert api.client == mock_client


class TestProspectsMatch:
    """Tests for prospect match endpoint."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_match_single_prospect(self, api: ProspectsAPI):
        """Test matching a single prospect."""
        prospects = [{"first_name": "John", "last_name": "Doe"}]
        api.match(prospects)

        api.client.post.assert_called_once_with(
            "/prospects/match",
            json={"prospects_to_match": prospects}
        )

    def test_match_multiple_prospects(self, api: ProspectsAPI):
        """Test matching multiple prospects."""
        prospects = [
            {"first_name": "John", "last_name": "Doe"},
            {"first_name": "Jane", "last_name": "Smith"}
        ]
        api.match(prospects)

        api.client.post.assert_called_once_with(
            "/prospects/match",
            json={"prospects_to_match": prospects}
        )

    def test_match_with_linkedin(self, api: ProspectsAPI):
        """Test matching with LinkedIn URL."""
        prospects = [{"linkedin_url": "https://linkedin.com/in/johndoe"}]
        api.match(prospects)

        api.client.post.assert_called_once()


class TestProspectsSearch:
    """Tests for prospect search endpoint."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_search_basic(self, api: ProspectsAPI):
        """Test basic search."""
        filters = {"business_ids": ["abc123"]}
        api.search(filters)

        api.client.post.assert_called_once_with(
            "/prospects",
            json={
                "mode": "full",
                "size": 100,
                "page_size": 100,
                "page": 1,
                "filters": filters
            }
        )

    def test_search_with_pagination(self, api: ProspectsAPI):
        """Test search with pagination."""
        filters = {"business_ids": ["abc123"]}
        api.search(filters, size=500, page_size=50, page=2)

        api.client.post.assert_called_once_with(
            "/prospects",
            json={
                "mode": "full",
                "size": 500,
                "page_size": 50,
                "page": 2,
                "filters": filters
            }
        )

    def test_search_complex_filters(self, api: ProspectsAPI):
        """Test search with complex filters."""
        filters = {
            "business_ids": ["abc123"],
            "job_levels": ["cxo", "vp", "director"],
            "departments": ["Engineering", "Sales"],
            "has_email": True,
            "has_phone": True
        }
        api.search(filters)

        call_args = api.client.post.call_args
        assert call_args[1]["json"]["filters"] == filters


class TestProspectsEnrich:
    """Tests for prospect enrichment endpoints."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_enrich_contacts(self, api: ProspectsAPI):
        """Test contact information enrichment."""
        prospect_id = "prospect123"
        api.enrich_contacts(prospect_id)

        api.client.post.assert_called_once_with(
            "/prospects/contacts_information/enrich",
            json={"prospect_id": prospect_id}
        )

    def test_enrich_social(self, api: ProspectsAPI):
        """Test social media enrichment."""
        prospect_id = "prospect123"
        api.enrich_social(prospect_id)

        api.client.post.assert_called_once_with(
            "/prospects/linkedin_posts/enrich",
            json={"prospect_id": prospect_id}
        )

    def test_enrich_profile(self, api: ProspectsAPI):
        """Test professional profile enrichment."""
        prospect_id = "prospect123"
        api.enrich_profile(prospect_id)

        api.client.post.assert_called_once_with(
            "/prospects/profiles/enrich",
            json={"prospect_id": prospect_id}
        )

    def test_bulk_enrich(self, api: ProspectsAPI):
        """Test bulk prospect enrichment."""
        prospect_ids = ["id1", "id2", "id3"]
        api.bulk_enrich(prospect_ids)

        api.client.post.assert_called_once_with(
            "/prospects/contacts_information/bulk_enrich",
            json={"prospect_ids": prospect_ids}
        )

    def test_bulk_enrich_with_types(self, api: ProspectsAPI):
        """Test bulk enrichment with specific types."""
        prospect_ids = ["id1", "id2"]
        enrich_types = ["contacts", "social"]
        api.bulk_enrich(prospect_ids, enrich_types=enrich_types)

        api.client.post.assert_called_once_with(
            "/prospects/contacts_information/bulk_enrich",
            json={
                "prospect_ids": prospect_ids,
                "enrich_types": enrich_types
            }
        )


class TestProspectsAutocomplete:
    """Tests for prospect autocomplete endpoint."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_autocomplete(self, api: ProspectsAPI):
        """Test autocomplete."""
        query = "john"
        api.autocomplete(query)

        api.client.get.assert_called_once_with(
            "/prospects/autocomplete",
            params={"query": query}
        )


class TestProspectsStatistics:
    """Tests for prospect statistics endpoint."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_statistics_basic(self, api: ProspectsAPI):
        """Test basic statistics."""
        filters = {"business_ids": ["abc123"]}
        api.statistics(filters)

        api.client.post.assert_called_once_with(
            "/prospects/statistics",
            json={"filters": filters}
        )

    def test_statistics_with_group_by(self, api: ProspectsAPI):
        """Test statistics with grouping."""
        filters = {"business_ids": ["abc123"]}
        group_by = ["department", "job_level"]
        api.statistics(filters, group_by=group_by)

        api.client.post.assert_called_once_with(
            "/prospects/statistics",
            json={
                "filters": filters,
                "group_by": group_by
            }
        )


class TestProspectsEvents:
    """Tests for prospect events endpoints."""

    @pytest.fixture
    def api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock(spec=ExploriumAPI)
        return ProspectsAPI(mock_client)

    def test_list_events(self, api: ProspectsAPI):
        """Test listing events."""
        prospect_ids = ["id1", "id2"]
        event_types = ["prospect_changed_company", "prospect_changed_role"]
        api.list_events(prospect_ids, event_types)

        api.client.post.assert_called_once_with(
            "/prospects/events",
            json={"prospect_ids": prospect_ids, "event_types": event_types}
        )

    def test_enroll_events(self, api: ProspectsAPI):
        """Test enrolling for event monitoring."""
        prospect_ids = ["id1", "id2"]
        event_types = ["prospect_changed_company"]
        enrollment_key = "my_enrollment"

        api.enroll_events(prospect_ids, event_types, enrollment_key)

        api.client.post.assert_called_once_with(
            "/prospects/events/enrollments",
            json={
                "prospect_ids": prospect_ids,
                "event_types": event_types,
                "enrollment_key": enrollment_key
            }
        )

    def test_list_enrollments(self, api: ProspectsAPI):
        """Test listing enrollments."""
        api.list_enrollments()

        api.client.get.assert_called_once_with("/prospects/events/enrollments")
