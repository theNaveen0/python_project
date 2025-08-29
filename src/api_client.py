"""
Async OpenRouter Chat Completions client with robust backoff and safe parsing.
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Dict, List

import aiohttp

from .config import API_ENDPOINT, MODEL, HTTP_TIMEOUT_SECS, USER_AGENT
# Defensive import so a missing SYSTEM_PROMPT can never crash the EXE.
try:
    from .config import SYSTEM_PROMPT as _SYSTEM_PROMPT
except Exception:
    _SYSTEM_PROMPT = (
        "You are a helpful assistant. If the user asks programming questions, "
        "prefer Java 17 and return a runnable 'public class Main' example."
    )

from .utils import logger


class ChatAPIError(Exception):
    pass


class GrokAPIError(ChatAPIError):
    """Back-compat name used in tests; keep as alias."""
    pass


class GrokAPIClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key

    async def send_query(self, query: str) -> str:
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        # OpenRouter requires these headers in addition to Authorization.
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            "HTTP-Referer": "https://invisiblechat.local",  # any URL you own/control is fine
            "X-Title": "InvisibleChat",
        }

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        payload: Dict[str, Any] = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 512,   # stay within free-tier quota
            "stream": False,
        }

        timeout = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECS)

        # Up to 4 tries for 429/5xx with exponential backoff + jitter
        for attempt in range(4):
            try:
                async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                    async with session.post(API_ENDPOINT, json=payload, ssl=True) as resp:
                        status = resp.status
                        text_body = await resp.text()  # read once; log + parse
                        logger.info("[OpenRouter] HTTP %s (attempt %d) body[0:200]=%r",
                                    status, attempt + 1, text_body[:200])

                        if status == 401:
                            raise ChatAPIError("Authentication failed (401). Check your OpenRouter API key.")
                        if status == 429:
                            if attempt < 3:
                                delay = (2 ** attempt) + random.uniform(0.0, 0.5)
                                logger.warning("Rate limited (429). Retrying in %.2fs", delay)
                                await asyncio.sleep(delay)
                                continue
                            raise ChatAPIError("Rate limited (429). Please slow down.")
                        if status >= 500:
                            if attempt < 3:
                                delay = (2 ** attempt) + random.uniform(0.0, 0.5)
                                logger.warning("Server error (%s). Retrying in %.2fs", status, delay)
                                await asyncio.sleep(delay)
                                continue
                            raise ChatAPIError(f"Server error ({status}). Try again later.")

                        # Parse JSON (OpenRouter uses OpenAI format)
                        try:
                            data = json.loads(text_body)
                        except json.JSONDecodeError:
                            raise ChatAPIError(
                                "API did not return JSON (wrong URL or missing headers). "
                                "Check app.log for the first 200 chars."
                            )

                        return self._parse_response(data)

            except aiohttp.ClientConnectionError as e:
                if attempt < 3:
                    delay = (2 ** attempt) + random.uniform(0.0, 0.5)
                    logger.warning("Network error (%s). Retrying in %.2fs", e, delay)
                    await asyncio.sleep(delay)
                    continue
                raise ChatAPIError(f"Network error: {e}") from e
            except asyncio.TimeoutError as e:
                if attempt < 3:
                    delay = (2 ** attempt) + random.uniform(0.0, 0.5)
                    logger.warning("Timeout. Retrying in %.2fs", delay)
                    await asyncio.sleep(delay)
                    continue
                raise ChatAPIError("Request timed out.") from e
            except ChatAPIError:
                raise
            except Exception as e:
                logger.error("Unexpected error: %s", e, exc_info=True)
                raise ChatAPIError(f"Unexpected error: {e}") from e

        raise ChatAPIError("Failed after retries.")

    @staticmethod
    def _parse_response(data: Dict[str, Any]) -> str:
        # Handle OpenRouter / OpenAI error objects
        if "error" in data:
            msg = data["error"].get("message", "Unknown API error")
            raise ChatAPIError(f"API error: {msg}")

        choices = data.get("choices") or []
        if not choices:
            if "output" in data and isinstance(data["output"], str):
                return data["output"]
            raise ChatAPIError("Malformed response: no choices.")

        msg = choices[0].get("message") or {}
        content = msg.get("content") or choices[0].get("text")
        if not content:
            raise ChatAPIError("Empty response from assistant.")
        return str(content)
