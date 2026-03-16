"""The UK NOTAMs integration."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_ATTRIBUTION,
    CONF_AERODROMES,
    CONF_COORD_AREAS,
    CONF_COORDINATES,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_RANGE_NM,
    CONF_REFRESH_INTERVAL,
    DEFAULT_REFRESH_INTERVAL,
    DOMAIN,
    NATS_PIB_URL,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]

COORDINATE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_LATITUDE): cv.latitude,
        vol.Required(CONF_LONGITUDE): cv.longitude,
        vol.Required(CONF_RANGE_NM): cv.positive_float,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_AERODROMES): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_COORDINATES): vol.Any(
                    COORDINATE_SCHEMA,
                    vol.All(cv.ensure_list, [COORDINATE_SCHEMA]),
                ),
                vol.Optional(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                ): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the UK NOTAMs component from YAML (legacy)."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=config[DOMAIN],
        )
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up UK NOTAMs from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    conf = entry.options if entry.options else entry.data

    _LOGGER.info("UK NOTAMs integration setup — entry_id: %s", entry.entry_id)

    aerodromes = conf.get(CONF_AERODROMES, [])
    coordinate_areas = (
        conf.get(CONF_COORD_AREAS)
        or conf.get(CONF_COORDINATES)
        or conf.get("coordinate_areas")
        or []
    )

    if not aerodromes and not coordinate_areas:
        _LOGGER.error(
            "UK NOTAMs requires either 'aerodromes' or 'coordinates' in configuration"
        )
        return False

    refresh_interval = conf.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)

    coordinator = UKNOTAMDataUpdateCoordinator(
        hass,
        entry_id=entry.entry_id,
        aerodromes=aerodromes,
        coordinates=coordinate_areas,
        refresh_interval=refresh_interval,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register refresh service (only once across all entries)
    if not hass.services.has_service(DOMAIN, "refresh"):

        async def handle_refresh(call):
            """Handle the refresh service call."""
            _LOGGER.info("Manual refresh requested via service call")
            await coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, "refresh", handle_refresh)
        _LOGGER.info("Registered %s.refresh service", DOMAIN)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class UKNOTAMDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching UK NOTAM data from the NATS PIB feed."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        aerodromes: list[str],
        coordinates: list[dict[str, Any]] | None,
        refresh_interval: int,
    ) -> None:
        """Initialise the coordinator."""
        self.entry_id = entry_id
        self.aerodromes = [code.upper() for code in aerodromes]
        self.coordinates = coordinates or []

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the NATS PIB XML feed."""
        session = async_get_clientsession(self.hass)

        try:
            async with asyncio.timeout(30):
                async with session.get(NATS_PIB_URL) as response:
                    response.raise_for_status()
                    xml_content = await response.text()

            from .parser import parse_notam_xml

            data = parse_notam_xml(xml_content, self.aerodromes, self.coordinates)

            _LOGGER.debug(
                "Fetched UK NOTAM data: %d matching NOTAMs",
                len(data.get("notams", [])),
            )

            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with NATS PIB feed: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error parsing NOTAM data: {err}") from err
