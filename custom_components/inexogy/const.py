"""Konstanten der inexogy-Integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "inexogy"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Der Zähler liefert alle 30 s einen neuen Wert; häufiger zu fragen bringt
# nichts und belastet nur die Cloud-API.
DEFAULT_SCAN_INTERVAL = 30

PLATFORMS: list[Platform] = [Platform.SENSOR]
