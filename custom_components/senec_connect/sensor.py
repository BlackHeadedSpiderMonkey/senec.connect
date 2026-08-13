"""Sensor platform for the SENEC Connect integration.

Creates sensor entities for battery, meter, BESS nameplate, and wallbox data.
Entity descriptions are defined declaratively with value extraction functions.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SenecDataUpdateCoordinator
from .models import DeviceData


def _battery_state_value(data: DeviceData) -> StateType:
    """Map battery state integer to human-readable string."""
    if data.battery is None:
        return None
    state = data.battery.state
    if state == 0:
        return "OK"
    if state == 1:
        return "Fehler"
    return str(state)


@dataclass(frozen=True, kw_only=True)
class SenecSensorEntityDescription(SensorEntityDescription):
    """Sensor entity description with value extraction functions."""

    value_fn: Callable[[DeviceData], StateType]
    available_fn: Callable[[DeviceData], bool]


# --- Battery Sensors ---

BATTERY_SENSOR_DESCRIPTIONS: tuple[SenecSensorEntityDescription, ...] = (
    SenecSensorEntityDescription(
        key="battery_soc",
        translation_key="battery_soc",
        name="Battery State of Charge",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda data: (
            data.battery.state_of_charge if data.battery is not None else None
        ),
        available_fn=lambda data: (
            data.battery is not None and data.battery.state_of_charge is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="battery_power",
        translation_key="battery_power",
        name="Battery Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.battery.power if data.battery is not None else None
        ),
        available_fn=lambda data: (
            data.battery is not None and data.battery.power is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        name="Battery Voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        value_fn=lambda data: (
            data.battery.voltage if data.battery is not None else None
        ),
        available_fn=lambda data: (
            data.battery is not None and data.battery.voltage is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="battery_current",
        translation_key="battery_current",
        name="Battery Current",
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        value_fn=lambda data: (
            data.battery.current if data.battery is not None else None
        ),
        available_fn=lambda data: (
            data.battery is not None and data.battery.current is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="battery_state",
        translation_key="battery_state",
        name="Battery State",
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=_battery_state_value,
        available_fn=lambda data: (
            data.battery is not None and data.battery.state is not None
        ),
    ),
)

# --- Meter Sensors ---

METER_SENSOR_DESCRIPTIONS: tuple[SenecSensorEntityDescription, ...] = (
    SenecSensorEntityDescription(
        key="grid_power",
        translation_key="grid_power",
        name="Grid Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.meter.grid_power if data.meter is not None else None
        ),
        available_fn=lambda data: (
            data.meter is not None and data.meter.grid_power is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="consumption",
        translation_key="consumption",
        name="Consumption",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.meter.consumption if data.meter is not None else None
        ),
        available_fn=lambda data: (
            data.meter is not None and data.meter.consumption is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="production",
        translation_key="production",
        name="Production",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.meter.production if data.meter is not None else None
        ),
        available_fn=lambda data: (
            data.meter is not None and data.meter.production is not None
        ),
    ),
)

# --- BESS Nameplate Sensors ---

BESS_SENSOR_DESCRIPTIONS: tuple[SenecSensorEntityDescription, ...] = (
    SenecSensorEntityDescription(
        key="bess_manufacturer",
        translation_key="bess_manufacturer",
        name="BESS Manufacturer",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: (
            data.bess_nameplate.manufacturer
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.manufacturer is not None
            and data.bess_nameplate.manufacturer != ""
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_model",
        translation_key="bess_model",
        name="BESS Model",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: (
            data.bess_nameplate.model
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.model is not None
            and data.bess_nameplate.model != ""
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_serial",
        translation_key="bess_serial",
        name="BESS Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: (
            data.bess_nameplate.serial_number
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.serial_number is not None
            and data.bess_nameplate.serial_number != ""
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_system_id",
        translation_key="bess_system_id",
        name="BESS System ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=None,
        state_class=None,
        native_unit_of_measurement=None,
        value_fn=lambda data: (
            data.bess_nameplate.system_id
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.system_id is not None
            and data.bess_nameplate.system_id != ""
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_design_capacity",
        translation_key="bess_design_capacity",
        name="BESS Design Capacity",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="Wh",
        value_fn=lambda data: (
            data.bess_nameplate.design_capacity
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.design_capacity is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_charge_power",
        translation_key="bess_charge_power",
        name="BESS Charge Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.bess_nameplate.active_charge_power
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.active_charge_power is not None
        ),
    ),
    SenecSensorEntityDescription(
        key="bess_discharge_power",
        translation_key="bess_discharge_power",
        name="BESS Discharge Power",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        value_fn=lambda data: (
            data.bess_nameplate.active_discharge_power
            if data.bess_nameplate is not None
            else None
        ),
        available_fn=lambda data: (
            data.bess_nameplate is not None
            and data.bess_nameplate.active_discharge_power is not None
        ),
    ),
)

# --- Wallbox Sensors ---

WALLBOX_SENSOR_DESCRIPTIONS: tuple[SenecSensorEntityDescription, ...] = (
    SenecSensorEntityDescription(
        key="charging_power",
        translation_key="wallbox_charging_power",
        name="Charging Power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        # value_fn and available_fn are not used for wallbox sensors directly;
        # the WallboxSensorEntity overrides native_value and available.
        value_fn=lambda data: None,
        available_fn=lambda data: True,
    ),
)

# All non-wallbox sensor descriptions combined
DEVICE_SENSOR_DESCRIPTIONS: tuple[SenecSensorEntityDescription, ...] = (
    *BATTERY_SENSOR_DESCRIPTIONS,
    *METER_SENSOR_DESCRIPTIONS,
    *BESS_SENSOR_DESCRIPTIONS,
)


class SenecSensorEntity(
    CoordinatorEntity[SenecDataUpdateCoordinator], SensorEntity
):
    """Sensor entity for SENEC device data."""

    entity_description: SenecSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        description: SenecSensorEntityDescription,
        serial_number: str,
    ) -> None:
        """Initialize the sensor entity.

        Args:
            coordinator: The data update coordinator.
            description: The entity description with value/available functions.
            serial_number: The device serial number for unique_id generation.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._serial_number = serial_number
        self._attr_unique_id = f"{serial_number}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the primary SENEC device."""
        device_data = self.coordinator.data.get(self._serial_number)
        manufacturer = "SENEC"
        model = None
        if device_data and device_data.bess_nameplate:
            manufacturer = device_data.bess_nameplate.manufacturer
            model = device_data.bess_nameplate.model
        return DeviceInfo(
            identifiers={(DOMAIN, self._serial_number)},
            manufacturer=manufacturer,
            model=model,
            config_entry_id=self.coordinator.config_entry.entry_id,
        )

    @property
    def available(self) -> bool:
        """Return True if the entity is available."""
        if not self.coordinator.last_update_success:
            return False
        device_data = self.coordinator.data.get(self._serial_number)
        if device_data is None:
            return False
        return self.entity_description.available_fn(device_data)

    @property
    def native_value(self) -> StateType:
        """Return the sensor value."""
        device_data = self.coordinator.data.get(self._serial_number)
        if device_data is None:
            return None
        return self.entity_description.value_fn(device_data)


class SenecWallboxSensorEntity(
    CoordinatorEntity[SenecDataUpdateCoordinator], SensorEntity
):
    """Sensor entity for SENEC wallbox data."""

    entity_description: SenecSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SenecDataUpdateCoordinator,
        description: SenecSensorEntityDescription,
        serial_number: str,
        wallbox_id: str,
    ) -> None:
        """Initialize the wallbox sensor entity.

        Args:
            coordinator: The data update coordinator.
            description: The entity description.
            serial_number: The parent device serial number.
            wallbox_id: The wallbox identifier (e.g. "WB-01").
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._serial_number = serial_number
        self._wallbox_id = wallbox_id
        self._attr_unique_id = (
            f"{serial_number}_{wallbox_id}_{description.key}"
        )
        self._attr_name = f"{wallbox_id} {description.name}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the wallbox device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._wallbox_id)},
            manufacturer="SENEC",
            model="Wallbox",
            name=f"Wallbox {self._wallbox_id}",
            via_device=(DOMAIN, self._serial_number),
            config_entry_id=self.coordinator.config_entry.entry_id,
        )

    @property
    def available(self) -> bool:
        """Return True if the wallbox sensor is available."""
        if not self.coordinator.last_update_success:
            return False
        device_data = self.coordinator.data.get(self._serial_number)
        if device_data is None:
            return False
        # Check if this wallbox is still present in the data
        return any(
            wb.id == self._wallbox_id for wb in device_data.wallboxes
        )

    @property
    def native_value(self) -> StateType:
        """Return the wallbox sensor value."""
        device_data = self.coordinator.data.get(self._serial_number)
        if device_data is None:
            return None
        for wb in device_data.wallboxes:
            if wb.id == self._wallbox_id:
                return wb.charging_power
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SENEC sensor entities from a config entry.

    Creates sensor entities for each selected device based on the
    coordinator data. Wallbox sensors are created dynamically based
    on the evse array in each device's data.
    """
    coordinator: SenecDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SenecSensorEntity | SenecWallboxSensorEntity] = []

    for serial_number, device_data in coordinator.data.items():
        # Create all standard device sensors (battery, meter, BESS)
        for description in DEVICE_SENSOR_DESCRIPTIONS:
            entities.append(
                SenecSensorEntity(
                    coordinator=coordinator,
                    description=description,
                    serial_number=serial_number,
                )
            )

        # Create wallbox sensors dynamically based on evse array
        for wallbox in device_data.wallboxes:
            for description in WALLBOX_SENSOR_DESCRIPTIONS:
                entities.append(
                    SenecWallboxSensorEntity(
                        coordinator=coordinator,
                        description=description,
                        serial_number=serial_number,
                        wallbox_id=wallbox.id,
                    )
                )

    async_add_entities(entities)
