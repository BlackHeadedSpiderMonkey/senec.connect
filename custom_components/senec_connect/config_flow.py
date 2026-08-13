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
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api_client import SenecApiClient
from .const import API_BASE_URL, DEFAULT_POLLING_INTERVAL, DOMAIN, MIN_POLLING_INTERVAL
from .exceptions import SenecApiError, SenecAuthError, SenecConnectionError
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
        self._error_detail: str = ""

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
                try:
                    # Validate API key by calling the API
                    session = async_get_clientsession(self.hass)
                    client = SenecApiClient(session=session, api_key=api_key)

                    _LOGGER.debug("Validating API key against %s", API_BASE_URL)
                    devices = await client.async_validate_api_key()
                    _LOGGER.debug("API validation returned %d devices", len(devices))
                except SenecAuthError as err:
                    _LOGGER.warning("Auth error during API validation: %s", err)
                    errors["base"] = "invalid_auth"
                except SenecConnectionError as err:
                    _LOGGER.warning("Connection error during API validation: %s", err)
                    errors["base"] = "cannot_connect"
                except Exception as err:
                    _LOGGER.exception("Unexpected error during API validation: %s", err)
                    # Create a persistent notification so we can see the error
                    # even if logging doesn't work
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "SENEC Connect Debug",
                            "message": f"{type(err).__name__}: {err}",
                            "notification_id": "senec_debug",
                        },
                    )
                    errors["base"] = "unknown"
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
                # Set unique_id to prevent duplicate entries
                await self.async_set_unique_id(self._api_key)
                self._abort_if_unique_id_configured()

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
                    vol.Required(CONF_SELECTED_DEVICES): cv.multi_select(
                        device_options
                    ),
                }
            ),
            errors=errors,
            description_placeholders={"devices": str(len(device_options))},
        )
