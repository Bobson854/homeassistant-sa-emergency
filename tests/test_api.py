"""Tests for the SA Emergency API client."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.core import HomeAssistant
from tests.fixtures import load_json_fixture, load_text_fixture

from custom_components.sa_emergency.api import (
    SaEmergencyApi,
    SaEmergencyApiCommunicationError,
    SaEmergencyApiInvalidResponseError,
    _looks_like_html,
)
from custom_components.sa_emergency.const import IMS_INCIDENTS_URL, IMS_QUERY_PARAMS


def _mock_response(*, status: int = 200, text: str = "") -> AsyncMock:
    """Build an async context manager mock HTTP response."""
    response = AsyncMock()
    response.status = status
    response.text = AsyncMock(return_value=text)
    response.__aenter__.return_value = response
    response.__aexit__.return_value = None
    return response


def _mock_session(response: AsyncMock) -> MagicMock:
    """Build a mock aiohttp client session."""
    session = MagicMock()
    session.get.return_value = response
    return session


async def test_api_fetches_valid_ims_payload(hass: HomeAssistant) -> None:
    """Test a valid IMS ArcGIS response returns attribute records."""
    payload = load_json_fixture("ims_combined_features.json")
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text=json.dumps(payload)))

    records = await api.async_get_ims_incidents()

    assert len(records) == 2
    assert records[0]["ident"] == "F2610030053"
    api._session.get.assert_called_once()
    assert api._session.get.call_args.args[0] == IMS_INCIDENTS_URL
    assert api._session.get.call_args.kwargs["params"] == IMS_QUERY_PARAMS


async def test_api_rejects_http_error(hass: HomeAssistant) -> None:
    """Test non-200 HTTP responses fail."""
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(status=503, text="Unavailable"))

    with pytest.raises(SaEmergencyApiCommunicationError, match="HTTP 503"):
        await api.async_get_ims_incidents()


async def test_api_rejects_html_payload(hass: HomeAssistant) -> None:
    """Test HTML payloads are rejected even when HTTP 200."""
    api = SaEmergencyApi(hass)
    api._session = _mock_session(
        _mock_response(text=load_text_fixture("cfs_html_response.html"))
    )

    with pytest.raises(SaEmergencyApiInvalidResponseError, match="HTML"):
        await api.async_get_ims_incidents()


async def test_api_rejects_non_json_payload(hass: HomeAssistant) -> None:
    """Test non-JSON payloads are rejected."""
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text="not json"))

    with pytest.raises(SaEmergencyApiInvalidResponseError, match="invalid JSON"):
        await api.async_get_ims_incidents()


async def test_api_rejects_invalid_top_level_structure(hass: HomeAssistant) -> None:
    """Test invalid top-level JSON structures are rejected."""
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text='["not", "an", "object"]'))

    with pytest.raises(
        SaEmergencyApiInvalidResponseError, match="must be a JSON object"
    ):
        await api.async_get_ims_incidents()


async def test_api_ignores_malformed_features(hass: HomeAssistant) -> None:
    """Test malformed features are ignored while valid records remain."""
    payload = load_json_fixture("ims_mixed_valid_invalid_features.json")
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text=json.dumps(payload)))

    records = await api.async_get_ims_incidents()

    assert len(records) == 4


async def test_api_communication_error(hass: HomeAssistant) -> None:
    """Test network failures raise a communication error."""
    api = SaEmergencyApi(hass)
    api._session = MagicMock()
    api._session.get.side_effect = TimeoutError()

    with pytest.raises(SaEmergencyApiCommunicationError, match="timed out"):
        await api.async_get_ims_incidents()


async def test_api_empty_features(hass: HomeAssistant) -> None:
    """Test an empty features array is a successful response."""
    payload = load_json_fixture("ims_empty_features.json")
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text=json.dumps(payload)))

    records = await api.async_get_ims_incidents()

    assert records == []


async def test_api_rejects_arcgis_error(hass: HomeAssistant) -> None:
    """Test ArcGIS application-level errors fail even with HTTP 200."""
    payload = load_json_fixture("mfs_arcgis_error.json")
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text=json.dumps(payload)))

    with pytest.raises(
        SaEmergencyApiInvalidResponseError, match="IMS incident feed error"
    ):
        await api.async_get_ims_incidents()


async def test_api_rejects_missing_features(hass: HomeAssistant) -> None:
    """Test responses without a features array fail."""
    payload = load_json_fixture("mfs_missing_features.json")
    api = SaEmergencyApi(hass)
    api._session = _mock_session(_mock_response(text=json.dumps(payload)))

    with pytest.raises(SaEmergencyApiInvalidResponseError, match="missing features"):
        await api.async_get_ims_incidents()


def test_looks_like_html() -> None:
    """Test HTML detection helper."""
    assert _looks_like_html("<html><body>Error</body></html>") is True
    assert _looks_like_html('[{"ident":"1"}]') is False
