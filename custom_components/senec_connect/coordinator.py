"""DataUpdateCoordinator for the SENEC Connect integration.

Periodically polls the SENEC.Connect API and distributes device data
to sensor entities. Handles error mapping and device filtering.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api_client import SenecApiClient
from .exceptions import SenecApiError, SenecAuthError, SenecConnectionError
from .models import DeviceData

_LOGGER = logging.getLogger(__name__)


class SenecDataUpdateCoordinator(DataUpdateCoordinator[dict[str, DeviceData]]):
    """Coordinator for periodic SENEC data polling.

    Fetches device data from the SENEC.Connect API, filters by selected
    serial numbers, and provides the data as a dict keyed by serial_number.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: SenecApiClient,
        selected_serials: list[str],
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: The Home Assistant instance.
            client: The SENEC API client for making requests.
            selected_serials: List of device serial numbers to track.
            update_interval: Time between polling cycles (min 60s).
        """
        super().__init__(
            hass,
            _LOGGER,
            name="SENEC Connect",
            update_interval=update_interval,
        )
        self.client = client
        self.selected_serials = selected_serials

    async def _async_update_data(self) -> dict[str, DeviceData]:
        """Fetch and filter device data from the SENEC API.

        Returns:
            A dict mapping serial_number to DeviceData for each selected
            device that is present in the API response.

        Raises:
            UpdateFailed: If the API call fails or returns no data.
        """
        try:
            devices = await self.client.async_get_device_data()
        except SenecAuthError as err:
            raise UpdateFailed(
                f"Authentication failed: {err}"
            ) from err
        except SenecApiError as err:
            raise UpdateFailed(
                f"API error (HTTP {err.status_code}): {err}"
            ) from err
        except SenecConnectionError as err:
            raise UpdateFailed(
                f"Connection error: {err}"
            ) from err

        if not devices:
            raise UpdateFailed("No device data available")

        # Filter to only selected devices and key by serial_number
        result: dict[str, DeviceData] = {}
        for device in devices:
            if (
                device.bess_nameplate is not None
                and device.bess_nameplate.serial_number in self.selected_serials
            ):
                result[device.bess_nameplate.serial_number] = device

        return result
