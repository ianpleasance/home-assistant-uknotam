# Multiple Coordinate Areas - Feature Update

## Overview

Version 1.1.0 adds support for **multiple coordinate areas** while maintaining full backward compatibility with the existing single coordinate configuration.

## What Changed

### Before (v1.0.0)
You could only monitor **one** geographic area:

```yaml
notam:
  coordinates:
    latitude: 51.4700
    longitude: -0.4543
    range_nm: 50
```

### After (v1.1.0)
You can now monitor **multiple** geographic areas simultaneously:

```yaml
notam:
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
```

## Benefits

✅ **Monitor multiple regions** without separate integrations  
✅ **Cover flight paths** with multiple waypoint areas  
✅ **Flexible coverage** - different ranges for different areas  
✅ **Backward compatible** - existing configs still work  
✅ **OR logic** - NOTAM included if it matches ANY area

## Use Cases

### Flight Path Monitoring
```yaml
notam:
  coordinates:
    - latitude: 51.1537   # Departure
      longitude: -0.1821
      range_nm: 25
    - latitude: 52.3555   # Mid-route
      longitude: 0.1750
      range_nm: 25
    - latitude: 53.3537   # Arrival
      longitude: -2.2750
      range_nm: 25
```

### Regional Coverage
```yaml
notam:
  coordinates:
    - latitude: 51.5074   # Southeast England
      longitude: -0.1278
      range_nm: 60
    - latitude: 53.4808   # Northwest England
      longitude: -2.2426
      range_nm: 60
    - latitude: 55.8642   # Scotland
      longitude: -4.2518
      range_nm: 60
```

### Combined with Airfields
```yaml
notam:
  airfields:
    - "EGLL"  # Explicitly include Heathrow
    - "EGCC"  # Explicitly include Manchester
  coordinates:
    - latitude: 51.4700   # Plus London area
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537   # Plus Manchester area
      longitude: -2.2750
      range_nm: 30
```

## How It Works

### Filtering Logic

A NOTAM is included if **any** of these conditions are true:
1. Its ICAO code matches a configured airfield
2. Its coordinate circle intersects with **any** configured coordinate area

### Example

Configuration:
```yaml
coordinates:
  - latitude: 51.47     # Area 1: London (50 NM)
    longitude: -0.45
    range_nm: 50
  - latitude: 53.35     # Area 2: Manchester (30 NM)
    longitude: -2.27
    range_nm: 30
```

NOTAM at Gatwick (51.15°N, 0.18°W, 5 NM radius):
- Distance to Area 1: ~28 NM
- Check: 28 ≤ (50 + 5) = 55 ✅ **MATCH**
- Result: NOTAM is included

NOTAM at Liverpool (53.33°N, 2.85°W, 3 NM radius):
- Distance to Area 1: ~180 NM ❌ No match
- Distance to Area 2: ~25 NM
- Check: 25 ≤ (30 + 3) = 33 ✅ **MATCH**
- Result: NOTAM is included

## Technical Changes

### Files Modified

1. **`__init__.py`**
   - Schema accepts both `dict` and `list[dict]`
   - Normalizes single dict to list internally
   - Type hint updated: `list[dict[str, Any]] | None`

2. **`parser.py`**
   - `parse_notam_xml()` accepts `list[dict]`
   - `_should_include_notam()` loops through all coordinate areas
   - Returns `True` if NOTAM matches ANY area

3. **Documentation**
   - README.md updated with examples
   - INSTALLATION.md updated with multiple area options
   - QUICKREF.md updated
   - PROJECT_SUMMARY.md updated
   - CHANGELOG.md documents the feature
   - example_config.yaml expanded

4. **Version**
   - manifest.json: `1.0.0` → `1.1.0`

### Backward Compatibility

✅ **Fully backward compatible**

Old configuration (single dict):
```yaml
notam:
  coordinates:
    latitude: 51.4700
    longitude: -0.4543
    range_nm: 50
```

This is **automatically converted** to:
```yaml
notam:
  coordinates:
    - latitude: 51.4700
      longitude: -0.4543
      range_nm: 50
```

No configuration changes required for existing users.

## Configuration Validation

Both formats are valid:

### Single Area (backward compatible)
```yaml
notam:
  coordinates:
    latitude: 51.4700
    longitude: -0.4543
    range_nm: 50
```

### Multiple Areas (new feature)
```yaml
notam:
  coordinates:
    - latitude: 51.4700
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537
      longitude: -2.2750
      range_nm: 30
```

Both pass validation and work correctly.

## Performance Impact

**Minimal to none:**
- Additional coordinate areas add minimal processing time
- Each NOTAM is checked against each area (simple distance calculation)
- With 3 areas and 50 NOTAMs: ~150 distance calculations per refresh
- Haversine calculation is highly optimized (simple math operations)
- No noticeable performance impact expected

## Migration

**No migration required!**

Your existing configuration continues to work exactly as before. The single coordinate dict format is automatically handled.

If you want to use multiple areas:
1. Change `coordinates:` value from dict to list of dicts
2. Add more coordinate areas as needed
3. Restart Home Assistant

That's it!

## Testing Recommendations

1. **Test single area (backward compatibility)**
   ```yaml
   notam:
     coordinates:
       latitude: 51.4700
       longitude: -0.4543
       range_nm: 50
   ```
   Expected: Works exactly as before

2. **Test multiple areas**
   ```yaml
   notam:
     coordinates:
       - latitude: 51.4700
         longitude: -0.4543
         range_nm: 50
       - latitude: 53.3537
         longitude: -2.2750
         range_nm: 30
   ```
   Expected: NOTAMs from both areas appear

3. **Test combined filtering**
   ```yaml
   notam:
     airfields:
       - "EGLL"
     coordinates:
       - latitude: 51.4700
         longitude: -0.4543
         range_nm: 50
       - latitude: 53.3537
         longitude: -2.2750
         range_nm: 30
   ```
   Expected: NOTAMs from EGLL + both coordinate areas

## Examples in Config File

See `example_config.yaml` for complete working examples:
- Example 3: Multiple coordinate areas
- Example 4: Combined airfields + multiple areas
- Example 6: Monitor flight path with multiple waypoints
- Example 7: Comprehensive UK coverage

## Summary

**Version:** 1.1.0  
**Feature:** Multiple coordinate area support  
**Breaking Changes:** None  
**Migration Required:** No  
**Performance Impact:** Minimal  
**Documentation:** Fully updated  

This enhancement provides significantly more flexibility in monitoring NOTAMs across multiple geographic regions while maintaining complete backward compatibility with existing configurations.
