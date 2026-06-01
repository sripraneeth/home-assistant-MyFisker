"""Constants for the My Fisker integration."""

DOMAIN = "my_fisker"

DEVICE_MANUCFACTURER = "Fisker inc."
DEVICE_MODEL = "Fisker (Ocean)"

API_TIMEOUT = 15
DEFAULT_SCAN_INTERVAL = 30

# --- New OV Loop / GoLoop cloud API (see ADR in OceanHome project) ---
# Auth0 Resource Owner Password Grant for the access token.
AUTH0_URL = "https://ovloop.auth0.com/oauth/token"
AUTH0_CLIENT_ID = "0o56La53yZHn39sDjpRJEE6XOT3ZSdEM"
AUTH0_SCOPE = "openid profile email offline_access"
# GoLoop SDK base that serves Fisker vehicle stats + commands.
GOLOOP_BASE_URL = "https://ccc.skipti.com/api/v1"
URL_STATS = f"{GOLOOP_BASE_URL}/fisker/stats"
URL_COMMAND = f"{GOLOOP_BASE_URL}/vehicle"  # POST {URL_COMMAND}/{command}

CONF_VIN = "vin"

# Maps the integration's button command keys to the cloud /vehicle/{endpoint} + value.
COMMAND_MAP = {
    "doors_lock": ("doors", "lock"),
    "doors_unlock": ("doors", "unlock"),
    "trunk_open": ("trunk", "open"),
    "trunk_close": ("trunk", "close"),
    "california_mode": ("california_mode", None),
}

TRIM_EXTREME_ULTRA_BATT_CAPACITY = 106
TRIM_SPORT_BATT_CAPACITY = 75

DIGITAL_TWIN = "digital_twin"

LIST_CLIMATE_CONTROL_SEAT_HEAT = ["Unknown", "High", "Medium", "Low", "Off"]
LIST_CLIMATE_CONTROL_STEERING_WHEEL_HEAT = ["Unknown", "Off", "On"]

CLIMATE_CONTROL_SEAT_HEAT = {
    0: ["Unknown", "mdi:help-rhombus-outline"],
    1: ["High", "mdi:car-seat-heater"],
    2: ["Medium", "mdi:car-seat-heater"],
    3: ["Low", "mdi:car-seat-heater"],
    4: ["Off", "mdi:car-seat-heater"],
}

CLIMATE_CONTROL_STEERING_WHEEL_HEAT = {
    False: ["Off", "mdi:car-door"],
    True: ["On", "mdi:car-door"],
}

GEAR_IN_PARK = {
    False: ["Driving", "mdi:car-door"],
    True: ["Parked", "mdi:car-door"],
}

DOOR_LOCK = {
    False: ["Closed", "mdi:car-door"],
    True: ["Open", "mdi:car-door"],
}
