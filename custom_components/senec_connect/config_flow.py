"""Config Flow for the SENEC Connect integration.

Implements a two-step UI configuration:
Step 1 (async_step_user): API key and polling interval input with validation
Step 2 (async_step_devices): Device selection from discovered devices
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import SenecApiClient
from .const import DEFAULT_POLLING_INTERVAL, DOMAIN, MIN_POLLING_INTERVAL
from .exceptions import SenecAuthError, SenecConnectionError
from .models import DeviceData

_LOGGER = logging.getLogger(__name__)

CONF_API_KEY = "api_key"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_SELECTED_DEVICES = "selected_devices"


class SenecConnectConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow Handler for SENEC Connect."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._devices: list[DeviceData] = []
        self._api_key: str = ""
        self._polling_interval: int = DEFAULT_POLLING_INTERVAL

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the first step: API key and polling interval input."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY, "").strip()
            polling_interval = user_input.get(
                CONF_POLLING_INTERVAL, DEFAULT_POLLING_INTERVAL
            )

            # Validate empty API key without making an API call
            if not api_key:
                errors["base"] = "empty_api_key"
            # Validate polling interval minimum
            elif polling_interval < MIN_POLLING_INTERVAL:
                errors["base"] = "invalid_interval"
            else:
                # Set unique_id to the API key and abort if already configured
                await self.async_set_unique_id(api_key)
                self._abort_if_unique_id_configured()

                # Validate API key by calling the API
                session = async_get_clientsession(self.hass)
                client = SenecApiClient(session=session, api_key=api_key)

                try:
                    devices = await client.async_validate_api_key()
                except SenecAuthError:
                    errors["base"] = "invalid_auth"
                except SenecConnectionError:
                    errors["base"] = "cannot_connect"
                else:
                    if not devices:
                        errors["base"] = "no_devices"
                    else:
                        # Store data for step 2
                        self._devices = devices
                        self._api_key = api_key
                        self._polling_interval = polling_interval
                        return await self.async_step_devices()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                    vol.Required(
                        CONF_POLLING_INTERVAL,
                        default=DEFAULT_POLLING_INTERVAL,
                    ): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    async def async_step_devices(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the second step: device selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input.get(CONF_SELECTED_DEVICES, [])

            if not selected:
                errors["base"] = "no_selection"
            else:
                return self.async_create_entry(
                    title="SENEC Connect",
                    data={
                        CONF_API_KEY: self._api_key,
                        CONF_POLLING_INTERVAL: self._polling_interval,
                        CONF_SELECTED_DEVICES: selected,
                    },
                )

        # Build multi-select options: {serial_number: "model (serial_number)"}
        device_options: dict[str, str] = {}
        for device in self._devices:
            if device.bess_nameplate:
                serial = device.bess_nameplate.serial_number
                model = device.bess_nameplate.model
                device_options[serial] = f"{model} ({serial})"

        return self.async_show_form(
            step_id="devices",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SELECTED_DEVICES): vol.All(
                        vol.Coerce(list),
                        [vol.In(device_options)],
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"devices": str(len(device_options))},
        )
