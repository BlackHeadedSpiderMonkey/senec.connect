"""Unit tests for the SENEC API Client.

Uses mocked aiohttp session responses for HTTP mocking and pytest-asyncio
for async tests.
Validates: Requirements 11.2
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.senec_connect.api_client import (
    ENDPOINT_DEVICE_DATA,
    SenecApiClient,
)
from custom_components.senec_connect.const import (
    API_BASE_URL,
    INCLUDE_FULL,
    INCLUDE_VALIDATE,
    REQUEST_TIMEOUT,
)
from custom_components.senec_connect.exceptions import (
    SenecApiError,
    SenecAuthError,
    SenecConnectionError,
)
from custom_components.senec_connect.models import DeviceData

from .conftest import API_KEY

DEVICE_DATA_URL = f"{API_BASE_URL}{ENDPOINT_DEVICE_DATA}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session() -> MagicMock:
    """Create a mock aiohttp ClientSession."""
    return MagicMock(spec=aiohttp.ClientSession)


@pytest.fixture
def client(mock_session: MagicMock) -> SenecApiClient:
    """Create a SenecApiClient with mock session."""
    return SenecApiClient(session=mock_session, api_key=API_KEY)


def _create_mock_response(
    status: int = 200, json_data: list | dict | None = None, text: str = ""
) -> AsyncMock:
    """Create a mock aiohttp response as async context manager.

    Simulates aioresponses behavior by providing a mock that acts
    as an async context manager returning a response with status,
    json(), and text() methods.
    """
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data if json_data is not None else [])
    response.text = AsyncMock(return_value=text)

    # Make it work as async context manager (simulates session.get(...))
    context = AsyncMock()
    context.__aenter__ = AsyncMock(return_value=response)
    context.__aexit__ = AsyncMock(return_value=False)
    return context


# ---------------------------------------------------------------------------
# Initialization Tests
# ---------------------------------------------------------------------------


class TestSenecApiClientInit:
    """Tests for SenecApiClient initialization."""

    def test_init_stores_session_and_api_key(
        self, mock_session: MagicMock
    ) -> None:
        """Client stores session and api_key."""
        client = SenecApiClient(session=mock_session, api_key=API_KEY)

        assert client._session is mock_session
        assert client._api_key == API_KEY

    def test_init_configures_timeout(
        self, mock_session: MagicMock
    ) -> None:
        """Client configures a timeout matching REQUEST_TIMEOUT (10s)."""
        client = SenecApiClient(session=mock_session, api_key=API_KEY)

        assert client._timeout.total == REQUEST_TIMEOUT


# ---------------------------------------------------------------------------
# Successful API Call Tests
# ---------------------------------------------------------------------------


class TestSuccessfulApiCall:
    """Tests for successful API responses (mocked aiohttp responses)."""

    async def test_successful_request_returns_device_data(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
        mock_device_response_full: list[dict],
    ) -> None:
        """Successful API call returns parsed DeviceData list."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, mock_device_response_full)
        )

        result = await client.async_get_device_data()

        assert len(result) == 1
        assert isinstance(result[0], DeviceData)
        assert result[0].battery is not None
        assert result[0].battery.state_of_charge == 75
        assert result[0].battery.power == 1500.0
        assert result[0].battery.voltage == 52.3
        assert result[0].battery.current == 28.7
        assert result[0].bess_nameplate is not None
        assert result[0].bess_nameplate.serial_number == "v4-00012ff4"
        assert result[0].bess_nameplate.model == "SENEC.Home E4 - 1ph 6 AC"
        assert result[0].meter is not None
        assert result[0].meter.grid_power == -500.0
        assert result[0].meter.consumption == 1200.0
        assert result[0].meter.production == 3200.0
        assert len(result[0].wallboxes) == 1
        assert result[0].wallboxes[0].id == "WB-01"
        assert result[0].wallboxes[0].charging_power == 7400.0

    async def test_request_uses_correct_url_and_headers(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """Request is made with correct URL, auth header, and params."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, [])
        )

        await client.async_get_device_data()

        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        # Positional arg: URL
        assert call_args[0][0] == DEVICE_DATA_URL
        # Keyword args
        assert call_args[1]["headers"] == {
            "Ocp-Apim-Subscription-Key": API_KEY
        }
        assert call_args[1]["params"] == {"include": INCLUDE_FULL}

    async def test_request_uses_include_full_by_default(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """Default include parameter is INCLUDE_FULL."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, [])
        )

        await client.async_get_device_data()

        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["params"] == {"include": INCLUDE_FULL}

    async def test_custom_include_parameter(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """Custom include parameter is passed to the API."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, [])
        )

        await client.async_get_device_data(include="bessNameplate")

        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["params"] == {"include": "bessNameplate"}


# ---------------------------------------------------------------------------
# HTTP Error Tests: 401/403 → SenecAuthError
# ---------------------------------------------------------------------------


class TestHttpAuthErrors:
    """Tests for HTTP 401/403 → SenecAuthError mapping."""

    async def test_http_401_raises_auth_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 401 response raises SenecAuthError."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(401)
        )

        with pytest.raises(SenecAuthError, match="401"):
            await client.async_get_device_data()

    async def test_http_403_raises_auth_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 403 response raises SenecAuthError."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(403)
        )

        with pytest.raises(SenecAuthError, match="403"):
            await client.async_get_device_data()


# ---------------------------------------------------------------------------
# HTTP Error Tests: 500 → SenecApiError
# ---------------------------------------------------------------------------


class TestHttpApiErrors:
    """Tests for HTTP 5xx/4xx (non-auth) → SenecApiError mapping."""

    async def test_http_500_raises_api_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 500 response raises SenecApiError with status_code=500."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(500, text="Internal Server Error")
        )

        with pytest.raises(SenecApiError) as exc_info:
            await client.async_get_device_data()

        assert exc_info.value.status_code == 500
        assert "500" in str(exc_info.value)

    async def test_http_429_raises_api_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 429 (rate limit) response raises SenecApiError."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(429, text="Too Many Requests")
        )

        with pytest.raises(SenecApiError) as exc_info:
            await client.async_get_device_data()

        assert exc_info.value.status_code == 429

    async def test_http_404_raises_api_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """HTTP 404 response raises SenecApiError."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(404, text="Not Found")
        )

        with pytest.raises(SenecApiError) as exc_info:
            await client.async_get_device_data()

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Connection Error Tests: Timeout → SenecConnectionError
# ---------------------------------------------------------------------------


class TestConnectionErrors:
    """Tests for timeout and network errors → SenecConnectionError."""

    async def test_timeout_raises_connection_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """asyncio.TimeoutError raises SenecConnectionError."""
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(SenecConnectionError):
            await client.async_get_device_data()

    async def test_client_error_raises_connection_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """aiohttp.ClientError raises SenecConnectionError."""
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )

        with pytest.raises(SenecConnectionError):
            await client.async_get_device_data()

    async def test_server_disconnect_raises_connection_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """aiohttp.ServerDisconnectedError raises SenecConnectionError."""
        mock_session.get = MagicMock(
            side_effect=aiohttp.ServerDisconnectedError()
        )

        with pytest.raises(SenecConnectionError):
            await client.async_get_device_data()


# ---------------------------------------------------------------------------
# Response Parsing Tests: Empty Array + Multi-Device
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Tests for parsing API response data."""

    async def test_empty_array_returns_empty_list(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """Empty JSON array [] returns an empty list of DeviceData."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, [])
        )

        result = await client.async_get_device_data()

        assert result == []
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_multi_device_response_parsed_correctly(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
        mock_device_response_multi: list[dict],
    ) -> None:
        """Multi-device response is parsed into multiple DeviceData objects."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, mock_device_response_multi)
        )

        result = await client.async_get_device_data()

        assert len(result) == 3

        # Device 1: Full data with all sections
        assert result[0].battery is not None
        assert result[0].battery.state_of_charge == 85
        assert result[0].battery.power == 2000.0
        assert result[0].bess_nameplate is not None
        assert result[0].bess_nameplate.serial_number == "v4-device-001"
        assert result[0].bess_nameplate.system_id == "S4H1-AAAA-0001"
        assert result[0].meter is not None
        assert result[0].meter.grid_power == -1500.0
        assert result[0].meter.consumption == 800.0
        assert result[0].meter.production == 4300.0
        assert len(result[0].wallboxes) == 2
        assert result[0].wallboxes[0].id == "WB-01"
        assert result[0].wallboxes[0].charging_power == 11000.0
        assert result[0].wallboxes[0].ev_charging is True
        assert result[0].wallboxes[1].id == "WB-02"
        assert result[0].wallboxes[1].ev_charging is False
        assert result[0].wallboxes[1].charging_power == 0.0

        # Device 2: Partial data (no battery, no wallbox)
        assert result[1].battery is None
        assert result[1].bess_nameplate is not None
        assert result[1].bess_nameplate.serial_number == "v3-device-002"
        assert result[1].bess_nameplate.system_id is None
        assert result[1].meter is not None
        assert result[1].meter.grid_power == 300.0
        assert result[1].wallboxes == []

        # Device 3: Minimal data (only bessNameplate)
        assert result[2].battery is None
        assert result[2].bess_nameplate is not None
        assert result[2].bess_nameplate.serial_number == "v4-device-003"
        assert result[2].bess_nameplate.design_capacity == 20000
        assert result[2].bess_nameplate.active_charge_power == 5000
        assert result[2].meter is None
        assert result[2].wallboxes == []

    async def test_partial_device_response_handles_nulls(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
        mock_device_response_partial: list[dict],
    ) -> None:
        """Partial response with null battery/evse is handled gracefully."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, mock_device_response_partial)
        )

        result = await client.async_get_device_data()

        assert len(result) == 1
        assert result[0].battery is None
        assert result[0].bess_nameplate is not None
        assert result[0].meter is not None
        assert result[0].meter.grid_power == 200.0
        assert result[0].meter.consumption is None
        assert result[0].meter.production is None
        assert result[0].wallboxes == []

    async def test_minimal_device_response(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
        mock_device_response_minimal: list[dict],
    ) -> None:
        """Minimal response with only bessNameplate parses correctly."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, mock_device_response_minimal)
        )

        result = await client.async_get_device_data()

        assert len(result) == 1
        assert result[0].battery is None
        assert result[0].bess_nameplate is not None
        assert result[0].bess_nameplate.model == "SENEC.Home V3"
        assert result[0].bess_nameplate.serial_number == "v3-0000abcd"
        assert result[0].meter is None
        assert result[0].wallboxes == []


# ---------------------------------------------------------------------------
# Validate API Key Tests
# ---------------------------------------------------------------------------


class TestAsyncValidateApiKey:
    """Tests for async_validate_api_key method."""

    async def test_validate_calls_with_include_bessNameplate(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
        mock_device_response_minimal: list[dict],
    ) -> None:
        """validate_api_key uses include=bessNameplate."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(200, mock_device_response_minimal)
        )

        result = await client.async_validate_api_key()

        call_kwargs = mock_session.get.call_args[1]
        assert call_kwargs["params"] == {"include": INCLUDE_VALIDATE}
        assert len(result) == 1
        assert result[0].bess_nameplate is not None

    async def test_validate_propagates_auth_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """validate_api_key propagates SenecAuthError."""
        mock_session.get = MagicMock(
            return_value=_create_mock_response(401)
        )

        with pytest.raises(SenecAuthError):
            await client.async_validate_api_key()

    async def test_validate_propagates_connection_error(
        self,
        client: SenecApiClient,
        mock_session: MagicMock,
    ) -> None:
        """validate_api_key propagates SenecConnectionError on timeout."""
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(SenecConnectionError):
            await client.async_validate_api_key()
