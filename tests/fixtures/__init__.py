"""Test helpers for loading CFS fixtures."""

from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def load_json_fixture(name: str):
    """Load a JSON fixture from tests/fixtures."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def load_text_fixture(name: str) -> str:
    """Load a text fixture from tests/fixtures."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")
