"""Helpers for IMS feed tests."""

from __future__ import annotations

from typing import Any

from tests.fixtures import load_json_fixture

IMS_AUTHORITY_CFS = "South Australian Country Fire Service"
IMS_AUTHORITY_MFS = "South Australian Metropolitan Fire Service"


def load_ims_attribute_records(fixture_name: str) -> list[dict[str, Any]]:
    """Load attribute dicts from an IMS fixture (features wrapper or list)."""
    payload = load_json_fixture(fixture_name)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and "features" in payload:
        records: list[dict[str, Any]] = []
        for feature in payload["features"]:
            if isinstance(feature, dict) and isinstance(
                feature.get("attributes"), dict
            ):
                records.append(feature["attributes"])
        return records
    if isinstance(payload, dict):
        return [payload]
    return []


def ims_cfs_record(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid CFS IMS attribute record."""
    record: dict[str, Any] = {
        "ident": "CFS001",
        "authority": IMS_AUTHORITY_CFS,
        "event": "Grass Fire",
        "inc_status": "GOING",
        "inc_level": 1,
        "effective": 1791006922000,
        "location": "TEST LOCATION",
        "lat": -35.1234,
        "long": 139.5678,
    }
    record.update(overrides)
    return record


def ims_mfs_record(**overrides: Any) -> dict[str, Any]:
    """Build a minimal valid MFS IMS attribute record."""
    record: dict[str, Any] = {
        "ident": "MFS001",
        "authority": IMS_AUTHORITY_MFS,
        "event": "Structure Fire",
        "inc_status": "GOING",
        "inc_level": 1,
        "effective": 1787831280000,
        "location": "MFS TEST",
        "lat": -34.831308,
        "long": 138.712425,
    }
    record.update(overrides)
    return record
