# UK NOTAM Integration

Monitor UK NOTAMs (Notices to Airmen) in Home Assistant.

## Features

- ✈️ Track NOTAMs by aerodrome (EGLL, EGSS, EGKK, etc.)
- 📍 Geographic filtering by coordinates and range
- 🔄 Auto-cleanup of expired NOTAMs
- 📅 Validity dates for each NOTAM
- 🏢 Full aerodrome names (e.g., "HEATHROW")

## Quick Start

Add to `configuration.yaml`:

```yaml
notam:
  aerodromes:
    - "EGLL"  # Heathrow
    - "EGKK"  # Gatwick
  coordinates:
    - latitude: 51.4700
      longitude: -0.4543
      range_nm: 50
  refresh_interval: 60
```

## What You Get

Each NOTAM creates a sensor with:
- **Entity ID:** `sensor.notam_egll_a6550_25`
- **State:** NOTAM description
- **Attributes:** Validity dates, coordinates, aerodrome name

## Documentation

See [README.md](https://github.com/USERNAME/ha-notam) for full documentation.

## Data Source

UK NATS PIB (Pre-flight Information Bulletin) XML feed.

## Version

**Current:** v3.0.2  
**Requires:** Home Assistant 2024.1.0+
