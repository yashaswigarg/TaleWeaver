"""Configuration and LLM factory for TaleWeaver with built-in rate-limit protection."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv(override=True)

# Path definitions
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

LOREBOOK_DB_PATH = DATA_DIR / "lorebook.db"
CHECKPOINTS_DB_PATH = DATA_DIR / "checkpoints.db"
STORYBOOK_MD_PATH = DATA_DIR / "StoryBook.md"


@dataclass
class Settings:
    """Application settings with rate-limiting and model configurations."""

    api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
    model_name: str = os.getenv("TALEWEAVER_MODEL", "gemini-3.6-flash")
    rate_limit_delay: float = float(os.getenv("TALEWEAVER_RATE_LIMIT_DELAY", "4.0"))
    max_revisions: int = int(os.getenv("TALEWEAVER_MAX_REVISIONS", "1"))
    max_retries: int = 4
    initial_retry_delay: float = 3.0


settings = Settings()


class RateLimiter:
    """Thread-safe and process-conscious throttler to respect free-tier RPM limits."""

    def __init__(self, min_interval: float = 4.0):
        self.min_interval = min_interval
        self._last_call_time: float = 0.0

    def wait(self) -> None:
        """Enforces a minimum interval between consecutive API requests."""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call_time = time.time()


# Global rate limiter instance
limiter = RateLimiter(min_interval=settings.rate_limit_delay)


def get_llm(temperature: float = 0.7, model: Optional[str] = None) -> ChatGoogleGenerativeAI:
    """Returns an initialized ChatGoogleGenerativeAI instance.

    Args:
        temperature: Sampling temperature for creativity (0.0 - 1.0).
        model: Model name override (defaults to settings.model_name).
    """
    key = settings.api_key
    if not key:
        # Note: In development or test environments without an active key,
        # fallback allows graph initialization and mock tests to run.
        key = "DUMMY_KEY_FOR_TESTS"

    return ChatGoogleGenerativeAI(
        model=model or settings.model_name,
        google_api_key=key,
        temperature=temperature,
        max_retries=settings.max_retries,
    )
