"""Shared test fixtures for SENEC Connect tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.senec_connect.models import (
    BatteryData,
    BessNameplateData,
    DeviceData,
    MeterData,
    WallboxData,
)

API_KEY = "test-subscription-key-12345"


# ---------------------------------------------------------------------------
# Factory Functions
# ---------------------------------------------------------------------------


def make_battery_data(**overrides: Any) -> BatteryData:
    """Create a BatteryData object with sensible defaults.

    All fields can be overridden via keyword arguments.
    """
    defaults: dict[str, Any] = {
        "state": 0,
        "state_of_charge": 75,
        "power": 1500.0,
        "voltage": 52.3,
        "current": 28.7,
    }
    defaults.update(overrides)
    return BatteryData(**defaults)


def make_bess_nameplate_data(**overrides: Any) -> BessNameplateData:
    """Create a BessNameplateData object with sensible defaults.

    All fields can be overridden via keyword arguments.
    """
    defaults: dict[str, Any] = {
        "manufacturer": "SENEC GmbH",
        "model": "SENEC.Home E4 - 1ph 6 AC",
        "serial_number": "v4-00012ff4",
        "system_id": "S4H1-02ER23323-0199-8F",
        "design_capacity": 10000,
        "active_charge_power": 2500,
        "active_discharge_power": 2500,
    }
    defaults.update(overrides)
    return BessNameplateData(**defaults)


def make_meter_data(**overrides: Any) -> MeterData:
    """Create a MeterData object with sensible defaults.

    All fields can be overridden via keyword arguments.
    """
    defaults: dict[str, Any] = {
        "grid_power": -500.0,
        "consumption": 1200.0,
        "production": 3200.0,
    }
    defaults.update(overrides)
    return MeterData(**defaults)


def make_wallbox_data(**overrides: Any) -> WallboxData:
    """Create a WallboxData object with sensible defaults.

    All fields can be overridden via keyword arguments.
    """
    defaults: dict[str, Any] = {
        "id": "WB-01",
        "ev_connected": True,
        "ev_charging": True,
        "charging_power": 7400.0,
    }
    defaults.update(overrides)
    return WallboxData(**defaults)


def make_device_data(**overrides: Any) -> DeviceData:
    """Create a DeviceData object with sensible defaults.

    By default, creates a fully-populated device with battery, bess_nameplate,
    meter, and one wallbox. Any section can be overridden or set to None.

    Examples:
        # Full device with defaults
        device = make_device_data()

        # Device without battery
        device = make_device_data(battery=None)

        # Device with custom serial number
        device = make_device_data(
            bess_nameplate=make_bess_nameplate_data(serial_number="v4-custom")
        )

        # Device with no wallboxes
        device = make_device_data(wallboxes=[])
    """
    defaults: dict[str, Any] = {
        "battery": make_battery_data(),
        "bess_nameplate": make_bess_nameplate_data(),
        "meter": make_meter_data(),
        "wallboxes": [make_wallbox_data()],
    }
    defaults.update(overrides)
    return DeviceData(**defaults)


# ---------------------------------------------------------------------------
# Autouse Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_frame_report_usage():
    """Patch frame.report_usage to avoid ContextVar requirement in tests."""
    with patch("homeassistant.helpers.frame.report_usage"):
        yield


# ---------------------------------------------------------------------------
# Core Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hass() -> HomeAssistant:
    """Return a mocked Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config_entries = MagicMock()
    hass.config_entries.async_entries = MagicMock(return_value=[])
    return hass


@pytest.fixture
def api_key() -> str:
    """Return a test API key."""
    return API_KEY


# ---------------------------------------------------------------------------
# API Response Fixtures (raw dicts - as returned by the API)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_device_response_full() -> list[dict]:
    """Return a full device data API response with all sections."""
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
            "evse": [
                {
                    "id": "WB-01",
                    "ev_connected": True,
                    "ev_charging": True,
                    "charging_power": 7400.0,
                }
            ],
        }
    ]


@pytest.fixture
def mock_device_response_minimal() -> list[dict]:
    """Return a minimal device data response (only bessNameplate)."""
    return [
        {
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home V3",
                "serial_number": "v3-0000abcd",
                "system_id": None,
                "design_capacity": 5000,
                "active_charge_power": 2000,
                "active_discharge_power": 2000,
            }
        }
    ]


@pytest.fixture
def mock_device_response_partial() -> list[dict]:
    """Return a partial device data response.

    Device has bessNameplate and meter, but battery and evse are null/missing.
    This simulates a scenario where some data sections are unavailable.
    """
    return [
        {
            "battery": None,
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
                "grid_power": 200.0,
                "consumption": None,
                "production": None,
            },
            "evse": None,
        }
    ]


@pytest.fixture
def mock_device_response_multi() -> list[dict]:
    """Return a multi-device API response with mixed data availability.

    Contains three devices:
    - Device 1: Full data (all sections present)
    - Device 2: Partial data (only bessNameplate + meter, no battery/wallbox)
    - Device 3: Minimal data (only bessNameplate)
    """
    return [
        {
            "battery": {
                "state": 0,
                "state_of_charge": 85,
                "power": 2000.0,
                "voltage": 53.1,
                "current": 37.6,
            },
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home E4 - 1ph 6 AC",
                "serial_number": "v4-device-001",
                "system_id": "S4H1-AAAA-0001",
                "design_capacity": 10000,
                "active_charge_power": 2500,
                "active_discharge_power": 2500,
            },
            "meter": {
                "grid_power": -1500.0,
                "consumption": 800.0,
                "production": 4300.0,
            },
            "evse": [
                {
                    "id": "WB-01",
                    "ev_connected": True,
                    "ev_charging": True,
                    "charging_power": 11000.0,
                },
                {
                    "id": "WB-02",
                    "ev_connected": True,
                    "ev_charging": False,
                    "charging_power": 0.0,
                },
            ],
        },
        {
            "battery": None,
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home V3",
                "serial_number": "v3-device-002",
                "system_id": None,
                "design_capacity": 5000,
                "active_charge_power": 2000,
                "active_discharge_power": 2000,
            },
            "meter": {
                "grid_power": 300.0,
                "consumption": 1500.0,
                "production": 1200.0,
            },
            "evse": None,
        },
        {
            "bessNameplate": {
                "manufacturer": "SENEC GmbH",
                "model": "SENEC.Home E4 - 3ph 12 AC",
                "serial_number": "v4-device-003",
                "system_id": "S4H1-CCCC-0003",
                "design_capacity": 20000,
                "active_charge_power": 5000,
                "active_discharge_power": 5000,
            },
        },
    ]


@pytest.fixture
def mock_device_response_empty() -> list[dict]:
    """Return an empty device data API response (no devices)."""
    return []


@pytest.fixture
def mock_device_response_error_401() -> dict:
    """Return a 401 error response payload."""
    return {
        "statusCode": 401,
        "message": "Access denied due to invalid subscription key.",
    }


@pytest.fixture
def mock_device_response_error_500() -> dict:
    """Return a 500 error response payload."""
    return {
        "statusCode": 500,
        "message": "Internal server error.",
    }
