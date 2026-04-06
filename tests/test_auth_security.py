from unittest.mock import MagicMock, patch

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

    with patch("custom_components.nissan_connect.NCISession") as mock_nci:
        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)
    mock_nci.assert_called_once_with(region="EU", unique_id="test@example.com")


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

    with patch("custom_components.nissan_connect.NCISession") as mock_nci:
        mock_session = mock_nci.return_value
        mock_session.refresh_access_token.side_effect = AuthenticationError("refresh failed")

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, entry)
    mock_nci.assert_called_once_with(region="EU", unique_id="test@example.com")


def test_authentication_error_is_runtime_error():
    assert issubclass(AuthenticationError, RuntimeError)
