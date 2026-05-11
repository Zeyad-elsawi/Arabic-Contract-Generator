"""Thin wrappers around the Groq SDK.

Three call-sites:

* ``draft_contract_stream`` - drafter, streamed for live UI updates.
* ``run_critic``            - critic, JSON-mode, blocking.
* ``run_refiner``           - per-clause edit, JSON-mode, blocking.
* ``transcribe_audio``      - Whisper Large v3 for Arabic voice input.

We re-use a single ``Groq`` client and rely on the SDK's built-in retries.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from groq import Groq

import config


# ---------------------------------------------------------------------------
# Client (lazy, cached)
# ---------------------------------------------------------------------------
_CLIENT: Groq | None = None


def get_client() -> Groq:
    """Return a cached Groq client. Raises if no API key is configured."""
    global _CLIENT
    if _CLIENT is None:
        key = config.get_api_key("GROQ_API_KEY")
        if not key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to .streamlit/secrets.toml "
                "or set the environment variable."
            )
        _CLIENT = Groq(api_key=key)
    return _CLIENT


# ---------------------------------------------------------------------------
# Drafter (streaming)
# ---------------------------------------------------------------------------
def draft_contract_stream(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> Iterator[str]:
    """Stream the drafter's JSON output token-by-token.

    The caller is expected to accumulate the chunks and ``json.loads`` the
    final string. We use Groq's ``response_format={"type": "json_object"}``
    so the output is guaranteed to be parseable JSON.
    """
    client = get_client()
    schema_hint = (
        "\n\nSchema for your JSON output:\n```json\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n```"
    )

    stream = client.chat.completions.create(
        model=config.DRAFTER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt + schema_hint},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.DRAFTER_TEMPERATURE,
        max_completion_tokens=config.DRAFTER_MAX_TOKENS,
        response_format={"type": "json_object"},
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ---------------------------------------------------------------------------
# Critic (blocking, JSON)
# ---------------------------------------------------------------------------
def run_critic(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> str:
    """Blocking critic call. Returns the raw JSON string."""
    client = get_client()
    schema_hint = (
        "\n\nSchema for your JSON output:\n```json\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n```"
    )

    response = client.chat.completions.create(
        model=config.CRITIC_MODEL,
        messages=[
            {"role": "system", "content": system_prompt + schema_hint},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.CRITIC_TEMPERATURE,
        max_completion_tokens=config.CRITIC_MAX_TOKENS,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


# ---------------------------------------------------------------------------
# Refiner (blocking, JSON, streamed for UX)
# ---------------------------------------------------------------------------
def run_refiner_stream(
    *,
    system_prompt: str,
    user_prompt: str,
    schema: dict[str, Any],
) -> Iterator[str]:
    """Stream the refiner output."""
    client = get_client()
    schema_hint = (
        "\n\nSchema for your JSON output:\n```json\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n```"
    )

    stream = client.chat.completions.create(
        model=config.REFINER_MODEL,
        messages=[
            {"role": "system", "content": system_prompt + schema_hint},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config.REFINER_TEMPERATURE,
        max_completion_tokens=config.REFINER_MAX_TOKENS,
        response_format={"type": "json_object"},
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ---------------------------------------------------------------------------
# Whisper transcription
# ---------------------------------------------------------------------------
def transcribe_audio(audio_bytes: bytes, filename: str = "audio.webm") -> str:
    """Send audio bytes to Groq Whisper and return the Arabic transcript."""
    client = get_client()
    response = client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=config.WHISPER_MODEL,
        language="ar",
        response_format="text",
    )
    # SDK returns either a string or an object with .text depending on version
    if isinstance(response, str):
        return response
    return getattr(response, "text", "") or ""
