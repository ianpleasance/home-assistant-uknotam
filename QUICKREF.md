# NOTAM Integration - Quick Reference

## File Structure
```
custom_components/notam/
├── __init__.py           # Main integration setup & coordinator
├── sensor.py            # Sensor entity definitions
├── parser.py            # XML parsing & coordinate calculations
├── manifest.json        # Integration metadata
├── strings.json         # UI strings
├── README.md            # Full documentation
├── INSTALLATION.md      # Installation guide
└── example_config.yaml  # Configuration examples
```

## Minimal Configuration

```yaml
notam:
  airfields:
    - "EGLL"
  refresh_interval: 60
```

## Entities Created

### Always Created (3 sensors)
- `sensor.notam_validfrom`
- `sensor.notam_validto`
- `sensor.notam_issued`

### Per Matching NOTAM
- `sensor.<code>_<series>_<number>_<year>` (e.g., `sensor.egll_a_1234_24`)

## Key Features

✅ Filters by ICAO airfield codes  
✅ Filters by single or multiple coordinate areas (NM)  
✅ Haversine distance calculations  
✅ Circle intersection detection  
✅ Dynamic entity creation/removal  
✅ Configurable refresh interval  
✅ Parses coordinates: `5408N00316W` format  
✅ Converts timestamps: ISO 8601 → `YYYY-MM-DD HH:MM:SS`

## Configuration Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `airfields` | list[str] | No* | - | ICAO codes (4 letters) |
| `coordinates` | dict or list | No* | - | Single or multiple areas |
| `refresh_interval` | int | No | 60 | Minutes between updates |

*At least one required: `airfields` OR `coordinates`

## Coordinate Schema

**Single Area:**
```yaml
coordinates:
  latitude: 51.4700    # Decimal degrees
  longitude: -0.4543   # Decimal degrees
  range_nm: 50         # Nautical miles
```

**Multiple Areas (NEW!):**
```yaml
coordinates:
  - latitude: 51.4700   # London
    longitude: -0.4543
    range_nm: 50
  - latitude: 53.3537   # Manchester
    longitude: -2.2750
    range_nm: 30
```

## Entity State & Attributes

**State:** Full NOTAM text (ItemE field)

**Attributes:**
- `code` - ICAO code
- `series` - NOTAM series
- `number` - NOTAM number
- `year` - NOTAM year
- `radius_nm` - NOTAM radius
- `coordinates` - Raw coordinates
- `latitude` - Parsed latitude
- `longitude` - Parsed longitude

## Common ICAO Codes

| Code | Airport |
|------|---------|
| EGLL | Heathrow |
| EGKK | Gatwick |
| EGSS | Stansted |
| EGGW | Luton |
| EGLC | London City |
| EGCC | Manchester |
| EGPF | Glasgow |
| EGPH | Edinburgh |

## Installation Steps

1. Copy `notam/` folder to `/config/custom_components/`
2. Add config to `configuration.yaml`
3. Restart Home Assistant
4. Check Developer Tools → States for `sensor.notam_*`

## Data Source

**URL:** https://pibs.nats.co.uk/operational/pibs/PIB.xml  
**Provider:** NATS (UK National Air Traffic Services)  
**Type:** Public XML feed, no auth required

## Filtering Logic

### Airfield Match
```
NOTAM.Code == configured_airfield → INCLUDE
```

### Geographic Match
```
For each configured coordinate area:
  distance = haversine(area_coords, notam_coords)
  if distance <= (area_range + notam_radius) → INCLUDE
```
**Result:** NOTAM included if it matches ANY area

## Troubleshooting Checklist

- [ ] Files in `/config/custom_components/notam/`
- [ ] Valid YAML configuration
- [ ] Either `airfields` OR `coordinates` configured
- [ ] ICAO codes are 4 letters in quotes (e.g., `"EGLL"`)
- [ ] Home Assistant restarted after installation
- [ ] Check logs: Configuration → Logs → filter "notam"
- [ ] Verify feed accessible: https://pibs.nats.co.uk/operational/pibs/PIB.xml

## Example Automation

```yaml
automation:
  - alias: "NOTAM Alert"
    trigger:
      platform: state
      entity_id: sensor.egll_*
    action:
      service: notify.mobile_app
      data:
        message: "New NOTAM: {{ trigger.to_state.state[:100] }}"
```

## Performance

- **Refresh interval:** 15-60 minutes recommended
- **Coordinate parsing:** Regex-based, efficient
- **Distance calculations:** Haversine formula (optimized)
- **Entity management:** Dynamic add/remove on updates
- **Memory:** Minimal (XML parsed, not stored)

## Version

**Current:** 1.0.0  
**Home Assistant:** 2023.1+ (uses modern coordinator pattern)  
**Python:** 3.11+ recommended
