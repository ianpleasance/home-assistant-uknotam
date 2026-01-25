# NOTAM Integration - Installation Guide

## Quick Start

### Step 1: Install the Integration

1. **Create the custom_components directory** (if it doesn't exist):
   ```
   mkdir -p /config/custom_components/
   ```

2. **Copy the notam folder** to custom_components:
   ```
   /config/custom_components/notam/
   ```

   Your directory structure should look like:
   ```
   /config/
   ├── custom_components/
   │   └── notam/
   │       ├── __init__.py
   │       ├── manifest.json
   │       ├── parser.py
   │       ├── sensor.py
   │       ├── strings.json
   │       └── README.md
   └── configuration.yaml
   ```

### Step 2: Configure in configuration.yaml

Add one of these configurations to your `configuration.yaml`:

**Option A: Monitor specific airports**
```yaml
notam:
  airfields:
    - "EGLL"  # London Heathrow
    - "EGKK"  # London Gatwick
  refresh_interval: 60
```

**Option B: Monitor single geographic area**
```yaml
notam:
  coordinates:
    latitude: 51.4700
    longitude: -0.4543
    range_nm: 50
  refresh_interval: 60
```

**Option C: Monitor multiple geographic areas (NEW!)**
```yaml
notam:
  coordinates:
    - latitude: 51.4700   # London area
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537   # Manchester area
      longitude: -2.2750
      range_nm: 30
  refresh_interval: 60
```

**Option D: Combined - airports and multiple areas**
```yaml
notam:
  airfields:
    - "EGLL"
  coordinates:
    - latitude: 51.4700   # London area
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537   # Manchester area
      longitude: -2.2750
      range_nm: 30
  refresh_interval: 120
```

### Step 3: Restart Home Assistant

Restart Home Assistant to load the integration:
- Configuration → Server Controls → Restart

or use the command:
```
ha core restart
```

### Step 4: Verify Installation

1. **Check the logs** for any errors:
   - Go to Configuration → Logs
   - Look for entries containing "notam"

2. **Check for entities**:
   - Go to Developer Tools → States
   - Filter for "notam"
   - You should see:
     - `sensor.notam_validfrom`
     - `sensor.notam_validto`
     - `sensor.notam_issued`
     - `sensor.<code>_<series>_<number>_<year>` (one per matching NOTAM)

## Troubleshooting

### Integration not loading

**Problem:** No NOTAM entities appear

**Solutions:**
1. Check configuration.yaml syntax:
   ```yaml
   # Valid:
   notam:
     airfields:
       - "EGLL"
   
   # Invalid (missing quotes):
   notam:
     airfields:
       - EGLL
   ```

2. Verify you have either `airfields` or `coordinates` configured

3. Check Home Assistant logs for errors

### No matching NOTAMs

**Problem:** Global sensors exist but no NOTAM sensors

**Possible causes:**
1. No active NOTAMs match your filters
2. ICAO codes are incorrect (must be 4 letters)
3. Geographic range is too small
4. All NOTAMs in your area have expired

**Solutions:**
1. Verify ICAO codes are correct (e.g., "EGLL" not "LHR")
2. Increase geographic range
3. Check the NATS feed directly: https://pibs.nats.co.uk/operational/pibs/PIB.xml

### XML parsing errors

**Problem:** Errors in logs about XML parsing

**Solutions:**
1. Check your internet connection
2. Verify the NATS feed is accessible: https://pibs.nats.co.uk/operational/pibs/PIB.xml
3. Wait a few minutes and restart (feed might be temporarily unavailable)

### Entities disappear

**This is normal behavior:**
- NOTAMs expire regularly
- When a NOTAM expires and is removed from the feed, its sensor will keep the last known state
- New sensors are automatically created when new matching NOTAMs appear

## Advanced Configuration

### Multiple regions

You can only configure one `notam:` section, but you can include multiple airfields and/or a large geographic area:

```yaml
notam:
  airfields:
    - "EGLL"  # London
    - "EGCC"  # Manchester
    - "EGPF"  # Glasgow
    - "EGPH"  # Edinburgh
  coordinates:
    latitude: 53.0  # Center of UK
    longitude: -2.0
    range_nm: 200  # Cover most of UK
  refresh_interval: 60
```

### Refresh interval tuning

- **Default:** 60 minutes
- **Minimum recommended:** 15 minutes (to avoid overloading the NATS server)
- **For real-time monitoring:** 15-30 minutes
- **For occasional checking:** 120-240 minutes

```yaml
notam:
  airfields:
    - "EGLL"
  refresh_interval: 15  # Update every 15 minutes
```

## Automation Examples

### Alert on new NOTAM

```yaml
automation:
  - alias: "Alert on new NOTAM at Heathrow"
    trigger:
      - platform: state
        entity_id: sensor.egll_*
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state != trigger.from_state.state }}"
    action:
      - service: notify.mobile_app
        data:
          title: "New NOTAM"
          message: "{{ trigger.to_state.attributes.friendly_name }}: {{ trigger.to_state.state[:100] }}..."
```

### Dashboard card

```yaml
type: entities
title: Active NOTAMs
entities:
  - entity: sensor.notam_validfrom
    name: Valid From
  - entity: sensor.notam_validto
    name: Valid To
  - entity: sensor.notam_issued
    name: Issued
  - type: divider
  - entity: sensor.egll_a_1234_24
    name: Heathrow NOTAM
```

### Count NOTAMs template

```yaml
sensor:
  - platform: template
    sensors:
      notam_count:
        friendly_name: "Active NOTAMs"
        value_template: >-
          {{ states.sensor 
             | selectattr('entity_id', 'match', 'sensor\\.eg[a-z]{2}_.*') 
             | list 
             | count }}
        icon_template: mdi:airplane-alert
```

## Support

For issues or questions:
1. Check the logs in Configuration → Logs
2. Verify your configuration matches the examples
3. Check the NATS feed is accessible
4. Open an issue on GitHub with:
   - Your configuration (remove sensitive data)
   - Relevant log entries
   - Home Assistant version

## Data Source

This integration uses the official NATS (UK National Air Traffic Services) Pre-flight Information Bulletin XML feed:
- URL: https://pibs.nats.co.uk/operational/pibs/PIB.xml
- Public feed, no authentication required
- Updates regularly throughout the day
