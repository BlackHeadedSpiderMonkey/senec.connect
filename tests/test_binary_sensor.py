"""Tests for the SENEC Connect binary sensor platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.senec_connect.binary_sensor import (
    BINARY_SENSOR_DESCRIPTIONS,
    SenecBinarySensorEntity,
    SenecBinarySensorEntityDescription,
    WallboxBinarySensorTracker,
    async_setup_entry,
)
from custom_components.senec_connect.const import DOMAIN
from custom_components.senec_connect.models import (
    BessNameplateData,
    DeviceData,
    WallboxData,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator with device data containing a wallbox."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "v4-00012ff4": DeviceData(
            bess_nameplate=BessNameplateData(
                manufacturer="SENEC GmbH",
                model="SENEC.Home E4",
                serial_number="v4-00012ff4",
                design_capacity=10000,
                active_charge_power=2500,
                active_discharge_power=2500,
            ),
            wallboxes=[
                WallboxData(
                    id="WB-01",
                    ev_connected=True,
                    ev_charging=False,
                    charging_power=0.0,
                ),
            ],
        ),
    }
    coordinator.async_add_listener = MagicMock()
    return coordinator


@pytest.fixture
def mock_coordinator_multi_wallbox():
    """Create a mock coordinator with multiple wallboxes."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "v4-00012ff4": DeviceData(
            bess_nameplate=BessNameplateData(
                manufacturer="SENEC GmbH",
                model="SENEC.Home E4",
                serial_number="v4-00012ff4",
                design_capacity=10000,
                active_charge_power=2500,
                active_discharge_power=2500,
            ),
            wallboxes=[
                WallboxData(
                    id="WB-01",
                    ev_connected=True,
                    ev_charging=True,
                    charging_power=7400.0,
                ),
                WallboxData(
                    id="WB-02",
                    ev_connected=False,
                    ev_charging=False,
                    charging_power=0.0,
                ),
            ],
        ),
    }
    coordinator.async_add_listener = MagicMock()
    return coordinator


class TestBinarySensorDescriptions:
    """Test binary sensor entity descriptions."""

    def test_ev_connected_description(self):
        """Test EV Connected sensor description has correct attributes."""
        desc = BINARY_SENSOR_DESCRIPTIONS[0]
        assert desc.key == "ev_connected"
        assert desc.device_class.value == "connectivity"

    def test_ev_charging_description(self):
        """Test EV Charging sensor description has correct attributes."""
        desc = BINARY_SENSOR_DESCRIPTIONS[1]
        assert desc.key == "ev_charging"
        assert desc.device_class.value == "battery_charging"

    def test_ev_connected_value_fn(self):
        """Test EV Connected value_fn extracts correct value."""
        wb = WallboxData(id="WB-01", ev_connected=True, ev_charging=False, charging_power=0.0)
        desc = BINARY_SENSOR_DESCRIPTIONS[0]
        assert desc.value_fn(wb) is True

    def test_ev_charging_value_fn(self):
        """Test EV Charging value_fn extracts correct value."""
        wb = WallboxData(id="WB-01", ev_connected=True, ev_charging=True, charging_power=7400.0)
        desc = BINARY_SENSOR_DESCRIPTIONS[1]
        assert desc.value_fn(wb) is True

    def test_ev_charging_value_fn_not_charging(self):
        """Test EV Charging value_fn returns False when not charging."""
        wb = WallboxData(id="WB-01", ev_connected=True, ev_charging=False, charging_power=0.0)
        desc = BINARY_SENSOR_DESCRIPTIONS[1]
        assert desc.value_fn(wb) is False


class TestSenecBinarySensorEntity:
    """Test binary sensor entity behavior."""

    def test_unique_id_format(self, mock_coordinator):
        """Test unique_id follows {serial}_{wb_id}_{suffix} format."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.unique_id == "v4-00012ff4_WB-01_ev_connected"

    def test_unique_id_charging(self, mock_coordinator):
        """Test unique_id for charging sensor."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[1],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.unique_id == "v4-00012ff4_WB-01_ev_charging"

    def test_device_info(self, mock_coordinator):
        """Test device info returns correct wallbox device info."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        device_info = entity.device_info
        assert device_info["identifiers"] == {(DOMAIN, "WB-01")}
        assert device_info["manufacturer"] == "SENEC"
        assert device_info["model"] == "Wallbox"
        assert device_info["name"] == "Wallbox WB-01"
        assert device_info["via_device"] == (DOMAIN, "v4-00012ff4")

    def test_is_on_ev_connected_true(self, mock_coordinator):
        """Test is_on returns True when EV is connected."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.is_on is True

    def test_is_on_ev_charging_false(self, mock_coordinator):
        """Test is_on returns False when EV is not charging."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[1],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.is_on is False

    def test_is_on_no_data(self, mock_coordinator):
        """Test is_on returns None when coordinator has no data."""
        mock_coordinator.data = None
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.is_on is None

    def test_is_on_device_missing(self, mock_coordinator):
        """Test is_on returns None when device is not in coordinator data."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="nonexistent-serial",
            wallbox_id="WB-01",
        )
        assert entity.is_on is None

    def test_is_on_wallbox_missing(self, mock_coordinator):
        """Test is_on returns None when wallbox is not in device data."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-99",
        )
        assert entity.is_on is None

    def test_available_true(self, mock_coordinator):
        """Test entity is available when wallbox exists in data."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.available is True

    def test_available_false_no_data(self, mock_coordinator):
        """Test entity is unavailable when coordinator has no data."""
        mock_coordinator.data = None
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.available is False

    def test_available_false_update_failed(self, mock_coordinator):
        """Test entity is unavailable when last update failed."""
        mock_coordinator.last_update_success = False
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        assert entity.available is False

    def test_available_false_wallbox_removed(self, mock_coordinator):
        """Test entity is unavailable when wallbox no longer exists."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-99",
        )
        assert entity.available is False

    def test_set_unavailable(self, mock_coordinator):
        """Test set_unavailable marks the entity as forced unavailable."""
        entity = SenecBinarySensorEntity(
            coordinator=mock_coordinator,
            entity_description=BINARY_SENSOR_DESCRIPTIONS[0],
            serial_number="v4-00012ff4",
            wallbox_id="WB-01",
        )
        # Mock async_write_ha_state since we're not in a real HA context
        entity.async_write_ha_state = MagicMock()
        entity.set_unavailable()
        assert entity.available is False
        entity.async_write_ha_state.assert_called_once()


class TestWallboxBinarySensorTracker:
    """Test dynamic wallbox entity tracking."""

    def test_initial_entities_created(self, mock_coordinator):
        """Test that initial entities are created on setup."""
        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        tracker = WallboxBinarySensorTracker(mock_coordinator, mock_add_entities)
        tracker.setup()

        # 1 wallbox × 2 descriptions = 2 entities
        assert len(added_entities) == 2
        unique_ids = {e.unique_id for e in added_entities}
        assert "v4-00012ff4_WB-01_ev_connected" in unique_ids
        assert "v4-00012ff4_WB-01_ev_charging" in unique_ids

    def test_multi_wallbox_entities_created(self, mock_coordinator_multi_wallbox):
        """Test that entities are created for multiple wallboxes."""
        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        tracker = WallboxBinarySensorTracker(
            mock_coordinator_multi_wallbox, mock_add_entities
        )
        tracker.setup()

        # 2 wallboxes × 2 descriptions = 4 entities
        assert len(added_entities) == 4
        unique_ids = {e.unique_id for e in added_entities}
        assert "v4-00012ff4_WB-01_ev_connected" in unique_ids
        assert "v4-00012ff4_WB-01_ev_charging" in unique_ids
        assert "v4-00012ff4_WB-02_ev_connected" in unique_ids
        assert "v4-00012ff4_WB-02_ev_charging" in unique_ids

    def test_new_wallbox_adds_entities(self, mock_coordinator):
        """Test that a new wallbox appearing triggers entity creation."""
        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        tracker = WallboxBinarySensorTracker(mock_coordinator, mock_add_entities)
        tracker.setup()

        # Initially 2 entities (WB-01)
        assert len(added_entities) == 2

        # Simulate coordinator update with new wallbox
        mock_coordinator.data["v4-00012ff4"] = DeviceData(
            wallboxes=[
                WallboxData(id="WB-01", ev_connected=True, ev_charging=False, charging_power=0.0),
                WallboxData(id="WB-02", ev_connected=False, ev_charging=False, charging_power=0.0),
            ],
        )

        # Trigger the listener callback
        listener_callback = mock_coordinator.async_add_listener.call_args[0][0]
        listener_callback()

        # Should now have 4 entities total (2 from WB-01 + 2 from WB-02)
        assert len(added_entities) == 4

    def test_removed_wallbox_marks_unavailable(self, mock_coordinator):
        """Test that a removed wallbox marks its entities as unavailable."""
        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        tracker = WallboxBinarySensorTracker(mock_coordinator, mock_add_entities)
        tracker.setup()

        # Mock async_write_ha_state for all created entities
        for entity in added_entities:
            entity.async_write_ha_state = MagicMock()

        # Remove wallbox from data
        mock_coordinator.data["v4-00012ff4"] = DeviceData(wallboxes=[])

        # Trigger the listener callback
        listener_callback = mock_coordinator.async_add_listener.call_args[0][0]
        listener_callback()

        # Both entities should now have been set as unavailable
        for entity in added_entities:
            assert entity.available is False

    def test_no_entities_when_no_wallboxes(self):
        """Test that no entities are created when evse is empty."""
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.data = {
            "v4-00012ff4": DeviceData(wallboxes=[]),
        }
        coordinator.async_add_listener = MagicMock()

        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        tracker = WallboxBinarySensorTracker(coordinator, mock_add_entities)
        tracker.setup()

        assert len(added_entities) == 0


class TestAsyncSetupEntry:
    """Test the async_setup_entry function."""

    async def test_setup_entry_creates_tracker(self, hass):
        """Test that async_setup_entry creates a tracker and initial entities."""
        coordinator = MagicMock()
        coordinator.last_update_success = True
        coordinator.data = {
            "v4-00012ff4": DeviceData(
                wallboxes=[
                    WallboxData(id="WB-01", ev_connected=True, ev_charging=False, charging_power=0.0),
                ],
            ),
        }
        coordinator.async_add_listener = MagicMock()

        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        hass.data[DOMAIN] = {entry.entry_id: coordinator}

        added_entities = []

        def mock_add_entities(entities):
            added_entities.extend(entities)

        await async_setup_entry(hass, entry, mock_add_entities)

        assert len(added_entities) == 2
        assert coordinator.async_add_listener.called
