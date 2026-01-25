# NOTAM Integration - Fixed Version 3.0.3

## 📦 What You Have

Your fixed NOTAM integration is ready in the `notam` folder with the following corrections:

### Issues Fixed ✅

1. **Aerodromes not saving in config UI** - Now properly parses "EGMC,EGLL" format
2. **Old coordinates persisting** - Configuration rebuilt from scratch, no leftover -54 coords
3. **Config flow validation** - Ensures at least one filter is configured
4. **Enhanced logging** - See exactly what configuration is being used

## 🚀 Installation Steps

### Step 1: Backup Current Config (Optional)
```bash
cp -r /config/custom_components/notam /config/custom_components/notam.backup
```

### Step 2: Install Fixed Version
Copy the `notam` folder to your Home Assistant:
```bash
cp -r notam /config/custom_components/
```

### Step 3: Restart Home Assistant
```bash
# Via UI: Settings → System → Restart
# Or via CLI:
ha core restart
```

### Step 4: Reconfigure Integration
1. Go to **Settings → Devices & Services**
2. Find **NOTAM** integration
3. Click **Configure**
4. Enter your aerodromes: `EGMC,EGLL` (or whatever you want)
5. **Save**

### Step 5: Verify Configuration
Check your logs (Settings → System → Logs):

**Search for:** `NOTAM Integration Setup`

**You should see:**
```
============================================================
NOTAM Integration Setup - Config Entry ID: abc123...
Full config entry data: {'aerodromes': ['EGMC', 'EGLL'], ...}
============================================================
Parsed configuration:
  Aerodromes: ['EGMC', 'EGLL']
  Coordinate areas count: 0
  Refresh interval: 60 minutes
```

## 🎯 What Changed

### config_flow.py
- **Rewrote `NotamOptionsFlow.async_step_init()`** - Builds config from scratch, no more copying old data
- **Fixed `async_step_coordinates()`** - Properly merges coordinate config with base settings
- **Added validation** - Checks for at least one filter before saving

### __init__.py  
- **Enhanced logging** - Shows full config, parsed values, detailed coordinate info
- **Added CONF_COORD_AREAS constant** - For consistency
- **Improved coordinate lookup** - Checks multiple key names for backward compatibility

### strings.json & translations/en.json
- **Added "no_filters" error** - Clear message when neither aerodromes nor coords configured

## 🧪 Quick Test

After installing, try this:

1. **Configure:** `EGMC,EGLL` as aerodromes
2. **Check logs:** Should show `['EGMC', 'EGLL']`
3. **No coordinates:** Should show `Coordinate areas count: 0`

If you see coordinates you didn't configure (like -54), the old data is still cached. Solution:
1. Delete the integration completely
2. Restart Home Assistant  
3. Re-add with fresh configuration

## 📁 Files in This Package

```
notam/
├── __init__.py           ✏️ MODIFIED - Added logging
├── config_flow.py        ✏️ MODIFIED - Fixed options flow
├── sensor.py             ✓ No changes needed
├── parser.py             ✓ No changes needed
├── manifest.json         ✏️ MODIFIED - Version 3.0.3
├── strings.json          ✏️ MODIFIED - Added errors
├── translations/
│   └── en.json          ✏️ MODIFIED - Added errors
├── CHANGELOG_v3.0.3.md  📄 NEW - Version history
└── [documentation files]
```

## 📋 Configuration Reference

### Aerodromes Only
```yaml
# In UI config:
Aerodromes: EGMC,EGLL,EGKK
Modify coordinates: [ ] (unchecked)
```

### Coordinates Only
```yaml
# In UI config:
Aerodromes: (blank)
Modify coordinates: [x] (checked)
# Then enter lat/lon/range
```

### Both
```yaml
# In UI config:
Aerodromes: EGMC,EGLL
Modify coordinates: [x] (checked)
# Then enter lat/lon/range
```

## ❓ Troubleshooting

### Problem: Aerodromes still blank after saving
**Solution:** Make sure you're using valid 4-letter ICAO codes (EGLL not egll, no spaces)

### Problem: Old coordinates still appear
**Solution:** 
1. Delete integration (Settings → Devices & Services → NOTAM → Delete)
2. Restart Home Assistant
3. Re-add integration with fresh config

### Problem: No sensors appearing
**Solution:** Check logs for "matched filters" - you may need active NOTAMs for your aerodromes

### Problem: Integration won't reload after config change
**Solution:** Restart Home Assistant completely

## 🔍 Useful Log Commands

```bash
# See configuration being used
grep "NOTAM Integration Setup" /config/home-assistant.log -A 10

# See NOTAMs found
grep "Fetched NOTAM data" /config/home-assistant.log

# See filtering decisions  
grep "NOTAM aerodrome" /config/home-assistant.log
```

## 📊 Expected Results

After configuration, you should see:
- ✅ Sensor entities: `sensor.notam_egmc_a1234_25`, etc.
- ✅ Global sensors: `sensor.notam_issued`, `sensor.notam_valid_from`, `sensor.notam_valid_to`
- ✅ Log message: "Fetched NOTAM data: X matching NOTAMs"

## 🆘 Still Having Issues?

If you're still experiencing problems:

1. **Check you copied all files** - Especially translations/en.json
2. **Clear browser cache** - Sometimes UI forms cache old data
3. **Check entity registry** - Old entities might be sticking around
4. **Share logs** - The new detailed logging will help diagnose issues

## 📚 Documentation

- `FIXES_APPLIED.md` - Detailed explanation of all fixes
- `QUICK_FIX_REFERENCE.md` - Quick troubleshooting guide
- `CHANGELOG_v3.0.3.md` - Version history
- `README.md` - Full integration documentation

## ✨ What's Next?

Once you confirm this is working, let me know if you need:
- Additional features (e.g., showing current coordinates in UI)
- More filtering options
- Better coordinate management
- Anything else!

---

**Version:** 3.0.3  
**Status:** Ready to install  
**Breaking Changes:** None  
**Migration Required:** No

**Installation Location:** `/mnt/user-data/outputs/notam/`

Enjoy your fixed NOTAM integration! 🛫
