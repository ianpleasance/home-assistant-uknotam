# NOTAM Integration v2.0 - UI Configuration Guide

## 🎉 What's New in v2.0

**UI-Based Setup!** You can now configure the NOTAM integration through the Home Assistant user interface instead of editing `configuration.yaml`.

### Key Features

✅ **Graphical configuration** - No YAML editing required  
✅ **Step-by-step wizard** - Guided setup process  
✅ **Options flow** - Reconfigure anytime through UI  
✅ **Multiple coordinate areas** - Add as many as you want  
✅ **Backward compatible** - YAML config still works (auto-imports)  

---

## 🚀 Quick Start (UI Method)

### Step 1: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ ADD INTEGRATION**
3. Search for **"NOTAM"**
4. Click on **NOTAM**

### Step 2: Configure Filters

You'll see the configuration form:

**Airfield Codes (optional):**
- Enter ICAO codes separated by commas
- Example: `EGLL, EGKK, EGSS`

**Add Coordinate Areas (optional):**
- Check this box to add geographic filtering

**Refresh Interval:**
- How often to check for updates (minutes)
- Default: 60 minutes

⚠️ **You must provide either airfields OR coordinates**

Click **SUBMIT**

### Step 3: Add Coordinate Areas (if selected)

If you checked "Add coordinate areas", you'll see:

**Latitude:** Decimal degrees (e.g., 51.4700)  
**Longitude:** Decimal degrees (e.g., -0.4543)  
**Range (NM):** Radius in nautical miles (e.g., 50)  

**Add another coordinate area:**
- Check this to add more areas
- Uncheck when done

Click **SUBMIT**

### Step 4: Done!

The integration is now set up and your sensors will appear in:
- **Developer Tools** → **States**
- Look for `sensor.notam_*`

---

## 📋 Configuration Examples

### Example 1: Airfields Only

1. Add integration
2. Enter airfields: `EGLL, EGKK`
3. Leave "Add coordinate areas" unchecked
4. Submit

**Result:** Monitors Heathrow and Gatwick

### Example 2: Single Coordinate Area

1. Add integration
2. Leave airfields blank
3. Check "Add coordinate areas"
4. Submit
5. Enter: Lat 51.4700, Lon -0.4543, Range 50
6. Leave "Add another" unchecked
7. Submit

**Result:** Monitors 50 NM around London

### Example 3: Multiple Coordinate Areas

1. Add integration
2. Leave airfields blank
3. Check "Add coordinate areas"
4. Submit
5. **First area:** Lat 51.4700, Lon -0.4543, Range 50
6. **Check "Add another"**
7. Submit
8. **Second area:** Lat 53.3537, Lon -2.2750, Range 30
9. **Check "Add another"**
10. Submit
11. **Third area:** Lat 55.9533, Lon -3.1883, Range 40
12. **Uncheck "Add another"**
13. Submit

**Result:** Monitors London, Manchester, and Edinburgh areas

### Example 4: Combined (Airfields + Coordinates)

1. Add integration
2. Enter airfields: `EGLL`
3. Check "Add coordinate areas"
4. Submit
5. Add coordinate areas as desired
6. Submit

**Result:** Monitors Heathrow + coordinate areas

---

## 🔧 Reconfiguring (Options Flow)

To change your configuration later:

1. Go to **Settings** → **Devices & Services**
2. Find **NOTAM** integration
3. Click **CONFIGURE**
4. Update settings:
   - Change airfield codes
   - Change refresh interval
   - Check "Modify coordinates" to replace coordinate areas
5. Click **SUBMIT**

**Note:** When modifying coordinates, you must re-add all areas (they're replaced, not edited).

---

## 🆚 UI vs YAML Configuration

### UI Method (Recommended)

**Pros:**
- ✅ No file editing
- ✅ Guided setup
- ✅ Can reconfigure anytime
- ✅ Validates input immediately
- ✅ User-friendly

**Cons:**
- ❌ Must add coordinate areas one at a time

### YAML Method (Still Supported)

**Pros:**
- ✅ All config in one place
- ✅ Easy to add many coordinate areas at once
- ✅ Version control friendly

**Cons:**
- ❌ Must edit files
- ❌ Requires Home Assistant restart
- ❌ Manual syntax validation

**YAML config is automatically imported to UI config flow**

---

## 📝 YAML Configuration (Legacy)

If you prefer YAML, you can still use it. Add to `configuration.yaml`:

```yaml
notam:
  airfields:
    - "EGLL"
    - "EGKK"
  coordinates:
    - latitude: 51.4700
      longitude: -0.4543
      range_nm: 50
    - latitude: 53.3537
      longitude: -2.2750
      range_nm: 30
  refresh_interval: 60
```

**After restart**, this will automatically import into the UI as a config entry.

---

## 🎯 UI Field Descriptions

### Initial Setup Screen

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **ICAO Airfield Codes** | Text | No* | Comma-separated 4-letter codes (e.g., EGLL, EGKK) |
| **Add coordinate areas** | Checkbox | No | Check to enable geographic filtering |
| **Refresh Interval** | Number | Yes | Minutes between updates (default: 60) |

*At least one of airfields or coordinates required

### Coordinate Area Screen

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **Latitude** | Number | Yes | Decimal degrees (-90 to 90) |
| **Longitude** | Number | Yes | Decimal degrees (-180 to 180) |
| **Range (NM)** | Number | Yes | Radius in nautical miles (>0) |
| **Add another area** | Checkbox | No | Check to add more areas |

---

## ⚠️ Common Issues

### "Must provide either airfields or coordinates"

**Problem:** You didn't enter any airfields and didn't check "Add coordinate areas"

**Solution:** 
- Enter at least one airfield code, OR
- Check "Add coordinate areas" box

### "Invalid ICAO code format"

**Problem:** Airfield codes must be exactly 4 letters

**Solutions:**
- ✅ Correct: `EGLL, EGKK, EGSS`
- ❌ Wrong: `LHR, GATWICK, LONDON`
- ❌ Wrong: `EGL, EGKK1, EG-LL`

### "Failed to connect to NATS feed"

**Problem:** Cannot reach https://pibs.nats.co.uk/operational/pibs/PIB.xml

**Solutions:**
- Check internet connection
- Wait a few minutes and try again
- Verify NATS feed is accessible

### "Range must be greater than 0"

**Problem:** You entered 0 or negative range

**Solution:** Enter a positive number (e.g., 50)

---

## 🔄 Migration from v1.x

### If Using YAML Config

**Your config will automatically import!**

1. Install v2.0
2. Restart Home Assistant
3. Your YAML config imports to UI
4. Integration works as before

You can:
- Keep YAML config (still works)
- Remove YAML and use UI only
- Mix both (not recommended)

### If Want to Switch to UI

1. Note your current YAML configuration
2. Remove `notam:` section from configuration.yaml
3. Restart Home Assistant
4. Add integration through UI
5. Configure using your noted settings

---

## 📊 After Setup

### Verify Installation

1. Go to **Developer Tools** → **States**
2. Filter for `notam`
3. You should see:
   - `sensor.notam_validfrom`
   - `sensor.notam_validto`
   - `sensor.notam_issued`
   - `sensor.<code>_<series>_<number>_<year>` (per NOTAM)

### Integration Card

The integration appears in **Settings** → **Devices & Services**:

**Title Format:**
- Airfields only: `NOTAM: EGLL, EGKK`
- Coordinates only: `NOTAM: 3 area(s)`
- Combined: `NOTAM: EGLL + 2 area(s)`

---

## 🎓 Tips & Best Practices

### Adding Many Coordinate Areas

If you need 5+ coordinate areas, consider:
- Using YAML config (faster to type)
- OR being patient with UI (add one at a time)

### Testing Your Config

After setup:
1. Check logs for errors: **Settings** → **System** → **Logs**
2. Verify sensors exist: **Developer Tools** → **States**
3. Wait for first refresh (up to refresh_interval minutes)

### Reconfiguring

**Small changes** (add/remove airfield):
- Use OPTIONS flow (click CONFIGURE)

**Major changes** (completely different areas):
- Remove integration
- Add again with new config

---

## 🆘 Support

**Not working?**
1. Check **Settings** → **System** → **Logs**
2. Look for "notam" entries
3. Common issues usually show here

**Need help?**
- See README.md for detailed documentation
- See INSTALLATION.md for troubleshooting
- Check GitHub issues

---

## 🎉 Summary

**v2.0 adds UI configuration while keeping full YAML support!**

**Recommended Setup Method:**
1. Use UI for initial setup (easier)
2. Use OPTIONS to reconfigure (convenient)
3. Use YAML only if managing many coordinate areas

**Key Advantage:**
No more restarting Home Assistant to change configuration!

---

**Ready to set up?**

1. Settings → Devices & Services
2. Add Integration
3. Search: NOTAM
4. Follow the wizard!
