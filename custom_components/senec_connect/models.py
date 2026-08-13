"""Data models for the SENEC Connect integration.

Frozen dataclasses representing the SENEC.Connect API response structure
(GeneralDeviceData schema). Each model provides from_dict() for JSON parsing
and to_dict() for serialization/round-trip verification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class BatteryData:
    """Battery data from the SENEC system.

    Attributes:
        state: Battery status (0 = OK, 1 = error).
        state_of_charge: Current state of charge in percentage (0-100).
        power: Current charging/discharging power in watt (+ charging, - discharging).
        voltage: Current battery voltage in volt (nullable).
        current: Current battery current in ampere (+ charging, - discharging, nullable).
    """

    state: int
    state_of_charge: int
    power: float
    voltage: Optional[float] = None
    current: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BatteryData:
        """Create BatteryData from an API response dictionary."""
        return cls(
            state=data["state"],
            state_of_charge=data["state_of_charge"],
            power=float(data["power"]),
            voltage=float(data["voltage"]) if data.get("voltage") is not None else None,
            current=float(data["current"]) if data.get("current") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "state": self.state,
            "state_of_charge": self.state_of_charge,
            "power": self.power,
            "voltage": self.voltage,
            "current": self.current,
        }


@dataclass(frozen=True)
class BessNameplateData:
    """Battery Energy Storage System (BESS) nameplate data.

    Attributes:
        manufacturer: Device manufacturer (e.g. "SENEC GmbH").
        model: Device model name (e.g. "SENEC.Home E4 - 1ph 6 AC").
        serial_number: Device serial number (e.g. "v4-00012ff4").
        system_id: System identifier (not in API schema, from requirements; nullable).
        design_capacity: Installed net capacity in watt hours (Wh).
        active_charge_power: Max charge power in watt (W).
        active_discharge_power: Max discharge power in watt (W).
    """

    manufacturer: str
    model: str
    serial_number: str
    design_capacity: int
    active_charge_power: int
    active_discharge_power: int
    system_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BessNameplateData:
        """Create BessNameplateData from an API response dictionary."""
        return cls(
            manufacturer=data["manufacturer"],
            model=data["model"],
            serial_number=data["serial_number"],
            system_id=data.get("system_id"),
            design_capacity=data["design_capacity"],
            active_charge_power=data["active_charge_power"],
            active_discharge_power=data["active_discharge_power"],
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "system_id": self.system_id,
            "design_capacity": self.design_capacity,
            "active_charge_power": self.active_charge_power,
            "active_discharge_power": self.active_discharge_power,
        }


@dataclass(frozen=True)
class MeterData:
    """Meter data from the SENEC system.

    Attributes:
        grid_power: Grid power in watt (+ from grid, - to grid).
        consumption: Total house consumption without wallbox in watt (nullable).
        production: PV production in watt (nullable).
    """

    grid_power: float
    consumption: Optional[float] = None
    production: Optional[float] = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeterData:
        """Create MeterData from an API response dictionary."""
        return cls(
            grid_power=float(data["grid_power"]),
            consumption=(
                float(data["consumption"])
                if data.get("consumption") is not None
                else None
            ),
            production=(
                float(data["production"])
                if data.get("production") is not None
                else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "grid_power": self.grid_power,
            "consumption": self.consumption,
            "production": self.production,
        }


@dataclass(frozen=True)
class WallboxData:
    """Wallbox (EVSE) data from the SENEC system.

    Attributes:
        id: Wallbox identifier (e.g. "WB-01").
        ev_connected: True if a vehicle is connected.
        ev_charging: True if a vehicle is currently charging.
        charging_power: Current charging power in volt-amperes (VA).
    """

    id: str
    ev_connected: bool
    ev_charging: bool
    charging_power: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WallboxData:
        """Create WallboxData from an API response dictionary."""
        return cls(
            id=data["id"],
            ev_connected=data["ev_connected"],
            ev_charging=data["ev_charging"],
            charging_power=float(data["charging_power"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary."""
        return {
            "id": self.id,
            "ev_connected": self.ev_connected,
            "ev_charging": self.ev_charging,
            "charging_power": self.charging_power,
        }


@dataclass(frozen=True)
class DeviceData:
    """Complete device data aggregating all sections.

    Maps the GeneralDeviceData schema from the SENEC.Connect API.
    The API uses "bessNameplate" and "evse" as JSON keys which are mapped
    to bess_nameplate and wallboxes respectively.

    Attributes:
        battery: Battery data section (nullable if not included/available).
        bess_nameplate: BESS nameplate data section (nullable).
        meter: Meter data section (nullable).
        wallboxes: List of wallbox data (empty if no EVSE present).
    """

    battery: Optional[BatteryData] = None
    bess_nameplate: Optional[BessNameplateData] = None
    meter: Optional[MeterData] = None
    wallboxes: list[WallboxData] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeviceData:
        """Create DeviceData from an API response dictionary.

        Handles JSON key mapping:
        - "bessNameplate" -> bess_nameplate
        - "evse" -> wallboxes
        """
        battery_raw = data.get("battery")
        bess_raw = data.get("bessNameplate")
        meter_raw = data.get("meter")
        evse_raw = data.get("evse")

        return cls(
            battery=BatteryData.from_dict(battery_raw) if battery_raw else None,
            bess_nameplate=(
                BessNameplateData.from_dict(bess_raw) if bess_raw else None
            ),
            meter=MeterData.from_dict(meter_raw) if meter_raw else None,
            wallboxes=(
                [WallboxData.from_dict(wb) for wb in evse_raw]
                if evse_raw
                else []
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dictionary.

        Uses Python-friendly keys (bess_nameplate, wallboxes) for round-trip
        testing with from_dict() which expects API keys (bessNameplate, evse).
        For round-trip compatibility, use to_api_dict() instead.
        """
        return {
            "battery": self.battery.to_dict() if self.battery else None,
            "bess_nameplate": (
                self.bess_nameplate.to_dict() if self.bess_nameplate else None
            ),
            "meter": self.meter.to_dict() if self.meter else None,
            "wallboxes": [wb.to_dict() for wb in self.wallboxes],
        }

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize to an API-compatible dictionary.

        Uses the original API JSON keys (bessNameplate, evse) for
        round-trip verification with from_dict().
        """
        result: dict[str, Any] = {}
        if self.battery is not None:
            result["battery"] = self.battery.to_dict()
        if self.bess_nameplate is not None:
            result["bessNameplate"] = self.bess_nameplate.to_dict()
        if self.meter is not None:
            result["meter"] = self.meter.to_dict()
        if self.wallboxes:
            result["evse"] = [wb.to_dict() for wb in self.wallboxes]
        return result
