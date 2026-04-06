from unittest.mock import MagicMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.nissan_connect import async_setup_entry
from custom_components.nissan_connect.kamereon.kamereon import AuthenticationError


@pytest.mark.asyncio
async def test_async_setup_entry_raises_auth_failed_without_token(hass):
    entry = MagicMock()
    entry.data = {"email": "test@example.com", "region": "EU"}
    entry.unique_id = "test@example.com"
    entry.add_update_listener.return_value = lambda: None
    entry.async_on_unload = MagicMock()

    with pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


@pytest.mark.asyncio
async def test_async_setup_entry_raises_auth_failed_on_refresh_error(hass):
    entry = MagicMock()
    entry.data = {
        "email": "test@example.com",
        "region": "EU",
        "token": {"access_token": "token"},
    }
    entry.unique_id = "test@example.com"
    entry.add_update_listener.return_value = lambda: None
    entry.async_on_unload = MagicMock()

    with pytest.raises(ConfigEntryAuthFailed):
        await async_setup_entry(hass, entry)


def test_authentication_error_is_runtime_error():
    assert issubclass(AuthenticationError, RuntimeError)
