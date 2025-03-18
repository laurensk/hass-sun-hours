from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

import aiohttp
from bs4 import BeautifulSoup
import re

from .const import DOMAIN, SENSOR_TYPES

async def get_value(_sensor_config: dict, seoString: str, code: str) -> int:

    url = f"{_sensor_config["baseUrl"]}/{seoString}/{code}.html"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()

                soup = BeautifulSoup(html, "html.parser")

                first_sun = soup.find(class_="sun")
                rows = first_sun.find_all(class_="row")
                last_row = rows[-1]
                spans = last_row.find_all("span")
                last_span_text = spans[-1].get_text(strip=True)
                
                sun_hours = parse_hours(last_span_text)

                return sun_hours
            raise Exception("Failed to fetch locations...")
        
def parse_hours(text):
    """Extract the integer hour value from a string using regex."""
    match = re.search(r"(\d+)", text)
    return int(match.group(1)) if match else 0

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
):
    """Set up sensors for Sun Hours integration."""
    title = hass.data[DOMAIN][entry.entry_id]["title"]
    code = hass.data[DOMAIN][entry.entry_id]["code"]
    seoString = hass.data[DOMAIN][entry.entry_id]["seoString"]

    entities = []
    for sensor_type, sensor_config in SENSOR_TYPES.items():
        entities.append(SunHoursSensor(sensor_type, sensor_config, title, code, seoString))

    async_add_entities(entities, update_before_add=True)


class SunHoursSensor(SensorEntity):
    """Representation of a Sun Hours Sensor."""

    def __init__(self, sensor_type, sensor_config, title, code, seoString):
        self._sensor_type = sensor_type
        self._attr_name = f"{sensor_config["name"]} ({title})"
        self._sensor_config = sensor_config
        self._title = title
        self._code = code
        self._seoString = seoString
        self._state = None

    @property
    def unique_id(self):
        """Return a unique ID for this sensor."""
        return f"sun_hours_{self._code}_{self._sensor_type}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

    async def async_update(self):
        """Fetch new state data for the sensor.
           Here, implement your logic to fetch data from your API,
           using self._location_id or self._location if needed.
        """
        self._state = await get_value(self._sensor_config, self._seoString, self._code)
