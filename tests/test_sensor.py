"""Tests for the SENEC Connect sensor platform.

Covers:
- Entity creation with complete data
- Value mapping (native_value correctly mapped via value_fn)
- Availability logic (section null, field null)
- Wallbox entity creation and assignment
- Device registry entries (identifiers, manufacturer, model, via_device)

Validates: Requirements 11.5
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.senec_connect.const import DOMAIN
from custom_components.senec_connect.models import (
    BatteryData,
    BessNameplateData,
    DeviceData,
    MeterData,
    WallboxData,
)
from custom_components.senec_connect.sensor import (
    BATTERY_SENSOR_DESCRIPTIONS,
    BESS_SENSOR_DESCRIPTIONS,
    DEVICE_SENSOR_DESCRIPTIONS,
    METER_SENSOR_DESCRIPTIONS,
    WALLBOX_SENSOR_DESCRIPTIONS,
    SenecSensorEntity,
    SenecWallboxSensorEntity,
    async_setup_entry,
)


# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------

SERIAL = "v4-00012ff4"


def _battery(**overrides) -> BatteryData:
    defaults = {
        "state": 0,
        "state_of_charge": 75,
        "power": 1500.0,
        "voltage": 52.3,
        "current": 28.7,
    }
    defaults.update(overrides)
    return BatteryData(**defaults)


def _bess(**overrides) -> BessNameplateData:
    defaults = {
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


def _meter(**overrides) -> MeterData:
    defaults = {
        "grid_power": -500.0,
        "consumption": 1200.0,
        "production": 3200.0,
    }
    defaults.update(overrides)
    return MeterData(**defaults)


def _wallbox(**overrides) -> WallboxData:
    defaults = {
        "id": "WB-01",
        "ev_connected": True,
        "ev_charging": True,
        "charging_power": 7400.0,
    }
    defaults.update(overrides)
    return WallboxData(**defaults)


def _device(**overrides) -> DeviceData:
    defaults = {
        "battery": _battery(),
        "bess_nameplate": _bess(),
        "meter": _meter(),
        "wallboxes": [_wallbox()],
    }
    defaults.update(overrides)
    return DeviceData(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def coordinator():
    """Create a mock coordinator with full device data."""
    c = MagicMock()
    c.last_update_success = True
    c.config_entry = MagicMock()
    c.config_entry.entry_id = "test_entry_id"
    c.data = {SERIAL: _device()}
    return c


@pytest.fixture
def coordinator_no_battery():
    """Create a mock coordinator with no battery section."""
    c = MagicMock()
    c.last_update_success = True
    c.config_entry = MagicMock()
    c.config_entry.entry_id = "test_entry_id"
    c.data = {SERIAL: _device(battery=None)}
    return c


@pytest.fixture
def coordinator_no_meter():
    """Create a mock coordinator with no meter section."""
    c = MagicMock()
    c.last_update_success = True
    c.config_entry = MagicMock()
    c.config_entry.entry_id = "test_entry_id"
    c.data = {SERIAL: _device(meter=None)}
    return c


@pytest.fixture
def coordinator_partial_meter():
    """Create a mock coordinator with meter that has null fields."""
    c = MagicMock()
    c.last_update_success = True
    c.config_entry = MagicMock()
    c.config_entry.entry_id = "test_entry_id"
    c.data = {SERIAL: _device(meter=_meter(consumption=None, production=None))}
    return c


# ---------------------------------------------------------------------------
# Tests: Entity Creation with Complete Data
# ---------------------------------------------------------------------------


class TestSensorEntityCreation:
    """Test sensor entity creation with complete data."""

    def test_battery_soc_entity_creation(self, coordinator):
        """Test SenecSensorEntity is created correctly for battery SOC."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]  # battery_soc
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.entity_description == desc
        assert entity._serial_number == SERIAL
        assert entity._attr_has_entity_name is True

    def test_unique_id_format(self, coordinator):
        """Test unique_id follows {serial}_{key} format."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.unique_id == f"{SERIAL}_battery_soc"

    def test_unique_id_for_all_battery_sensors(self, coordinator):
        """Test unique_id is correct for all battery sensor descriptions."""
        expected_keys = [
            "battery_soc",
            "battery_power",
            "battery_voltage",
            "battery_current",
            "battery_state",
        ]
        for desc, expected_key in zip(BATTERY_SENSOR_DESCRIPTIONS, expected_keys):
            entity = SenecSensorEntity(coordinator, desc, SERIAL)
            assert entity.unique_id == f"{SERIAL}_{expected_key}"

    def test_unique_id_for_meter_sensors(self, coordinator):
        """Test unique_id is correct for all meter sensor descriptions."""
        expected_keys = ["grid_power", "consumption", "production"]
        for desc, expected_key in zip(METER_SENSOR_DESCRIPTIONS, expected_keys):
            entity = SenecSensorEntity(coordinator, desc, SERIAL)
            assert entity.unique_id == f"{SERIAL}_{expected_key}"

    def test_unique_id_for_bess_sensors(self, coordinator):
        """Test unique_id is correct for all BESS sensor descriptions."""
        expected_keys = [
            "bess_manufacturer",
            "bess_model",
            "bess_serial",
            "bess_system_id",
            "bess_design_capacity",
            "bess_charge_power",
            "bess_discharge_power",
        ]
        for desc, expected_key in zip(BESS_SENSOR_DESCRIPTIONS, expected_keys):
            entity = SenecSensorEntity(coordinator, desc, SERIAL)
            assert entity.unique_id == f"{SERIAL}_{expected_key}"

    def test_all_device_sensor_descriptions_combined(self):
        """Test DEVICE_SENSOR_DESCRIPTIONS contains all non-wallbox sensors."""
        expected_count = (
            len(BATTERY_SENSOR_DESCRIPTIONS)
            + len(METER_SENSOR_DESCRIPTIONS)
            + len(BESS_SENSOR_DESCRIPTIONS)
        )
        assert len(DEVICE_SENSOR_DESCRIPTIONS) == expected_count


# ---------------------------------------------------------------------------
# Tests: Value Mapping (native_value)
# ---------------------------------------------------------------------------


class TestSensorNativeValue:
    """Test that native_value is correctly mapped via value_fn."""

    def test_battery_soc_value(self, coordinator):
        """Test battery SOC returns the correct percentage value."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 75

    def test_battery_power_value(self, coordinator):
        """Test battery power returns the correct watt value."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[1]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 1500.0

    def test_battery_voltage_value(self, coordinator):
        """Test battery voltage returns the correct volt value."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[2]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 52.3

    def test_battery_current_value(self, coordinator):
        """Test battery current returns the correct ampere value."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[3]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 28.7

    def test_battery_state_value_ok(self, coordinator):
        """Test battery state returns 'OK' when state is 0."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[4]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "OK"

    def test_battery_state_value_error(self, coordinator):
        """Test battery state returns 'Fehler' when state is 1."""
        coordinator.data[SERIAL] = _device(battery=_battery(state=1))
        desc = BATTERY_SENSOR_DESCRIPTIONS[4]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "Fehler"

    def test_battery_state_value_unknown(self, coordinator):
        """Test battery state returns string of state for unknown codes."""
        coordinator.data[SERIAL] = _device(battery=_battery(state=42))
        desc = BATTERY_SENSOR_DESCRIPTIONS[4]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "42"

    def test_grid_power_value(self, coordinator):
        """Test grid power returns the correct value."""
        desc = METER_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == -500.0

    def test_consumption_value(self, coordinator):
        """Test consumption returns the correct value."""
        desc = METER_SENSOR_DESCRIPTIONS[1]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 1200.0

    def test_production_value(self, coordinator):
        """Test production returns the correct value."""
        desc = METER_SENSOR_DESCRIPTIONS[2]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 3200.0

    def test_bess_manufacturer_value(self, coordinator):
        """Test BESS manufacturer returns the correct value."""
        desc = BESS_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "SENEC GmbH"

    def test_bess_model_value(self, coordinator):
        """Test BESS model returns the correct value."""
        desc = BESS_SENSOR_DESCRIPTIONS[1]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "SENEC.Home E4 - 1ph 6 AC"

    def test_bess_serial_value(self, coordinator):
        """Test BESS serial number returns the correct value."""
        desc = BESS_SENSOR_DESCRIPTIONS[2]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == "v4-00012ff4"

    def test_bess_design_capacity_value(self, coordinator):
        """Test BESS design capacity returns the correct value."""
        desc = BESS_SENSOR_DESCRIPTIONS[4]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.native_value == 10000

    def test_native_value_none_when_device_missing(self, coordinator):
        """Test native_value returns None when device is not in data."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, "nonexistent-serial")
        assert entity.native_value is None

    def test_native_value_none_when_battery_section_null(self, coordinator_no_battery):
        """Test native_value returns None when battery section is null."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator_no_battery, desc, SERIAL)
        assert entity.native_value is None

    def test_native_value_none_when_meter_section_null(self, coordinator_no_meter):
        """Test native_value returns None when meter section is null."""
        desc = METER_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator_no_meter, desc, SERIAL)
        assert entity.native_value is None


# ---------------------------------------------------------------------------
# Tests: Availability Logic
# ---------------------------------------------------------------------------


class TestSensorAvailability:
    """Test entity availability logic."""

    def test_available_true_with_complete_data(self, coordinator):
        """Test entity is available when all data is present."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.available is True

    def test_unavailable_when_update_failed(self, coordinator):
        """Test entity is unavailable when last coordinator update failed."""
        coordinator.last_update_success = False
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.available is False

    def test_unavailable_when_device_not_in_data(self, coordinator):
        """Test entity is unavailable when device serial not in data."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, "nonexistent-serial")
        assert entity.available is False

    def test_unavailable_when_battery_section_null(self, coordinator_no_battery):
        """Test battery sensor is unavailable when battery section is null."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator_no_battery, desc, SERIAL)
        assert entity.available is False

    def test_unavailable_when_meter_section_null(self, coordinator_no_meter):
        """Test meter sensor is unavailable when meter section is null."""
        desc = METER_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator_no_meter, desc, SERIAL)
        assert entity.available is False

    def test_unavailable_when_field_null(self, coordinator_partial_meter):
        """Test sensor is unavailable when specific field is null."""
        desc = METER_SENSOR_DESCRIPTIONS[1]  # consumption
        entity = SenecSensorEntity(coordinator_partial_meter, desc, SERIAL)
        assert entity.available is False

    def test_available_when_field_present(self, coordinator_partial_meter):
        """Test sensor is available when specific field is present."""
        desc = METER_SENSOR_DESCRIPTIONS[0]  # grid_power
        entity = SenecSensorEntity(coordinator_partial_meter, desc, SERIAL)
        assert entity.available is True

    def test_all_battery_sensors_unavailable_when_no_battery(self, coordinator_no_battery):
        """Test all battery sensors are unavailable when battery section is null."""
        for desc in BATTERY_SENSOR_DESCRIPTIONS:
            entity = SenecSensorEntity(coordinator_no_battery, desc, SERIAL)
            assert entity.available is False, f"Sensor {desc.key} should be unavailable"

    def test_bess_sensor_unavailable_with_empty_string(self, coordinator):
        """Test BESS sensor is unavailable when value is empty string."""
        coordinator.data[SERIAL] = _device(bess_nameplate=_bess(manufacturer=""))
        desc = BESS_SENSOR_DESCRIPTIONS[0]  # bess_manufacturer
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        assert entity.available is False


# ---------------------------------------------------------------------------
# Tests: Wallbox Entity Creation and Assignment
# ---------------------------------------------------------------------------


class TestWallboxSensorEntity:
    """Test wallbox sensor entity creation and behavior."""

    def test_wallbox_entity_unique_id_format(self, coordinator):
        """Test unique_id follows {serial}_{wb_id}_{key} format."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        assert entity.unique_id == f"{SERIAL}_WB-01_charging_power"

    def test_wallbox_entity_name_format(self, coordinator):
        """Test wallbox entity name includes wallbox_id and description name."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        assert entity.name == "WB-01 Charging Power"

    def test_wallbox_native_value(self, coordinator):
        """Test wallbox entity returns the correct charging power."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        assert entity.native_value == 7400.0

    def test_wallbox_native_value_none_when_device_missing(self, coordinator):
        """Test wallbox native_value is None when device not in data."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, "nonexistent", "WB-01")
        assert entity.native_value is None

    def test_wallbox_native_value_none_when_wallbox_missing(self, coordinator):
        """Test wallbox native_value is None when wallbox not in device data."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-99")
        assert entity.native_value is None

    def test_wallbox_available_true(self, coordinator):
        """Test wallbox entity is available when wallbox exists."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        assert entity.available is True

    def test_wallbox_available_false_update_failed(self, coordinator):
        """Test wallbox entity is unavailable when last update failed."""
        coordinator.last_update_success = False
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        assert entity.available is False

    def test_wallbox_available_false_device_missing(self, coordinator):
        """Test wallbox entity is unavailable when device not in data."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, "nonexistent", "WB-01")
        assert entity.available is False

    def test_wallbox_available_false_wallbox_removed(self, coordinator):
        """Test wallbox entity is unavailable when wallbox was removed."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-99")
        assert entity.available is False

    def test_multiple_wallbox_entities(self, coordinator):
        """Test creating entities for multiple wallboxes."""
        coordinator.data[SERIAL] = _device(
            wallboxes=[
                _wallbox(id="WB-01", charging_power=7400.0),
                _wallbox(id="WB-02", charging_power=11000.0),
            ]
        )
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity1 = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        entity2 = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-02")

        assert entity1.native_value == 7400.0
        assert entity2.native_value == 11000.0
        assert entity1.unique_id != entity2.unique_id


# ---------------------------------------------------------------------------
# Tests: Device Registry Entries
# ---------------------------------------------------------------------------


class TestDeviceRegistryEntries:
    """Test device_info returns correct device registry information."""

    def test_primary_device_identifiers(self, coordinator):
        """Test primary device identifiers use (DOMAIN, serial)."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        device_info = entity.device_info
        assert device_info["identifiers"] == {(DOMAIN, SERIAL)}

    def test_primary_device_manufacturer_from_bess(self, coordinator):
        """Test primary device manufacturer comes from bess_nameplate."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        device_info = entity.device_info
        assert device_info["manufacturer"] == "SENEC GmbH"

    def test_primary_device_model_from_bess(self, coordinator):
        """Test primary device model comes from bess_nameplate."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        device_info = entity.device_info
        assert device_info["model"] == "SENEC.Home E4 - 1ph 6 AC"

    def test_primary_device_fallback_manufacturer(self, coordinator):
        """Test primary device falls back to 'SENEC' when no bess_nameplate."""
        coordinator.data[SERIAL] = _device(bess_nameplate=None)
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        device_info = entity.device_info
        assert device_info["manufacturer"] == "SENEC"
        assert device_info["model"] is None

    def test_primary_device_config_entry_id(self, coordinator):
        """Test primary device has correct config_entry_id."""
        desc = BATTERY_SENSOR_DESCRIPTIONS[0]
        entity = SenecSensorEntity(coordinator, desc, SERIAL)
        device_info = entity.device_info
        assert device_info["config_entry_id"] == "test_entry_id"

    def test_wallbox_device_identifiers(self, coordinator):
        """Test wallbox device identifiers use (DOMAIN, wallbox_id)."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["identifiers"] == {(DOMAIN, "WB-01")}

    def test_wallbox_device_manufacturer(self, coordinator):
        """Test wallbox device manufacturer is 'SENEC'."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["manufacturer"] == "SENEC"

    def test_wallbox_device_model(self, coordinator):
        """Test wallbox device model is 'Wallbox'."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["model"] == "Wallbox"

    def test_wallbox_device_name(self, coordinator):
        """Test wallbox device name includes wallbox ID."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["name"] == "Wallbox WB-01"

    def test_wallbox_via_device(self, coordinator):
        """Test wallbox device has via_device pointing to parent SENEC device."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["via_device"] == (DOMAIN, SERIAL)

    def test_wallbox_device_config_entry_id(self, coordinator):
        """Test wallbox device has correct config_entry_id."""
        desc = WALLBOX_SENSOR_DESCRIPTIONS[0]
        entity = SenecWallboxSensorEntity(coordinator, desc, SERIAL, "WB-01")
        device_info = entity.device_info
        assert device_info["config_entry_id"] == "test_entry_id"


# ---------------------------------------------------------------------------
# Tests: async_setup_entry
# ---------------------------------------------------------------------------


class TestAsyncSetupEntry:
    """Test the async_setup_entry function for sensors."""

    async def test_setup_creates_device_and_wallbox_sensors(self, hass):
        """Test setup creates sensors for devices and wallboxes."""
        c = MagicMock()
        c.last_update_success = True
        c.config_entry = MagicMock()
        c.config_entry.entry_id = "test_entry_id"
        c.data = {SERIAL: _device()}

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        hass.data[DOMAIN] = {entry.entry_id: c}

        added = []
        await async_setup_entry(hass, entry, added.extend)

        expected_device_sensors = len(DEVICE_SENSOR_DESCRIPTIONS)
        expected_wallbox_sensors = 1 * len(WALLBOX_SENSOR_DESCRIPTIONS)
        assert len(added) == expected_device_sensors + expected_wallbox_sensors

    async def test_setup_with_multiple_wallboxes(self, hass):
        """Test setup creates sensors for multiple wallboxes."""
        c = MagicMock()
        c.last_update_success = True
        c.config_entry = MagicMock()
        c.config_entry.entry_id = "test_entry_id"
        c.data = {
            SERIAL: _device(wallboxes=[_wallbox(id="WB-01"), _wallbox(id="WB-02")])
        }

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        hass.data[DOMAIN] = {entry.entry_id: c}

        added = []
        await async_setup_entry(hass, entry, added.extend)

        expected = len(DEVICE_SENSOR_DESCRIPTIONS) + 2 * len(WALLBOX_SENSOR_DESCRIPTIONS)
        assert len(added) == expected

    async def test_setup_without_wallboxes(self, hass):
        """Test setup creates only device sensors when no wallboxes."""
        c = MagicMock()
        c.last_update_success = True
        c.config_entry = MagicMock()
        c.config_entry.entry_id = "test_entry_id"
        c.data = {SERIAL: _device(wallboxes=[])}

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        hass.data[DOMAIN] = {entry.entry_id: c}

        added = []
        await async_setup_entry(hass, entry, added.extend)

        assert len(added) == len(DEVICE_SENSOR_DESCRIPTIONS)

    async def test_setup_with_multiple_devices(self, hass):
        """Test setup creates sensors for all selected devices."""
        c = MagicMock()
        c.last_update_success = True
        c.config_entry = MagicMock()
        c.config_entry.entry_id = "test_entry_id"
        c.data = {
            "device-001": _device(wallboxes=[]),
            "device-002": _device(wallboxes=[_wallbox(id="WB-01")]),
        }

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        hass.data[DOMAIN] = {entry.entry_id: c}

        added = []
        await async_setup_entry(hass, entry, added.extend)

        expected = 2 * len(DEVICE_SENSOR_DESCRIPTIONS) + 1 * len(WALLBOX_SENSOR_DESCRIPTIONS)
        assert len(added) == expected
