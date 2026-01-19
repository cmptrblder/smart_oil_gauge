import aiohttp
import logging
import re
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import AJAX_URL, LOGIN_URL, BASE_URL

_LOGGER = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": "https://app.smartoilgauge.com/",
}

class SmartOilGaugeCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, username, password):
        super().__init__(
            hass,
            _LOGGER,
            name="Smart Oil Gauge",
            update_interval=timedelta(minutes=30),
        )
        self.username = username
        self.password = password
        self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.logged_in = False

    async def _get_text(self, url: str) -> str:
        async with self.session.get(url, headers={"Referer": f"{BASE_URL}/"}) as resp:
            return await resp.text()

    def _parse_login_form(self, html: str):
        hidden = dict(
            re.findall(
                r'<input[^>]+type=["\']hidden["\'][^>]+name=["\']([^"\']+)["\'][^>]*value=["\']([^"\']*)["\']',
                html,
                flags=re.I,
            )
        )

        pw_match = re.search(
            r'<input[^>]*type=["\']password["\'][^>]*name=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )
        pw_name = pw_match.group(1) if pw_match else "password"

        user_match = re.search(
            r'<input[^>]*type=["\']email["\'][^>]*name=["\']([^"\']+)["\']',
            html,
            flags=re.I,
        )
        if not user_match:
            user_match = re.search(
                r'<input[^>]*type=["\']text["\'][^>]*name=["\']([^"\']+)["\']',
                html,
                flags=re.I,
            )
        user_name = user_match.group(1) if user_match else "username"

        return user_name, pw_name, hidden

    async def _post_json_lenient(self, url: str, data: dict):
        async with self.session.post(url, data=data, headers=DEFAULT_HEADERS) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            text = await resp.text()

            if "application/json" in ctype or "text/javascript" in ctype:
                try:
                    return resp.status, await resp.json(content_type=None)
                except Exception as e:
                    _LOGGER.debug("JSON parse failed (%s). Body starts: %r", e, text[:200])
                    return resp.status, {"_parse_error": str(e), "_raw": text[:1000]}

            return resp.status, {"_html": True, "_raw": text[:1000]}

    async def async_login(self):
        html = await self._get_text(LOGIN_URL)
        user_field, pw_field, hidden = self._parse_login_form(html)

        form = {}
        form.update(hidden)
        form[user_field] = self.username
        form[pw_field] = self.password

        async with self.session.post(
            LOGIN_URL,
            data=form,
            headers={"Referer": f"{BASE_URL}/"},
        ) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise UpdateFailed(f"Login HTTP {resp.status}")

            lowered = body.lower()
            if "login" in lowered and "password" in lowered and ("invalid" in lowered or "incorrect" in lowered):
                raise UpdateFailed("Login appears to have failed")

        status, payload = await self._post_json_lenient(AJAX_URL, {"action": "get_tanks_list", "tank_id": 0})

        if status == 401 or (isinstance(payload, dict) and payload.get("Status") == 401):
            raise UpdateFailed("Login succeeded but API still unauthorized")

        if isinstance(payload, dict) and payload.get("_html"):
            raise UpdateFailed("Login succeeded but API returned HTML")

        tanks = payload.get("tanks") if isinstance(payload, dict) else None
        if not tanks:
            raise UpdateFailed(f"Login validation failed. Response: {payload}")

        self.logged_in = True

    async def _async_update_data(self):
        try:
            if not self.logged_in:
                await self.async_login()

            status, payload = await self._post_json_lenient(AJAX_URL, {"action": "get_tanks_list", "tank_id": 0})

            if status == 401 or (isinstance(payload, dict) and payload.get("Status") == 401):
                self.logged_in = False
                raise UpdateFailed("Unauthorized (401)")

            if isinstance(payload, dict) and payload.get("_html"):
                self.logged_in = False
                raise UpdateFailed("API returned HTML")

            tanks = payload.get("tanks") if isinstance(payload, dict) else None
            if not tanks or not isinstance(tanks, list):
                raise UpdateFailed(f"Invalid API response: {payload}")

            return tanks[0]

        except Exception as err:
            self.logged_in = False
            raise UpdateFailed(err)
