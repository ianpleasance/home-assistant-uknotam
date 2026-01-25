# UK NOTAM Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/USERNAME/ha-notam.svg)](https://GitHub.com/USERNAME/ha-notam/releases/)

A Home Assistant custom integration that fetches and monitors NOTAMs (Notices to Airmen) from the UK NATS (National Air Traffic Services) PIB (Pre-flight Information Bulletin) feed.

## Features

✈️ **Monitor NOTAMs by Aerodrome** - Track specific UK aerodromes (EGLL, EGSS, EGKK, etc.)  
📍 **Geographic Filtering** - Monitor NOTAMs within a radius of coordinates  
🔄 **Auto-Cleanup** - Expired NOTAMs automatically removed  
📅 **Validity Dates** - Start and end dates for each NOTAM  
🏢 **Aerodrome Names** - Full names (e.g., "HEATHROW" not just "EGLL")  
⚙️ **Configurable Updates** - Set your own refresh interval

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the 3 dots in the top right corner
3. Select "Custom repositories"
4. Add this repository URL: `https://github.com/USERNAME/ha-notam`
5. Category: Integration
6. Click "Add"
7. Find "UK NOTAM Integration" in HACS and click "Download"
8. Restart Home Assistant

### Manual Installation

1. Download the latest release
2. Extract the `notam` folder to `<config_dir>/custom_components/`
3. Restart Home Assistant

## Configuration

### YAML Configuration (Recommended)

Add to your `configuration.yaml`:

```yaml
notam:
  aerodromes:
    - "EGLL"  # Heathrow
    - "EGKK"  # Gatwick
    - "EGSS"  # Stansted
    - "EGMC"  # Southend
    - "EGPH"  # Edinburgh
  coordinates:
    - latitude: 52.5111
      longitude: -2.6876
      range_nm: 50
  refresh_interval: 60  # minutes (default: 60)
```

**Note:** At least one of `aerodromes` or `coordinates` must be configured.

### UI Configuration

1. Go to Settings → Devices & Services
2. Click "+ Add Integration"
3. Search for "NOTAM"
4. Follow the configuration wizard

## Sensor Entities

### Global Sensors

- `sensor.notam_issue_date` - When the bulletin was issued
- `sensor.notam_valid_from` - Bulletin validity start
- `sensor.notam_valid_to` - Bulletin validity end

### NOTAM Sensors

Each NOTAM creates a sensor with:

**Entity ID:** `sensor.notam_<aerodrome>_<series><number>_<year>`  
Example: `sensor.notam_egll_a6550_25`

**Name:** `NOTAM <AERODROME> <NOF>/<SERIES><NUMBER>/<YEAR>`  
Example: `NOTAM EGLL EGGN/A6550/25`

**State:** Truncated description (first 255 chars)

### Attributes

Each NOTAM sensor has these attributes:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `nof` | `EGGN` | NOTAM Office (issuing office) |
| `aerodrome_code` | `EGLL` | ICAO code of affected aerodrome |
| `aerodrome_name` | `HEATHROW` | Full aerodrome name |
| `series` | `A` | NOTAM series |
| `number` | `6550` | NOTAM number |
| `year` | `25` | Year (20YY) |
| `description` | Full text | Complete NOTAM description |
| `start_validity` | `2025-08-15 11:38:00` | When NOTAM becomes active |
| `end_validity` | `2025-12-31 23:59:00` | When NOTAM expires (or "PERM") |
| `coordinates` | `5120N00024W` | Raw coordinate string |
| `latitude` | `51.333` | Decimal latitude |
| `longitude` | `-0.4` | Decimal longitude |
| `radius_nm` | `5.0` | Affected radius in nautical miles |

## Example Automations

### Notify When New NOTAM for Heathrow

```yaml
automation:
  - alias: "Alert on Heathrow NOTAM"
    trigger:
      - platform: event
        event_type: state_changed
    condition:
      - condition: template
        value_template: >
          {{ trigger.event.data.entity_id.startswith('sensor.notam_egll_') }}
      - condition: template
        value_template: >
          {{ trigger.event.data.old_state is none }}
    action:
      - service: notify.mobile_app
        data:
          title: "New Heathrow NOTAM"
          message: >
            {{ state_attr(trigger.event.data.entity_id, 'aerodrome_name') }}: 
            {{ states(trigger.event.data.entity_id) }}
```

### Dashboard Card Showing Active NOTAMs

```yaml
type: entities
title: Active NOTAMs
entities:
  - sensor.notam_egll_a6550_25
  - sensor.notam_egll_b2130_25
  - sensor.notam_egkk_c1234_25
show_header_toggle: false
```

### Filter NOTAMs by Aerodrome in Template

```yaml
{% set heathrow_notams = states.sensor 
  | selectattr('entity_id', 'search', 'notam_')
  | selectattr('attributes.aerodrome_code', 'eq', 'EGLL')
  | list %}

{{ heathrow_notams | count }} active NOTAMs for Heathrow
```

## Data Source

This integration fetches data from the UK NATS PIB XML feed:
`https://nats-uk.ead-it.com/cms-nats/export/html/en/pib-adhp-en-GB.xml`

The feed is updated regularly and contains NOTAMs for UK airspace.

## Filtering Logic

### Aerodrome Filtering

NOTAMs are matched by their `aerodrome_code` (ItemA field), NOT the issuing office (NOF field).

Example:
- You configure: `EGLL` (Heathrow)
- NOTAM has: `aerodrome_code: EGLL`, `nof: EGGN`
- ✅ **Match** - NOTAM is about EGLL

### Coordinate Filtering

NOTAMs are matched if their center point falls within your configured radius:
- Your center: `(52.5111, -2.6876)` with `range_nm: 50`
- NOTAM center: `(52.45, -1.75)` with `radius_nm: 5`
- Distance calculated using Haversine formula
- ✅ **Match** if distance ≤ (your range + NOTAM radius)

### Combined Filtering

If you configure both `aerodromes` and `coordinates`:
- NOTAMs are included if they match **either** filter
- OR logic, not AND

## Troubleshooting

### No sensors appearing

1. Check Home Assistant logs for errors
2. Verify your configuration:
   - `aerodromes` uses ICAO codes (4 letters, uppercase)
   - At least one filter (`aerodromes` or `coordinates`) is configured
3. Check if NOTAMs exist for your aerodromes:
   - Look for log messages: `Sample NOTAM X: aerodrome=EGXX`
   - Not all aerodromes have active NOTAMs at all times

### Old sensors not removed

Sensors are automatically removed when:
- NOTAM expires or is withdrawn
- Integration is restarted

If old sensors persist:
1. Restart Home Assistant
2. Check Developer Tools → Statistics for orphaned entities
3. Manually remove via Settings → Devices & Services → Entities

### Aerodrome names missing

Check logs for: `Parsed X aerodromes from aerodrome list`

If X = 0, the XML feed doesn't include an AerodromeList element. The integration will still work, but `aerodrome_name` attribute will be missing.

### Translation errors in config UI

These are harmless and have been fixed in v3.0.1+. Update to the latest version.

## Version History

See [CHANGELOG.md](CHANGELOG.md) for detailed version history.

### Recent Changes

**v3.0.1** - Bug fixes for aerodrome names, old sensor cleanup  
**v3.0.0** - Major update with aerodrome terminology, validity dates, auto-cleanup  
**v2.2.2** - Config flow fixes, deprecation warnings resolved

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

- **Issues:** [GitHub Issues](https://github.com/USERNAME/ha-notam/issues)
- **Discussions:** [GitHub Discussions](https://github.com/USERNAME/ha-notam/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This integration is for informational purposes only. Always check official NOTAM sources before flight planning. The author is not responsible for any decisions made based on data from this integration.

## Credits

- Data source: [NATS UK](https://nats-uk.ead-it.com/)
- Integration developed for Home Assistant community
- Thanks to all contributors!

---

**Note:** Replace `USERNAME` in URLs with your actual GitHub username when publishing to GitHub.
