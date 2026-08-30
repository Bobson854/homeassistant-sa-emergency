"""Source API clients for the SA Emergency integration."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CFS_INCIDENTS_URL, CFS_REQUEST_TIMEOUT_SECONDS

_LOGGER = logging.getLogger(__name__)


class SaEmergencyApiError(Exception):
    """Base exception for SA Emergency API failures."""


class SaEmergencyApiCommunicationError(SaEmergencyApiError):
    """Raised when the HTTP request fails."""


class SaEmergencyApiInvalidResponseError(SaEmergencyApiError):
    """Raised when the response payload is invalid or unexpected."""


class SaEmergencyApi:
    """Retrieve incident data from official SA emergency feeds."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._session: aiohttp.ClientSession | None = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Return the shared Home Assistant aiohttp session."""
        if self._session is None:
            self._session = async_get_clientsession(self._hass)
        return self._session

    async def async_get_cfs_incidents(self) -> list[dict[str, Any]]:
        """Fetch raw CFS current incident records."""
        timeout = aiohttp.ClientTimeout(total=CFS_REQUEST_TIMEOUT_SECONDS)

        try:
            async with self._get_session().get(
                CFS_INCIDENTS_URL, timeout=timeout
            ) as response:
                body = await response.text()
                if response.status != 200:
                    raise SaEmergencyApiCommunicationError(
                        f"CFS feed returned HTTP {response.status}"
                    )
        except TimeoutError as err:
            raise SaEmergencyApiCommunicationError(
                "CFS feed request timed out"
            ) from err
        except aiohttp.ClientError as err:
            raise SaEmergencyApiCommunicationError(
                f"CFS feed request failed: {err}"
            ) from err

        if _looks_like_html(body):
            raise SaEmergencyApiInvalidResponseError(
                "CFS feed returned HTML instead of JSON"
            )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError as err:
            raise SaEmergencyApiInvalidResponseError(
                "CFS feed returned invalid JSON"
            ) from err

        if not isinstance(payload, list):
            raise SaEmergencyApiInvalidResponseError(
                "CFS feed top-level payload must be a JSON array"
            )

        records: list[dict[str, Any]] = []
        for index, item in enumerate(payload):
            if isinstance(item, dict):
                records.append(item)
            else:
                _LOGGER.debug(
                    "Ignoring non-object CFS record at index %s: %r", index, item
                )

        _LOGGER.debug("CFS records fetched: %s", len(records))
        return records


def _looks_like_html(body: str) -> bool:
    """Return True when the payload appears to be HTML rather than JSON."""
    stripped = body.lstrip()
    if not stripped:
        return False
    lowered = stripped[:256].lower()
    return stripped.startswith("<") or "<!doctype html" in lowered or "<html" in lowered
