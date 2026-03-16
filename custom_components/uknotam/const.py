"""Constants for the UK NOTAM integration."""

DOMAIN = "uknotam"

CONF_AERODROMES = "aerodromes"
CONF_COORDINATES = "coordinates"
CONF_COORD_AREAS = "coordinate_areas"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RANGE_NM = "range_nm"
CONF_REFRESH_INTERVAL = "refresh_interval"

DEFAULT_REFRESH_INTERVAL = 60  # minutes

NATS_PIB_URL = "https://pibs.nats.co.uk/operational/pibs/PIB.xml"

ATTR_ATTRIBUTION = "Data provided by NATS UK NOTAM PIB feed"
