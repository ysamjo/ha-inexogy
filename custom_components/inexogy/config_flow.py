"""Konfiguration über die Oberfläche: E-Mail und Passwort des inexogy-Kontos."""

from __future__ import annotations

import logging
from typing import Any

import httpx
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from pydiscovergy import Discovergy
from pydiscovergy.error import DiscovergyError, InvalidLogin

from .const import CONF_EMAIL, CONF_PASSWORD, DOMAIN

_LOGGER = logging.getLogger(__name__)

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
)


class InexogyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Zugangsdaten abfragen und gegen die API prüfen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_EMAIL] = user_input[CONF_EMAIL].strip()
            try:
                meter = await self._async_first_meter(user_input)
            except InvalidLogin:
                errors["base"] = "invalid_auth"
            except (DiscovergyError, httpx.HTTPError):
                errors["base"] = "cannot_connect"
            except NoMeters:
                errors["base"] = "no_meters"
            else:
                await self.async_set_unique_id(meter.serial_number)
                self._abort_if_unique_id_configured()
                location = getattr(meter, "location", None)
                title = (
                    f"inexogy {location.city}"
                    if location is not None and getattr(location, "city", "")
                    else f"inexogy {meter.serial_number}"
                )
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def _async_first_meter(self, data: dict[str, Any]):
        """Login prüfen und den ersten Zähler zurückgeben."""
        client = Discovergy(
            email=data[CONF_EMAIL],
            password=data[CONF_PASSWORD],
        )
        meters = await client.meters()
        if not meters:
            raise NoMeters
        return meters[0]


class NoMeters(Exception):
    """Das Konto enthält keinen Zähler."""
