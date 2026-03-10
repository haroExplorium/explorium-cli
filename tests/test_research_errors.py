"""Tests for PRD-2: Research run output format and error handling."""

import asyncio
import json
import tempfile

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock

from explorium_cli.ai_client import validate_anthropic_key, is_permanent_error
from explorium_cli.research import run_research


class TestValidateAnthropicKey:
    """Test upfront API key validation."""

    @pytest.mark.asyncio
    async def test_valid_key(self):
        """Valid key should not raise."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="hi")]

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch("explorium_cli.ai_client._get_client", return_value=mock_client):
            await validate_anthropic_key()  # Should not raise

    @pytest.mark.asyncio
    async def test_invalid_key(self):
        """Invalid key should raise RuntimeError."""
        import anthropic

        mock_client = AsyncMock()
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.json.return_value = {"error": {"message": "invalid api key"}}
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.AuthenticationError(
                message="invalid api key",
                response=error_response,
                body={"error": {"message": "invalid api key"}},
            )
        )

        with patch("explorium_cli.ai_client._get_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="invalid"):
                await validate_anthropic_key()

    @pytest.mark.asyncio
    async def test_no_credits(self):
        """No credits should raise RuntimeError."""
        import anthropic

        mock_client = AsyncMock()
        error_response = MagicMock()
        error_response.status_code = 400
        error_response.json.return_value = {"error": {"message": "Your credit balance is too low"}}
        mock_client.messages.create = AsyncMock(
            side_effect=anthropic.BadRequestError(
                message="Your credit balance is too low",
                response=error_response,
                body={"error": {"message": "Your credit balance is too low"}},
            )
        )

        with patch("explorium_cli.ai_client._get_client", return_value=mock_client):
            with pytest.raises(RuntimeError, match="credits"):
                await validate_anthropic_key()


class TestIsPermanentError:
    """Test permanent error detection."""

    def test_auth_error_is_permanent(self):
        import anthropic
        error_response = MagicMock()
        error_response.status_code = 401
        e = anthropic.AuthenticationError(
            message="invalid",
            response=error_response,
            body={},
        )
        assert is_permanent_error(e) is True

    def test_bad_request_credit_is_permanent(self):
        import anthropic
        error_response = MagicMock()
        error_response.status_code = 400
        e = anthropic.BadRequestError(
            message="Your credit balance is too low",
            response=error_response,
            body={},
        )
        assert is_permanent_error(e) is True

    def test_generic_exception_is_not_permanent(self):
        assert is_permanent_error(Exception("timeout")) is False

    def test_rate_limit_is_not_permanent(self):
        import anthropic
        error_response = MagicMock()
        error_response.status_code = 429
        e = anthropic.RateLimitError(
            message="rate limited",
            response=error_response,
            body={},
        )
        assert is_permanent_error(e) is False


class TestResearchFailFast:
    """Test abort mechanism for permanent errors."""

    @pytest.mark.asyncio
    async def test_abort_on_permanent_error(self):
        """Permanent error should abort remaining tasks."""
        import anthropic

        records = [
            {"company_name": f"Company{i}"} for i in range(5)
        ]

        call_count = 0
        error_response = MagicMock()
        error_response.status_code = 401

        async def mock_research(prompt, company, domain="", max_searches=5):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise anthropic.AuthenticationError(
                    message="invalid api key",
                    response=error_response,
                    body={},
                )
            return {"answer": "ok", "reasoning": "found", "confidence": "high"}

        with patch("explorium_cli.research.validate_anthropic_key", new_callable=AsyncMock):
            with patch("explorium_cli.research.research_company", side_effect=mock_research):
                results = await run_research(
                    records, "test prompt", threads=1, no_polish=True
                )

        # First should be error, rest should be skipped
        assert results[0]["research_answer"].startswith("Error:")
        for r in results[1:]:
            assert r["research_answer"].startswith("Skipped:")

        # research_company should only be called once (then abort)
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_continues_on_transient_error(self):
        """Transient errors should not abort other tasks."""
        records = [
            {"company_name": f"Company{i}"} for i in range(4)
        ]

        call_count = 0

        async def mock_research(prompt, company, domain="", max_searches=5):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("timeout")
            return {"answer": f"answer for {company}", "reasoning": "found", "confidence": "high"}

        with patch("explorium_cli.research.validate_anthropic_key", new_callable=AsyncMock):
            with patch("explorium_cli.research.research_company", side_effect=mock_research):
                results = await run_research(
                    records, "test prompt", threads=1, no_polish=True
                )

        # 3 should succeed, 1 should have error
        successes = [r for r in results if not r["research_answer"].startswith("Error:")]
        errors = [r for r in results if r["research_answer"].startswith("Error:")]
        assert len(successes) == 3
        assert len(errors) == 1
        assert call_count == 4


class TestPolishFallback:
    """Test graceful fallback when prompt polishing fails."""

    @pytest.mark.asyncio
    async def test_polish_failure_uses_raw_prompt(self):
        """Failed polish should fall back to raw prompt."""
        records = [{"company_name": "Acme"}]

        async def mock_polish(prompt):
            raise Exception("API error")

        async def mock_research(prompt, company, domain="", max_searches=5):
            # Verify raw prompt is used (not polished)
            return {"answer": f"researched with: {prompt}", "reasoning": "", "confidence": "high"}

        with patch("explorium_cli.research.validate_anthropic_key", new_callable=AsyncMock):
            with patch("explorium_cli.research.polish_prompt", side_effect=mock_polish):
                with patch("explorium_cli.research.research_company", side_effect=mock_research):
                    results = await run_research(
                        records, "raw question", threads=1, no_polish=False
                    )

        assert "raw question" in results[0]["research_answer"]


class TestResearchCLIExitCodes:
    """Test exit codes for research command."""

    @patch("explorium_cli.commands.research_cmd.run_research")
    def test_all_failed_exits_1(self, mock_run):
        """All tasks failed should exit with code 1."""
        from explorium_cli.main import cli

        async def fake_run(**kwargs):
            return [
                {"company_name": "A", "research_answer": "Error: failed", "research_reasoning": "", "research_confidence": "low"},
                {"company_name": "B", "research_answer": "Error: failed", "research_reasoning": "", "research_confidence": "low"},
            ]

        mock_run.side_effect = lambda **kwargs: asyncio.get_event_loop().run_until_complete(fake_run(**kwargs))

        # We need to mock asyncio.run since the CLI calls it
        csv_content = "company_name\nAcme\nBeta\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            with patch("explorium_cli.commands.research_cmd.asyncio") as mock_asyncio:
                mock_asyncio.run.return_value = [
                    {"company_name": "A", "research_answer": "Error: failed", "research_reasoning": "", "research_confidence": "low"},
                    {"company_name": "B", "research_answer": "Error: failed", "research_reasoning": "", "research_confidence": "low"},
                ]

                runner = CliRunner(mix_stderr=False)
                result = runner.invoke(cli, [
                    "-o", "json",
                    "research", "run",
                    "-f", f.name,
                    "--prompt", "test",
                    "--no-polish",
                ])

        assert "All 2 research tasks failed" in result.stderr
        assert result.exit_code == 1

    @patch("explorium_cli.commands.research_cmd.asyncio")
    def test_partial_failure_exits_0(self, mock_asyncio):
        """Partial failure should exit 0 with warning."""
        from explorium_cli.main import cli

        mock_asyncio.run.return_value = [
            {"company_name": "A", "research_answer": "Good answer", "research_reasoning": "found", "research_confidence": "high"},
            {"company_name": "B", "research_answer": "Error: failed", "research_reasoning": "", "research_confidence": "low"},
            {"company_name": "C", "research_answer": "Good answer", "research_reasoning": "found", "research_confidence": "high"},
        ]

        csv_content = "company_name\nAcme\nBeta\nGamma\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "json",
                "research", "run",
                "-f", f.name,
                "--prompt", "test",
                "--no-polish",
            ])

        assert result.exit_code == 0
        assert "1/3 research tasks failed" in result.stderr


class TestResearchOutputFormat:
    """Test output format integration."""

    @patch("explorium_cli.commands.research_cmd.asyncio")
    def test_csv_output(self, mock_asyncio):
        """CSV output should work via -o csv."""
        from explorium_cli.main import cli

        mock_asyncio.run.return_value = [
            {"company_name": "Acme", "research_answer": "B2B", "research_reasoning": "found on site", "research_confidence": "high"},
        ]

        csv_content = "company_name\nAcme\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "-o", "csv",
                "research", "run",
                "-f", f.name,
                "--prompt", "test",
                "--no-polish",
            ])

        assert result.exit_code == 0
        assert "company_name" in result.output
        assert "research_answer" in result.output
        assert "B2B" in result.output

    @patch("explorium_cli.commands.research_cmd.asyncio")
    def test_json_default(self, mock_asyncio):
        """Default output should be JSON."""
        from explorium_cli.main import cli

        mock_asyncio.run.return_value = [
            {"company_name": "Acme", "research_answer": "B2B", "research_reasoning": "found", "research_confidence": "high"},
        ]

        csv_content = "company_name\nAcme\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write(csv_content)
            f.flush()

            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(cli, [
                "research", "run",
                "-f", f.name,
                "--prompt", "test",
                "--no-polish",
            ])

        assert result.exit_code == 0
        # Should be valid JSON
        parsed = json.loads(result.output)
        assert isinstance(parsed, list)
        assert parsed[0]["research_answer"] == "B2B"
