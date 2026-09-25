"""Lightweight, dependency-free content moderation for chat queries.

This is a heuristic keyword/phrase filter, not an ML classifier. It is
deliberately conservative and scoped to explicit sexual content and
clearly harmful/violent intent, so that legitimate BIS/standards queries
that happen to mention words like "safety", "hazard", "explosive" or
"weapon" (fire-safety, LPG cylinder, fireworks, arms/ammunition standards
are all real BIS subject matter) are not blocked.

Flow, mirroring the existing SlidingWindowRateLimiter in core/rate_limit.py:
  1st flagged message  -> warning only, question is NOT answered, no LLM call.
  2nd flagged message   -> the user is blocked for MODERATION_BLOCK_SECONDS.
  further messages while blocked -> told how long remains, no LLM call.
  Once the block expires, the strike count resets (a clean slate, not a ban).

Running entirely in-process (no DB writes) keeps this check cheap and keeps
it from ever being the thing that adds an extra provider/LLM call -- it only
ever *removes* calls, by short-circuiting the pipeline before AI #1/AI #2.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from threading import Lock

from backend.app.core.config import settings

# --------------------------------------------------------------------------
# Pattern lists. Phrase-level (verb + harmful noun) matching is used for the
# "harm" category specifically to avoid colliding with legitimate BIS safety
# vocabulary. The "sexual" category uses explicit terms that have no
# legitimate use in this product's domain.
# --------------------------------------------------------------------------
_SEXUAL_TERMS = [
    r"porn(?:ography|hub)?", r"xxx", r"hardcore sex", r"nude(?:s)?\s*(?:photo|pic|image)",
    r"naked\s*(?:photo|pic|image|girl|boy|woman|man)", r"sex\s*video", r"sexting",
    r"nsfw", r"hentai", r"blow\s*job", r"hand\s*job", r"orgasm", r"masturbat\w*",
    r"erotic\w*", r"incest", r"gangbang", r"escort\s*service", r"child\s*porn\w*",
    r"rape\s*(?:video|story|scene|fantasy)", r"molest\w*", r"fetish\s*(?:video|content)",
]

_HARM_PHRASES = [
    r"how (?:do|can|to) i?\s*(?:make|build|create|assemble)\s*(?:a\s*)?(?:bomb|explosive device|pipe bomb|ied)",
    r"how (?:do|can|to) i?\s*(?:make|build|create|3d print)\s*(?:a\s*)?(?:gun|firearm|weapon)\s*(?:at home|myself|to kill|to hurt)",
    r"how (?:do|can|to) i?\s*(?:make|synthesi[sz]e|prepare)\s*(?:a\s*)?poison\s*(?:to kill|to hurt|for someone)",
    r"how (?:do|can|to) i?\s*kill\s*(?:someone|a person|my|him|her|them)",
    r"how (?:do|can|to) i?\s*(?:murder|assassinate)\s*(?:someone|a person)",
    r"(?:best|easiest) way to (?:kill|murder|hurt badly|torture)\s*(?:someone|a person|him|her|them)",
    r"how to (?:carry out|plan|commit)\s*(?:an?\s*)?(?:terror|terrorist|mass shooting|bomb) attack",
    r"acid attack\s*how",
]

_ALL_PATTERNS = [(re.compile(p, re.IGNORECASE), "sexual") for p in _SEXUAL_TERMS] + [
    (re.compile(p, re.IGNORECASE), "harm") for p in _HARM_PHRASES
]


def _flag_category(message: str) -> str | None:
    for pattern, category in _ALL_PATTERNS:
        if pattern.search(message):
            return category
    return None


@dataclass
class ModerationResult:
    flagged: bool = False
    blocked: bool = False
    warned: bool = False
    retry_after_seconds: int = 0
    category: str | None = None
    message: str = ""


_WARNING_TEXT = (
    "Your message was flagged as sexual or harm-related content, which "
    "ManakMitra can't help with. This is a warning -- if this happens "
    "again, your account will be temporarily blocked from chatting for "
    "1 hour. If you think this was a mistake, please use the Feedback / "
    "Contact option to let our team know."
)


def _blocked_text(retry_after_seconds: int) -> str:
    minutes = max(1, (retry_after_seconds + 59) // 60)
    return (
        "You've been temporarily blocked from ManakMitra AI chat for "
        f"repeatedly sending flagged sexual/harm-related content. "
        f"Please try again in about {minutes} minute{'s' if minutes != 1 else ''}. "
        "If you think this was a mistake, please use the Feedback / Contact "
        "option to let our team know."
    )


class ModerationGuard:
    """Tracks per-user strikes and temporary blocks entirely in memory."""

    def __init__(self, block_seconds: int | None = None):
        self.block_seconds = block_seconds if block_seconds is not None else settings.MODERATION_BLOCK_SECONDS
        # identity -> {"strikes": int, "blocked_until": float | None}
        self._state: dict[str, dict] = {}
        self._lock = Lock()

    def check(self, identity: str, message: str) -> ModerationResult:
        if not settings.MODERATION_ENABLED:
            return ModerationResult()

        identity = identity or "anonymous"
        now = time.monotonic()

        with self._lock:
            record = self._state.get(identity)

            # Currently serving a block.
            if record and record.get("blocked_until") and record["blocked_until"] > now:
                retry_after = int(record["blocked_until"] - now)
                return ModerationResult(
                    flagged=True, blocked=True, retry_after_seconds=retry_after,
                    message=_blocked_text(retry_after),
                )

            # A previous block has expired -- clear it and start fresh.
            if record and record.get("blocked_until") and record["blocked_until"] <= now:
                self._state.pop(identity, None)
                record = None

            category = _flag_category(message)
            if not category:
                return ModerationResult()

            strikes = (record or {}).get("strikes", 0) + 1
            if strikes >= 2:
                blocked_until = now + self.block_seconds
                self._state[identity] = {"strikes": 0, "blocked_until": blocked_until}
                return ModerationResult(
                    flagged=True, blocked=True, category=category,
                    retry_after_seconds=self.block_seconds,
                    message=_blocked_text(self.block_seconds),
                )

            self._state[identity] = {"strikes": strikes, "blocked_until": None}
            return ModerationResult(
                flagged=True, warned=True, category=category, message=_WARNING_TEXT,
            )

    def cleanup(self) -> None:
        """Drop identities with no active block/strikes (optional housekeeping,
        mirrors SlidingWindowRateLimiter.cleanup; safe to call periodically)."""
        now = time.monotonic()
        with self._lock:
            for identity in list(self._state):
                record = self._state[identity]
                blocked_until = record.get("blocked_until")
                if blocked_until is not None and blocked_until <= now:
                    self._state.pop(identity, None)


moderation_guard = ModerationGuard()
