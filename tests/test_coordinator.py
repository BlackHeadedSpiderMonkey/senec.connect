"""Unit tests for the SenecDataUpdateCoordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.senec_connect.api_client import SenecApiClient
from custom_components.senec_connect.coordinator import SenecDataUpdateCoordinator
from custom_components.senec_connect.exceptions import (
    SenecApiError,
    SenecAuthError,
    SenecConnectionError,
)
from custom_components.senec_connect.models import DeviceData


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return a mocked SenecApiClient."""
    client = AsyncMock(spec=SenecApiClient)
    return client


@pytest.fixture
def coordinator(
    hass: HomeAssistant, mock_client: AsyncMock
) -> SenecDataUpdateCoordinator:
    """Return a coordinator with default config."""
    return SenecDataUpdateCoordinator(
        hass=hass,
        client=mock_client,
        selected_serials=["v4-00012ff4"],
        update_interval=timedelta(seconds=60),
    )


@pytest.fixture
def multi_device_response() -> list[dict]:
    """Return a multi-device API response."""
    return [
        {
            "battery": {
                "state": 0,
                "state_of_charge": 75,
                "power": 1500.0,
                "voltage": 52.3,
                "current": 28.7,
            },
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home E4 - 1ph 6 AC",
                "serial_number": "v4-00012ff4",
                "system_id": "S4H1-02ER23323-0199-8F",
                "design_capacity": 10000,
                "active_charge_power": 2500,
                "active_discharge_power": 2500,
            },
            "meter": {
                "grid_power": -500.0,
                "consumption": 1200.0,
                "production": 3200.0,
            },
        },
        {
            "battery": {
                "state": 0,
                "state_of_charge": 50,
                "power": -800.0,
                "voltage": 51.0,
                "current": -15.7,
            },
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home V3",
                "serial_number": "v3-0000abcd",
                "system_id": None,
                "design_capacity": 5000,
                "active_charge_power": 2000,
                "active_discharge_power": 2000,
            },
            "meter": {
                "grid_power": 200.0,
                "consumption": 900.0,
                "production": None,
            },
        },
    ]


async def test_coordinator_init(
    hass: HomeAssistant, mock_client: AsyncMock
) -> None:
    """Test coordinator initialization."""
    coordinator = SenecDataUpdateCoordinator(
        hass=hass,
        client=mock_client,
        selected_serials=["v4-00012ff4", "v3-0000abcd"],
        update_interval=timedelta(seconds=120),
    )

    assert coordinator.client is mock_client
    assert coordinator.selected_serials == ["v4-00012ff4", "v3-0000abcd"]
    assert coordinator.update_interval == timedelta(seconds=120)
    assert coordinator.name == "SENEC Connect"


async def test_successful_update_single_device(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
    mock_device_response_full: list[dict],
) -> None:
    """Test successful data update with a single selected device."""
    mock_client.async_get_device_data.return_value = [
        DeviceData.from_dict(d) for d in mock_device_response_full
    ]

    result = await coordinator._async_update_data()

    assert "v4-00012ff4" in result
    assert result["v4-00012ff4"].bess_nameplate.serial_number == "v4-00012ff4"
    assert result["v4-00012ff4"].battery.state_of_charge == 75
    mock_client.async_get_device_data.assert_called_once()


async def test_successful_update_filters_to_selected_devices(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    multi_device_response: list[dict],
) -> None:
    """Test that only selected devices are included in the result."""
    coordinator = SenecDataUpdateCoordinator(
        hass=hass,
        client=mock_client,
        selected_serials=["v4-00012ff4"],
        update_interval=timedelta(seconds=60),
    )
    mock_client.async_get_device_data.return_value = [
        DeviceData.from_dict(d) for d in multi_device_response
    ]

    result = await coordinator._async_update_data()

    assert "v4-00012ff4" in result
    assert "v3-0000abcd" not in result
    assert len(result) == 1


async def test_successful_update_multiple_selected_devices(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    multi_device_response: list[dict],
) -> None:
    """Test that multiple selected devices are all included."""
    coordinator = SenecDataUpdateCoordinator(
        hass=hass,
        client=mock_client,
        selected_serials=["v4-00012ff4", "v3-0000abcd"],
        update_interval=timedelta(seconds=60),
    )
    mock_client.async_get_device_data.return_value = [
        DeviceData.from_dict(d) for d in multi_device_response
    ]

    result = await coordinator._async_update_data()

    assert "v4-00012ff4" in result
    assert "v3-0000abcd" in result
    assert len(result) == 2


async def test_missing_device_not_in_result(
    hass: HomeAssistant,
    mock_client: AsyncMock,
    mock_device_response_full: list[dict],
) -> None:
    """Test that a selected device missing from API response is not in result."""
    coordinator = SenecDataUpdateCoordinator(
        hass=hass,
        client=mock_client,
        selected_serials=["v4-00012ff4", "missing-serial"],
        update_interval=timedelta(seconds=60),
    )
    mock_client.async_get_device_data.return_value = [
        DeviceData.from_dict(d) for d in mock_device_response_full
    ]

    result = await coordinator._async_update_data()

    assert "v4-00012ff4" in result
    assert "missing-serial" not in result
    assert len(result) == 1


async def test_empty_api_response_raises_update_failed(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
) -> None:
    """Test that an empty API response raises UpdateFailed."""
    mock_client.async_get_device_data.return_value = []

    with pytest.raises(UpdateFailed, match="No device data available"):
        await coordinator._async_update_data()


async def test_auth_error_raises_update_failed(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
) -> None:
    """Test that SenecAuthError is wrapped in UpdateFailed."""
    mock_client.async_get_device_data.side_effect = SenecAuthError(
        "Authentication failed with status 401"
    )

    with pytest.raises(UpdateFailed, match="Authentication failed"):
        await coordinator._async_update_data()


async def test_api_error_raises_update_failed(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
) -> None:
    """Test that SenecApiError is wrapped in UpdateFailed."""
    mock_client.async_get_device_data.side_effect = SenecApiError(
        status_code=500, message="Internal Server Error"
    )

    with pytest.raises(UpdateFailed, match="API error.*500"):
        await coordinator._async_update_data()


async def test_connection_error_raises_update_failed(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
) -> None:
    """Test that SenecConnectionError is wrapped in UpdateFailed."""
    mock_client.async_get_device_data.side_effect = SenecConnectionError(
        "Connection timeout"
    )

    with pytest.raises(UpdateFailed, match="Connection error"):
        await coordinator._async_update_data()


async def test_device_without_bess_nameplate_is_skipped(
    coordinator: SenecDataUpdateCoordinator,
    mock_client: AsyncMock,
) -> None:
    """Test that devices without bess_nameplate data are skipped."""
    # A device with no bessNameplate section cannot be matched by serial
    mock_client.async_get_device_data.return_value = [
        DeviceData.from_dict({"battery": {"state": 0, "state_of_charge": 50, "power": 0.0}})
    ]

    result = await coordinator._async_update_data()

    assert len(result) == 0
