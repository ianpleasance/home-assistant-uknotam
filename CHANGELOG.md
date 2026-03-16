# Changelog

All notable changes to the UK NOTAMs integration are documented here.

---

## [2.0.0] — 2025

### Breaking changes
- **Domain renamed from `notam` to `uknotams`.**  
  After upgrading you must remove the old integration from Settings → Devices & Services and re-add it as **UK NOTAMs**. Any dashboard cards or automations referencing `sensor.notam_*` entity IDs will need updating to `sensor.uknotam_*`.

### Added
- `const.py` — all constants centralised, consistent with sibling integrations.
- `ATTR_ATTRIBUTION` on every sensor (`"Data provided by NATS UK NOTAM PIB feed"`).
- `DeviceInfo` on all sensor classes — sensors now group under a **UK NOTAM Monitor** device in the HA UI.
- `SensorStateClass.MEASUREMENT` on the three count sensors (PIB, FIRs, Aerodromes) so they graph in HA history.
- `last_updated` (timezone-aware via `dt_util.now()`) in `extra_state_attributes` on every sensor.
- `from __future__ import annotations` in all Python files.
- Translation files for all 13 languages: `da`, `de`, `en`, `es`, `fi`, `fr`, `it`, `ja`, `nl`, `no`, `pl`, `pt`, `sv`.
- `codeowners` set to `["@ianpleasance"]` in `manifest.json`.

### Fixed
- **Critical deduplication bug**: `existing_notams` tracking set previously used `nof_series_number_year` but `unique_id` used `aerodrome_nof_series+number_year` — these never matched, so dynamic entity add/remove was broken. Both now use a single canonical key function (`aerodrome_series+number_year`).
- **Duplicate entity ID warnings**: sensor `unique_id` and the tracking key are now derived from the same helper function, eliminating duplicate-creation log warnings on every update.
- **Monkey-patching removed**: `coordinator.async_add_entities` and `coordinator.entry_id` are no longer bolted on post-construction. `entry_id` is passed to `__init__`; `async_add_entities` is captured as a closure variable.
- Removed dead code: `NOTAMGlobalSensor` class (defined but never instantiated).
- Simplified `unique_id` format: removed redundant `nof` component (was `entry_id_aerodrome_nof_series+number_year`, now `entry_id_aerodrome_series+number_year`).

### Removed / consolidated docs
- Deleted: `INDEX.md`, `PROJECT_SUMMARY.md`, `README_INSTALLATION.md`, `QUICK_START.txt`, `info.md`.
- Merged into `README.md`: installation, UI configuration, quick-reference, multiple coordinates feature.

---

## [1.x] — 2024–2025 (original `notam` domain)

Initial releases under the `notam` domain. Supported aerodrome and coordinate-based filtering of the NATS PIB XML feed with dynamic NOTAM sensor creation and auto-cleanup of expired entities.
