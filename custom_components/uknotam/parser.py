"""XML parser for UK NOTAM data."""
import logging
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

_LOGGER = logging.getLogger(__name__)


def parse_notam_xml(
    xml_content: str,
    aerodromes: list[str],
    coordinates: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Parse NOTAM XML and filter based on configuration."""
    # Log configuration
    _LOGGER.debug("Parsing with filters - Aerodromes: %s, Coordinate areas: %s", 
                 aerodromes, len(coordinates) if coordinates else 0)
    if coordinates:
        for idx, coord in enumerate(coordinates):
            _LOGGER.debug("  Area %d: lat=%.4f, lon=%.4f, range=%.1f NM",
                         idx, coord.get("latitude", 0), coord.get("longitude", 0), 
                         coord.get("range_nm", 0))
    
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as err:
        _LOGGER.error("Failed to parse XML: %s", err)
        return {"global": {}, "notams": [], "aerodrome_list": {}}

    # Get namespace if present
    namespace = ""
    if root.tag.startswith("{"):
        namespace = root.tag.split("}")[0] + "}"
        _LOGGER.debug("XML namespace detected: %s", namespace)

    # Parse aerodrome list from header for aerodrome name lookup
    aerodrome_list = {}
    fir_list = {}
    aerodrome_details = []
    
    aerodrome_list_elem = root.find(f".//{namespace}AerodromeList") if namespace else root.find(".//AerodromeList")
    
    if aerodrome_list_elem is not None:
        _LOGGER.debug("Found AerodromeList element")
        
        # Parse each Aerodrome element
        aerodrome_elements = aerodrome_list_elem.findall(f"{namespace}Aerodrome") if namespace else aerodrome_list_elem.findall("Aerodrome")
        
        for aerodrome_elem in aerodrome_elements:
            # Helper to get text from aerodrome element
            def get_aero_text(tag: str) -> str:
                text = aerodrome_elem.findtext(f"{namespace}{tag}", "").strip()
                if not text and namespace:
                    text = aerodrome_elem.findtext(tag, "").strip()
                return text
            
            code = get_aero_text("Code")
            name = get_aero_text("Name")
            city = get_aero_text("CityName")
            iata = get_aero_text("IATA")
            invalid = get_aero_text("Invalid")
            
            if code:
                # Store simple name lookup
                aerodrome_list[code.upper()] = name
                
                # Parse FIRs for this aerodrome
                firs = []
                fir_list_elem = aerodrome_elem.find(f"{namespace}FIRList") or aerodrome_elem.find("FIRList")
                if fir_list_elem is not None:
                    fir_elements = fir_list_elem.findall(f"{namespace}FIR") if namespace else fir_list_elem.findall("FIR")
                    for fir_elem in fir_elements:
                        fir_icao = fir_elem.findtext(f"{namespace}ICAO", "") or fir_elem.findtext("ICAO", "")
                        fir_name = fir_elem.findtext(f"{namespace}Name", "") or fir_elem.findtext("Name", "")
                        if fir_icao:
                            firs.append(fir_icao)
                            # Store FIR in master list
                            if fir_icao not in fir_list:
                                fir_list[fir_icao] = fir_name
                
                # Store detailed aerodrome info
                aerodrome_info = {
                    "code": code,
                    "name": name,
                    "city": city,
                    "firs": firs,
                }
                if iata:
                    aerodrome_info["iata"] = iata
                if invalid and invalid.lower() != "false":
                    aerodrome_info["invalid"] = True
                    
                aerodrome_details.append(aerodrome_info)
        
        _LOGGER.debug("Parsed %d aerodromes and %d FIRs from aerodrome list", 
                     len(aerodrome_list), len(fir_list))
    else:
        _LOGGER.debug("No AerodromeList element found in XML")

    # Parse global data from AreaPIBHeader
    global_data = {}
    
    # Try with namespace first, then without
    header = root.find(f".//{namespace}AreaPIBHeader")
    if header is None:
        header = root.find(".//AreaPIBHeader")
    
    if header is not None:
        _LOGGER.debug("Found AreaPIBHeader element")
        
        # Dump the entire header as XML to see structure
        import xml.etree.ElementTree as ET_debug
        header_xml = ET_debug.tostring(header, encoding='unicode')
        _LOGGER.debug("Full AreaPIBHeader XML (first 1000 chars): %s", header_xml[:1000])
        
        # Log all children to see what fields actually exist
        _LOGGER.debug("AreaPIBHeader children:")
        for child in header:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            text = (child.text[:100] if child.text and len(child.text) > 100 else child.text) if child.text else "(empty)"
            _LOGGER.debug("  %s = '%s'", tag, text)
        
        # Helper function to get text from header
        def get_header_text(field_name: str) -> str:
            """Get text from header field, trying with and without namespace."""
            value = header.findtext(f"{namespace}{field_name}", "")
            if not value:
                value = header.findtext(field_name, "")
            _LOGGER.debug("  get_header_text('%s'): '%s' (namespace='%s')", field_name, value, namespace)
            return value
        
        # Extract all useful fields
        authority_name = get_header_text("AuthorityName")
        authority_title = get_header_text("AuthorityTitle")
        organisation = get_header_text("OrganisationName")
        issued = get_header_text("Issued")
        profile_name = get_header_text("ProfileName")
        content_explanation = get_header_text("ContentExplanation")
        
        # ValidFrom/ValidTo are inside a Validity sub-element
        valid_from = ""
        valid_to = ""
        validity_elem = header.find(f"{namespace}Validity") or header.find("Validity")
        if validity_elem is not None:
            valid_from = validity_elem.findtext(f"{namespace}ValidFrom", "") or validity_elem.findtext("ValidFrom", "")
            valid_to = validity_elem.findtext(f"{namespace}ValidTo", "") or validity_elem.findtext("ValidTo", "")
            _LOGGER.debug("Found Validity element - ValidFrom: '%s', ValidTo: '%s'", valid_from, valid_to)
        
        # LowerFL/UpperFL are inside a FlightLevel sub-element
        lower_fl = ""
        upper_fl = ""
        fl_elem = header.find(f"{namespace}FlightLevel") or header.find("FlightLevel")
        if fl_elem is not None:
            lower_fl = fl_elem.findtext(f"{namespace}LowerFL", "") or fl_elem.findtext("LowerFL", "")
            upper_fl = fl_elem.findtext(f"{namespace}UpperFL", "") or fl_elem.findtext("UpperFL", "")
        
        _LOGGER.debug("Parsed PIB header - ValidFrom: '%s', ValidTo: '%s', Issued: '%s'", 
                     valid_from, valid_to, issued)

        global_data = {
            "authority_name": authority_name,
            "authority_title": authority_title,
            "organisation": organisation,
            "valid_from": _format_datetime(valid_from) if valid_from else "",
            "valid_to": _format_datetime(valid_to) if valid_to else "",
            "issued": _format_datetime(issued) if issued else "",
            "profile_name": profile_name,
            "content_explanation": content_explanation,
            "lower_fl": lower_fl,
            "upper_fl": upper_fl,
        }
    else:
        _LOGGER.warning("AreaPIBHeader element not found in XML")
        _LOGGER.debug("Root element: %s", root.tag)
        # List first few children for debugging
        for i, child in enumerate(root):
            if i < 5:
                _LOGGER.debug("Root child %d: %s", i, child.tag)

    # Parse NOTAMs - also handle namespace
    notams = []
    notam_elements = root.findall(f".//{namespace}Notam") if namespace else root.findall(".//Notam")
    
    _LOGGER.debug("Found %d NOTAM elements", len(notam_elements))
    
    # Reset debug counter for this parse
    if hasattr(_should_include_notam, '_debug_count'):
        _should_include_notam._debug_count = 0
    
    # Log first NOTAM element structure
    if notam_elements:
        first_elem = notam_elements[0]
        _LOGGER.debug("First NOTAM element children:")
        for child in first_elem:
            tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            text = (child.text[:50] + "...") if child.text and len(child.text) > 50 else child.text
            _LOGGER.debug("  %s = '%s'", tag, text if text else "(empty)")
    
    # Log first NOTAM details for debugging
    sample_count = 0
    parsed_count = 0
    failed_count = 0
    
    for notam_elem in notam_elements:
        notam_data = _parse_notam_element(notam_elem, namespace, aerodrome_list)
        
        if notam_data:
            parsed_count += 1
            # Log first 3 parsed NOTAMs to see structure
            if sample_count < 3:
                sample_count += 1
                _LOGGER.debug("Sample NOTAM %d: nof=%s, aerodrome=%s, series=%s, number=%s, year=%s, coords=%s, radius=%s, has_lat_lon=%s",
                             sample_count, notam_data.get("nof"), notam_data.get("aerodrome_code"), 
                             notam_data.get("series"), notam_data.get("number"), notam_data.get("year"),
                             notam_data.get("coordinates", "none"),
                             notam_data.get("radius_nm", 0),
                             "latitude" in notam_data and "longitude" in notam_data)
            
            if _should_include_notam(notam_data, aerodromes, coordinates):
                notams.append(notam_data)
        else:
            failed_count += 1
    
    _LOGGER.debug("Parsing complete: %d parsed successfully, %d failed to parse, %d matched filters",
                 parsed_count, failed_count, len(notams))

    return {
        "global": global_data, 
        "notams": notams, 
        "aerodrome_list": aerodrome_list,
        "fir_list": fir_list,
        "aerodrome_details": aerodrome_details,
    }


def _parse_notam_element(notam_elem: ET.Element, namespace: str = "", aerodrome_list: dict = None) -> dict[str, Any] | None:
    """Parse a single NOTAM element."""
    if aerodrome_list is None:
        aerodrome_list = {}
    
    # Helper to get text with or without namespace
    def get_text(tag: str) -> str:
        text = notam_elem.findtext(f"{namespace}{tag}", "").strip()
        if not text and namespace:
            text = notam_elem.findtext(tag, "").strip()
        return text
    
    # Actual field names from NATS PIB XML:
    # NOF = NOTAM Office (issuing office code)
    # ItemA = Location (actual aerodrome code)
    nof = get_text("NOF")
    aerodrome_code = get_text("ItemA")  # This is the actual aerodrome
    series = get_text("Series")
    number = get_text("Number")
    year = get_text("Year")
    coordinates = get_text("Coordinates")
    radius = get_text("Radius")
    description = get_text("ItemE")
    start_validity = get_text("StartValidity")
    end_validity = get_text("EndValidity")

    if not nof or not series or not number or not year:
        return None

    notam_data = {
        "nof": nof.upper(),  # NOTAM Office
        "aerodrome_code": aerodrome_code.upper() if aerodrome_code else "",
        "series": series,
        "number": number,
        "year": year,
        "coordinates": coordinates,
        "radius_nm": float(radius) if radius else 0.0,
        "description": description,
        "start_validity": _format_notam_datetime(start_validity),
        "end_validity": end_validity if end_validity == "PERM" else _format_notam_datetime(end_validity),
    }
    
    # Add aerodrome name if available in lookup
    if aerodrome_code and aerodrome_code.upper() in aerodrome_list:
        notam_data["aerodrome_name"] = aerodrome_list[aerodrome_code.upper()]

    # Parse coordinates if available
    if coordinates:
        parsed_coords = _parse_coordinates(coordinates)
        if parsed_coords:
            notam_data["latitude"] = parsed_coords["latitude"]
            notam_data["longitude"] = parsed_coords["longitude"]

    return notam_data


def _should_include_notam(
    notam: dict[str, Any],
    aerodromes: list[str],
    coordinates: list[dict[str, Any]] | None,
) -> bool:
    """Determine if NOTAM should be included based on filters."""
    # Check aerodrome match - only check aerodrome_code (location), NOT nof (office)
    # aerodrome_code is the actual location the NOTAM is about (e.g., EGLL, EGSS)
    # nof is just the office that issued it (e.g., EGGN)
    if aerodromes:
        aerodrome_code = notam.get("aerodrome_code", "")
        if aerodrome_code and aerodrome_code in aerodromes:
            _LOGGER.debug("NOTAM aerodrome '%s' matches aerodrome filter", aerodrome_code)
            return True
        # Also log NOF for comparison
        if aerodrome_code:
            _LOGGER.debug("NOTAM aerodrome '%s' (NOF: %s) not in configured list %s", 
                         aerodrome_code, notam.get("nof"), aerodromes)

    # Check coordinate proximity - match if within ANY configured coordinate circle
    if coordinates and "latitude" in notam and "longitude" in notam:
        notam_lat = notam["latitude"]
        notam_lon = notam["longitude"]
        notam_radius = notam.get("radius_nm", 0.0)

        # Loop through each configured coordinate center
        for idx, coord_filter in enumerate(coordinates):
            user_lat = coord_filter["latitude"]
            user_lon = coord_filter["longitude"]
            user_range = coord_filter["range_nm"]

            # Calculate distance between centers
            distance = _haversine_distance(user_lat, user_lon, notam_lat, notam_lon)

            # Check if circles intersect
            # Circles intersect if distance <= sum of radii
            if distance <= (user_range + notam_radius):
                _LOGGER.debug(
                    "NOTAM at (%s, %s) matches coordinate area %d (distance: %.1f NM <= %.1f NM)",
                    notam_lat, notam_lon, idx, distance, user_range + notam_radius
                )
                return True  # Match found - include this NOTAM

    # Log why NOTAM was excluded (only first 10 to avoid spam)
    if not hasattr(_should_include_notam, '_debug_count'):
        _should_include_notam._debug_count = 0
    
    if _should_include_notam._debug_count < 10:
        _should_include_notam._debug_count += 1
        reason = []
        if not aerodromes and not coordinates:
            reason.append("no filters configured")
        else:
            if aerodromes:
                reason.append(f"aerodrome_code '{notam.get('aerodrome_code', 'N/A')}' not in aerodromes {aerodromes}")
            if coordinates:
                if "latitude" not in notam or "longitude" not in notam:
                    reason.append(f"NOTAM has no parsed coordinates (raw: {notam.get('coordinates', 'none')})")
                else:
                    reason.append(f"coordinates ({notam.get('latitude')}, {notam.get('longitude')}) outside all ranges")
        
        _LOGGER.debug("NOTAM %s (aerodrome: %s) excluded: %s", 
                     notam["nof"], notam.get("aerodrome_code", "N/A"),
                     "; ".join(reason))

    return False


def _parse_coordinates(coord_string: str) -> dict[str, float] | None:
    """Parse coordinate string like '5408N00316W' into lat/lon."""
    # Format: DDMM[SS]N/SDDDMM[SS]E/W
    # Examples: 5408N00316W, 5408N00316W, 540830N0031645W
    
    # Try to match the pattern
    pattern = r"(\d{2})(\d{2})(\d{2})?([NS])(\d{3})(\d{2})(\d{2})?([EW])"
    match = re.match(pattern, coord_string.strip())

    if not match:
        _LOGGER.debug("Could not parse coordinates: %s", coord_string)
        return None

    lat_deg = int(match.group(1))
    lat_min = int(match.group(2))
    lat_sec = int(match.group(3)) if match.group(3) else 0
    lat_dir = match.group(4)

    lon_deg = int(match.group(5))
    lon_min = int(match.group(6))
    lon_sec = int(match.group(7)) if match.group(7) else 0
    lon_dir = match.group(8)

    # Convert to decimal degrees
    latitude = lat_deg + lat_min / 60 + lat_sec / 3600
    if lat_dir == "S":
        latitude = -latitude

    longitude = lon_deg + lon_min / 60 + lon_sec / 3600
    if lon_dir == "W":
        longitude = -longitude

    return {"latitude": latitude, "longitude": longitude}


def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points in nautical miles."""
    # Radius of Earth in nautical miles
    R = 3440.065

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance


def _format_datetime(dt_string: str) -> str:
    """Convert ISO 8601 datetime to Home Assistant format."""
    if not dt_string:
        return ""

    try:
        # Parse ISO 8601 format
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        # Return in HA format: YYYY-MM-DD HH:MM:SS
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError) as err:
        _LOGGER.debug("Could not parse datetime %s: %s", dt_string, err)
        return dt_string


def _format_notam_datetime(dt_string: str) -> str:
    """Convert NOTAM datetime format to Home Assistant format.
    
    NOTAM format: YYMMDDHHmm (e.g., 2508151138 = 2025-08-15 11:38)
    Returns: YYYY-MM-DD HH:MM:SS
    """
    if not dt_string or dt_string == "PERM" or dt_string == "UFN":
        return dt_string
    
    try:
        # NOTAM format: YYMMDDHHmm
        if len(dt_string) == 10 and dt_string.isdigit():
            year = int("20" + dt_string[0:2])  # YY -> 20YY
            month = int(dt_string[2:4])
            day = int(dt_string[4:6])
            hour = int(dt_string[6:8])
            minute = int(dt_string[8:10])
            
            dt = datetime(year, month, day, hour, minute)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError) as err:
        _LOGGER.debug("Could not parse NOTAM datetime %s: %s", dt_string, err)
    
    return dt_string
