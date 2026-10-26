"""Sensoren des inexogy-Zählers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import InexogyConfigEntry
from .const import DOMAIN
from .coordinator import InexogyCoordinator, InexogyReading


@dataclass(frozen=True, kw_only=True)
class InexogySensorDescription(SensorEntityDescription):
    """Sensor mit Zugriffsfunktion auf den Messpunkt."""

    value_fn: Callable[[InexogyReading], float | None]


SENSORS: tuple[InexogySensorDescription, ...] = (
    InexogySensorDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda reading: reading.power,
    ),
    InexogySensorDescription(
        key="power_out",
        translation_key="power_out",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda reading: reading.power_out,
    ),
    InexogySensorDescription(
        key="energy_in",
        translation_key="energy_in",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda reading: reading.energy_in,
    ),
    InexogySensorDescription(
        key="energy_out",
        translation_key="energy_out",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda reading: reading.energy_out,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InexogyConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Alle Sensoren des Zählers anlegen."""
    coordinator = entry.runtime_data
    async_add_entities(InexogySensor(coordinator, entry, description) for description in SENSORS)


class InexogySensor(CoordinatorEntity[InexogyCoordinator], SensorEntity):
    """Ein Messwert des Zählers."""

    _attr_has_entity_name = True
    entity_description: InexogySensorDescription

    def __init__(
        self,
        coordinator: InexogyCoordinator,
        entry: InexogyConfigEntry,
        description: InexogySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        meter = self.coordinator.meter
        return DeviceInfo(
            identifiers={(DOMAIN, meter.serial_number if meter else "unknown")},
            manufacturer="inexogy",
            model=(meter.meter_type or None) if meter else None,
            serial_number=meter.serial_number if meter else None,
            # Der Name landet im Entity-ID-Präfix und lässt sich später nicht
            # mehr ändern (die IDs sind dann vergeben): "sensor.inexogy_zahler_bezug".
            name="inexogy Zähler",
            configuration_url="https://my.inexogy.com",
        )

    @property
    def native_value(self) -> float | None:
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
