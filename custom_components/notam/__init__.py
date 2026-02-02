"""The NOTAM integration."""
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

_LOGGER = logging.getLogger(__name__)

DOMAIN = "notam"
PLATFORMS = [Platform.SENSOR]

CONF_AERODROMES = "aerodromes"
CONF_COORDINATES = "coordinates"
CONF_COORD_AREAS = "coordinate_areas"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RANGE_NM = "range_nm"
CONF_REFRESH_INTERVAL = "refresh_interval"

DEFAULT_REFRESH_INTERVAL = 60  # minutes

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
                    COORDINATE_SCHEMA,  # Single coordinate dict (backward compatible)
                    vol.All(cv.ensure_list, [COORDINATE_SCHEMA])  # List of coordinate dicts
                ),
                vol.Optional(CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL): cv.positive_int,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the NOTAM component from YAML (legacy)."""
    hass.data.setdefault(DOMAIN, {})
    
    if DOMAIN not in config:
        return True

    # Import YAML config to config entry
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "import"},
            data=config[DOMAIN],
        )
    )
    
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up NOTAM from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Get configuration from entry - check options first (from config UI), then data (from YAML)
    conf = entry.options if entry.options else entry.data
    
    _LOGGER.info("=" * 60)
    _LOGGER.info("NOTAM Integration Setup - Config Entry ID: %s", entry.entry_id)
    _LOGGER.info("Reading from: %s", "options" if entry.options else "data")
    _LOGGER.info("Full config: %s", conf)
    _LOGGER.info("=" * 60)
    
    # Validate that at least one filter is provided
    aerodromes = conf.get(CONF_AERODROMES, [])
    # Check all possible coordinate key names for backward compatibility
    coordinate_areas = (
        conf.get("coordinate_areas") or 
        conf.get(CONF_COORDINATES) or 
        conf.get(CONF_COORD_AREAS) or 
        []
    )
    
    _LOGGER.info("Parsed configuration:")
    _LOGGER.info("  Aerodromes: %s", aerodromes)
    _LOGGER.info("  Coordinate areas count: %d", len(coordinate_areas) if coordinate_areas else 0)
    if coordinate_areas:
        for idx, coord in enumerate(coordinate_areas):
            _LOGGER.info("    Area %d: lat=%s, lon=%s, range=%s NM",
                        idx + 1,
                        coord.get(CONF_LATITUDE),
                        coord.get(CONF_LONGITUDE),
                        coord.get(CONF_RANGE_NM))
    
    if not aerodromes and not coordinate_areas:
        _LOGGER.error(
            "NOTAM integration requires either 'aerodromes' or 'coordinates' configuration"
        )
        return False

    # Create coordinator
    refresh_interval = conf.get(CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL)
    _LOGGER.info("  Refresh interval: %d minutes", refresh_interval)
    
    coordinator = NOTAMDataUpdateCoordinator(
        hass,
        aerodromes=aerodromes,
        coordinates=coordinate_areas,
        refresh_interval=refresh_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Load platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Setup options flow update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register services
    async def handle_refresh(call):
        """Handle the refresh service call."""
        _LOGGER.info("Manual refresh requested via service call")
        await coordinator.async_request_refresh()
    
    # Register the service (only once, even if multiple config entries)
    if not hass.services.has_service(DOMAIN, "refresh"):
        hass.services.async_register(
            DOMAIN,
            "refresh",
            handle_refresh,
        )
        _LOGGER.info("Registered notam.refresh service")

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


class NOTAMDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching NOTAM data."""

    def __init__(
        self,
        hass: HomeAssistant,
        aerodromes: list[str],
        coordinates: list[dict[str, Any]] | None,
        refresh_interval: int,
    ) -> None:
        """Initialize."""
        self.aerodromes = [code.upper() for code in aerodromes]
        self.coordinates = coordinates  # Now a list of coordinate dicts or None
        self.url = "https://pibs.nats.co.uk/operational/pibs/PIB.xml"

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=refresh_interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        session = async_get_clientsession(self.hass)

        try:
            async with asyncio.timeout(30):
                async with session.get(self.url) as response:
                    response.raise_for_status()
                    xml_content = await response.text()

            # Parse XML
            from .parser import parse_notam_xml

            data = parse_notam_xml(
                xml_content,
                self.aerodromes,
                self.coordinates,
            )

            _LOGGER.debug(
                "Fetched NOTAM data: %d matching NOTAMs", len(data.get("notams", []))
            )

            return data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Error parsing NOTAM data: {err}") from err
