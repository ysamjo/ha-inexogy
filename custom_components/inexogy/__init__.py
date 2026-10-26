"""Einrichtung der inexogy-Integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import InexogyCoordinator

# Bewusst keine ``type``-Anweisung: die gibt es erst ab Python 3.12, ruff prüft
# hier aber gegen 3.11. Die Zuweisung tut dasselbe und läuft überall.
InexogyConfigEntry = ConfigEntry[InexogyCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: InexogyConfigEntry) -> bool:
    """Coordinator starten und Sensoren anlegen."""
    coordinator = InexogyCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: InexogyConfigEntry) -> bool:
    """Sensoren abmelden."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
