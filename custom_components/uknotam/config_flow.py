"""Config flow for UK NOTAMs integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AERODROMES,
    CONF_COORD_AREAS,
    CONF_COORDINATES,
    CONF_RANGE_NM,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    NATS_PIB_URL,
)

_LOGGER = logging.getLogger(__name__)


class UKNOTAMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for UK NOTAMs."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the config flow."""
        self._data: dict[str, Any] = {}
        self._coordinate_areas: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._data = user_input.copy()

            has_aerodromes = user_input.get(CONF_AERODROMES, "").strip()
            has_coordinates = user_input.get("add_coordinates", False)

            if not has_aerodromes and not has_coordinates:
                errors["base"] = "no_filters"
            elif has_aerodromes:
                codes = [c.strip().upper() for c in has_aerodromes.split(",") if c.strip()]
                if not all(len(c) == 4 and c.isalpha() for c in codes):
                    errors[CONF_AERODROMES] = "invalid_icao"
                else:
                    self._data[CONF_AERODROMES] = codes

            if not errors:
                try:
                    await self._test_connection()
                except aiohttp.ClientError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during connection test")
                    errors["base"] = "unknown"

            if not errors:
                if user_input.get("add_coordinates", False):
                    return await self.async_step_coordinates()
                return self._create_entry()

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AERODROMES, default=""): str,
                vol.Optional("add_coordinates", default=False): bool,
                vol.Optional(CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_coordinates(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle coordinate configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                latitude = user_input[CONF_LATITUDE]
                longitude = user_input[CONF_LONGITUDE]
                range_nm = user_input[CONF_RANGE_NM]

                if range_nm <= 0:
                    errors[CONF_RANGE_NM] = "invalid_range"

                if not errors:
                    self._coordinate_areas.append(
                        {
                            CONF_LATITUDE: latitude,
                            CONF_LONGITUDE: longitude,
                            CONF_RANGE_NM: range_nm,
                        }
                    )

                    if user_input.get("add_another", False):
                        return await self.async_step_coordinates()

                    self._data[CONF_COORD_AREAS] = self._coordinate_areas
                    return self._create_entry()

            except (ValueError, KeyError):
                errors["base"] = "invalid_coordinates"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE): cv.latitude,
                vol.Required(CONF_LONGITUDE): cv.longitude,
                vol.Required(CONF_RANGE_NM, default=50): cv.positive_float,
                vol.Optional("add_another", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="coordinates",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> config_entries.FlowResult:
        """Handle import from configuration.yaml."""
        await self.async_set_unique_id("uknotam_integration")
        self._abort_if_unique_id_configured()

        data: dict[str, Any] = {
            CONF_REFRESH_INTERVAL: import_data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
        }

        if CONF_AERODROMES in import_data:
            data[CONF_AERODROMES] = import_data[CONF_AERODROMES]

        if CONF_COORDINATES in import_data:
            coords = import_data[CONF_COORDINATES]
            data[CONF_COORD_AREAS] = [coords] if isinstance(coords, dict) else coords

        return self.async_create_entry(title="UK NOTAMs (imported from YAML)", data=data)

    def _create_entry(self) -> config_entries.FlowResult:
        """Create the config entry."""
        title_parts: list[str] = []

        if CONF_AERODROMES in self._data:
            aerodromes = self._data[CONF_AERODROMES]
            if len(aerodromes) <= 2:
                title_parts.append(", ".join(aerodromes))
            else:
                title_parts.append(f"{len(aerodromes)} aerodromes")

        if self._coordinate_areas:
            title_parts.append(f"{len(self._coordinate_areas)} area(s)")

        title = "UK NOTAMs: " + " + ".join(title_parts) if title_parts else "UK NOTAMs"

        return self.async_create_entry(title=title, data=self._data)

    async def _test_connection(self) -> None:
        """Test connection to the NATS PIB feed."""
        session = async_get_clientsession(self.hass)
        async with session.get(NATS_PIB_URL, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            await response.text()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> "UKNOTAMOptionsFlow":
        """Get the options flow for this handler."""
        return UKNOTAMOptionsFlow()


class UKNOTAMOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for UK NOTAMs integration."""

    def __init__(self) -> None:
        """Initialise."""
        self._coordinate_areas: list[dict[str, Any]] = []
        self._pending_data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            data: dict[str, Any] = {
                CONF_REFRESH_INTERVAL: user_input.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
            }

            aerodromes_input = user_input.get(CONF_AERODROMES, "").strip()
            if aerodromes_input:
                codes = [c.strip().upper() for c in aerodromes_input.split(",") if c.strip()]
                if not all(len(c) == 4 and c.isalpha() for c in codes):
                    errors[CONF_AERODROMES] = "invalid_icao"
                else:
                    data[CONF_AERODROMES] = codes
            else:
                data[CONF_AERODROMES] = []

            if not errors:
                if user_input.get("modify_coordinates", False):
                    self._coordinate_areas = []
                    self._pending_data = data
                    return await self.async_step_coordinates()

                # Preserve existing coordinates
                for key in (CONF_COORD_AREAS, "coordinate_areas", "coordinates"):
                    if key in self.config_entry.data:
                        data[CONF_COORD_AREAS] = self.config_entry.data[key]
                        break
                else:
                    data[CONF_COORD_AREAS] = []

                if not data.get(CONF_AERODROMES) and not data.get(CONF_COORD_AREAS):
                    errors["base"] = "no_filters"
                else:
                    return self.async_create_entry(title="", data=data)

        current_aerodromes = self.config_entry.data.get(CONF_AERODROMES, [])
        aerodromes_str = ", ".join(current_aerodromes) if current_aerodromes else ""

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AERODROMES, default=aerodromes_str): str,
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
                ): cv.positive_int,
                vol.Optional("modify_coordinates", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_coordinates(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle coordinate configuration in options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                latitude = user_input[CONF_LATITUDE]
                longitude = user_input[CONF_LONGITUDE]
                range_nm = user_input[CONF_RANGE_NM]

                if range_nm <= 0:
                    errors[CONF_RANGE_NM] = "invalid_range"

                if not errors:
                    self._coordinate_areas.append(
                        {
                            CONF_LATITUDE: latitude,
                            CONF_LONGITUDE: longitude,
                            CONF_RANGE_NM: range_nm,
                        }
                    )

                    if user_input.get("add_another", False):
                        return await self.async_step_coordinates()

                    data = dict(self._pending_data)
                    data[CONF_COORD_AREAS] = self._coordinate_areas
                    data.setdefault(CONF_AERODROMES, [])
                    data.setdefault(
                        CONF_REFRESH_INTERVAL,
                        self.config_entry.data.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL),
                    )

                    if not data.get(CONF_AERODROMES) and not data.get(CONF_COORD_AREAS):
                        errors["base"] = "no_filters"
                    else:
                        return self.async_create_entry(title="", data=data)

            except (ValueError, KeyError):
                errors["base"] = "invalid_coordinates"

        # Use first existing coordinate as default if available
        existing = (
            self.config_entry.options.get(CONF_COORD_AREAS)
            or self.config_entry.data.get(CONF_COORD_AREAS, [])
        )
        first = existing[0] if existing and not self._coordinate_areas else {}

        data_schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE, default=first.get(CONF_LATITUDE, 0.0)): cv.latitude,
                vol.Required(CONF_LONGITUDE, default=first.get(CONF_LONGITUDE, 0.0)): cv.longitude,
                vol.Required(CONF_RANGE_NM, default=first.get(CONF_RANGE_NM, 50)): cv.positive_float,
                vol.Optional("add_another", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="coordinates",
            data_schema=data_schema,
            description_placeholders={"count": str(len(self._coordinate_areas))},
            errors=errors,
        )
