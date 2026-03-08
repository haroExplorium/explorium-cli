"""Anthropic AI client wrapper for research commands."""

import asyncio
import json
import os
from typing import Any

import anthropic


SONNET_MODEL = "claude-sonnet-4-6"
HAIKU_MODEL = "claude-haiku-4-5-20251001"

POLISH_SYSTEM = (
    "You are a research prompt engineer. The user will give you a raw question "
    "they want answered about many companies. Rewrite it into a precise, "
    "unambiguous research prompt that a web-search AI agent can execute for "
    "each company independently. The prompt should:\n"
    "1. Be self-contained (no references to 'the company' without a placeholder)\n"
    "2. Use {company_name} and optionally {domain} as placeholders\n"
    "3. Specify the desired output format: a short answer, reasoning, and "
    "confidence (high/medium/low)\n"
    "4. Be concise (under 200 words)\n\n"
    "Return ONLY the rewritten prompt, nothing else."
)

RESEARCH_SYSTEM = (
    "You are a company research analyst. Use web search to answer the question "
    "about the specified company. Be factual and concise.\n\n"
    "You MUST respond in this exact format:\n"
    "ANSWER: <your direct answer>\n"
    "REASONING: <brief explanation of how you found this>\n"
    "CONFIDENCE: <high|medium|low>"
)

MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0


def _get_client() -> anthropic.AsyncAnthropic:
    """Create an async Anthropic client from env var."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is required. "
            "Set it with: export ANTHROPIC_API_KEY=sk-ant-..."
        )
    return anthropic.AsyncAnthropic(api_key=api_key)


async def _call_with_retry(coro_factory, max_retries: int = MAX_RETRIES) -> Any:
    """Call an async function with retry on rate limit (429) errors."""
    delay = RETRY_BASE_DELAY
    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except anthropic.RateLimitError:
            if attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
        except anthropic.APIStatusError as e:
            if e.status_code == 529 and attempt < max_retries:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise


async def polish_prompt(raw_prompt: str) -> str:
    """Use Sonnet to polish a raw research question into a precise prompt."""
    client = _get_client()

    async def _call():
        return await client.messages.create(
            model=SONNET_MODEL,
            max_tokens=1024,
            system=POLISH_SYSTEM,
            messages=[{"role": "user", "content": raw_prompt}],
        )

    response = await _call_with_retry(_call)
    return response.content[0].text.strip()


async def research_company(
    prompt: str,
    company_name: str,
    domain: str = "",
    max_searches: int = 5,
) -> dict[str, str]:
    """Use Haiku + web_search to research a single company.

    Args:
        prompt: The polished research prompt (with {company_name}/{domain} placeholders).
        company_name: Company name to research.
        domain: Optional company domain.
        max_searches: Max web search tool uses allowed.

    Returns:
        Dict with keys: answer, reasoning, confidence.
    """
    client = _get_client()

    filled_prompt = prompt.replace("{company_name}", company_name)
    filled_prompt = filled_prompt.replace("{domain}", domain or "")

    async def _call():
        return await client.messages.create(
            model=HAIKU_MODEL,
            max_tokens=1024,
            system=RESEARCH_SYSTEM,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_searches,
            }],
            messages=[{"role": "user", "content": filled_prompt}],
        )

    response = await _call_with_retry(_call)

    # Extract text from response (skip tool use blocks)
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    full_text = "\n".join(text_parts)
    return parse_research_response(full_text)


def _strip_markdown(line: str) -> str:
    """Strip markdown bold/italic markers and leading - or * list markers."""
    import re
    # Remove bold/italic markers first (before list marker removal)
    s = line.replace("**", "").replace("__", "")
    # Remove leading list markers (- or *)
    s = re.sub(r"^\s*[-*]\s+", "", s)
    return s


def parse_research_response(text: str) -> dict[str, str]:
    """Parse ANSWER/REASONING/CONFIDENCE from model response text.

    Handles plain text and markdown-formatted responses (e.g. **ANSWER:**).

    Args:
        text: Raw model response text.

    Returns:
        Dict with keys: answer, reasoning, confidence.
    """
    result = {"answer": "", "reasoning": "", "confidence": ""}

    lines = text.strip().split("\n")
    current_key = None
    current_lines: list[str] = []

    for line in lines:
        cleaned = _strip_markdown(line).strip()
        cleaned_upper = cleaned.upper()

        matched_key = None
        matched_label = None
        for key, label in [("answer", "ANSWER:"), ("reasoning", "REASONING:"), ("confidence", "CONFIDENCE:")]:
            if cleaned_upper.startswith(label):
                matched_key = key
                matched_label = label
                break

        if matched_key:
            if current_key:
                result[current_key] = "\n".join(current_lines).strip()
            current_key = matched_key
            # Extract value after the label
            value = cleaned[len(matched_label):].strip()
            current_lines = [value]
        elif current_key:
            current_lines.append(line.strip())

    if current_key:
        result[current_key] = "\n".join(current_lines).strip()

    # Normalize confidence
    conf = result["confidence"].lower().strip()
    if conf in ("high", "medium", "low"):
        result["confidence"] = conf
    elif not conf:
        result["confidence"] = "low"

    # If parsing failed completely, put the whole text as the answer
    if not result["answer"] and text.strip():
        result["answer"] = text.strip()
        result["confidence"] = "low"

    return result
