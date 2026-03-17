"""Support for UK NOTAM sensors."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_ATTRIBUTION, DOMAIN
from . import UKNOTAMDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Shared device info helper — all sensors belong to the same device per entry
def _device_info(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="UK NOTAM",
        manufacturer="NATS",
        entry_type=DeviceEntryType.SERVICE,
    )


def _make_notam_unique_id(entry_id: str, notam: dict[str, Any]) -> str:
    """Generate a canonical unique_id for a NOTAM sensor.

    Format: <entry_id>_<aerodrome>_<series><number>_<year>
    e.g.  : abc123_egll_a6550_25

    NOF is intentionally excluded — for the purpose of deduplication
    within a single PIB fetch, the aerodrome+series+number+year tuple
    is sufficient and avoids the redundancy when NOF == aerodrome.
    """
    aerodrome = (notam.get("aerodrome_code") or notam.get("nof") or "unknown").lower()
    series = (notam.get("series") or "x").lower()
    number = (notam.get("number") or "0").lower()
    year = (notam.get("year") or "00").lower()
    return f"{entry_id}_{aerodrome}_{series}{number}_{year}"


def _make_notam_tracking_key(notam: dict[str, Any]) -> str:
    """Generate the tracking key used in existing_notams set.

    MUST match the key produced by _make_notam_unique_id (minus entry_id prefix)
    so that the dynamic add/remove listener can correctly detect new/gone NOTAMs.
    """
    aerodrome = (notam.get("aerodrome_code") or notam.get("nof") or "unknown").lower()
    series = (notam.get("series") or "x").lower()
    number = (notam.get("number") or "0").lower()
    year = (notam.get("year") or "00").lower()
    return f"{aerodrome}_{series}{number}_{year}"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up UK NOTAM sensors from a config entry."""
    coordinator: UKNOTAMDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # ------------------------------------------------------------------
    # Remove any stale entities left over from previous versions / runs
    # that no longer match NOTAMs in the current feed.
    # ------------------------------------------------------------------
    from homeassistant.helpers import entity_registry as er

    entity_reg = er.async_get(hass)
    current_unique_ids: set[str] = set()

    if coordinator.data and "notams" in coordinator.data:
        current_unique_ids = {
            _make_notam_unique_id(entry.entry_id, n)
            for n in coordinator.data["notams"]
        }

    # Also keep the three global sensor unique IDs
    global_unique_ids = {
        f"{entry.entry_id}_uknotam_data",
        f"{entry.entry_id}_uknotam_firs",
        f"{entry.entry_id}_uknotam_aerodromes",
    }

    for entity_entry in list(entity_reg.entities.values()):
        if entity_entry.config_entry_id != entry.entry_id:
            continue
        if entity_entry.domain != "sensor":
            continue
        uid = entity_entry.unique_id
        if uid in global_unique_ids:
            continue
        if uid not in current_unique_ids:
            _LOGGER.info(
                "Removing stale/old NOTAM entity %s (unique_id: %s)",
                entity_entry.entity_id,
                uid,
            )
            entity_reg.async_remove(entity_entry.entity_id)

    # ------------------------------------------------------------------
    # Create global summary sensors
    # ------------------------------------------------------------------
    global_sensors = [
        UKNOTAMPIBSensor(coordinator, entry),
        UKNOTAMFIRSensor(coordinator, entry),
        UKNOTAMAerodromeSensor(coordinator, entry),
    ]

    # ------------------------------------------------------------------
    # Create per-NOTAM sensors — deduplicate by unique_id
    # ------------------------------------------------------------------
    notam_sensors: list[UKNOTAMSensor] = []
    seen_unique_ids: set[str] = set()

    if coordinator.data and "notams" in coordinator.data:
        _LOGGER.info(
            "Creating sensors for %d NOTAMs", len(coordinator.data["notams"])
        )
        for notam in coordinator.data["notams"]:
            if not notam.get("nof") or not notam.get("series") or not notam.get("number") or not notam.get("year"):
                _LOGGER.warning("Skipping NOTAM with missing fields: %s", notam)
                continue

            uid = _make_notam_unique_id(entry.entry_id, notam)
            if uid in seen_unique_ids:
                _LOGGER.debug(
                    "Skipping duplicate NOTAM unique_id %s", uid
                )
                continue

            seen_unique_ids.add(uid)
            notam_sensors.append(UKNOTAMSensor(coordinator, entry, notam))
    else:
        _LOGGER.warning("No NOTAM data available during sensor setup")

    _LOGGER.info(
        "Adding %d NOTAM sensors + %d global sensors",
        len(notam_sensors),
        len(global_sensors),
    )
    async_add_entities(global_sensors + notam_sensors, update_before_add=True)

    # ------------------------------------------------------------------
    # Track existing NOTAMs for dynamic add/remove on subsequent updates
    # ------------------------------------------------------------------
    existing_notams: set[str] = {
        _make_notam_tracking_key(n)
        for n in coordinator.data.get("notams", [])
    } if coordinator.data else set()

    @callback
    def _async_add_remove_entities() -> None:
        """Dynamically add new NOTAM entities discovered after initial setup."""
        nonlocal existing_notams

        if not coordinator.data or "notams" not in coordinator.data:
            return

        current_keys: set[str] = {
            _make_notam_tracking_key(n) for n in coordinator.data["notams"]
        }
        new_keys = current_keys - existing_notams

        if new_keys:
            new_entities: list[UKNOTAMSensor] = []
            seen_in_batch: set[str] = set()
            for notam in coordinator.data["notams"]:
                key = _make_notam_tracking_key(notam)
                if key in new_keys and key not in seen_in_batch:
                    seen_in_batch.add(key)
                    new_entities.append(UKNOTAMSensor(coordinator, entry, notam))

            if new_entities:
                async_add_entities(new_entities)
                _LOGGER.info("Dynamically added %d new NOTAM sensors", len(new_entities))

        existing_notams = current_keys

    coordinator.async_add_listener(_async_add_remove_entities)


# ---------------------------------------------------------------------------
# Global / summary sensors
# ---------------------------------------------------------------------------

class UKNOTAMPIBSensor(CoordinatorEntity, SensorEntity):
    """PIB bulletin metadata + total NOTAM count."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:airplane-clock"
    _attr_name = "Data"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: UKNOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_uknotam_data"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        """Return total number of active NOTAMs."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("notams", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return PIB bulletin metadata."""
        attrs: dict[str, Any] = {
            "attribution": ATTR_ATTRIBUTION,
            "last_updated": dt_util.now().isoformat(),
        }
        if not self.coordinator.data:
            return attrs

        global_data = self.coordinator.data.get("global", {})
        attrs.update(
            {
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
        )
        return attrs


class UKNOTAMFIRSensor(CoordinatorEntity, SensorEntity):
    """Flight Information Region list sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:earth"
    _attr_name = "FIRs"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: UKNOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_uknotam_firs"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        """Return number of FIRs."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("fir_list", {}))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return FIR list."""
        attrs: dict[str, Any] = {
            "attribution": ATTR_ATTRIBUTION,
            "last_updated": dt_util.now().isoformat(),
        }
        if not self.coordinator.data:
            return attrs

        fir_list = self.coordinator.data.get("fir_list", {})
        attrs["firs"] = fir_list
        attrs["fir_count"] = len(fir_list)
        return attrs


class UKNOTAMAerodromeSensor(CoordinatorEntity, SensorEntity):
    """Aerodrome list sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:airport"
    _attr_name = "Aerodromes"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: UKNOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_uknotam_aerodromes"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> int:
        """Return number of aerodromes."""
        if not self.coordinator.data:
            return 0
        return len(self.coordinator.data.get("aerodrome_details", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return aerodrome details."""
        attrs: dict[str, Any] = {
            "attribution": ATTR_ATTRIBUTION,
            "last_updated": dt_util.now().isoformat(),
        }
        if not self.coordinator.data:
            return attrs

        aerodrome_details = self.coordinator.data.get("aerodrome_details", [])
        attrs["aerodromes"] = aerodrome_details
        attrs["aerodrome_count"] = len(aerodrome_details)
        return attrs


# ---------------------------------------------------------------------------
# Per-NOTAM sensor
# ---------------------------------------------------------------------------

class UKNOTAMSensor(CoordinatorEntity, SensorEntity):
    """Representation of a single UK NOTAM."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:airplane-alert"

    def __init__(
        self,
        coordinator: UKNOTAMDataUpdateCoordinator,
        entry: ConfigEntry,
        notam: dict[str, Any],
    ) -> None:
        """Initialise."""
        super().__init__(coordinator)
        self._notam = notam
        self._entry = entry

        aerodrome = (notam.get("aerodrome_code") or notam.get("nof") or "unknown").upper()
        series = (notam.get("series") or "x").upper()
        number = (notam.get("number") or "0").lower()
        year = (notam.get("year") or "00").lower()

        self._attr_unique_id = _make_notam_unique_id(entry.entry_id, notam)
        self._attr_name = f"{aerodrome} {series}{number}/{year}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> str:
        """Return NOTAM description, truncated to 255 chars."""
        notam = self._current_notam()
        description = notam.get("description", "") if notam else self._notam.get("description", "")
        return description[:252] + "..." if len(description) > 255 else description

    @property
    def available(self) -> bool:
        """Return True only if the NOTAM is still present in the feed."""
        if not self.coordinator.last_update_success:
            return False
        return self._current_notam() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return NOTAM attributes."""
        notam = self._current_notam() or self._notam

        attrs: dict[str, Any] = {
            "attribution": ATTR_ATTRIBUTION,
            "last_updated": dt_util.now().isoformat(),
            "nof": notam.get("nof", ""),
            "aerodrome_code": notam.get("aerodrome_code", ""),
            "series": notam.get("series", ""),
            "number": notam.get("number", ""),
            "year": notam.get("year", ""),
            "description": notam.get("description", ""),
            "start_validity": notam.get("start_validity", ""),
            "end_validity": notam.get("end_validity", ""),
        }

        for optional_key in (
            "aerodrome_name",
            "coordinates",
            "latitude",
            "longitude",
            "radius_nm",
        ):
            if optional_key in notam:
                attrs[optional_key] = notam[optional_key]

        return attrs

    def _current_notam(self) -> dict[str, Any] | None:
        """Find the matching NOTAM in the latest coordinator data."""
        if not self.coordinator.data or "notams" not in self.coordinator.data:
            return None
        for notam in self.coordinator.data["notams"]:
            if self._matches_notam(notam):
                return notam
        return None

    def _matches_notam(self, notam: dict[str, Any]) -> bool:
        """Return True if notam corresponds to this sensor's NOTAM."""
        return (
            notam.get("nof") == self._notam.get("nof")
            and notam.get("series") == self._notam.get("series")
            and notam.get("number") == self._notam.get("number")
            and notam.get("year") == self._notam.get("year")
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data and remove entity when NOTAM expires."""
        if self.coordinator.data and "notams" in self.coordinator.data:
            if not any(
                self._matches_notam(n) for n in self.coordinator.data["notams"]
            ):
                _LOGGER.info(
                    "NOTAM %s no longer in feed — removing entity",
                    self._attr_unique_id,
                )
                self._attr_available = False
                self.async_write_ha_state()

                from homeassistant.helpers import entity_registry as er

                entity_reg = er.async_get(self.hass)
                if entity_reg.async_get(self.entity_id):
                    entity_reg.async_remove(self.entity_id)
                return

        self.async_write_ha_state()
