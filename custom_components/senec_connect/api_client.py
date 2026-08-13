"""API Client for the SENEC Connect integration.

Handles HTTP communication with the SENEC.Connect REST API including
authentication, timeout handling, and exception mapping.
"""

from __future__ import annotations

import asyncio
import logging

import aiohttp

from .const import API_BASE_URL, INCLUDE_FULL, INCLUDE_VALIDATE, REQUEST_TIMEOUT
from .exceptions import SenecApiError, SenecAuthError, SenecConnectionError
from .models import DeviceData

_LOGGER = logging.getLogger(__name__)

ENDPOINT_DEVICE_DATA = "/v1/systems/device-data/general"


class SenecApiClient:
    """Async HTTP Client for the SENEC.Connect API."""

    def __init__(self, session: aiohttp.ClientSession, api_key: str) -> None:
        """Initialize the SENEC API client.

        Args:
            session: An aiohttp ClientSession for making HTTP requests.
            api_key: The Ocp-Apim-Subscription-Key for API authentication.
        """
        self._session = session
        self._api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    async def async_get_device_data(
        self, include: str = INCLUDE_FULL
    ) -> list[DeviceData]:
        """Fetch device data from the SENEC.Connect API.

        Args:
            include: Comma-separated list of data sections to include.
                     Defaults to "battery,bessNameplate,meter,evse".

        Returns:
            A list of DeviceData objects parsed from the API response.

        Raises:
            SenecAuthError: If the API returns HTTP 401 or 403.
            SenecApiError: If the API returns any other 4xx or 5xx status.
            SenecConnectionError: If a network error or timeout occurs.
        """
        url = f"{API_BASE_URL}{ENDPOINT_DEVICE_DATA}"
        headers = {"Ocp-Apim-Subscription-Key": self._api_key}
        params = {"include": include}

        try:
            async with self._session.get(
                url, headers=headers, params=params, timeout=self._timeout
            ) as response:
                if response.status in (401, 403):
                    raise SenecAuthError(
                        f"Authentication failed with status {response.status}"
                    )

                if response.status >= 400:
                    text = await response.text()
                    raise SenecApiError(
                        status_code=response.status,
                        message=f"API request failed: {response.status} - {text}",
                    )

                data = await response.json()
                return [DeviceData.from_dict(item) for item in data]

        except (SenecAuthError, SenecApiError):
            raise
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            raise SenecConnectionError(
                f"Connection to SENEC API failed: {err}"
            ) from err

    async def async_validate_api_key(self) -> list[DeviceData]:
        """Validate the API key by fetching device nameplate data.

        Makes a request with include=bessNameplate to verify the API key
        is valid and retrieve basic device information.

        Returns:
            A list of DeviceData objects (with only bess_nameplate populated).

        Raises:
            SenecAuthError: If the API returns HTTP 401 or 403.
            SenecApiError: If the API returns any other 4xx or 5xx status.
            SenecConnectionError: If a network error or timeout occurs.
        """
        return await self.async_get_device_data(include=INCLUDE_VALIDATE)
