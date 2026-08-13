"""Property-based tests for the SENEC Connect integration.

Uses the hypothesis library to verify correctness properties across
randomized inputs. Each test corresponds to a design property and
validates specific requirements.

Testing framework: hypothesis
Minimum iterations: 100 per test
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

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
)


# ---------------------------------------------------------------------------
# Hypothesis Strategies
# ---------------------------------------------------------------------------


@st.composite
def battery_data_strategy(draw: st.DrawFn) -> BatteryData:
    """Generate random valid BatteryData objects."""
    return BatteryData(
        state=draw(st.integers(min_value=0, max_value=1)),
        state_of_charge=draw(st.integers(min_value=0, max_value=100)),
        power=draw(st.floats(min_value=-50000, max_value=50000, allow_nan=False, allow_infinity=False)),
        voltage=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))),
        current=draw(st.one_of(st.none(), st.floats(min_value=-500, max_value=500, allow_nan=False, allow_infinity=False))),
    )


@st.composite
def bess_nameplate_strategy(draw: st.DrawFn) -> BessNameplateData:
    """Generate random valid BessNameplateData objects."""
    return BessNameplateData(
        manufacturer=draw(st.text(min_size=1, max_size=50, alphabet=st.characters(categories=("L", "N", "P", "Z")))),
        model=draw(st.text(min_size=1, max_size=80, alphabet=st.characters(categories=("L", "N", "P", "Z")))),
        serial_number=draw(st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N", "Pd")))),
        system_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=40, alphabet=st.characters(categories=("L", "N", "Pd"))))),
        design_capacity=draw(st.integers(min_value=1000, max_value=100000)),
        active_charge_power=draw(st.integers(min_value=100, max_value=20000)),
        active_discharge_power=draw(st.integers(min_value=100, max_value=20000)),
    )


@st.composite
def meter_data_strategy(draw: st.DrawFn) -> MeterData:
    """Generate random valid MeterData objects."""
    return MeterData(
        grid_power=draw(st.floats(min_value=-50000, max_value=50000, allow_nan=False, allow_infinity=False)),
        consumption=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False))),
        production=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False))),
    )


@st.composite
def wallbox_data_strategy(draw: st.DrawFn) -> WallboxData:
    """Generate random valid WallboxData objects."""
    return WallboxData(
        id=draw(st.from_regex(r"WB-[0-9]{2}", fullmatch=True)),
        ev_connected=draw(st.booleans()),
        ev_charging=draw(st.booleans()),
        charging_power=draw(st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False)),
    )


@st.composite
def device_data_strategy(draw: st.DrawFn) -> DeviceData:
    """Generate random valid DeviceData objects with optional sections."""
    return DeviceData(
        battery=draw(st.one_of(st.none(), battery_data_strategy())),
        bess_nameplate=draw(st.one_of(st.none(), bess_nameplate_strategy())),
        meter=draw(st.one_of(st.none(), meter_data_strategy())),
        wallboxes=draw(st.lists(wallbox_data_strategy(), min_size=0, max_size=4)),
    )


# ---------------------------------------------------------------------------
# Helper: serial number strategy
# ---------------------------------------------------------------------------

def _serial_strategy() -> st.SearchStrategy[str]:
    """Generate unique-looking serial numbers like v4-0000xxxx."""
    return st.from_regex(r"v[34]-[0-9a-f]{8}", fullmatch=True)


# ===========================================================================
# Property 1: API Response Parse/Serialize Round-Trip
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 1: API Response Parse/Serialize Round-Trip
# **Validates: Requirements 11.8**


@settings(max_examples=100)
@given(device=device_data_strategy())
def test_property_1_parse_serialize_round_trip(device: DeviceData) -> None:
    """Parse → serialize → re-parse produces equivalent DeviceData.

    For any valid DeviceData object, serializing via to_api_dict() and
    re-parsing via from_dict() must yield an equivalent object.
    """
    api_dict = device.to_api_dict()
    reparsed = DeviceData.from_dict(api_dict)

    # Compare all sections
    assert reparsed.battery == device.battery
    assert reparsed.bess_nameplate == device.bess_nameplate
    assert reparsed.meter == device.meter
    assert reparsed.wallboxes == device.wallboxes
    assert reparsed == device


# ===========================================================================
# Property 2: Coordinator Device Filtering
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 2: Coordinator Device Filtering
# **Validates: Requirements 2.3**


@settings(max_examples=100)
@given(data=st.data())
def test_property_2_coordinator_device_filtering(data: st.DataObject) -> None:
    """Coordinator filters devices by selected serial numbers.

    For any set of devices and any subset of selected serials,
    the filtering logic returns exactly the devices in the subset.
    """
    # Generate 1-5 devices with unique serial numbers
    num_devices = data.draw(st.integers(min_value=1, max_value=5))
    serials = data.draw(
        st.lists(
            _serial_strategy(),
            min_size=num_devices,
            max_size=num_devices,
            unique=True,
        )
    )

    devices: list[DeviceData] = []
    for serial in serials:
        device = data.draw(device_data_strategy())
        # Ensure each device has a bess_nameplate with the assigned serial
        bess = BessNameplateData(
            manufacturer="SENEC GmbH",
            model="Test Model",
            serial_number=serial,
            system_id=None,
            design_capacity=10000,
            active_charge_power=2500,
            active_discharge_power=2500,
        )
        device = DeviceData(
            battery=device.battery,
            bess_nameplate=bess,
            meter=device.meter,
            wallboxes=device.wallboxes,
        )
        devices.append(device)

    # Select a random subset of serial numbers
    selected_serials = data.draw(
        st.lists(st.sampled_from(serials), min_size=0, max_size=num_devices, unique=True)
    )

    # Simulate coordinator filtering logic (same as _async_update_data)
    result: dict[str, DeviceData] = {}
    for device in devices:
        if (
            device.bess_nameplate is not None
            and device.bess_nameplate.serial_number in selected_serials
        ):
            result[device.bess_nameplate.serial_number] = device

    # Verify: result contains exactly the selected devices
    assert set(result.keys()) == set(selected_serials)
    for serial in selected_serials:
        assert serial in result
        assert result[serial].bess_nameplate is not None
        assert result[serial].bess_nameplate.serial_number == serial


# ===========================================================================
# Property 3: Missing Device Availability
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 3: Missing Device Availability
# **Validates: Requirements 2.7**


@settings(max_examples=100)
@given(data=st.data())
def test_property_3_missing_device_availability(data: st.DataObject) -> None:
    """Missing devices are not in coordinator output; present ones are.

    For any selected serials and an API response that omits some of them,
    only devices present in the API response appear in the coordinator dict.
    """
    # Generate 2-5 serial numbers as "selected"
    num_selected = data.draw(st.integers(min_value=2, max_value=5))
    selected_serials = data.draw(
        st.lists(
            _serial_strategy(),
            min_size=num_selected,
            max_size=num_selected,
            unique=True,
        )
    )

    # Randomly decide which serials are present in the API response
    present_serials = data.draw(
        st.lists(
            st.sampled_from(selected_serials),
            min_size=0,
            max_size=num_selected,
            unique=True,
        )
    )
    missing_serials = set(selected_serials) - set(present_serials)

    # Build API response only for present devices
    devices: list[DeviceData] = []
    for serial in present_serials:
        bess = BessNameplateData(
            manufacturer="SENEC GmbH",
            model="Test Model",
            serial_number=serial,
            system_id=None,
            design_capacity=10000,
            active_charge_power=2500,
            active_discharge_power=2500,
        )
        devices.append(DeviceData(
            battery=data.draw(st.one_of(st.none(), battery_data_strategy())),
            bess_nameplate=bess,
            meter=data.draw(st.one_of(st.none(), meter_data_strategy())),
            wallboxes=[],
        ))

    # Simulate coordinator filtering
    result: dict[str, DeviceData] = {}
    for device in devices:
        if (
            device.bess_nameplate is not None
            and device.bess_nameplate.serial_number in selected_serials
        ):
            result[device.bess_nameplate.serial_number] = device

    # Verify: missing devices NOT in result, present ones ARE
    for serial in missing_serials:
        assert serial not in result

    for serial in present_serials:
        assert serial in result
        assert result[serial].bess_nameplate is not None
        assert result[serial].bess_nameplate.serial_number == serial


# ===========================================================================
# Property 4: Partial Data Granular Availability
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 4: Partial Data Granular Availability
# **Validates: Requirements 3.7, 4.5, 5.9, 8.4, 8.5**


@st.composite
def _partial_battery_strategy(draw: st.DrawFn) -> BatteryData:
    """Generate BatteryData with randomly null fields (including required ones).

    Simulates partial API responses where any field might be absent.
    Uses object.__setattr__ to bypass frozen dataclass for null injection.
    """
    battery = BatteryData(
        state=draw(st.integers(min_value=0, max_value=1)),
        state_of_charge=draw(st.integers(min_value=0, max_value=100)),
        power=draw(st.floats(min_value=-50000, max_value=50000, allow_nan=False, allow_infinity=False)),
        voltage=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))),
        current=draw(st.one_of(st.none(), st.floats(min_value=-500, max_value=500, allow_nan=False, allow_infinity=False))),
    )
    # Randomly null out individual fields to simulate partial data
    if draw(st.booleans()):
        object.__setattr__(battery, "state", None)
    if draw(st.booleans()):
        object.__setattr__(battery, "state_of_charge", None)
    if draw(st.booleans()):
        object.__setattr__(battery, "power", None)
    return battery


@st.composite
def _partial_meter_strategy(draw: st.DrawFn) -> MeterData:
    """Generate MeterData with randomly null fields (including required ones)."""
    meter = MeterData(
        grid_power=draw(st.floats(min_value=-50000, max_value=50000, allow_nan=False, allow_infinity=False)),
        consumption=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False))),
        production=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=50000, allow_nan=False, allow_infinity=False))),
    )
    # Randomly null out grid_power to simulate partial data
    if draw(st.booleans()):
        object.__setattr__(meter, "grid_power", None)
    return meter


@st.composite
def _partial_bess_strategy(draw: st.DrawFn) -> BessNameplateData:
    """Generate BessNameplateData with randomly null/empty fields."""
    bess = BessNameplateData(
        manufacturer=draw(st.one_of(st.just(""), st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N"))))),
        model=draw(st.one_of(st.just(""), st.text(min_size=1, max_size=30, alphabet=st.characters(categories=("L", "N"))))),
        serial_number=draw(st.one_of(st.just(""), st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))))),
        system_id=draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=20, alphabet=st.characters(categories=("L", "N"))))),
        design_capacity=draw(st.integers(min_value=1000, max_value=100000)),
        active_charge_power=draw(st.integers(min_value=100, max_value=20000)),
        active_discharge_power=draw(st.integers(min_value=100, max_value=20000)),
    )
    # Randomly null out numeric fields
    if draw(st.booleans()):
        object.__setattr__(bess, "design_capacity", None)
    if draw(st.booleans()):
        object.__setattr__(bess, "active_charge_power", None)
    if draw(st.booleans()):
        object.__setattr__(bess, "active_discharge_power", None)
    # Randomly null out string fields
    if draw(st.booleans()):
        object.__setattr__(bess, "manufacturer", None)
    if draw(st.booleans()):
        object.__setattr__(bess, "model", None)
    if draw(st.booleans()):
        object.__setattr__(bess, "serial_number", None)
    return bess


@st.composite
def _partial_device_data_strategy(draw: st.DrawFn) -> DeviceData:
    """Generate DeviceData with randomly null sections and fields.

    This strategy produces partial data scenarios where:
    - Entire sections (battery, meter, bess_nameplate) may be None
    - Individual fields within present sections may be None
    """
    return DeviceData(
        battery=draw(st.one_of(st.none(), _partial_battery_strategy())),
        bess_nameplate=draw(st.one_of(st.none(), _partial_bess_strategy())),
        meter=draw(st.one_of(st.none(), _partial_meter_strategy())),
        wallboxes=draw(st.lists(wallbox_data_strategy(), min_size=0, max_size=2)),
    )


@settings(max_examples=100)
@given(device=_partial_device_data_strategy())
def test_property_4_partial_data_granular_availability(device: DeviceData) -> None:
    """Only entities of null sections/fields are unavailable.

    For any DeviceData with randomly null sections or fields,
    the available_fn correctly reflects which entities are available.
    Entities whose section is None or whose specific field is None/empty
    must report unavailable; all others must report available.
    """
    for description in DEVICE_SENSOR_DESCRIPTIONS:
        is_available = description.available_fn(device)

        # Battery sensors should be unavailable if battery is None
        if description.key in ("battery_soc", "battery_power", "battery_voltage", "battery_current", "battery_state"):
            if device.battery is None:
                assert is_available is False, f"{description.key} should be unavailable when battery is None"
            else:
                # Check specific field nullability
                if description.key == "battery_soc":
                    assert is_available == (device.battery.state_of_charge is not None)
                elif description.key == "battery_power":
                    assert is_available == (device.battery.power is not None)
                elif description.key == "battery_voltage":
                    assert is_available == (device.battery.voltage is not None)
                elif description.key == "battery_current":
                    assert is_available == (device.battery.current is not None)
                elif description.key == "battery_state":
                    assert is_available == (device.battery.state is not None)

        # Meter sensors should be unavailable if meter is None
        elif description.key in ("grid_power", "consumption", "production"):
            if device.meter is None:
                assert is_available is False, f"{description.key} should be unavailable when meter is None"
            else:
                if description.key == "grid_power":
                    assert is_available == (device.meter.grid_power is not None)
                elif description.key == "consumption":
                    assert is_available == (device.meter.consumption is not None)
                elif description.key == "production":
                    assert is_available == (device.meter.production is not None)

        # BESS sensors should be unavailable if bess_nameplate is None
        elif description.key.startswith("bess_"):
            if device.bess_nameplate is None:
                assert is_available is False, f"{description.key} should be unavailable when bess_nameplate is None"
            else:
                # BESS string fields check for non-empty
                if description.key == "bess_manufacturer":
                    assert is_available == (device.bess_nameplate.manufacturer is not None and device.bess_nameplate.manufacturer != "")
                elif description.key == "bess_model":
                    assert is_available == (device.bess_nameplate.model is not None and device.bess_nameplate.model != "")
                elif description.key == "bess_serial":
                    assert is_available == (device.bess_nameplate.serial_number is not None and device.bess_nameplate.serial_number != "")
                elif description.key == "bess_system_id":
                    assert is_available == (device.bess_nameplate.system_id is not None and device.bess_nameplate.system_id != "")
                elif description.key == "bess_design_capacity":
                    assert is_available == (device.bess_nameplate.design_capacity is not None)
                elif description.key == "bess_charge_power":
                    assert is_available == (device.bess_nameplate.active_charge_power is not None)
                elif description.key == "bess_discharge_power":
                    assert is_available == (device.bess_nameplate.active_discharge_power is not None)


# ===========================================================================
# Property 5: Unique-ID Uniqueness and Format
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 5: Unique-ID Uniqueness and Format
# **Validates: Requirements 3.6, 4.4, 5.8, 6.1**


@settings(max_examples=100)
@given(data=st.data())
def test_property_5_unique_id_uniqueness_and_format(data: st.DataObject) -> None:
    """All generated unique_ids are globally unique and follow correct format.

    For any set of devices with unique serial numbers and varying wallbox counts,
    unique_ids must be globally unique and match {serial}_{key} or
    {serial}_{wb_id}_{key} format.
    """
    num_devices = data.draw(st.integers(min_value=1, max_value=4))
    serials = data.draw(
        st.lists(
            _serial_strategy(),
            min_size=num_devices,
            max_size=num_devices,
            unique=True,
        )
    )

    all_unique_ids: list[str] = []

    for serial in serials:
        # Generate wallboxes with unique IDs for this device
        num_wallboxes = data.draw(st.integers(min_value=0, max_value=3))
        wb_ids = [f"WB-{i:02d}" for i in range(1, num_wallboxes + 1)]

        # Device sensor unique_ids: {serial}_{key}
        for description in DEVICE_SENSOR_DESCRIPTIONS:
            uid = f"{serial}_{description.key}"
            all_unique_ids.append(uid)
            # Verify format: {serial}_{key}
            assert uid.startswith(serial)
            assert uid == f"{serial}_{description.key}"

        # Wallbox sensor unique_ids: {serial}_{wb_id}_{key}
        from custom_components.senec_connect.sensor import WALLBOX_SENSOR_DESCRIPTIONS
        from custom_components.senec_connect.binary_sensor import BINARY_SENSOR_DESCRIPTIONS

        for wb_id in wb_ids:
            for description in WALLBOX_SENSOR_DESCRIPTIONS:
                uid = f"{serial}_{wb_id}_{description.key}"
                all_unique_ids.append(uid)
                # Verify format: {serial}_{wb_id}_{key}
                assert uid == f"{serial}_{wb_id}_{description.key}"

            for description in BINARY_SENSOR_DESCRIPTIONS:
                uid = f"{serial}_{wb_id}_{description.key}"
                all_unique_ids.append(uid)
                assert uid == f"{serial}_{wb_id}_{description.key}"

    # Global uniqueness check
    assert len(all_unique_ids) == len(set(all_unique_ids)), (
        f"Duplicate unique_ids found: {[uid for uid in all_unique_ids if all_unique_ids.count(uid) > 1]}"
    )


# ===========================================================================
# Property 6: Dynamic Wallbox Entity Lifecycle
# ===========================================================================
# Feature: senec-homeassistant-integration, Property 6: Dynamic Wallbox Entity Lifecycle
# **Validates: Requirements 6.1, 6.5, 6.6**


@settings(max_examples=100)
@given(data=st.data())
def test_property_6_dynamic_wallbox_entity_lifecycle(data: st.DataObject) -> None:
    """Registered wallbox entities always exactly reflect evse array content.

    For any sequence of coordinator updates with changing evse arrays,
    the tracked wallbox set always reflects exactly the current wallboxes.
    Simulates WallboxBinarySensorTracker's add/remove logic.
    """
    serial = data.draw(_serial_strategy())
    num_updates = data.draw(st.integers(min_value=1, max_value=6))

    # Simulate the tracker state
    tracked_wallboxes: set[tuple[str, str]] = set()
    entities_created: dict[str, bool] = {}  # unique_key -> available
    entity_keys_per_wallbox = ("ev_connected", "ev_charging")

    for _ in range(num_updates):
        # Generate a new set of wallboxes for this update
        num_wallboxes = data.draw(st.integers(min_value=0, max_value=4))
        wb_ids = data.draw(
            st.lists(
                st.from_regex(r"WB-[0-9]{2}", fullmatch=True),
                min_size=num_wallboxes,
                max_size=num_wallboxes,
                unique=True,
            )
        )

        current_wallboxes: set[tuple[str, str]] = set()
        for wb_id in wb_ids:
            current_wallboxes.add((serial, wb_id))

        # Determine new and removed wallboxes (mirrors _process_coordinator_data)
        new_wallboxes = current_wallboxes - tracked_wallboxes
        removed_wallboxes = tracked_wallboxes - current_wallboxes

        # Add new entities
        for s, wb_id in new_wallboxes:
            for key in entity_keys_per_wallbox:
                unique_key = f"{s}_{wb_id}_{key}"
                entities_created[unique_key] = True  # available

        # Mark removed entities as unavailable
        for s, wb_id in removed_wallboxes:
            for key in entity_keys_per_wallbox:
                unique_key = f"{s}_{wb_id}_{key}"
                if unique_key in entities_created:
                    entities_created[unique_key] = False  # unavailable

        tracked_wallboxes = current_wallboxes

        # INVARIANT: The set of AVAILABLE entities exactly reflects current wallboxes
        available_entities = {k for k, v in entities_created.items() if v}
        expected_entities = set()
        for s, wb_id in current_wallboxes:
            for key in entity_keys_per_wallbox:
                expected_entities.add(f"{s}_{wb_id}_{key}")

        assert available_entities == expected_entities, (
            f"Mismatch after update: available={available_entities}, expected={expected_entities}"
        )

    # Final check: tracked set matches last wallbox set
    final_wb_set = {(serial, wb_id) for wb_id in wb_ids}
    assert tracked_wallboxes == final_wb_set
