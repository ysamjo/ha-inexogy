"""Abfrage des inexogy-/Discovergy-Zählers für Home Assistant.

Die Umrechnung der Rohwerte (Milliwatt, 10⁻⁷ Wh) steht bewusst hier und nicht
als Import aus einem anderen Projekt: eine HA-Integration muss für sich
lauffähig sein.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pydiscovergy import Discovergy
from pydiscovergy.const import Resolution
from pydiscovergy.error import DiscovergyClientError, DiscovergyError, InvalidLogin

from .const import CONF_EMAIL, CONF_PASSWORD, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Die API liefert Leistung in Milliwatt und Zählerstände in 10⁻⁷ Wh.
_POWER_DIVISOR = 1000.0
_ENERGY_DIVISOR = 10_000_000_000.0
_ENERGY_RAW_THRESHOLD = 100_000_000


def normalize(values: dict) -> tuple[float, float]:
    """Rohwerte in ``(Bezug, Einspeisung)`` in Watt, beide nie negativ.

    Je nach Zählertyp kommt die Einspeisung als eigenes Feld ``powerOut`` oder
    als negatives ``power``.
    """
    power = float(values.get("power", 0.0) or 0.0) / _POWER_DIVISOR
    power_out = float(values.get("powerOut", 0.0) or 0.0) / _POWER_DIVISOR
    if power < 0:
        power_out = max(power_out, -power)
        power = 0.0
    return round(power, 1), round(power_out, 1)


def scale_energy(raw: float | int | None) -> float | None:
    """Zählerstand in kWh."""
    if raw is None:
        return None
    value = float(raw)
    if abs(value) > _ENERGY_RAW_THRESHOLD:
        return round(value / _ENERGY_DIVISOR, 2)
    return round(value, 2)


@dataclass
class InexogyReading:
    """Ein Messpunkt des Zählers."""

    power: float
    power_out: float
    energy_in: float | None
    energy_out: float | None
    timestamp: float


@dataclass
class InexogyMeter:
    """Stammdaten des Zählers (für das Geräte-Register)."""

    meter_id: str
    serial_number: str
    meter_type: str
    location: str


class InexogyCoordinator(DataUpdateCoordinator[InexogyReading]):
    """Pollt den Zähler und hält Stammdaten und HTTP-Client."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        # Kein eigener httpx-Client: pydiscovergy benutzt den übergebenen mit
        # ``async with`` und schließt ihn danach – ein zweiter Aufruf würde mit
        # „Cannot open a client instance more than once" scheitern. Ohne Angabe
        # legt die Bibliothek pro Anfrage einen frischen an.
        self.client = Discovergy(
            email=entry.data[CONF_EMAIL],
            password=entry.data[CONF_PASSWORD],
        )
        self.meter: InexogyMeter | None = None
        self._fields: list[str] = []

    async def _async_resolve_meter(self) -> InexogyMeter:
        if self.meter is not None:
            return self.meter

        meters = await self.client.meters()
        if not meters:
            raise UpdateFailed("Keine Zähler im inexogy-Konto gefunden")

        meter = meters[0]
        location = getattr(meter, "location", None)
        self.meter = InexogyMeter(
            meter_id=meter.meter_id,
            serial_number=meter.serial_number,
            meter_type=getattr(meter, "meter_type", "") or "",
            location=(
                f"{location.street} {location.street_number}, {location.zip} {location.city}"
                if location
                else ""
            ),
        )
        _LOGGER.debug("Zähler gefunden: %s", self.meter.serial_number)
        return self.meter

    async def _async_update_data(self) -> InexogyReading:
        try:
            meter = await self._async_resolve_meter()

            if not self._fields:
                try:
                    self._fields = await self.client.meter_field_names(meter_id=meter.meter_id)
                except DiscovergyError as err:  # Feldnamen sind nur Beiwerk
                    _LOGGER.debug("Feldnamen nicht lesbar: %s", err)

            reading = await self.client.meter_last_reading(meter_id=meter.meter_id)
            values = dict(reading.values or {})
            power, power_out = normalize(values)

            # Intervallzähler liefern in ``last_reading`` oft nur Nullen.
            # Dann den letzten berechneten Wert nehmen, statt künstlich
            # 0-W-Punkte in die Statistik zu schreiben.
            if power == 0.0 and power_out == 0.0:
                candidate = await self._async_recent_reading(meter)
                if candidate is not None:
                    reading, values = candidate
                    power, power_out = normalize(values)

            return InexogyReading(
                power=power,
                power_out=power_out,
                energy_in=scale_energy(values.get("energy")),
                energy_out=scale_energy(values.get("energyOut")),
                timestamp=reading.time.timestamp() if reading.time else time.time(),
            )

        except InvalidLogin as err:
            raise ConfigEntryAuthFailed(
                "inexogy lehnt die Zugangsdaten ab – E-Mail und Passwort prüfen"
            ) from err
        except (DiscovergyClientError, DiscovergyError) as err:
            raise UpdateFailed(f"inexogy nicht erreichbar: {err}") from err

    async def _async_recent_reading(self, meter: InexogyMeter):
        """Letzter brauchbarer 3-Minuten-Wert, ``None`` wenn keiner da ist."""
        try:
            recent = await self.client.meter_readings(
                meter_id=meter.meter_id,
                start_time=datetime.now(UTC) - timedelta(hours=2),
                resolution=Resolution.THREE_MINUTES,
                field_names=["power", "powerOut", "energy", "energyOut"],
            )
        except (DiscovergyClientError, DiscovergyError) as err:
            _LOGGER.debug("Rückfall auf meter_readings fehlgeschlagen: %s", err)
            return None

        if not recent:
            return None

        candidate = recent[-1]
        values = dict(candidate.values or {})
        power, power_out = normalize(values)
        if power == 0.0 and power_out == 0.0:
            return None
        return candidate, values
