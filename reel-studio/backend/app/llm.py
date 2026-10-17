"""Minimal Claude client over the REST API (optional - everything has a local fallback)."""
import json
import re
from typing import Any, Optional

import requests

from . import config


def available() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def complete(system: str, user: str, max_tokens: int = 6000, temperature: float = 0.3) -> str:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": config.CLAUDE_MODEL,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=300,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Claude API {resp.status_code}: {resp.text[:300]}")
    return "".join(b.get("text", "") for b in resp.json().get("content", []) if b.get("type") == "text")


def parse_json(text: str) -> Any:
    """Extract the first JSON object from a model reply (tolerates ``` fences / chatter)."""
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.S)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("no JSON object in model reply")
    return json.loads(text[start:end + 1])


def complete_json(system: str, user: str, max_tokens: int = 6000) -> Any:
    last: Optional[Exception] = None
    for _ in range(2):
        try:
            return parse_json(complete(system, user, max_tokens))
        except (ValueError, json.JSONDecodeError) as e:
            last = e
    raise RuntimeError(f"Claude returned invalid JSON: {last}")
