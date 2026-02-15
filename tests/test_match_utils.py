"""Tests for match_utils module - match-based enrichment resolution."""

import pytest
from unittest.mock import MagicMock

from explorium_cli.api.businesses import BusinessesAPI
from explorium_cli.api.prospects import ProspectsAPI


class TestMatchExceptions:
    """Tests for match-related exception classes."""

    def test_match_error_raised_when_no_matches(self):
        """MatchError should be raised when no matches are found."""
        from explorium_cli.match_utils import MatchError

        with pytest.raises(MatchError) as exc_info:
            raise MatchError("No business matches found for: name=Acme")

        assert "No business matches found" in str(exc_info.value)

    def test_low_confidence_error_includes_suggestions(self):
        """LowConfidenceError should include match suggestions."""
        from explorium_cli.match_utils import LowConfidenceError

        suggestions = [
            {"business_id": "id1", "name": "Acme Corp", "match_confidence": 0.6},
            {"business_id": "id2", "name": "Acme Inc", "match_confidence": 0.5},
        ]

        error = LowConfidenceError(suggestions, min_confidence=0.8)

        assert error.suggestions == suggestions
        assert error.min_confidence == 0.8
        assert "confidence" in str(error).lower()


class TestResolveBusinessId:
    """Tests for resolve_business_id function."""

    @pytest.fixture
    def mock_businesses_api(self) -> BusinessesAPI:
        """Create a BusinessesAPI instance with mock client."""
        mock_client = MagicMock()
        return BusinessesAPI(mock_client)

    def test_returns_id_directly_when_provided(self, mock_businesses_api: BusinessesAPI):
        """When business_id is provided, return it without calling match API."""
        from explorium_cli.match_utils import resolve_business_id

        result = resolve_business_id(
            mock_businesses_api,
            business_id="existing_id_123"
        )

        assert result == "existing_id_123"
        # Should NOT call match API
        mock_businesses_api.client.post.assert_not_called()

    def test_calls_match_when_name_provided(self, mock_businesses_api: BusinessesAPI):
        """When name is provided, call match API and return business_id."""
        from explorium_cli.match_utils import resolve_business_id

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "matched_id_456",
                    "name": "Starbucks",
                    "match_confidence": 0.95
                }
            ]
        }

        result = resolve_business_id(
            mock_businesses_api,
            name="Starbucks"
        )

        assert result == "matched_id_456"
        mock_businesses_api.client.post.assert_called_once()

    def test_calls_match_when_domain_provided(self, mock_businesses_api: BusinessesAPI):
        """When domain is provided, call match API and return business_id."""
        from explorium_cli.match_utils import resolve_business_id

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "matched_id_789",
                    "name": "Google",
                    "website": "google.com",
                    "match_confidence": 0.99
                }
            ]
        }

        result = resolve_business_id(
            mock_businesses_api,
            domain="google.com"
        )

        assert result == "matched_id_789"

    def test_calls_match_when_linkedin_provided(self, mock_businesses_api: BusinessesAPI):
        """When linkedin is provided, call match API and return business_id."""
        from explorium_cli.match_utils import resolve_business_id

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "linkedin_id_101",
                    "name": "Microsoft",
                    "match_confidence": 0.97
                }
            ]
        }

        result = resolve_business_id(
            mock_businesses_api,
            linkedin="https://linkedin.com/company/microsoft"
        )

        assert result == "linkedin_id_101"

    def test_raises_match_error_when_no_matches(self, mock_businesses_api: BusinessesAPI):
        """Raise MatchError when match API returns empty data."""
        from explorium_cli.match_utils import resolve_business_id, MatchError

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": []
        }

        with pytest.raises(MatchError) as exc_info:
            resolve_business_id(mock_businesses_api, name="NonexistentCompany")

        assert "No business matches found" in str(exc_info.value)

    def test_raises_low_confidence_error_below_threshold(self, mock_businesses_api: BusinessesAPI):
        """Raise LowConfidenceError when match confidence is below threshold."""
        from explorium_cli.match_utils import resolve_business_id, LowConfidenceError

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "low_conf_id",
                    "name": "Maybe Starbucks",
                    "match_confidence": 0.6
                },
                {
                    "business_id": "low_conf_id_2",
                    "name": "Starbucks-ish",
                    "match_confidence": 0.5
                }
            ]
        }

        with pytest.raises(LowConfidenceError) as exc_info:
            resolve_business_id(
                mock_businesses_api,
                name="Starbucks",
                min_confidence=0.8
            )

        assert len(exc_info.value.suggestions) == 2
        assert exc_info.value.min_confidence == 0.8

    def test_accepts_match_at_threshold(self, mock_businesses_api: BusinessesAPI):
        """Accept match when confidence equals threshold."""
        from explorium_cli.match_utils import resolve_business_id

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "threshold_id",
                    "name": "Starbucks",
                    "match_confidence": 0.8
                }
            ]
        }

        result = resolve_business_id(
            mock_businesses_api,
            name="Starbucks",
            min_confidence=0.8
        )

        assert result == "threshold_id"

    def test_default_min_confidence_is_0_8(self, mock_businesses_api: BusinessesAPI):
        """Default min_confidence should be 0.8."""
        from explorium_cli.match_utils import resolve_business_id, LowConfidenceError

        mock_businesses_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "business_id": "low_conf_id",
                    "name": "Starbucks",
                    "match_confidence": 0.79
                }
            ]
        }

        with pytest.raises(LowConfidenceError):
            resolve_business_id(mock_businesses_api, name="Starbucks")


class TestResolveProspectId:
    """Tests for resolve_prospect_id function."""

    @pytest.fixture
    def mock_prospects_api(self) -> ProspectsAPI:
        """Create a ProspectsAPI instance with mock client."""
        mock_client = MagicMock()
        return ProspectsAPI(mock_client)

    def test_returns_id_directly_when_provided(self, mock_prospects_api: ProspectsAPI):
        """When prospect_id is provided, return it without calling match API."""
        from explorium_cli.match_utils import resolve_prospect_id

        result = resolve_prospect_id(
            mock_prospects_api,
            prospect_id="existing_prospect_123"
        )

        assert result == "existing_prospect_123"
        mock_prospects_api.client.post.assert_not_called()

    def test_calls_match_when_names_provided(self, mock_prospects_api: ProspectsAPI):
        """When first_name and last_name are provided, call match API."""
        from explorium_cli.match_utils import resolve_prospect_id

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "prospect_id": "matched_prospect_456",
                    "first_name": "John",
                    "last_name": "Doe",
                    "match_confidence": 0.95
                }
            ]
        }

        result = resolve_prospect_id(
            mock_prospects_api,
            first_name="John",
            last_name="Doe",
            company_name="Acme Corp"
        )

        assert result == "matched_prospect_456"

    def test_calls_match_when_linkedin_provided(self, mock_prospects_api: ProspectsAPI):
        """When linkedin is provided, call match API."""
        from explorium_cli.match_utils import resolve_prospect_id

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "prospect_id": "linkedin_prospect_789",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "match_confidence": 0.98
                }
            ]
        }

        result = resolve_prospect_id(
            mock_prospects_api,
            linkedin="https://linkedin.com/in/janesmith"
        )

        assert result == "linkedin_prospect_789"

    def test_raises_match_error_when_no_matches(self, mock_prospects_api: ProspectsAPI):
        """Raise MatchError when match API returns empty data."""
        from explorium_cli.match_utils import resolve_prospect_id, MatchError

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": []
        }

        with pytest.raises(MatchError) as exc_info:
            resolve_prospect_id(
                mock_prospects_api,
                first_name="Unknown",
                last_name="Person",
                company_name="Acme"
            )

        assert "No prospect matches found" in str(exc_info.value)

    def test_raises_low_confidence_error_below_threshold(self, mock_prospects_api: ProspectsAPI):
        """Raise LowConfidenceError when match confidence is below threshold."""
        from explorium_cli.match_utils import resolve_prospect_id, LowConfidenceError

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [
                {
                    "prospect_id": "low_conf_prospect",
                    "first_name": "John",
                    "last_name": "Doe",
                    "match_confidence": 0.5
                }
            ]
        }

        with pytest.raises(LowConfidenceError) as exc_info:
            resolve_prospect_id(
                mock_prospects_api,
                first_name="John",
                last_name="Doe",
                company_name="Acme",
                min_confidence=0.8
            )

        assert len(exc_info.value.suggestions) == 1


class TestResolveProspectIdEmail:
    """Tests for resolve_prospect_id with email parameter (bug fix).

    Email-only prospects were silently matched with empty params because
    resolve_prospect_id didn't accept an email parameter.
    """

    @pytest.fixture
    def mock_prospects_api(self) -> ProspectsAPI:
        mock_client = MagicMock()
        return ProspectsAPI(mock_client)

    def test_email_only_sends_email_to_match_api(self, mock_prospects_api: ProspectsAPI):
        """Email-only match should send email in match params."""
        from explorium_cli.match_utils import resolve_prospect_id

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [{"prospect_id": "email_prospect_1", "match_confidence": 0.95}]
        }

        result = resolve_prospect_id(
            mock_prospects_api,
            email="robert.soong@ahss.org"
        )

        assert result == "email_prospect_1"
        call_args = mock_prospects_api.client.post.call_args
        payload = call_args[1]["json"]["prospects_to_match"][0]
        assert payload["email"] == "robert.soong@ahss.org"
        # Name should NOT be included (email is a strong ID, no company)
        assert "full_name" not in payload

    def test_email_is_strong_id_strips_name_without_company(self, mock_prospects_api: ProspectsAPI):
        """Email should be treated as a strong ID — name dropped when no company."""
        from explorium_cli.match_utils import resolve_prospect_id

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [{"prospect_id": "email_prospect_2", "match_confidence": 0.95}]
        }

        resolve_prospect_id(
            mock_prospects_api,
            first_name="Robert",
            last_name="Soong",
            email="robert.soong@ahss.org"
        )

        payload = mock_prospects_api.client.post.call_args[1]["json"]["prospects_to_match"][0]
        assert payload["email"] == "robert.soong@ahss.org"
        assert "full_name" not in payload

    def test_email_with_company_includes_name(self, mock_prospects_api: ProspectsAPI):
        """Email + company_name should include name in match params."""
        from explorium_cli.match_utils import resolve_prospect_id

        mock_prospects_api.client.post.return_value = {
            "status": "success",
            "data": [{"prospect_id": "email_prospect_3", "match_confidence": 0.95}]
        }

        resolve_prospect_id(
            mock_prospects_api,
            first_name="Robert",
            last_name="Soong",
            email="robert.soong@ahss.org",
            company_name="AHSS"
        )

        payload = mock_prospects_api.client.post.call_args[1]["json"]["prospects_to_match"][0]
        assert payload["email"] == "robert.soong@ahss.org"
        assert payload["full_name"] == "Robert Soong"
        assert payload["company_name"] == "AHSS"

    def test_validate_accepts_email_only(self):
        """validate_prospect_match_params should accept email as sole identifier."""
        from explorium_cli.match_utils import validate_prospect_match_params

        # Should NOT raise
        validate_prospect_match_params(
            prospect_id=None,
            first_name=None,
            last_name=None,
            linkedin=None,
            company_name=None,
            email="test@example.com"
        )


class TestBusinessMatchOptions:
    """Tests for business_match_options decorator."""

    def test_decorator_adds_all_options(self):
        """business_match_options should add --id, --name, --domain, --linkedin, --min-confidence."""
        import click
        from explorium_cli.match_utils import business_match_options

        @click.command()
        @business_match_options
        def test_cmd(**kwargs):
            return kwargs

        # Check that all expected options are present
        option_names = [param.name for param in test_cmd.params]

        assert "business_id" in option_names
        assert "name" in option_names
        assert "domain" in option_names
        assert "linkedin" in option_names
        assert "min_confidence" in option_names

    def test_decorator_preserves_existing_options(self):
        """business_match_options should not interfere with other options."""
        import click
        from explorium_cli.match_utils import business_match_options

        @click.command()
        @business_match_options
        @click.option("--extra", help="Extra option")
        def test_cmd(**kwargs):
            return kwargs

        option_names = [param.name for param in test_cmd.params]
        assert "extra" in option_names
        assert "business_id" in option_names


class TestProspectMatchOptions:
    """Tests for prospect_match_options decorator."""

    def test_decorator_adds_all_options(self):
        """prospect_match_options should add all expected options."""
        import click
        from explorium_cli.match_utils import prospect_match_options

        @click.command()
        @prospect_match_options
        def test_cmd(**kwargs):
            return kwargs

        option_names = [param.name for param in test_cmd.params]

        assert "prospect_id" in option_names
        assert "first_name" in option_names
        assert "last_name" in option_names
        assert "linkedin" in option_names
        assert "company_name" in option_names
        assert "min_confidence" in option_names


class TestValidateMatchParams:
    """Tests for validation of match parameters."""

    def test_raises_error_when_no_params_provided_business(self):
        """Should raise error when neither ID nor match params provided for business."""
        from explorium_cli.match_utils import validate_business_match_params

        with pytest.raises(ValueError) as exc_info:
            validate_business_match_params(
                business_id=None,
                name=None,
                domain=None,
                linkedin=None
            )

        assert "Provide --id or match parameters" in str(exc_info.value)

    def test_raises_error_when_no_params_provided_prospect(self):
        """Should raise error when neither ID nor match params provided for prospect."""
        from explorium_cli.match_utils import validate_prospect_match_params

        with pytest.raises(ValueError) as exc_info:
            validate_prospect_match_params(
                prospect_id=None,
                first_name=None,
                last_name=None,
                linkedin=None,
                company_name=None
            )

        assert "Provide --id or match parameters" in str(exc_info.value)

    def test_valid_when_id_provided(self):
        """Should not raise when ID is provided."""
        from explorium_cli.match_utils import validate_business_match_params

        # Should not raise
        validate_business_match_params(
            business_id="some_id",
            name=None,
            domain=None,
            linkedin=None
        )

    def test_valid_when_name_provided(self):
        """Should not raise when name is provided."""
        from explorium_cli.match_utils import validate_business_match_params

        # Should not raise
        validate_business_match_params(
            business_id=None,
            name="Starbucks",
            domain=None,
            linkedin=None
        )
