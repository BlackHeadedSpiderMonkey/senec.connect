"""SENEC Connect integration for Home Assistant.

Sets up the integration by creating the API client and coordinator,
then forwards platform setup to sensor and binary_sensor.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import SenecApiClient
from .const import DOMAIN
from .coordinator import SenecDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SENEC Connect from a config entry.

    Creates the API client and data coordinator, performs the initial
    data fetch, and forwards setup to sensor/binary_sensor platforms.
    """
    session = async_get_clientsession(hass)

    api_key: str = entry.data["api_key"]
    polling_interval: int = entry.data["polling_interval"]
    selected_devices: list[str] = entry.data["selected_devices"]

    client = SenecApiClient(session=session, api_key=api_key)

    coordinator = SenecDataUpdateCoordinator(
        hass=hass,
        client=client,
        selected_serials=selected_devices,
        update_interval=timedelta(seconds=polling_interval),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Pre-register parent devices so via_device references work
    device_registry = dr.async_get(hass)
    for serial_number, device_data in coordinator.data.items():
        manufacturer = "SENEC"
        model = None
        if device_data.bess_nameplate:
            manufacturer = device_data.bess_nameplate.manufacturer
            model = device_data.bess_nameplate.model
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, serial_number)},
            manufacturer=manufacturer,
            model=model,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a SENEC Connect config entry.

    Unloads sensor/binary_sensor platforms and cleans up stored data.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok
