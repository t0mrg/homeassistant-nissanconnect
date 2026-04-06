import voluptuous as vol
from homeassistant.config_entries import (ConfigFlow, OptionsFlow)
from .const import DOMAIN, CONFIG_VERSION, DEFAULT_INTERVAL_POLL, DEFAULT_INTERVAL_CHARGING, DEFAULT_INTERVAL_STATISTICS, DEFAULT_INTERVAL_FETCH, DEFAULT_REGION, REGIONS
from .kamereon import NCISession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
from homeassistant.const import CONF_PASSWORD

USER_SCHEMA = vol.Schema({
    vol.Required("email"): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    # vol.Required(
    #     "interval", default=DEFAULT_INTERVAL_POLL
    # ): int,
    # vol.Required(
    #     "interval_charging", default=DEFAULT_INTERVAL_CHARGING
    # ): int,
    # vol.Required(
    #     "interval_fetch", default=DEFAULT_INTERVAL_FETCH
    # ): int,
    # vol.Required(
    #     "interval_statistics", default=DEFAULT_INTERVAL_STATISTICS
    # ): int,
    vol.Required(
        "region", default=DEFAULT_REGION.lower()): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[el.lower() for el in REGIONS], # Translation keys must be lowercase
                mode=selector.SelectSelectorMode.DROPDOWN,
                translation_key="region"
            ),
    ),
    vol.Required(
        "imperial_distance", default=False): bool
})


class NissanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow."""
    VERSION = CONFIG_VERSION
    _reauth_entry = None

    async def async_step_user(self, info):
        errors = {}
        if info is not None:
            info["region"] = info["region"].upper()

            await self.async_set_unique_id(info["email"])
            self._abort_if_unique_id_configured()

            # Validate credentials
            kamereon_session = NCISession(
                region=info["region"]
            )

            try:
                await self.hass.async_add_executor_job(kamereon_session.login,
                                                       info["email"],
                                                       info[CONF_PASSWORD]
                                                       )
            except:
                errors["base"] = "auth_error"

            if len(errors) == 0:
                data = dict(info)
                data.pop(CONF_PASSWORD, None)
                data["token"] = kamereon_session.token
                return self.async_create_entry(
                    title=info["email"],
                    data=data
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    def async_get_options_flow(entry):
        return NissanOptionsFlow(entry)

    async def async_step_reauth(self, entry_data):
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}

        if user_input is not None:
            kamereon_session = NCISession(region=self._reauth_entry.data["region"])
            try:
                await self.hass.async_add_executor_job(
                    kamereon_session.login,
                    self._reauth_entry.data["email"],
                    user_input[CONF_PASSWORD],
                )
            except Exception:
                errors["base"] = "auth_error"

            if not errors:
                data = dict(self._reauth_entry.data)
                data["token"] = kamereon_session.token
                self.hass.config_entries.async_update_entry(self._reauth_entry, data=data)
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): cv.string}),
            errors=errors,
        )


class NissanOptionsFlow(OptionsFlow):
    """Options flow."""

    def __init__(self, entry) -> None:
        self._config_entry = entry

    async def async_step_init(self, options):
        errors = {}
        # If form filled
        if options is not None:
            data = dict(self._config_entry.data)
            # Validate credentials
            kamereon_session = NCISession(
                region=data["region"]
            )
            if CONF_PASSWORD in options:
                try:
                    await self.hass.async_add_executor_job(kamereon_session.login,
                                                           self._config_entry.data.get("email"),
                                                           options[CONF_PASSWORD]
                                                           )
                except:
                    errors["base"] = "auth_error"

            # If we have no errors, update the data array
            if len(errors) == 0:
                # If password not provided, dont take the new details
                if not CONF_PASSWORD in options:
                    options.pop('email', None)
                    options.pop(CONF_PASSWORD, None)
                else:
                    options.pop(CONF_PASSWORD, None)
                    options["token"] = kamereon_session.token

                # Update data
                data.update(options)
                self.hass.config_entries.async_update_entry(
                    self._config_entry, data=data
                )

                # Update options
                return self.async_create_entry(
                    title="",
                    data={}
                )

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema({
                # vol.Required("email", default=self._config_entry.data.get("email", "")): cv.string,
                vol.Optional(CONF_PASSWORD): cv.string,
                vol.Required(
                    "interval", default=self._config_entry.data.get("interval", DEFAULT_INTERVAL_POLL)
                ): int,
                vol.Required(
                    "interval_charging", default=self._config_entry.data.get("interval_charging", DEFAULT_INTERVAL_CHARGING)
                ): int,
                vol.Required(
                    "interval_fetch", default=self._config_entry.data.get("interval_fetch", DEFAULT_INTERVAL_FETCH)
                ): int,
                vol.Required(
                    "interval_statistics", default=self._config_entry.data.get("interval_statistics", DEFAULT_INTERVAL_STATISTICS)
                ): int,
                # Excluded from config flow under #61
                # vol.Required(
                #     "imperial_distance", default=self._config_entry.data.get("imperial_distance", False)): bool
            }), errors=errors
        )
