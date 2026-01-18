"""Pytest fixtures and configuration for Explorium CLI tests."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary config directory."""
    config_dir = tmp_path / ".explorium"
    config_dir.mkdir(parents=True)
    yield config_dir


@pytest.fixture
def temp_config_file(temp_config_dir: Path) -> Path:
    """Create a temporary config file with test values."""
    config_file = temp_config_dir / "config.yaml"
    config_data = {
        "api_key": "test_api_key_12345",
        "base_url": "https://api.explorium.ai/v1",
        "default_output": "json",
        "default_page_size": 100,
    }
    with open(config_file, "w") as f:
        yaml.safe_dump(config_data, f)
    return config_file


@pytest.fixture
def mock_env_vars() -> Generator[None, None, None]:
    """Set up mock environment variables."""
    env_vars = {
        "EXPLORIUM_API_KEY": "env_api_key_67890",
        "EXPLORIUM_BASE_URL": "https://custom.api.com/v1",
        "EXPLORIUM_DEFAULT_OUTPUT": "table",
        "EXPLORIUM_PAGE_SIZE": "50",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        yield


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Remove Explorium environment variables."""
    env_vars_to_remove = [
        "EXPLORIUM_API_KEY",
        "EXPLORIUM_BASE_URL",
        "EXPLORIUM_DEFAULT_OUTPUT",
        "EXPLORIUM_PAGE_SIZE",
    ]
    original = {k: os.environ.get(k) for k in env_vars_to_remove}
    for k in env_vars_to_remove:
        os.environ.pop(k, None)
    yield
    for k, v in original.items():
        if v is not None:
            os.environ[k] = v


# =============================================================================
# CLI Fixtures
# =============================================================================

@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI test runner."""
    return CliRunner(mix_stderr=False)


@pytest.fixture
def isolated_cli_runner() -> CliRunner:
    """Create an isolated Click CLI test runner with temp filesystem."""
    return CliRunner(mix_stderr=False, env={"HOME": "/tmp/test_home"})


# =============================================================================
# API Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_api_response() -> dict[str, Any]:
    """Standard successful API response."""
    return {
        "status": "success",
        "data": [],
        "meta": {"page": 1, "total": 0}
    }


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock requests session."""
    session = MagicMock()
    response = MagicMock()
    response.json.return_value = {"status": "success", "data": []}
    response.raise_for_status.return_value = None
    session.request.return_value = response
    return session


# =============================================================================
# Business API Response Fixtures
# =============================================================================

@pytest.fixture
def business_match_response() -> dict[str, Any]:
    """Mock response for business match endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "business_id": "8adce3ca1cef0c986b22310e369a0793",
                "name": "Starbucks Corporation",
                "website": "starbucks.com",
                "match_confidence": 0.98
            }
        ]
    }


@pytest.fixture
def business_search_response() -> dict[str, Any]:
    """Mock response for business search endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "business_id": "8adce3ca1cef0c986b22310e369a0793",
                "name": "Starbucks Corporation",
                "website": "starbucks.com",
                "country": "US",
                "employee_count": 350000,
                "revenue": "29B",
                "industry": "Food & Beverages"
            },
            {
                "business_id": "abc123def456",
                "name": "Dunkin' Brands",
                "website": "dunkinbrands.com",
                "country": "US",
                "employee_count": 1200,
                "revenue": "1.4B",
                "industry": "Food & Beverages"
            }
        ],
        "meta": {
            "page": 1,
            "size": 100,
            "total": 2
        }
    }


@pytest.fixture
def business_enrich_response() -> dict[str, Any]:
    """Mock response for business enrich endpoint."""
    return {
        "status": "success",
        "data": {
            "business_id": "8adce3ca1cef0c986b22310e369a0793",
            "name": "Starbucks Corporation",
            "website": "starbucks.com",
            "description": "Starbucks Corporation is an American multinational chain of coffeehouses.",
            "founded_year": 1971,
            "headquarters": {
                "city": "Seattle",
                "state": "Washington",
                "country": "US"
            },
            "employee_count": 350000,
            "revenue": "29B",
            "industry": "Food & Beverages",
            "technologies": ["Java", "Python", "AWS", "Kubernetes"],
            "social_media": {
                "linkedin": "https://linkedin.com/company/starbucks",
                "twitter": "https://twitter.com/starbucks"
            }
        }
    }


@pytest.fixture
def business_lookalike_response() -> dict[str, Any]:
    """Mock response for business lookalike endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "business_id": "lookalike_001",
                "name": "Peet's Coffee",
                "similarity_score": 0.92
            },
            {
                "business_id": "lookalike_002",
                "name": "Dutch Bros Coffee",
                "similarity_score": 0.88
            }
        ]
    }


@pytest.fixture
def business_autocomplete_response() -> dict[str, Any]:
    """Mock response for business autocomplete endpoint."""
    return {
        "status": "success",
        "data": [
            {"name": "Starbucks", "business_id": "id1"},
            {"name": "Starwood Hotels", "business_id": "id2"},
            {"name": "Star Tribune", "business_id": "id3"}
        ]
    }


@pytest.fixture
def business_events_response() -> dict[str, Any]:
    """Mock response for business events endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "business_id": "8adce3ca1cef0c986b22310e369a0793",
                "event_type": "new_funding_round",
                "event_date": "2024-01-15",
                "details": {
                    "amount": "100M",
                    "round": "Series D"
                }
            }
        ]
    }


# =============================================================================
# Prospect API Response Fixtures
# =============================================================================

@pytest.fixture
def prospect_match_response() -> dict[str, Any]:
    """Mock response for prospect match endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "prospect_id": "f0bc40c20b185d6b102662a6621632beeedcef7c",
                "first_name": "John",
                "last_name": "Doe",
                "match_confidence": 0.95
            }
        ]
    }


@pytest.fixture
def prospect_search_response() -> dict[str, Any]:
    """Mock response for prospect search endpoint."""
    return {
        "status": "success",
        "data": [
            {
                "prospect_id": "prospect_001",
                "first_name": "John",
                "last_name": "Doe",
                "job_title": "VP of Engineering",
                "department": "Engineering",
                "job_level": "vp",
                "business_id": "8adce3ca1cef0c986b22310e369a0793"
            },
            {
                "prospect_id": "prospect_002",
                "first_name": "Jane",
                "last_name": "Smith",
                "job_title": "Director of Sales",
                "department": "Sales",
                "job_level": "director",
                "business_id": "8adce3ca1cef0c986b22310e369a0793"
            }
        ],
        "meta": {
            "page": 1,
            "size": 100,
            "total": 2
        }
    }


@pytest.fixture
def prospect_enrich_contacts_response() -> dict[str, Any]:
    """Mock response for prospect contacts enrichment."""
    return {
        "status": "success",
        "data": {
            "prospect_id": "prospect_001",
            "emails": [
                {"email": "john.doe@company.com", "type": "work", "confidence": 0.95}
            ],
            "phones": [
                {"phone": "+1-555-123-4567", "type": "mobile", "confidence": 0.85}
            ]
        }
    }


@pytest.fixture
def prospect_enrich_social_response() -> dict[str, Any]:
    """Mock response for prospect social media enrichment."""
    return {
        "status": "success",
        "data": {
            "prospect_id": "prospect_001",
            "linkedin": "https://linkedin.com/in/johndoe",
            "twitter": "https://twitter.com/johndoe",
            "github": "https://github.com/johndoe"
        }
    }


@pytest.fixture
def prospect_enrich_profile_response() -> dict[str, Any]:
    """Mock response for prospect professional profile enrichment."""
    return {
        "status": "success",
        "data": {
            "prospect_id": "prospect_001",
            "first_name": "John",
            "last_name": "Doe",
            "job_title": "VP of Engineering",
            "company": "Starbucks",
            "location": "Seattle, WA",
            "experience": [
                {
                    "title": "VP of Engineering",
                    "company": "Starbucks",
                    "start_date": "2020-01",
                    "end_date": None
                },
                {
                    "title": "Senior Director",
                    "company": "Amazon",
                    "start_date": "2015-06",
                    "end_date": "2019-12"
                }
            ],
            "education": [
                {
                    "school": "MIT",
                    "degree": "MS Computer Science",
                    "year": 2010
                }
            ],
            "skills": ["Python", "Leadership", "Cloud Architecture"]
        }
    }


@pytest.fixture
def prospect_statistics_response() -> dict[str, Any]:
    """Mock response for prospect statistics endpoint."""
    return {
        "status": "success",
        "data": {
            "total_prospects": 150,
            "by_department": {
                "Engineering": 45,
                "Sales": 30,
                "Marketing": 25,
                "Finance": 20,
                "Operations": 30
            },
            "by_job_level": {
                "cxo": 5,
                "vp": 15,
                "director": 30,
                "manager": 50,
                "senior": 50
            }
        }
    }


# =============================================================================
# Webhook API Response Fixtures
# =============================================================================

@pytest.fixture
def webhook_response() -> dict[str, Any]:
    """Mock response for webhook operations."""
    return {
        "status": "success",
        "data": {
            "partner_id": "my_partner",
            "webhook_url": "https://myapp.com/webhook",
            "created_at": "2024-01-15T10:00:00Z",
            "updated_at": "2024-01-15T10:00:00Z"
        }
    }


# =============================================================================
# Error Response Fixtures
# =============================================================================

@pytest.fixture
def api_error_response() -> dict[str, Any]:
    """Mock API error response."""
    return {
        "status": "error",
        "error": {
            "code": "INVALID_REQUEST",
            "message": "Invalid business_id format"
        }
    }


@pytest.fixture
def api_auth_error_response() -> dict[str, Any]:
    """Mock API authentication error response."""
    return {
        "status": "error",
        "error": {
            "code": "UNAUTHORIZED",
            "message": "Invalid or missing API key"
        }
    }


@pytest.fixture
def api_rate_limit_response() -> dict[str, Any]:
    """Mock API rate limit error response."""
    return {
        "status": "error",
        "error": {
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Too many requests. Please try again later."
        }
    }


# =============================================================================
# File Fixtures
# =============================================================================

@pytest.fixture
def businesses_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file with business data."""
    file_path = tmp_path / "businesses.json"
    data = [
        {"name": "Company A", "website": "companya.com"},
        {"name": "Company B", "website": "companyb.com"},
        {"name": "Company C", "website": "companyc.com"}
    ]
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def prospects_json_file(tmp_path: Path) -> Path:
    """Create a temporary JSON file with prospect data."""
    file_path = tmp_path / "prospects.json"
    data = [
        {"first_name": "John", "last_name": "Doe", "linkedin": "https://linkedin.com/in/johndoe"},
        {"first_name": "Jane", "last_name": "Smith", "linkedin": "https://linkedin.com/in/janesmith"}
    ]
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


@pytest.fixture
def business_ids_file(tmp_path: Path) -> Path:
    """Create a temporary file with business IDs."""
    file_path = tmp_path / "business_ids.txt"
    ids = ["id1", "id2", "id3"]
    with open(file_path, "w") as f:
        f.write("\n".join(ids))
    return file_path
