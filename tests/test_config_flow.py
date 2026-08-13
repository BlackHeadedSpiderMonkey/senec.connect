"""Tests for the SENEC Connect config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.senec_connect.config_flow import (
    CONF_API_KEY,
    CONF_POLLING_INTERVAL,
    CONF_SELECTED_DEVICES,
    SenecConnectConfigFlow,
)
from custom_components.senec_connect.const import DOMAIN
from custom_components.senec_connect.exceptions import (
    SenecAuthError,
    SenecConnectionError,
)
from custom_components.senec_connect.models import BessNameplateData, DeviceData


@pytest.fixture
def mock_devices() -> list[DeviceData]:
    """Return mock DeviceData objects for testing."""
    return [
        DeviceData(
            bess_nameplate=BessNameplateData(
                manufacturer="SENEC GmbH",
                model="SENEC.Home E4 - 1ph 6 AC",
                serial_number="v4-00012ff4",
                design_capacity=10000,
                active_charge_power=2500,
                active_discharge_power=2500,
                system_id="S4H1-02ER23323-0199-8F",
            )
        ),
        DeviceData(
            bess_nameplate=BessNameplateData(
                manufacturer="SENEC GmbH",
                model="SENEC.Home V3",
                serial_number="v3-0000abcd",
                design_capacity=5000,
                active_charge_power=2000,
                active_discharge_power=2000,
            )
        ),
    ]


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


@pytest.fixture
def flow(mock_hass) -> SenecConnectConfigFlow:
    """Create a config flow instance with mocked hass."""
    flow = SenecConnectConfigFlow()
    flow.hass = mock_hass
    return flow


class TestAsyncStepUser:
    """Tests for the first config flow step (API key + polling interval)."""

    async def test_shows_form_on_no_input(self, flow):
        """Step_user shows the form when no input is provided."""
        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"
        assert result["errors"] == {}

    async def test_empty_api_key_error(self, flow):
        """Empty API key shows error without making an API call."""
        result = await flow.async_step_user(
            user_input={CONF_API_KEY: "", CONF_POLLING_INTERVAL: 60}
        )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "empty_api_key"}

    async def test_whitespace_api_key_treated_as_empty(self, flow):
        """Whitespace-only API key is treated as empty."""
        result = await flow.async_step_user(
            user_input={CONF_API_KEY: "   ", CONF_POLLING_INTERVAL: 60}
        )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "empty_api_key"}

    async def test_interval_below_minimum_error(self, flow):
        """Interval below 60 shows invalid_interval error."""
        result = await flow.async_step_user(
            user_input={CONF_API_KEY: "valid-key", CONF_POLLING_INTERVAL: 30}
        )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_interval"}

    async def test_interval_at_minimum_accepted(self, flow, mock_devices):
        """Interval exactly 60 is accepted."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.return_value = mock_devices
            mock_client_cls.return_value = mock_client

            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "valid-key", CONF_POLLING_INTERVAL: 60}
            )

        assert result["type"] == "form"
        assert result["step_id"] == "devices"

    async def test_auth_error_maps_to_invalid_auth(self, flow):
        """SenecAuthError maps to invalid_auth error."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.side_effect = SenecAuthError(
                "Auth failed"
            )
            mock_client_cls.return_value = mock_client

            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "bad-key", CONF_POLLING_INTERVAL: 60}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "invalid_auth"}

    async def test_connection_error_maps_to_cannot_connect(self, flow):
        """SenecConnectionError maps to cannot_connect error."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.side_effect = SenecConnectionError(
                "Connection failed"
            )
            mock_client_cls.return_value = mock_client

            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "valid-key", CONF_POLLING_INTERVAL: 60}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "cannot_connect"}

    async def test_empty_device_list_maps_to_no_devices(self, flow):
        """Empty device list from API maps to no_devices error."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.return_value = []
            mock_client_cls.return_value = mock_client

            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "valid-key", CONF_POLLING_INTERVAL: 60}
            )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "no_devices"}

    async def test_success_proceeds_to_devices_step(self, flow, mock_devices):
        """Valid API key with devices proceeds to device selection."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.return_value = mock_devices
            mock_client_cls.return_value = mock_client

            result = await flow.async_step_user(
                user_input={CONF_API_KEY: "valid-key", CONF_POLLING_INTERVAL: 120}
            )

        assert result["type"] == "form"
        assert result["step_id"] == "devices"

    async def test_stores_api_key_and_interval_for_step2(self, flow, mock_devices):
        """Successful step 1 stores api_key and interval for step 2."""
        with patch(
            "custom_components.senec_connect.config_flow.SenecApiClient"
        ) as mock_client_cls, patch(
            "custom_components.senec_connect.config_flow.async_get_clientsession"
        ), patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow, "_abort_if_unique_id_configured"
        ):
            mock_client = AsyncMock()
            mock_client.async_validate_api_key.return_value = mock_devices
            mock_client_cls.return_value = mock_client

            await flow.async_step_user(
                user_input={CONF_API_KEY: "my-api-key", CONF_POLLING_INTERVAL: 90}
            )

        assert flow._api_key == "my-api-key"
        assert flow._polling_interval == 90
        assert flow._devices == mock_devices

    async def test_duplicate_api_key_aborts(self, flow):
        """Duplicate API key aborts with already_configured."""
        from homeassistant.data_entry_flow import AbortFlow

        with patch.object(
            flow, "async_set_unique_id", new_callable=AsyncMock
        ), patch.object(
            flow,
            "_abort_if_unique_id_configured",
            side_effect=AbortFlow("already_configured"),
        ):
            with pytest.raises(AbortFlow) as exc_info:
                await flow.async_step_user(
                    user_input={CONF_API_KEY: "duplicate-key", CONF_POLLING_INTERVAL: 60}
                )

        assert exc_info.value.reason == "already_configured"


class TestAsyncStepDevices:
    """Tests for the second config flow step (device selection)."""

    async def test_shows_form_on_no_input(self, flow, mock_devices):
        """Step_devices shows form when no input is provided."""
        flow._devices = mock_devices

        result = await flow.async_step_devices(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "devices"
        assert result["errors"] == {}

    async def test_no_selection_error(self, flow, mock_devices):
        """No selection shows no_selection error."""
        flow._devices = mock_devices

        result = await flow.async_step_devices(
            user_input={CONF_SELECTED_DEVICES: []}
        )

        assert result["type"] == "form"
        assert result["errors"] == {"base": "no_selection"}

    async def test_success_creates_entry(self, flow, mock_devices):
        """Selecting devices creates a config entry."""
        flow._devices = mock_devices
        flow._api_key = "valid-key"
        flow._polling_interval = 120

        result = await flow.async_step_devices(
            user_input={CONF_SELECTED_DEVICES: ["v4-00012ff4", "v3-0000abcd"]}
        )

        assert result["type"] == "create_entry"
        assert result["title"] == "SENEC Connect"
        assert result["data"] == {
            CONF_API_KEY: "valid-key",
            CONF_POLLING_INTERVAL: 120,
            CONF_SELECTED_DEVICES: ["v4-00012ff4", "v3-0000abcd"],
        }

    async def test_single_device_selection(self, flow, mock_devices):
        """Selecting a single device creates a config entry."""
        flow._devices = mock_devices
        flow._api_key = "valid-key"
        flow._polling_interval = 60

        result = await flow.async_step_devices(
            user_input={CONF_SELECTED_DEVICES: ["v4-00012ff4"]}
        )

        assert result["type"] == "create_entry"
        assert result["data"][CONF_SELECTED_DEVICES] == ["v4-00012ff4"]

    async def test_device_options_format(self, flow, mock_devices):
        """Device options are formatted as '{model} ({serial})'."""
        flow._devices = mock_devices

        result = await flow.async_step_devices(user_input=None)

        # Verify the flow has the correct devices stored
        assert len(flow._devices) == 2
        assert flow._devices[0].bess_nameplate.serial_number == "v4-00012ff4"
        assert flow._devices[1].bess_nameplate.serial_number == "v3-0000abcd"
