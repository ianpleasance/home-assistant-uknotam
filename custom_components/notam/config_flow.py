"""Config flow for NOTAM integration."""
import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

DOMAIN = "notam"

CONF_AERODROMES = "aerodromes"
CONF_COORDINATES = "coordinates"
CONF_RANGE_NM = "range_nm"
CONF_REFRESH_INTERVAL = "refresh_interval"
DEFAULT_REFRESH_INTERVAL = 60

# For storing multiple coordinate areas
CONF_COORD_AREAS = "coordinate_areas"


class NotamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for NOTAM."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._coordinate_areas = []

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Store the initial data
            self._data = user_input.copy()

            # Validate we have at least one filter method selected
            has_airfields = user_input.get(CONF_AERODROMES, "").strip()
            has_coordinates = user_input.get("add_coordinates", False)

            if not has_airfields and not has_coordinates:
                errors["base"] = "no_filters"
            elif has_airfields:
                # Validate ICAO codes
                codes = [c.strip().upper() for c in has_airfields.split(",") if c.strip()]
                if not all(len(c) == 4 and c.isalpha() for c in codes):
                    errors["aerodromes"] = "invalid_icao"
                else:
                    self._data[CONF_AERODROMES] = codes

            if not errors:
                # Test connection to NATS feed
                try:
                    await self._test_connection()
                except aiohttp.ClientError:
                    errors["base"] = "cannot_connect"
                except Exception:
                    _LOGGER.exception("Unexpected error during connection test")
                    errors["base"] = "unknown"

            if not errors:
                if user_input.get("add_coordinates", False):
                    # Go to coordinate step
                    return await self.async_step_coordinates()
                else:
                    # Create entry with just aerodromes
                    return self._create_entry()

        # Show initial form
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AERODROMES, default=""): str,
                vol.Optional("add_coordinates", default=False): bool,
                vol.Optional(
                    CONF_REFRESH_INTERVAL, default=DEFAULT_REFRESH_INTERVAL
                ): cv.positive_int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_coordinates(self, user_input=None):
        """Handle coordinate configuration."""
        errors = {}

        if user_input is not None:
            # Validate coordinate input
            try:
                latitude = user_input[CONF_LATITUDE]
                longitude = user_input[CONF_LONGITUDE]
                range_nm = user_input[CONF_RANGE_NM]

                if range_nm <= 0:
                    errors["range_nm"] = "invalid_range"

                if not errors:
                    # Add this coordinate area
                    self._coordinate_areas.append(
                        {
                            CONF_LATITUDE: latitude,
                            CONF_LONGITUDE: longitude,
                            CONF_RANGE_NM: range_nm,
                        }
                    )

                    # Check if user wants to add another area
                    if user_input.get("add_another", False):
                        return await self.async_step_coordinates()
                    else:
                        # Done adding coordinates
                        self._data[CONF_COORD_AREAS] = self._coordinate_areas
                        return self._create_entry()

            except (ValueError, KeyError):
                errors["base"] = "invalid_coordinates"

        # Show coordinate form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE): cv.latitude,
                vol.Required(CONF_LONGITUDE): cv.longitude,
                vol.Required(CONF_RANGE_NM, default=50): cv.positive_float,
                vol.Optional("add_another", default=False): bool,
            }
        )

        description = f"Added {len(self._coordinate_areas)} area(s) so far." if self._coordinate_areas else "Add first coordinate area."

        return self.async_show_form(
            step_id="coordinates",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_import(self, import_data):
        """Handle import from configuration.yaml."""
        # Check if already configured
        await self.async_set_unique_id("notam_integration")
        self._abort_if_unique_id_configured()

        # Convert YAML format to config entry format
        data = {
            CONF_REFRESH_INTERVAL: import_data.get(
                CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
            ),
        }

        if CONF_AERODROMES in import_data:
            data[CONF_AERODROMES] = import_data[CONF_AERODROMES]

        if CONF_COORDINATES in import_data:
            coords = import_data[CONF_COORDINATES]
            # Handle both single dict and list of dicts
            if isinstance(coords, dict):
                data[CONF_COORD_AREAS] = [coords]
            else:
                data[CONF_COORD_AREAS] = coords

        return self.async_create_entry(
            title="NOTAM (imported from YAML)",
            data=data,
        )

    def _create_entry(self):
        """Create the config entry."""
        # Build title
        title_parts = []
        if CONF_AERODROMES in self._data:
            airfields = self._data[CONF_AERODROMES]
            if len(airfields) <= 2:
                title_parts.append(", ".join(airfields))
            else:
                title_parts.append(f"{len(airfields)} airfields")

        if self._coordinate_areas:
            title_parts.append(f"{len(self._coordinate_areas)} area(s)")

        title = "NOTAM: " + " + ".join(title_parts) if title_parts else "NOTAM"

        return self.async_create_entry(
            title=title,
            data=self._data,
        )

    async def _test_connection(self):
        """Test connection to NATS feed."""
        session = async_get_clientsession(self.hass)
        url = "https://pibs.nats.co.uk/operational/pibs/PIB.xml"

        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            response.raise_for_status()
            # Just check we can fetch it, don't parse
            await response.text()

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NotamOptionsFlow()


class NotamOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for NOTAM integration."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        # Initialize coordinate areas list if not set
        if not hasattr(self, '_coordinate_areas'):
            self._coordinate_areas = []
        
        errors = {}

        if user_input is not None:
            # Build new data dictionary from scratch
            data = {}
            
            # Process refresh interval
            data[CONF_REFRESH_INTERVAL] = user_input.get(
                CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
            )

            # Validate and process airfields if provided
            aerodromes_input = user_input.get(CONF_AERODROMES, "").strip()
            if aerodromes_input:
                codes = [
                    c.strip().upper()
                    for c in aerodromes_input.split(",")
                    if c.strip()
                ]
                if not all(len(c) == 4 and c.isalpha() for c in codes):
                    errors["aerodromes"] = "invalid_icao"
                else:
                    data[CONF_AERODROMES] = codes
                    _LOGGER.debug("Validated aerodromes: %s", codes)
            else:
                data[CONF_AERODROMES] = []
                _LOGGER.debug("No aerodromes configured")

            # Check if user wants to modify coordinates
            if not errors:
                if user_input.get("modify_coordinates", False):
                    # User wants to reconfigure coordinates
                    self._coordinate_areas = []
                    self._pending_data = data  # Store the data to merge later
                    return await self.async_step_coordinates()
                else:
                    # Keep existing coordinates OR clear them if they don't want to modify
                    # Check if coordinates currently exist
                    has_coords = (
                        CONF_COORD_AREAS in self.config_entry.data or
                        "coordinates" in self.config_entry.data or
                        "coordinate_areas" in self.config_entry.data
                    )
                    
                    if has_coords:
                        # Preserve existing coordinates
                        if CONF_COORD_AREAS in self.config_entry.data:
                            data[CONF_COORD_AREAS] = self.config_entry.data[CONF_COORD_AREAS]
                        elif "coordinate_areas" in self.config_entry.data:
                            data[CONF_COORD_AREAS] = self.config_entry.data["coordinate_areas"]
                        elif "coordinates" in self.config_entry.data:
                            data[CONF_COORD_AREAS] = self.config_entry.data["coordinates"]
                        _LOGGER.debug("Keeping existing coordinates: %s", data.get(CONF_COORD_AREAS))
                    else:
                        # No coordinates to preserve
                        data[CONF_COORD_AREAS] = []
                        _LOGGER.debug("No coordinates configured")
                    
                    # Validate we have at least one filter
                    if not data.get(CONF_AERODROMES) and not data.get(CONF_COORD_AREAS):
                        errors["base"] = "no_filters"
                    else:
                        _LOGGER.info("Updating NOTAM config: aerodromes=%s, coordinate_areas=%d", 
                                    data.get(CONF_AERODROMES), len(data.get(CONF_COORD_AREAS, [])))
                        return self.async_create_entry(title="", data=data)

        # Get current values from config entry
        current_airfields = self.config_entry.data.get(CONF_AERODROMES, [])
        airfields_str = ", ".join(current_airfields) if current_airfields else ""

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AERODROMES, default=airfields_str): str,
                vol.Optional(
                    CONF_REFRESH_INTERVAL,
                    default=self.config_entry.data.get(
                        CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                    ),
                ): cv.positive_int,
                vol.Optional("modify_coordinates", default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_coordinates(self, user_input=None):
        """Handle coordinate configuration in options."""
        # Initialize coordinate areas list if not set
        if not hasattr(self, '_coordinate_areas'):
            self._coordinate_areas = []
        
        # Initialize pending data storage if not set
        if not hasattr(self, '_pending_data'):
            self._pending_data = {}
        
        errors = {}

        if user_input is not None:
            # Validate coordinate input
            try:
                latitude = user_input[CONF_LATITUDE]
                longitude = user_input[CONF_LONGITUDE]
                range_nm = user_input[CONF_RANGE_NM]

                if range_nm <= 0:
                    errors["range_nm"] = "invalid_range"

                if not errors:
                    # Add this coordinate area
                    self._coordinate_areas.append(
                        {
                            CONF_LATITUDE: latitude,
                            CONF_LONGITUDE: longitude,
                            CONF_RANGE_NM: range_nm,
                        }
                    )

                    # Check if user wants to add another area
                    if user_input.get("add_another", False):
                        return await self.async_step_coordinates()
                    else:
                        # Done adding coordinates - merge with base config
                        data = self._pending_data.copy() if self._pending_data else {}
                        data[CONF_COORD_AREAS] = self._coordinate_areas

                        # Ensure all required fields are present
                        if CONF_AERODROMES not in data:
                            data[CONF_AERODROMES] = []
                        if CONF_REFRESH_INTERVAL not in data:
                            data[CONF_REFRESH_INTERVAL] = self.config_entry.data.get(
                                CONF_REFRESH_INTERVAL, DEFAULT_REFRESH_INTERVAL
                            )
                        
                        # Validate we have at least one filter
                        if not data.get(CONF_AERODROMES) and not data.get(CONF_COORD_AREAS):
                            errors["base"] = "no_filters"
                        else:
                            _LOGGER.info("Updating NOTAM config with coordinates: aerodromes=%s, coordinate_areas=%d", 
                                        data.get(CONF_AERODROMES), len(data.get(CONF_COORD_AREAS, [])))
                            return self.async_create_entry(title="", data=data)

            except (ValueError, KeyError):
                errors["base"] = "invalid_coordinates"

        # Get current coordinates to show as defaults
        current_coords = self.config_entry.options.get(CONF_COORD_AREAS, []) or self.config_entry.data.get(CONF_COORD_AREAS, [])
        
        # If this is the first area being added and we have existing coords, show them
        default_lat = 0.0
        default_lon = 0.0
        default_range = 50
        
        if not self._coordinate_areas and current_coords and len(current_coords) > 0:
            # Show the first existing coordinate as default
            first_coord = current_coords[0]
            default_lat = first_coord.get(CONF_LATITUDE, 0.0)
            default_lon = first_coord.get(CONF_LONGITUDE, 0.0)
            default_range = first_coord.get(CONF_RANGE_NM, 50)
            _LOGGER.debug("Showing existing coordinate: lat=%s, lon=%s, range=%s", default_lat, default_lon, default_range)

        # Show coordinate form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE, default=default_lat): cv.latitude,
                vol.Required(CONF_LONGITUDE, default=default_lon): cv.longitude,
                vol.Required(CONF_RANGE_NM, default=default_range): cv.positive_float,
                vol.Optional("add_another", default=False): bool,
            }
        )

        description = f"Added {len(self._coordinate_areas)} area(s). Current: lat={default_lat}, lon={default_lon}, range={default_range} NM" if current_coords else "Add coordinate area"

        return self.async_show_form(
            step_id="coordinates",
            data_schema=data_schema,
            description_placeholders={"count": description},
            errors=errors,
        )
