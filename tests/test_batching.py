"""Unit tests for batching utilities."""

import io
from unittest.mock import MagicMock

import pytest
import click

from explorium_cli.batching import (
    parse_csv_ids,
    parse_csv_business_match_params,
    parse_csv_prospect_match_params,
    batched_enrich,
)


class TestParseCsvIds:
    """Tests for parse_csv_ids function."""

    def test_parse_csv_with_prospect_id_column(self):
        """Test parsing CSV with prospect_id column."""
        csv_content = "prospect_id,name,email\np1,John,john@example.com\np2,Jane,jane@example.com\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="prospect_id")

        assert ids == ["p1", "p2"]

    def test_parse_csv_with_business_id_column(self):
        """Test parsing CSV with business_id column."""
        csv_content = "business_id,company_name\nb1,Acme\nb2,Globex\nb3,Initech\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="business_id")

        assert ids == ["b1", "b2", "b3"]

    def test_parse_csv_strips_whitespace(self):
        """Test that whitespace is stripped from IDs."""
        csv_content = "prospect_id,name\n  p1  ,John\n p2,Jane\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="prospect_id")

        assert ids == ["p1", "p2"]

    def test_parse_csv_skips_empty_ids(self):
        """Test that empty IDs are skipped."""
        csv_content = "prospect_id,name\np1,John\n,Jane\n   ,Empty\np2,Valid\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="prospect_id")

        assert ids == ["p1", "p2"]

    def test_parse_csv_missing_column_error(self):
        """Test error when required column is missing."""
        csv_content = "name,email\nJohn,john@example.com\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_ids(file, column_name="prospect_id")

        assert "CSV file must contain a 'prospect_id' column" in str(exc_info.value)
        assert "Found columns: name, email" in str(exc_info.value)

    def test_parse_csv_empty_file_error(self):
        """Test error when CSV file is empty."""
        file = io.StringIO("")

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_ids(file, column_name="prospect_id")

        assert "empty or has no header row" in str(exc_info.value)

    def test_parse_csv_no_ids_error(self):
        """Test error when CSV has header but no data rows."""
        csv_content = "prospect_id,name\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_ids(file, column_name="prospect_id")

        assert "No IDs found in file" in str(exc_info.value)

    def test_parse_csv_all_empty_ids_error(self):
        """Test error when all IDs in CSV are empty."""
        csv_content = "prospect_id,name\n,John\n   ,Jane\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_ids(file, column_name="prospect_id")

        assert "No IDs found in file" in str(exc_info.value)

    def test_parse_csv_ids_uppercase_column(self):
        """Test that PROSPECT_ID header works (case-insensitive)."""
        csv_content = "PROSPECT_ID,name\np1,John\np2,Jane\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="prospect_id")

        assert ids == ["p1", "p2"]

    def test_parse_csv_ids_mixed_case(self):
        """Test that Prospect_Id header works (case-insensitive)."""
        csv_content = "Prospect_Id,name\np1,John\np2,Jane\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="prospect_id")

        assert ids == ["p1", "p2"]

    def test_parse_csv_ids_business_id_case_insensitive(self):
        """Test that Business_ID header works (case-insensitive)."""
        csv_content = "Business_ID,company\nb1,Acme\nb2,Globex\n"
        file = io.StringIO(csv_content)

        ids = parse_csv_ids(file, column_name="business_id")

        assert ids == ["b1", "b2"]


class TestBatchedEnrich:
    """Tests for batched_enrich function."""

    def test_single_batch_under_limit(self):
        """Test that single batch under 50 makes one API call."""
        mock_api = MagicMock()
        mock_api.return_value = {"status": "success", "data": [{"id": "p1"}]}

        ids = [f"p{i}" for i in range(30)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 1
        assert len(mock_api.call_args[0][0]) == 30
        assert result["status"] == "success"
        assert len(result["data"]) == 1

    def test_exactly_50_ids_single_batch(self):
        """Test that exactly 50 IDs makes one batch."""
        mock_api = MagicMock()
        mock_api.return_value = {"status": "success", "data": [{"id": f"p{i}"} for i in range(50)]}

        ids = [f"p{i}" for i in range(50)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 1

    def test_51_ids_two_batches(self):
        """Test that 51 IDs makes two batches."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": [{"id": f"p{i}"} for i in range(50)]},
            {"status": "success", "data": [{"id": "p50"}]}
        ]

        ids = [f"p{i}" for i in range(51)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 2
        # First batch: 50 IDs
        assert len(mock_api.call_args_list[0][0][0]) == 50
        # Second batch: 1 ID
        assert len(mock_api.call_args_list[1][0][0]) == 1

    def test_100_ids_two_batches(self):
        """Test that 100 IDs makes two batches of 50."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": [{"id": f"p{i}"} for i in range(50)]},
            {"status": "success", "data": [{"id": f"p{i}"} for i in range(50, 100)]}
        ]

        ids = [f"p{i}" for i in range(100)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 2
        assert len(mock_api.call_args_list[0][0][0]) == 50
        assert len(mock_api.call_args_list[1][0][0]) == 50

    def test_75_ids_two_batches(self):
        """Test that 75 IDs makes two batches (50 + 25)."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": [{"id": f"p{i}"} for i in range(50)]},
            {"status": "success", "data": [{"id": f"p{i}"} for i in range(50, 75)]}
        ]

        ids = [f"p{i}" for i in range(75)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 2
        assert len(mock_api.call_args_list[0][0][0]) == 50
        assert len(mock_api.call_args_list[1][0][0]) == 25

    def test_combines_data_from_batches(self):
        """Test that data from all batches is combined."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": [{"id": "p1"}, {"id": "p2"}]},
            {"status": "success", "data": [{"id": "p3"}]}
        ]

        ids = [f"p{i}" for i in range(75)]
        result = batched_enrich(mock_api, ids, entity_name="prospects", show_progress=False)

        assert len(result["data"]) == 3
        assert result["data"][0]["id"] == "p1"
        assert result["data"][1]["id"] == "p2"
        assert result["data"][2]["id"] == "p3"

    def test_passes_kwargs_to_api_method(self):
        """Test that additional kwargs are passed to API method."""
        mock_api = MagicMock()
        mock_api.return_value = {"status": "success", "data": []}

        ids = ["p1", "p2"]
        batched_enrich(
            mock_api, ids,
            entity_name="prospects",
            show_progress=False,
            enrich_types=["email", "phone"]
        )

        call_kwargs = mock_api.call_args[1]
        assert call_kwargs["enrich_types"] == ["email", "phone"]

    def test_custom_batch_size(self):
        """Test that custom batch size is respected."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": []},
            {"status": "success", "data": []},
            {"status": "success", "data": []},
            {"status": "success", "data": []},
            {"status": "success", "data": []}
        ]

        ids = [f"p{i}" for i in range(25)]
        batched_enrich(mock_api, ids, batch_size=5, entity_name="prospects", show_progress=False)

        assert mock_api.call_count == 5
        for call in mock_api.call_args_list:
            assert len(call[0][0]) == 5


class TestBatchedEnrichProgressOutput:
    """Tests for batched_enrich progress messages."""

    def test_no_progress_for_single_batch(self, capsys):
        """Test that progress is not shown for single batch."""
        mock_api = MagicMock()
        mock_api.return_value = {"status": "success", "data": []}

        ids = [f"p{i}" for i in range(30)]
        batched_enrich(mock_api, ids, entity_name="prospects", show_progress=True)

        captured = capsys.readouterr()
        assert "Batch" not in captured.err

    def test_progress_shown_for_multiple_batches(self, capsys):
        """Test that progress is shown for multiple batches."""
        mock_api = MagicMock()
        mock_api.side_effect = [
            {"status": "success", "data": []},
            {"status": "success", "data": []}
        ]

        ids = [f"p{i}" for i in range(75)]
        batched_enrich(mock_api, ids, entity_name="prospects", show_progress=True)

        captured = capsys.readouterr()
        assert "Batch 1/2" in captured.err
        assert "Batch 2/2" in captured.err
        assert "prospects" in captured.err
        assert "Enriched 75 prospects total" in captured.err


class TestParseCsvBusinessMatchParams:
    """Tests for parse_csv_business_match_params function."""

    def test_parse_with_name_and_domain(self):
        csv_content = "name,domain\nAcme Corp,acme.com\nGlobex Inc,globex.com\n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert result == [
            {"name": "Acme Corp", "domain": "acme.com"},
            {"name": "Globex Inc", "domain": "globex.com"},
        ]

    def test_parse_with_website_column(self):
        csv_content = "name,website\nAcme Corp,https://acme.com\n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert result == [{"name": "Acme Corp", "domain": "https://acme.com"}]

    def test_parse_with_linkedin_url(self):
        csv_content = "name,linkedin_url\nAcme Corp,https://linkedin.com/company/acme\n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert result == [
            {"name": "Acme Corp", "linkedin_url": "https://linkedin.com/company/acme"},
        ]

    def test_parse_skips_empty_rows(self):
        csv_content = "name,domain\nAcme Corp,acme.com\n,,\n  ,  \nGlobex,globex.com\n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert len(result) == 2
        assert result[0]["name"] == "Acme Corp"
        assert result[1]["name"] == "Globex"

    def test_parse_strips_whitespace(self):
        csv_content = "name,domain\n  Acme Corp  ,  acme.com  \n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_parse_partial_columns(self):
        csv_content = "name,domain\nAcme Corp,\n,globex.com\n"
        file = io.StringIO(csv_content)

        result = parse_csv_business_match_params(file)

        assert result == [
            {"name": "Acme Corp"},
            {"domain": "globex.com"},
        ]

    def test_empty_file_error(self):
        file = io.StringIO("")

        with pytest.raises(click.UsageError, match="empty or has no header row"):
            parse_csv_business_match_params(file)

    def test_no_valid_rows_error(self):
        csv_content = "name,domain\n,,\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError, match="No valid business match rows"):
            parse_csv_business_match_params(file)

    def test_header_only_error(self):
        csv_content = "name,domain\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError, match="No valid business match rows"):
            parse_csv_business_match_params(file)


class TestParseCsvProspectMatchParams:
    """Tests for parse_csv_prospect_match_params function."""

    def test_parse_with_full_name(self):
        csv_content = "full_name,company_name\nJohn Doe,Acme Corp\nJane Smith,Globex\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [
            {"full_name": "John Doe", "company_name": "Acme Corp"},
            {"full_name": "Jane Smith", "company_name": "Globex"},
        ]

    def test_parse_with_first_and_last_name(self):
        csv_content = "first_name,last_name,company_name\nJohn,Doe,Acme Corp\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"full_name": "John Doe", "company_name": "Acme Corp"}]

    def test_parse_with_linkedin(self):
        """When linkedin is present without company_name, full_name is stripped."""
        csv_content = "full_name,linkedin\nJohn Doe,https://linkedin.com/in/johndoe\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [
            {"linkedin": "https://linkedin.com/in/johndoe"},
        ]

    def test_full_name_column_takes_precedence(self):
        csv_content = "first_name,last_name,full_name\nJohn,Doe,Jonathan Doe\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result[0]["full_name"] == "Jonathan Doe"

    def test_parse_first_name_only(self):
        csv_content = "first_name,company_name\nJohn,Acme\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"full_name": "John", "company_name": "Acme"}]

    def test_parse_last_name_only(self):
        csv_content = "last_name,company_name\nDoe,Acme\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"full_name": "Doe", "company_name": "Acme"}]

    def test_parse_skips_empty_rows(self):
        csv_content = "full_name,company_name\nJohn Doe,Acme\n,,\nJane Smith,Globex\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert len(result) == 2

    def test_parse_strips_whitespace(self):
        csv_content = "full_name,company_name\n  John Doe  ,  Acme Corp  \n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"full_name": "John Doe", "company_name": "Acme Corp"}]

    def test_empty_file_error(self):
        file = io.StringIO("")

        with pytest.raises(click.UsageError, match="empty or has no header row"):
            parse_csv_prospect_match_params(file)

    def test_no_valid_rows_error(self):
        csv_content = "full_name,company_name\n,,\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError, match="No valid prospect match rows"):
            parse_csv_prospect_match_params(file)

    def test_parse_with_email(self):
        csv_content = "full_name,email,company_name\nJohn Doe,john@acme.com,Acme Corp\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [
            {"full_name": "John Doe", "email": "john@acme.com", "company_name": "Acme Corp"},
        ]

    def test_email_only_row(self):
        csv_content = "full_name,email\n,john@acme.com\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"email": "john@acme.com"}]

    def test_linkedin_only_row(self):
        csv_content = "full_name,linkedin\n,https://linkedin.com/in/johndoe\n"
        file = io.StringIO(csv_content)

        result = parse_csv_prospect_match_params(file)

        assert result == [{"linkedin": "https://linkedin.com/in/johndoe"}]


class TestBusinessColumnAliases:
    """Tests for business CSV column alias resolution."""

    def test_company_name_alias(self):
        """Test 'company_name' as alias for 'name'."""
        csv_content = "company_name,domain\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_company_alias(self):
        """Test 'company' as alias for 'name'."""
        csv_content = "company,website\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_business_name_alias(self):
        """Test 'business_name' as alias for 'name'."""
        csv_content = "business_name,domain\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_url_alias_for_domain(self):
        """Test 'url' as alias for 'domain'."""
        csv_content = "name,url\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_company_domain_alias(self):
        """Test 'company_domain' as alias for 'domain'."""
        csv_content = "name,company_domain\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_company_website_alias(self):
        """Test 'company_website' as alias for 'domain'."""
        csv_content = "name,company_website\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_site_alias_for_domain(self):
        """Test 'site' as alias for 'domain'."""
        csv_content = "name,site\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_linkedin_alias_for_linkedin_url(self):
        """Test 'linkedin' as alias for 'linkedin_url'."""
        csv_content = "name,linkedin\nAcme Corp,https://linkedin.com/company/acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "linkedin_url": "https://linkedin.com/company/acme"}]

    def test_case_insensitive_columns(self):
        """Test that column matching is case-insensitive."""
        csv_content = "Company_Name,Website\nAcme Corp,acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_business_match_params(file)
        assert result == [{"name": "Acme Corp", "domain": "acme.com"}]

    def test_unrecognized_columns_error(self):
        """Test that completely unrecognized columns raise a helpful error."""
        csv_content = "foo,bar,baz\nval1,val2,val3\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_business_match_params(file)

        error_msg = str(exc_info.value)
        assert "No recognized business columns" in error_msg
        assert "foo, bar, baz" in error_msg
        assert "name" in error_msg
        assert "domain" in error_msg
        assert "website" in error_msg


class TestProspectColumnAliases:
    """Tests for prospect CSV column alias resolution."""

    def test_firstname_alias(self):
        """Test 'firstname' as alias for 'first_name'."""
        csv_content = "firstname,lastname,company_name\nJohn,Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_first_alias(self):
        """Test 'first' as alias for 'first_name'."""
        csv_content = "first,last,company\nJohn,Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_surname_alias(self):
        """Test 'surname' as alias for 'last_name'."""
        csv_content = "first_name,surname,company_name\nJohn,Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_name_alias_for_full_name(self):
        """Test 'name' as alias for 'full_name'."""
        csv_content = "name,company_name\nJohn Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_fullname_alias(self):
        """Test 'fullname' as alias for 'full_name'."""
        csv_content = "fullname,company\nJohn Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_company_alias_for_company_name(self):
        """Test 'company' as alias for 'company_name'."""
        csv_content = "full_name,company\nJohn Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_employer_alias(self):
        """Test 'employer' as alias for 'company_name'."""
        csv_content = "full_name,employer\nJohn Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_organization_alias(self):
        """Test 'organization' as alias for 'company_name'."""
        csv_content = "full_name,organization\nJohn Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_email_address_alias(self):
        """Test 'email_address' as alias for 'email'. full_name stripped when email present without company."""
        csv_content = "full_name,email_address\nJohn Doe,john@acme.com\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"email": "john@acme.com"}]

    def test_linkedin_url_alias(self):
        """Test 'linkedin_url' as alias for 'linkedin'. full_name stripped when linkedin present without company."""
        csv_content = "full_name,linkedin_url\nJohn Doe,https://linkedin.com/in/johndoe\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"linkedin": "https://linkedin.com/in/johndoe"}]

    def test_linkedin_profile_alias(self):
        """Test 'linkedin_profile' as alias for 'linkedin'. full_name stripped when linkedin present without company."""
        csv_content = "full_name,linkedin_profile\nJohn Doe,https://linkedin.com/in/johndoe\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"linkedin": "https://linkedin.com/in/johndoe"}]

    def test_case_insensitive_columns(self):
        """Test that column matching is case-insensitive."""
        csv_content = "First_Name,Last_Name,Company\nJohn,Doe,Acme\n"
        file = io.StringIO(csv_content)
        result = parse_csv_prospect_match_params(file)
        assert result == [{"full_name": "John Doe", "company_name": "Acme"}]

    def test_unrecognized_columns_error(self):
        """Test that completely unrecognized columns raise a helpful error."""
        csv_content = "phone,address,zip_code\n555-1234,123 Main St,90210\n"
        file = io.StringIO(csv_content)

        with pytest.raises(click.UsageError) as exc_info:
            parse_csv_prospect_match_params(file)

        error_msg = str(exc_info.value)
        assert "No recognized prospect columns" in error_msg
        assert "phone, address, zip_code" in error_msg
        assert "first_name" in error_msg
        assert "full_name" in error_msg
        assert "company_name" in error_msg
