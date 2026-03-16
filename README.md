# UK NOTAMs Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/ianpleasance/home-assistant-uknotams.svg)](https://github.com/ianpleasance/home-assistant-uknotams/releases/)

A Home Assistant custom integration that fetches and monitors **NOTAMs** (Notices to Airmen) from the UK NATS (National Air Traffic Services) PIB (Pre-flight Information Bulletin) XML feed.

> **Upgrading from the old `notam` domain?** See the [Migration](#migration-from-notam-domain) section.

---

## Features

- ✈️ **Monitor by aerodrome** — track specific UK aerodromes (EGLL, EGSS, EGKK, EGMC, etc.)
- 📍 **Geographic filtering** — monitor NOTAMs within a configurable radius of one or more coordinate areas
- 🔄 **Auto-cleanup** — expired NOTAMs are automatically removed from Home Assistant
- 📅 **Validity dates** — each sensor shows start and end validity times
- 🏢 **Full aerodrome names** — displays "HEATHROW" alongside the ICAO code
- 🖥️ **UI or YAML config** — set up via the HA interface or `configuration.yaml`
- 🌍 **13 languages** — UI translated into da, de, en, es, fi, fr, it, ja, nl, no, pl, pt, sv

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three-dot menu → **Custom repositories**
3. Add `https://github.com/ianpleasance/home-assistant-uknotams` — Category: **Integration**
4. Find **UK NOTAMs** in HACS and click **Download**
5. Restart Home Assistant

### Manual

1. Download the latest release
2. Copy the `uknotams` folder into `<config>/custom_components/uknotams/`
3. Restart Home Assistant

---

## Configuration

### Via the UI (recommended)

1. Go to **Settings → Devices & Services → + Add Integration**
2. Search for **UK NOTAMs**
3. Follow the wizard:
   - Enter comma-separated ICAO aerodrome codes (e.g. `EGLL, EGKK, EGSS`) — optional if using coordinates
   - Optionally tick **Add coordinate areas** and step through adding one or more geographic areas
   - Set a refresh interval (default 60 minutes)

To reconfigure, go to **Settings → Devices & Services**, find **UK NOTAMs** and click **Configure**.

> **Note:** When modifying coordinate areas via the UI, all areas are replaced — re-add any you want to keep.

### Via YAML (`configuration.yaml`)

YAML config is automatically imported as a config entry on first startup. At least one of `aerodromes` or `coordinates` must be provided.

**Aerodromes only:**
```yaml
uknotams:
  aerodromes:
    - "EGLL"  # Heathrow
    - "EGKK"  # Gatwick
    - "EGSS"  # Stansted
    - "EGMC"  # Southend
  refresh_interval: 60
```

**Single coordinate area:**
```yaml
uknotams:
  coordinates:
    latitude: 51.4700
    longitude: -0.4543
    range_nm: 50
  refresh_interval: 60
```

**Multiple coordinate areas:**
```yaml
uknotams:
  coordinates:
    - latitude: 51.4700   # London area
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537   # Manchester area
      longitude: -2.2750
      range_nm: 30
    - latitude: 55.9533   # Edinburgh area
      longitude: -3.1883
      range_nm: 40
  refresh_interval: 60
```

**Combined — aerodromes and multiple coordinate areas:**
```yaml
uknotams:
  aerodromes:
    - "EGLL"
    - "EGCC"
  coordinates:
    - latitude: 51.4700
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537
      longitude: -2.2750
      range_nm: 30
  refresh_interval: 60
```

**Monitoring a flight path (waypoint areas):**
```yaml
uknotams:
  coordinates:
    - latitude: 51.1537   # Departure area
      longitude: -0.1821
      range_nm: 25
    - latitude: 52.3555   # Mid-route
      longitude: 0.1750
      range_nm: 25
    - latitude: 53.3537   # Arrival area
      longitude: -2.2750
      range_nm: 25
  refresh_interval: 30
```

---

## Sensor Entities

All sensors are grouped under a **UK NOTAM Monitor** device (manufacturer: NATS) in the HA device registry.

### Summary sensors (always created)

| Entity | State | Description |
|--------|-------|-------------|
| `sensor.uk_notam_data` | int | Total number of active NOTAMs matching your filters |
| `sensor.uk_notam_fi_rs` | int | Number of Flight Information Regions in the bulletin |
| `sensor.uk_notam_aerodromes` | int | Number of aerodromes in the bulletin |

`sensor.uk_notam_data` carries the full PIB bulletin metadata as attributes: `issued`, `valid_from`, `valid_to`, `authority_name`, `organisation`, `lower_fl`, `upper_fl`, etc.

### Per-NOTAM sensors (one per matching NOTAM)

**Entity ID:** `sensor.uk_notam_<aerodrome>_<series><number>_<year>`  
**Example:** `sensor.uk_notam_egll_a6550_25`

**Name:** `UK NOTAM <AERODROME> <SERIES><NUMBER>/<YEAR>`  
**Example:** `UK NOTAM EGLL A6550/25`

**State:** NOTAM description text (truncated to 255 characters if longer)

**Attributes:**

| Attribute | Example | Description |
|-----------|---------|-------------|
| `nof` | `EGGN` | NOTAM Office (issuing authority) |
| `aerodrome_code` | `EGLL` | ICAO code of the affected aerodrome |
| `aerodrome_name` | `HEATHROW` | Full aerodrome name |
| `series` | `A` | NOTAM series letter |
| `number` | `6550` | NOTAM number |
| `year` | `25` | Year (20YY) |
| `description` | (full text) | Complete NOTAM text |
| `start_validity` | `2025-08-15 11:38:00` | When the NOTAM becomes active |
| `end_validity` | `2025-12-31 23:59:00` | When it expires, or `PERM` / `UFN` |
| `coordinates` | `5120N00024W` | Raw coordinate string from feed |
| `latitude` | `51.333` | Parsed decimal latitude |
| `longitude` | `-0.4` | Parsed decimal longitude |
| `radius_nm` | `5.0` | Affected radius in nautical miles |
| `attribution` | (NATS data credit) | Data attribution |
| `last_updated` | `2025-08-15T12:00:00+01:00` | When this sensor was last refreshed |

---

## Filtering Logic

### Aerodrome filtering

NOTAMs are matched by their **aerodrome code** (the `ItemA` location field), not the issuing NOTAM Office (NOF). If you configure `EGLL`, you get NOTAMs *about* Heathrow, regardless of which office issued them.

### Coordinate filtering

A NOTAM is included if its centre point falls within a configured area, accounting for the NOTAM's own radius:

```
included if: haversine_distance(area_centre, notam_centre) ≤ (area_range_nm + notam_radius_nm)
```

This means NOTAMs whose affected area *intersects* your monitoring circle are included, not just those whose centre is inside it.

### Combined filtering (OR logic)

If you configure both aerodromes and coordinate areas, a NOTAM is included if it matches **either** filter — not both.

---

## Services

### `uknotams.refresh`

Force an immediate refresh from the NATS PIB feed, bypassing the normal interval:

```yaml
service: uknotams.refresh
```

---

## Example Automations

### Notify when a new NOTAM appears for your aerodrome

```yaml
automation:
  - alias: "Alert on new Heathrow NOTAM"
    trigger:
      - platform: event
        event_type: state_changed
    condition:
      - condition: template
        value_template: >
          {{ trigger.event.data.entity_id.startswith('sensor.uk_notam_egll_') and
             trigger.event.data.old_state is none }}
    action:
      - service: notify.mobile_app_ians_galaxy_a53
        data:
          title: "New NOTAM — Heathrow"
          message: >
            {{ states(trigger.event.data.entity_id) }}
```

### Dashboard card showing active NOTAMs

```yaml
type: entities
title: Active NOTAMs
entities:
  - sensor.uk_notam_data
  - sensor.uk_notam_egll_a6550_25
  - sensor.uk_notam_egkk_b1234_25
show_header_toggle: false
```

### Template to count NOTAMs by aerodrome

```yaml
{% set egll_notams = states.sensor
  | selectattr('entity_id', 'search', 'uk_notam_egll_')
  | list %}
{{ egll_notams | count }} active NOTAMs for Heathrow
```

---

## Data Source

Feed URL: `https://pibs.nats.co.uk/operational/pibs/PIB.xml`  
Provider: [NATS — UK National Air Traffic Services](https://www.nats.aero/)  
Public feed — no authentication required.

---

## Common UK ICAO Codes

| Code | Aerodrome |
|------|-----------|
| EGLL | London Heathrow |
| EGKK | London Gatwick |
| EGSS | London Stansted |
| EGGW | London Luton |
| EGLC | London City |
| EGMC | Southend |
| EGCC | Manchester |
| EGPF | Glasgow |
| EGPH | Edinburgh |
| EGBB | Birmingham |
| EGNT | Newcastle |
| EGNX | East Midlands |
| EGSH | Norwich |

---

## Troubleshooting

**No NOTAM sensors appear**
- Verify your ICAO codes are exactly 4 letters and refer to current UK aerodromes
- Not all aerodromes have active NOTAMs at all times — this is normal
- Check the NATS feed directly at the URL above to see if NOTAMs exist for your aerodrome
- Enable debug logging: add `logger: logs: custom_components.uknotams: debug` to `configuration.yaml`

**Duplicate entity warnings in logs**
- These were caused by a key-format mismatch in earlier versions and are fully fixed in v2.0.0

**Old `sensor.notam_*` entities remain after upgrade**
- Remove the old `notam` integration from Settings → Devices & Services
- The new `uknotams` integration creates fresh entities under `sensor.uk_notam_*`

**NOTAM sensors disappear**
- This is normal — sensors are removed automatically when a NOTAM expires or is withdrawn from the feed

**Cannot connect to NATS feed**
- Check your HA instance has outbound internet access
- The feed is occasionally briefly unavailable; the integration will retry on the next scheduled refresh

---

## Migration from `notam` Domain

Version 2.0.0 renames the integration domain from `notam` to `uknotams`.

1. Go to **Settings → Devices & Services** and remove the existing **NOTAM** integration
2. Restart Home Assistant
3. Add the **UK NOTAMs** integration (search for `uknotams`)
4. Update any dashboard cards, automations, or templates that reference `sensor.notam_*` to use `sensor.uk_notam_*`

If you were using YAML config with `notam:`, rename the key to `uknotams:`.

---

## Version History

See [CHANGELOG.md](CHANGELOG.md) for full details.

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Disclaimer

This integration is for informational purposes only. Always verify NOTAMs via official channels before flight planning. The author accepts no responsibility for decisions made on the basis of data provided by this integration.
