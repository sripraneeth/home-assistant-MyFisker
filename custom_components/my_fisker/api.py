"""Class to handle connections towards the Fisker / OV Loop cloud API.

Rewritten to use the current cloud API (Auth0 password grant + GoLoop REST stats),
replacing the deprecated auth.fiskerdps.com login and the cec WebSocket "digital twin".
The REST response is normalized into the same flattened keys the entities already use,
so sensors / binary sensors / trip-efficiency stats keep working unchanged.
"""

import logging
import time

import aiohttp

from .const import (
    API_TIMEOUT,
    AUTH0_CLIENT_ID,
    AUTH0_SCOPE,
    AUTH0_URL,
    COMMAND_MAP,
    DIGITAL_TWIN,
    TRIM_EXTREME_ULTRA_BATT_CAPACITY,
    TRIM_SPORT_BATT_CAPACITY,
    URL_COMMAND,
    URL_STATS,
)

_LOGGER = logging.getLogger(__name__)


class MyFiskerAPI:
    """Handle connection towards the Fisker / OV Loop cloud API."""

    def __init__(self, username: str, password: str, region: str, vin: str = ""):
        _LOGGER.debug("MyFiskerAPI init")
        self._username = username
        self._password = password
        self._region = region
        self.vin = vin

        self._accessToken = ""
        self._refreshToken = ""
        self._tokenExpiration = 0  # epoch seconds
        self._timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
        self.data = {}

    # ------------------------------------------------------------------ auth
    async def GetAuthTokenAsync(self):
        """Return a valid Auth0 access token, refreshing/logging in as needed."""
        now = int(time.time())
        # Reuse the cached token until 5 minutes before expiry.
        if self._accessToken and now < self._tokenExpiration - 300:
            return self._accessToken

        if self._refreshToken:
            refreshed = await self._refresh_token()
            if refreshed:
                return self._accessToken

        return await self._password_login()

    async def _password_login(self):
        payload = {
            "client_id": AUTH0_CLIENT_ID,
            "grant_type": "password",
            "username": self._username,
            "password": self._password,
            "scope": AUTH0_SCOPE,
        }
        async with (
            aiohttp.ClientSession(timeout=self._timeout) as session,
            session.post(AUTH0_URL, json=payload) as response,
        ):
            data = await response.json()
            if "access_token" in data:
                self._store_token(data)
                _LOGGER.debug("Auth0 password login ok")
            else:
                msg = data.get("error_description") or data.get("error") or "login failed"
                _LOGGER.error("Auth0 login failed: %s", msg)
                self._accessToken = msg
            return self._accessToken

    async def _refresh_token(self):
        payload = {
            "client_id": AUTH0_CLIENT_ID,
            "grant_type": "refresh_token",
            "refresh_token": self._refreshToken,
        }
        try:
            async with (
                aiohttp.ClientSession(timeout=self._timeout) as session,
                session.post(AUTH0_URL, json=payload) as response,
            ):
                data = await response.json()
                if "access_token" in data:
                    self._store_token(data)
                    _LOGGER.debug("Auth0 token refreshed")
                    return True
                _LOGGER.warning("Auth0 refresh failed: %s", data.get("error"))
                return False
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Auth0 refresh error: %s", e)
            return False

    def _store_token(self, data):
        self._accessToken = data["access_token"]
        self._refreshToken = data.get("refresh_token", self._refreshToken)
        self._tokenExpiration = int(time.time()) + int(data.get("expires_in", 14400))

    async def tokenReturn(self):
        return self._accessToken

    # --------------------------------------------------------------- profiles
    async def GetProfiles(self):
        """Validate access by fetching stats for the configured VIN; returns the VIN.

        The legacy WebSocket "profiles" lookup is gone; the VIN is provided in config.
        """
        if not self.vin:
            raise MyFiskerApiError("VIN is required")
        await self.GetDigitalTwin()
        return self.vin

    # ------------------------------------------------------------------ stats
    async def GetDigitalTwin(self):
        """Fetch /fisker/stats and normalize to the flattened keys entities expect."""
        token = await self.GetAuthTokenAsync()
        headers = {"Authorization": f"Bearer {token}"}
        async with (
            aiohttp.ClientSession(timeout=self._timeout) as session,
            session.get(URL_STATS, params={"vin": self.vin}, headers=headers) as response,
        ):
            if response.status != 200:
                text = await response.text()
                raise RequestError(f"stats failed: {text[:200]}", response.status)
            body = await response.json()

        data = body.get("data", body) or {}
        normalized = self._normalize(data)
        if self._region == "US":
            normalized = self._ConvertToImperial(normalized)
        self.data[DIGITAL_TWIN] = normalized
        return normalized

    def _battery_capacity(self):
        # VCF1Z=One, VCF1E=Extreme, VCF1U=Ultra (~106), VCF1S=Sport (~75)
        prefix = (self.vin or "")[0:5].upper()
        if prefix in ("VCF1Z", "VCF1E", "VCF1U"):
            return TRIM_EXTREME_ULTRA_BATT_CAPACITY
        if prefix == "VCF1S":
            return TRIM_SPORT_BATT_CAPACITY
        return TRIM_EXTREME_ULTRA_BATT_CAPACITY

    def _normalize(self, d: dict) -> dict:
        """Map the cloud stats JSON into the legacy flattened key structure."""

        def g(obj, *path, default=None):
            cur = obj
            for p in path:
                if not isinstance(cur, dict):
                    return default
                cur = cur.get(p)
            return cur if cur is not None else default

        soc_pct = g(d, "state_of_charge", "usable", default=g(d, "battery", "percent", default=0))
        capacity = self._battery_capacity()

        out = {
            "vin": self.vin,
            "online": g(d, "online", default=False),
            "online_hmi": g(d, "online_hmi", default=False),
            "updated": g(d, "updated", default=""),
            "ip": g(d, "ip", default=""),
            "trex_version": g(d, "trex_version", default=""),
            # battery / range (km base — converted for US)
            "battery_percent": g(d, "battery", "percent", default=0),
            "battery_state_of_charge": round(soc_pct * capacity / 100, 2),
            "battery_total_mileage_odometer": g(
                d, "battery", "total_kilometers_odometer",
                default=g(d, "battery", "total_mileage_odometer", default=0),
            ),
            "battery_max_miles": g(
                d, "max_range", "max_range_kilometers",
                default=g(d, "max_range", "max_miles", default=0),
            ),
            "battery_avg_cell_temp": g(d, "cell_temp", "avg_battery_temp", default=0),
            "battery_charge_type": g(d, "vcu0x260", "charge_type", default="Initial_value"),
            # climate (Celsius base)
            "climate_control_ambient_temperature": g(d, "ambient_temperature", "temperature_celsius", default=0),
            "climate_control_cabin_temperature": g(d, "cabin_climate", "cabin_temperature_celsius", default=0),
            "climate_control_internal_temperature": g(d, "cabin_climate", "internal_temperature_celsius", default=0),
            "climate_control_driver_seat_heat": g(d, "driver_seat_heat", "level", default=0),
            "climate_control_passenger_seat_heat": g(d, "passenger_seat_heat", "level", default=0),
            "climate_control_rear_defrost": g(d, "rear_defrost", "on", default=False),
            "climate_control_steering_wheel_heat": g(d, "steering_wheel_heat", "on", default=False),
            # speed / gear / readiness
            "vehicle_speed_speed": g(d, "vehicle_speed", "speed", default=0),
            "gear_in_park": g(d, "gear", "in_park", default=True),
            "vehicle_ready_state_is_vehicle_ready": g(d, "vehicle_ready_state", "is_vehicle_ready", default=False),
            # location
            "location_latitude": g(d, "location", "latitude", default=0),
            "location_longitude": g(d, "location", "longitude", default=0),
            "location_altitude": g(d, "location", "altitude", default=0),
            # locks & doors
            "door_locks_all": g(d, "door_locks", "all", default=False),
            "door_locks_driver": g(d, "door_locks", "driver", default=False),
            "doors_hood": g(d, "doors", "hood", default=False),
            "doors_trunk": g(d, "doors", "trunk", default=False),
            "doors_left_front": g(d, "doors", "left_front", default=False),
            "doors_left_rear": g(d, "doors", "left_rear", default=False),
            "doors_right_front": g(d, "doors", "right_front", default=False),
            "doors_right_rear": g(d, "doors", "right_rear", default=False),
            # windows + sunroof
            "windows_left_front": g(d, "windows", "left_front", default=0),
            "windows_left_rear": g(d, "windows", "left_rear", default=0),
            "windows_right_front": g(d, "windows", "right_front", default=0),
            "windows_right_rear": g(d, "windows", "right_rear", default=0),
            "windows_left_rear_quarter": g(d, "misc_windows", "left_rear_quarter", default=0),
            "windows_right_rear_quarter": g(d, "misc_windows", "right_rear_quarter", default=0),
            "windows_rear_windshield": g(d, "misc_windows", "rear_windshield", default=0),
            "windows_sunroof": g(d, "sunroof", "sunroof", default=0),
        }
        return out

    def _ConvertToImperial(self, dt: dict) -> dict:
        """Convert metric base values to imperial for the US region."""
        mi = 0.621371
        dt["vehicle_speed_speed"] = round((dt["vehicle_speed_speed"] or 0) * mi)
        dt["battery_max_miles"] = round((dt["battery_max_miles"] or 0) * mi)
        dt["battery_total_mileage_odometer"] = round(
            (dt["battery_total_mileage_odometer"] or 0) * mi
        )
        for k in (
            "battery_avg_cell_temp",
            "climate_control_cabin_temperature",
            "climate_control_ambient_temperature",
            "climate_control_internal_temperature",
        ):
            dt[k] = round((dt[k] or 0) * 1.8 + 32)
        dt["location_altitude"] = (dt["location_altitude"] or 0) * 3.28084
        return dt

    # --------------------------------------------------------------- commands
    async def SendCommandRequest(self, command: str, command_data: str = ""):
        """Send a remote command via the cloud /vehicle/{endpoint} API."""
        if command not in COMMAND_MAP:
            raise RequestError(f"Unknown command {command}", 400)
        endpoint, default_value = COMMAND_MAP[command]
        value = command_data or default_value
        token = await self.GetAuthTokenAsync()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {"vin": self.vin, "value": value}
        async with (
            aiohttp.ClientSession(timeout=self._timeout) as session,
            session.post(f"{URL_COMMAND}/{endpoint}", json=payload, headers=headers) as response,
        ):
            if response.status not in (200, 201, 202):
                text = await response.text()
                raise RequestError(f"command {command} failed: {text[:200]}", response.status)
            return await response.text()


class MyFiskerApiError(Exception):
    """Base exception for all MyFisker API errors"""


class AuthenticationError(MyFiskerApiError):
    """Authentication failed"""


class RequestError(MyFiskerApiError):
    """Failed to get the results from the API"""

    def __init__(self, message, error_code):
        super().__init__(message)
        self.error_code = error_code


class RequestConnectionError(MyFiskerApiError):
    """Failed to make the request to the API"""


class RequestTimeoutError(MyFiskerApiError):
    """Failed to get the results from the API"""
