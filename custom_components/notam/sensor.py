"""Support for NOTAM sensors."""
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, NOTAMDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NOTAM sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Clean up old v2.x sensors BEFORE creating new ones (those with old naming scheme)
    from homeassistant.helpers import entity_registry as er
    entity_reg = er.async_get(hass)
    entries_to_remove = []
    
    for entity_id in entity_reg.entities:
        if entity_id.startswith("sensor.notam_") and entry.entry_id in str(entity_reg.entities[entity_id].config_entry_id):
            # Check if this is an old format (has eggn, eggl, etc. as first part after notam_)
            # New format: sensor.notam_<aerodrome>_<series><number>_<year>
            # Old format: sensor.notam_<nof>_<series>_<number>_<year>
            parts = entity_id.replace("sensor.notam_", "").split("_")
            if len(parts) == 4:
                # Old format: notam_eggn_a_6550_25
                # New format: notam_egll_a6550_25 (series+number combined)
                entries_to_remove.append(entity_id)
            elif len(parts) == 3:
                # Could be new format, check if entity matches any current NOTAM
                entity_entry = entity_reg.entities.get(entity_id)
                if entity_entry:
                    # If unique_id doesn't match any current NOTAM, remove it
                    unique_id = entity_entry.unique_id
                    found = False
                    for notam in coordinator.data.get("notams", []):
                        aerodrome = notam.get("aerodrome_code", notam["nof"]).lower()
                        series = notam["series"].lower()
                        number = notam["number"].lower()
                        year = notam["year"].lower()
                        expected_unique_id = f"{entry.entry_id}_{aerodrome}_{series}{number}_{year}"
                        if unique_id == expected_unique_id:
                            found = True
                            break
                    if not found:
                        entries_to_remove.append(entity_id)
    
    # Remove old entities
    if entries_to_remove:
        _LOGGER.info("Removing %d old v2.x NOTAM sensors", len(entries_to_remove))
        for entity_id in entries_to_remove:
            entity_reg.async_remove(entity_id)

    # Create global sensors for PIB bulletin metadata, FIRs, and Aerodromes
    global_sensors = [
        NOTAMPIBSensor(coordinator, entry),
        NOTAMFIRSensor(coordinator, entry),
        NOTAMAerodromeSensor(coordinator, entry),
    ]

    # Create NOTAM sensors
    notam_sensors = []
    if coordinator.data and "notams" in coordinator.data:
        _LOGGER.info("Creating sensors for %d NOTAMs", len(coordinator.data["notams"]))
        for notam in coordinator.data["notams"]:
            notam_sensors.append(NOTAMSensor(coordinator, entry, notam))
    else:
        _LOGGER.warning("No NOTAM data available to create sensors!")

    _LOGGER.info("Adding %d NOTAM sensors + %d global sensors = %d total", 
                 len(notam_sensors), len(global_sensors), len(notam_sensors) + len(global_sensors))
    async_add_entities(global_sensors + notam_sensors, update_before_add=True)

    # Store reference for dynamic entity creation
    coordinator.async_add_entities = async_add_entities
    coordinator.entry_id = entry.entry_id
    coordinator.existing_notams = {
        f"{n['nof']}_{n['series']}_{n['number']}_{n['year']}"
        for n in coordinator.data.get("notams", [])
    }

    @callback
    def _async_add_remove_entities() -> None:
        """Add new entities and track removals."""
        if not coordinator.data or "notams" not in coordinator.data:
            return

        current_notams = {
            f"{n['nof']}_{n['series']}_{n['number']}_{n['year']}"
            for n in coordinator.data["notams"]
        }

        # Find new NOTAMs
        new_notams = current_notams - coordinator.existing_notams
        
        if new_notams:
            new_entities = []
            for notam in coordinator.data["notams"]:
                notam_id = f"{notam['nof']}_{notam['series']}_{notam['number']}_{notam['year']}"
                if notam_id in new_notams:
                    new_entities.append(NOTAMSensor(coordinator, entry, notam))
            
            if new_entities:
                async_add_entities(new_entities)
                _LOGGER.info("Added %d new NOTAM sensors", len(new_entities))

        coordinator.existing_notams = current_notams

    # Subscribe to coordinator updates for dynamic entity management
    coordinator.async_add_listener(_async_add_remove_entities)


class NOTAMPIBSensor(CoordinatorEntity, SensorEntity):
    """Representation of NOTAM PIB bulletin metadata sensor."""

    def __init__(
        self,
        coordinator: NOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "NOTAM Data"
        self._attr_unique_id = f"{entry.entry_id}_notam_data"
        self._attr_icon = "mdi:airplane-clock"

    @property
    def native_value(self) -> int | None:
        """Return the number of active NOTAMs as the state."""
        if not self.coordinator.data or "notams" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["notams"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return PIB bulletin metadata as attributes."""
        if not self.coordinator.data or "global" not in self.coordinator.data:
            return {}
        
        global_data = self.coordinator.data["global"]
        attrs = {
            "issued": global_data.get("issued", ""),
            "valid_from": global_data.get("valid_from", ""),
            "valid_to": global_data.get("valid_to", ""),
            "authority_name": global_data.get("authority_name", ""),
            "authority_title": global_data.get("authority_title", ""),
            "organisation": global_data.get("organisation", ""),
            "profile_name": global_data.get("profile_name", ""),
            "content_explanation": global_data.get("content_explanation", ""),
            "lower_fl": global_data.get("lower_fl", ""),
            "upper_fl": global_data.get("upper_fl", ""),
            "notam_count": len(self.coordinator.data.get("notams", [])),
        }
        
        return attrs


class NOTAMFIRSensor(CoordinatorEntity, SensorEntity):
    """Representation of FIR (Flight Information Region) list sensor."""

    def __init__(
        self,
        coordinator: NOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "NOTAM FIRs"
        self._attr_unique_id = f"{entry.entry_id}_notam_firs"
        self._attr_icon = "mdi:earth"

    @property
    def native_value(self) -> int | None:
        """Return the number of FIRs as the state."""
        if not self.coordinator.data or "fir_list" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["fir_list"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return FIR list as attributes."""
        if not self.coordinator.data or "fir_list" not in self.coordinator.data:
            return {}
        
        fir_list = self.coordinator.data["fir_list"]
        
        # Return as dict of ICAO: Name
        return {
            "firs": fir_list,
            "fir_count": len(fir_list),
        }


class NOTAMAerodromeSensor(CoordinatorEntity, SensorEntity):
    """Representation of Aerodrome list sensor."""

    def __init__(
        self,
        coordinator: NOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "NOTAM Aerodromes"
        self._attr_unique_id = f"{entry.entry_id}_notam_aerodromes"
        self._attr_icon = "mdi:airport"

    @property
    def native_value(self) -> int | None:
        """Return the number of aerodromes as the state."""
        if not self.coordinator.data or "aerodrome_details" not in self.coordinator.data:
            return 0
        return len(self.coordinator.data["aerodrome_details"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aerodrome list as attributes."""
        if not self.coordinator.data or "aerodrome_details" not in self.coordinator.data:
            return {}
        
        aerodrome_details = self.coordinator.data["aerodrome_details"]
        
        # Return as a list of aerodrome dicts
        return {
            "aerodromes": aerodrome_details,
            "aerodrome_count": len(aerodrome_details),
        }


class NOTAMGlobalSensor(CoordinatorEntity, SensorEntity):
    """Representation of a global NOTAM sensor (ValidFrom, ValidTo, Issued)."""

    def __init__(
        self,
        coordinator: NOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
        field: str,
        name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._field = field
        self._attr_name = f"NOTAM {name}"
        self._attr_unique_id = f"{entry.entry_id}_notam_{field}"
        self._attr_icon = "mdi:airplane"

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data or "global" not in self.coordinator.data:
            return None
        return self.coordinator.data["global"].get(self._field)


class NOTAMSensor(CoordinatorEntity, SensorEntity):
    """Representation of a NOTAM sensor."""

    def __init__(
        self,
        coordinator: NOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
        notam: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._notam = notam
        
        # Generate entity ID with aerodrome code
        # Format: notam_<aerodrome>_<series><number>_<year>
        # e.g., notam_egll_a6550_25 for EGLL aerodrome
        aerodrome = notam.get("aerodrome_code", notam["nof"]).lower()
        nof = notam["nof"].lower()
        series = notam["series"].lower()
        number = notam["number"].lower()
        year = notam["year"].lower()
        
        self._attr_unique_id = f"{entry.entry_id}_{aerodrome}_{series}{number}_{year}"
        # Name format: "NOTAM EGLL EGGN/A6550/25" (aerodrome NOF/Series+Number/Year)
        self._attr_name = f"NOTAM {aerodrome.upper()} {nof.upper()}/{series.upper()}{number}/{year}"
        self._attr_icon = "mdi:airplane-alert"

    @property
    def native_value(self) -> str:
        """Return the state of the sensor (description text, truncated to 255 chars)."""
        # Find the matching NOTAM in current coordinator data
        if self.coordinator.data and "notams" in self.coordinator.data:
            for notam in self.coordinator.data["notams"]:
                if self._matches_notam(notam):
                    description = notam.get("description", "")
                    # Truncate to 255 characters (HA state limit)
                    return description[:252] + "..." if len(description) > 255 else description
        
        # Fallback to stored NOTAM data
        description = self._notam.get("description", "")
        return description[:252] + "..." if len(description) > 255 else description

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return entity attributes."""
        # Find the matching NOTAM in current coordinator data
        notam = self._notam
        if self.coordinator.data and "notams" in self.coordinator.data:
            for current_notam in self.coordinator.data["notams"]:
                if self._matches_notam(current_notam):
                    notam = current_notam
                    break
        
        attrs = {
            "nof": notam.get("nof", ""),
            "aerodrome_code": notam.get("aerodrome_code", ""),
            "series": notam.get("series", ""),
            "number": notam.get("number", ""),
            "year": notam.get("year", ""),
            "description": notam.get("description", ""),  # Full text
            "start_validity": notam.get("start_validity", ""),
            "end_validity": notam.get("end_validity", ""),
        }
        
        # Add aerodrome name if available
        if "aerodrome_name" in notam:
            attrs["aerodrome_name"] = notam["aerodrome_name"]
        
        if "coordinates" in notam:
            attrs["coordinates"] = notam["coordinates"]
        if "latitude" in notam:
            attrs["latitude"] = notam["latitude"]
        if "longitude" in notam:
            attrs["longitude"] = notam["longitude"]
        if "radius_nm" in notam:
            attrs["radius_nm"] = notam["radius_nm"]
        
        return attrs

    def _matches_notam(self, notam: dict[str, Any]) -> bool:
        """Check if a NOTAM matches this sensor."""
        return (
            notam["nof"] == self._notam["nof"]
            and notam["series"] == self._notam["series"]
            and notam["number"] == self._notam["number"]
            and notam["year"] == self._notam["year"]
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Check if this NOTAM still exists in the data
        if self.coordinator.data and "notams" in self.coordinator.data:
            exists = any(
                self._matches_notam(notam)
                for notam in self.coordinator.data["notams"]
            )
            
            if not exists:
                # NOTAM no longer exists, remove the entity
                _LOGGER.info(
                    "NOTAM %s no longer in feed, removing entity", self._attr_unique_id
                )
                # Mark entity as unavailable and schedule for removal
                self._attr_available = False
                self.async_write_ha_state()
                
                # Schedule entity removal
                from homeassistant.helpers import entity_registry as er
                entity_reg = er.async_get(self.hass)
                if entity_reg.async_get(self.entity_id):
                    entity_reg.async_remove(self.entity_id)
                return
        
        self.async_write_ha_state()
