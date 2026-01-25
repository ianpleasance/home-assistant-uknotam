# NOTAM Integration - File Index

## 📁 Complete File List

### Core Integration Files (Required)

| File | Size | Purpose |
|------|------|---------|
| `__init__.py` | 4.3 KB | Main integration setup, coordinator, config validation |
| `sensor.py` | 7.5 KB | Sensor entity definitions (global + per-NOTAM) |
| `parser.py` | 5.7 KB | XML parsing, coordinate calculations, Haversine distance |
| `manifest.json` | 223 B | Integration metadata for Home Assistant |
| `strings.json` | 269 B | UI strings for integration display |

### Documentation Files

| File | Size | Purpose |
|------|------|---------|
| `README.md` | 5.5 KB | Complete feature documentation and usage guide |
| `INSTALLATION.md` | 5.7 KB | Step-by-step installation and troubleshooting |
| `QUICKREF.md` | 3.9 KB | Quick reference card for common tasks |
| `PROJECT_SUMMARY.md` | 7.7 KB | Technical project overview and requirements |
| `CHANGELOG.md` | 4.4 KB | Version history and future roadmap |
| `MULTIPLE_COORDINATES_FEATURE.md` | NEW | Multiple coordinate areas feature guide (v1.1.0) |

### Configuration Examples

| File | Size | Purpose |
|------|------|---------|
| `example_config.yaml` | 1.1 KB | Sample configurations for various use cases |

---

## 📋 Quick Navigation

### For Installation
1. **Start here:** `INSTALLATION.md`
2. **Reference:** `README.md`
3. **Quick lookup:** `QUICKREF.md`
4. **Config examples:** `example_config.yaml`

### For Development
1. **Overview:** `PROJECT_SUMMARY.md`
2. **Code structure:** `__init__.py`, `sensor.py`, `parser.py`
3. **Changes:** `CHANGELOG.md`

### For Users
1. **How to use:** `README.md`
2. **Setup guide:** `INSTALLATION.md`
3. **Quick tips:** `QUICKREF.md`
4. **Examples:** `example_config.yaml`

---

## 🏗️ Architecture Overview

```
NOTAM Integration
│
├── Configuration Layer (configuration.yaml)
│   ├── Airfield codes (ICAO)
│   ├── Coordinates (lat/lon/range)
│   └── Refresh interval
│
├── Data Layer (__init__.py + parser.py)
│   ├── HTTP fetch (NATS XML feed)
│   ├── XML parsing
│   ├── Coordinate conversion
│   ├── Distance calculation (Haversine)
│   └── Circle intersection detection
│
└── Entity Layer (sensor.py)
    ├── Global sensors (3)
    │   ├── sensor.notam_validfrom
    │   ├── sensor.notam_validto
    │   └── sensor.notam_issued
    │
    └── NOTAM sensors (dynamic)
        └── sensor.<code>_<series>_<number>_<year>
```

---

## 🔍 Key Components Explained

### __init__.py (Main Integration)
- **NOTAMDataUpdateCoordinator**: Manages periodic data fetching
- **async_setup()**: Validates config and initializes integration
- **Configuration schema**: Voluptuous validation
- **Error handling**: Logs errors, aborts on invalid config

### parser.py (Data Processing)
- **parse_notam_xml()**: Main XML parsing entry point
- **_parse_coordinates()**: Converts `5408N00316W` → lat/lon
- **_haversine_distance()**: Great-circle distance calculation
- **_should_include_notam()**: Filtering logic (airfield + coordinate)
- **_format_datetime()**: ISO 8601 → `YYYY-MM-DD HH:MM:SS`

### sensor.py (Entities)
- **NOTAMGlobalSensor**: Valid from/to/issued sensors (3 instances)
- **NOTAMSensor**: Per-NOTAM dynamic sensors
- **Dynamic management**: Add/remove entities as data changes
- **State management**: ItemE text as state, metadata as attributes

### manifest.json
- Domain: `notam`
- Version: `1.0.0`
- IoT class: `cloud_polling`
- No external dependencies

---

## 📊 Statistics

### Code Metrics
- **Total lines:** ~1,320
- **Python files:** 3 (17.5 KB total)
- **Documentation:** 5 files (27.2 KB total)
- **Configuration:** 2 files (1.5 KB total)

### Complexity
- **Functions:** ~20
- **Classes:** 3 (1 coordinator, 2 sensor types)
- **Configuration options:** 4
- **Entity types:** 2 (global + per-NOTAM)

### Coverage
- ✅ XML parsing
- ✅ Coordinate math
- ✅ Configuration validation
- ✅ Error handling
- ✅ Entity lifecycle
- ✅ State management
- ✅ Attribute population

---

## 🎯 What Each File Does

### Core Logic
1. **manifest.json** → Tells HA about the integration
2. **__init__.py** → Loads config, creates coordinator, fetches data
3. **parser.py** → Parses XML, calculates distances, filters NOTAMs
4. **sensor.py** → Creates entities, updates states, manages attributes
5. **strings.json** → Provides UI-friendly names

### Documentation
1. **README.md** → Complete user documentation
2. **INSTALLATION.md** → Step-by-step setup guide
3. **QUICKREF.md** → Fast reference for common tasks
4. **PROJECT_SUMMARY.md** → Technical overview
5. **CHANGELOG.md** → Version history

### Examples
1. **example_config.yaml** → Real-world configuration patterns

---

## 🚀 Installation Path

```
Download → Copy to custom_components/ → Configure YAML → Restart HA → Verify
```

**Destination:** `/config/custom_components/notam/`

**Files needed:** All Python files + manifest.json + strings.json

**Optional:** All .md files (for reference)

---

## 📖 Reading Order

### For First-Time Users
1. README.md (overview)
2. INSTALLATION.md (setup)
3. example_config.yaml (configuration)
4. QUICKREF.md (quick tips)

### For Developers
1. PROJECT_SUMMARY.md (technical overview)
2. __init__.py (integration setup)
3. parser.py (data processing)
4. sensor.py (entity creation)
5. CHANGELOG.md (version info)

### For Troubleshooting
1. INSTALLATION.md (troubleshooting section)
2. README.md (common issues)
3. QUICKREF.md (checklist)
4. Home Assistant logs

---

## ✨ Features at a Glance

| Feature | Implemented | File |
|---------|-------------|------|
| XML fetch | ✅ | __init__.py |
| XML parse | ✅ | parser.py |
| Coordinate parse | ✅ | parser.py |
| Haversine distance | ✅ | parser.py |
| Circle intersection | ✅ | parser.py |
| Airfield filter | ✅ | parser.py |
| Single coordinate filter | ✅ | parser.py |
| **Multiple coordinate areas** | ✅ **NEW** | parser.py |
| Global sensors | ✅ | sensor.py |
| NOTAM sensors | ✅ | sensor.py |
| Dynamic entities | ✅ | sensor.py |
| Config validation | ✅ | __init__.py |
| Error handling | ✅ | All files |
| Documentation | ✅ | .md files |

---

## 🎁 What You Get

A complete, production-ready Home Assistant integration that:
- Monitors UK NOTAMs in real-time
- Filters by location or airport
- Creates individual sensors for each NOTAM
- Updates automatically on your schedule
- Provides rich data for automations
- Includes comprehensive documentation
- Follows HA best practices
- Requires no external dependencies

---

## 📞 Next Steps

1. **Install:** Follow INSTALLATION.md
2. **Configure:** Use example_config.yaml
3. **Verify:** Check Developer Tools → States
4. **Automate:** Create automations with NOTAM sensors
5. **Enjoy:** Monitor airspace from Home Assistant!

---

**Total Package Size:** ~46 KB (all files)  
**Installation Time:** ~5 minutes  
**Complexity:** Low (YAML configuration only)  
**Maintenance:** Self-contained, no dependencies
