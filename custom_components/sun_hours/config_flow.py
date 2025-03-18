import logging

import voluptuous as vol

import aiohttp
import urllib.parse

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def get_location_suggestions(user_input: str) -> list[dict]:
    base_url = "https://www.wetter.com/search/autosuggest/"
    encoded_location = urllib.parse.quote(user_input)
    url = f"{base_url}{encoded_location}"

    headers = {
        "x-requested-with": "XMLHttpRequest"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                locations = data.get("locations", [])

                # Extract only title, code, and seoString
                result = [{"title": loc["title"], "code": loc["code"], "seoString": loc["seoString"]} for loc in locations]

                return result
            raise Exception("Failed to fetch locations...")


class SunHoursConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1
    _location_name: str | None = None
    _suggestions: list[dict] | None = None

    async def async_step_user(self, user_input=None):
        """Handle the initial step where user types in a location."""
        errors = {}
        if user_input is not None:
            # The user typed something for 'location_name'
            self._location_name = user_input.get("location_name")
            if not self._location_name:
                errors["base"] = "no_location"
            else:
                # If location is provided, go to the next step to list suggestions
                return await self.async_step_select_location()

        data_schema = vol.Schema({
            vol.Required("location_name"): str
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_select_location(self, user_input=None):
        """Handle step that displays autocomplete suggestions for the typed name."""
        errors = {}
        if user_input is not None:
            # The user selected a location
            selected_code = user_input.get("code")
            if selected_code:
                # We can now create the config entry with the chosen location
                chosen_loc = next((item for item in self._suggestions if item["code"] == selected_code), None)
                if chosen_loc is None:
                    errors["base"] = "invalid_selection"
                else:
                    return self._create_entry(chosen_loc)
            else:
                errors["base"] = "invalid_selection"

        # Fetch suggestions from some API or local logic
        self._suggestions = await get_location_suggestions(self._location_name)

        if not self._suggestions:
            # If no suggestions, show error or ask user to go back
            errors["base"] = "no_suggestions"
            return self.async_show_form(
                step_id="select_location",
                data_schema=vol.Schema({}),
                errors=errors
            )

        # Build a dict of suggestions: { "loc_id": "Location Name", ... }
        suggestions_dict = {
            suggestion["code"]: suggestion["title"]
            for suggestion in self._suggestions
        }

        data_schema = vol.Schema({
            vol.Required("code"): vol.In(suggestions_dict)
        })

        return self.async_show_form(
            step_id="select_location",
            data_schema=data_schema,
            errors=errors,
        )

    @callback
    def _create_entry(self, chosen_loc: dict):
        """Create the config entry after the user selected a location."""
        title = chosen_loc["title"]
        code = chosen_loc["code"]
        seoString = chosen_loc["seoString"]

        data = {
            "title": title,
            "code": code,
            "seoString": seoString
        }

        return self.async_create_entry(title=title, data=data)
