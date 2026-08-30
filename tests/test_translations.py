"""Tests for custom integration translations."""

import json
from pathlib import Path

REQUIRED_KEYS = (
    ("config", "step", "user", "title"),
    ("config", "error", "location_not_configured"),
    ("options", "step", "init", "title"),
    ("options", "error", "no_agencies_enabled"),
    ("entity", "sensor", "incidents", "name"),
    ("entity", "sensor", "nearest_incident", "name"),
    ("entity", "sensor", "highest_relevance", "name"),
)


def _load_en_translations() -> dict:
    path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "sa_emergency"
        / "translations"
        / "en.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def test_en_translations_contains_required_keys() -> None:
    """Test English translations include config, options, and entity strings."""
    translations = _load_en_translations()

    for parts in REQUIRED_KEYS:
        node = translations
        for part in parts:
            assert part in node, f"Missing translation key segment: {'.'.join(parts)}"
            node = node[part]
        assert isinstance(node, str)
        assert node.strip()


def test_strings_json_not_used_for_custom_integration() -> None:
    """Test translations/en.json is used instead of Core strings.json."""
    strings_path = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "sa_emergency"
        / "strings.json"
    )
    assert not strings_path.exists()
