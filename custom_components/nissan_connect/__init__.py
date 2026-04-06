import logging
from datetime import timedelta
from .kamereon import NCISession, AuthenticationError
from .coordinator import KamereonFetchCoordinator, KamereonPollCoordinator, StatisticsCoordinator
from .const import *
from homeassistant.exceptions import ConfigEntryAuthFailed

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config) -> bool:
    return True


async def async_update_listener(hass, entry):
    """Handle options flow credentials update."""
    config = entry.data
    account_id = config['email']

    # Loop each vehicle and update its session with the new credentials
    for vehicle in hass.data[DOMAIN][account_id][DATA_VEHICLES]:
        hass.data[DOMAIN][account_id][DATA_VEHICLES][vehicle].session.token = config.get("token")

    # Update intervals for coordinators
    hass.data[DOMAIN][account_id][DATA_COORDINATOR_STATISTICS].update_interval = timedelta(minutes=config.get("interval_statistics", DEFAULT_INTERVAL_STATISTICS))
    hass.data[DOMAIN][account_id][DATA_COORDINATOR_FETCH].update_interval = timedelta(minutes=config.get("interval_fetch", DEFAULT_INTERVAL_FETCH))
    
    # Refresh fetch coordinator
    await hass.data[DOMAIN][account_id][DATA_COORDINATOR_FETCH].async_refresh()


async def async_setup_entry(hass, entry):
    """This is called from the config flow."""
    account_id = entry.data['email']

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN].setdefault(account_id, {})

    config = dict(entry.data)

    kamereon_session = NCISession(
        region=config["region"],
        unique_id=entry.unique_id
    )

    data = hass.data[DOMAIN][account_id] = {
        DATA_VEHICLES: {}
    }

    _LOGGER.info("Logging in to service")
    token = config.get("token")
    if token:
        kamereon_session.token = token
        try:
            await hass.async_add_executor_job(kamereon_session.refresh_access_token)
        except AuthenticationError as ex:
            raise ConfigEntryAuthFailed("Token reauthentication required") from ex
    else:
        raise ConfigEntryAuthFailed("Token reauthentication required")

    # Persist any refreshed token values.
    # Non-dict token payloads are treated as empty to avoid persisting malformed state.
    new_token = kamereon_session.token
    previous_token = token if isinstance(token, dict) else {}
    current_token = new_token if isinstance(new_token, dict) else {}
    if current_token and current_token != previous_token:
        updated_data = dict(config)
        updated_data["token"] = new_token
        hass.config_entries.async_update_entry(entry, data=updated_data)

    _LOGGER.debug("Finding vehicles")
    for vehicle in await hass.async_add_executor_job(kamereon_session.fetch_vehicles):
        await hass.async_add_executor_job(vehicle.fetch_all)
        if vehicle.vin not in data[DATA_VEHICLES]:
            data[DATA_VEHICLES][vehicle.vin] = vehicle

    coordinator = data[DATA_COORDINATOR_FETCH] = KamereonFetchCoordinator(hass, config)
    poll_coordinator = data[DATA_COORDINATOR_POLL] = KamereonPollCoordinator(hass, config)
    stats_coordinator = data[DATA_COORDINATOR_STATISTICS] = StatisticsCoordinator(
        hass, config)

    _LOGGER.debug("Initialising entities")
    await hass.config_entries.async_forward_entry_setups(entry, ENTITY_TYPES)

    # Init fetch and state coordinators
    await coordinator.async_config_entry_first_refresh()
    await stats_coordinator.async_config_entry_first_refresh()

    # Init poll coordinator and ensure it runs
    entry.async_on_unload(
            poll_coordinator.async_add_listener(
                lambda *args: None, None
            )
    )
    await poll_coordinator.async_config_entry_first_refresh()

    entry.async_on_unload(entry.add_update_listener(async_update_listener))

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(entry, ENTITY_TYPES)


async def async_migrate_entry(hass, config_entry) -> bool:
    """Migrate old entry."""
    # Version number has gone backwards
    if CONFIG_VERSION < config_entry.version:
        _LOGGER.error(
            "Backwards migration not possible. Please update the integration.")
        return False

    # Version number has gone up
    if config_entry.version < CONFIG_VERSION:
        _LOGGER.debug("Migrating from version %s", config_entry.version)
        new_data = config_entry.data

        config_entry.version = CONFIG_VERSION
        hass.config_entries.async_update_entry(config_entry, data=new_data)

        _LOGGER.debug("Migration to version %s successful",
                      config_entry.version)

    return True
