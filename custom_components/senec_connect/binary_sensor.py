"""Binary sensor platform for the SENEC Connect integration.

Provides binary sensors for wallbox EV connection and charging status.
Entities are dynamically managed based on the evse array in coordinator data.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SenecDataUpdateCoordinator
from .models import WallboxData

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SenecBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a SENEC binary sensor entity with a value extraction function."""

    value_fn: Callable[[WallboxData], bool | None]


BINARY_SENSOR_DESCRIPTIONS: tuple[SenecBinarySensorEntityDescription, ...] = (
    SenecBinarySensorEntityDescription(
        key="ev_connected",
        name="EV Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda wb: wb.ev_connected,
    ),
    SenecBinarySensorEntityDescription(
        key="ev_charging",
        name="EV Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda wb: wb.ev_charging,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SENEC binary sensor entities from a config entry."""
    coordinator: SenecDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    tracker = WallboxBinarySensorTracker(coordinator, async_add_entities)
    tracker.setup()


class WallboxBinarySensorTracker:
    """Tracks wallbox presence and dynamically adds/removes binary sensor entities."""

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize the wallbox binary sensor tracker."""
        self.coordinator = coordinator
        self.async_add_entities = async_add_entities
        # Track known wallboxes as {(serial, wallbox_id): set_of_entity_keys}
        self._tracked_wallboxes: set[tuple[str, str]] = set()
        # Track entity objects for removal
        self._entities: dict[str, SenecBinarySensorEntity] = {}

    def setup(self) -> None:
        """Set up initial entities and register listener for updates."""
        self._process_coordinator_data()
        self.coordinator.async_add_listener(self._on_coordinator_update)

    @callback
    def _on_coordinator_update(self) -> None:
        """Handle coordinator data update - add/remove entities as needed."""
        self._process_coordinator_data()

    def _process_coordinator_data(self) -> None:
        """Process current coordinator data and sync entities."""
        if not self.coordinator.data:
            return

        current_wallboxes: set[tuple[str, str]] = set()

        for serial, device_data in self.coordinator.data.items():
            for wallbox in device_data.wallboxes:
                current_wallboxes.add((serial, wallbox.id))

        # Determine new wallboxes that need entities
        new_wallboxes = current_wallboxes - self._tracked_wallboxes

        # Determine removed wallboxes
        removed_wallboxes = self._tracked_wallboxes - current_wallboxes

        # Add entities for new wallboxes
        if new_wallboxes:
            new_entities: list[SenecBinarySensorEntity] = []
            for serial, wb_id in new_wallboxes:
                for description in BINARY_SENSOR_DESCRIPTIONS:
                    entity = SenecBinarySensorEntity(
                        coordinator=self.coordinator,
                        entity_description=description,
                        serial_number=serial,
                        wallbox_id=wb_id,
                    )
                    unique_key = f"{serial}_{wb_id}_{description.key}"
                    self._entities[unique_key] = entity
                    new_entities.append(entity)
            self.async_add_entities(new_entities)

        # Mark removed wallbox entities as unavailable
        for serial, wb_id in removed_wallboxes:
            for description in BINARY_SENSOR_DESCRIPTIONS:
                unique_key = f"{serial}_{wb_id}_{description.key}"
                entity = self._entities.get(unique_key)
                if entity is not None:
                    entity.set_unavailable()

        self._tracked_wallboxes = current_wallboxes


class SenecBinarySensorEntity(
    CoordinatorEntity[SenecDataUpdateCoordinator], BinarySensorEntity
):
    """Binary sensor entity for SENEC wallbox status."""

    entity_description: SenecBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        entity_description: SenecBinarySensorEntityDescription,
        serial_number: str,
        wallbox_id: str,
    ) -> None:
        """Initialize the binary sensor entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._serial_number = serial_number
        self._wallbox_id = wallbox_id
        self._attr_unique_id = f"{serial_number}_{wallbox_id}_{entity_description.key}"
        self._force_unavailable = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the wallbox device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._wallbox_id)},
            manufacturer="SENEC",
            model="Wallbox",
            name=f"Wallbox {self._wallbox_id}",
            via_device=(DOMAIN, self._serial_number),
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        if self._force_unavailable:
            return False
        if not self.coordinator.last_update_success:
            return False
        # Check if the wallbox still exists in the data
        data = self.coordinator.data
        if not data or self._serial_number not in data:
            return False
        device_data = data[self._serial_number]
        return any(wb.id == self._wallbox_id for wb in device_data.wallboxes)

    @property
    def is_on(self) -> bool | None:
        """Return the binary sensor state."""
        if not self.coordinator.data:
            return None
        device_data = self.coordinator.data.get(self._serial_number)
        if device_data is None:
            return None
        for wallbox in device_data.wallboxes:
            if wallbox.id == self._wallbox_id:
                return self.entity_description.value_fn(wallbox)
        return None

    @callback
    def set_unavailable(self) -> None:
        """Mark this entity as forcefully unavailable (wallbox removed)."""
        self._force_unavailable = True
        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # If the wallbox reappears, clear the force unavailable flag
        if self._force_unavailable and self.coordinator.data:
            device_data = self.coordinator.data.get(self._serial_number)
            if device_data is not None:
                if any(wb.id == self._wallbox_id for wb in device_data.wallboxes):
                    self._force_unavailable = False
        super()._handle_coordinator_update()
