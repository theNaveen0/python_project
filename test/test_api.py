import pytest
from src.api_client import GrokAPIClient, GrokAPIError


class DummyResp:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self, content_type=None):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class DummySession:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    def post(self, *args, **kwargs):
        return DummyResp(self.status, self.payload)


@pytest.mark.asyncio
async def test_send_query_success(monkeypatch):
    async def session_factory(*args, **kwargs):
        return DummySession(200, {"choices": [{"message": {"content": "Hello!"}}]})

    import aiohttp
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: session_factory())

    client = GrokAPIClient("test_key")
    resp = await client.send_query("Hi")
    assert resp == "Hello!"


@pytest.mark.asyncio
async def test_send_query_auth_error(monkeypatch):
    async def session_factory(*args, **kwargs):
        return DummySession(401, {"error": {"message": "Unauthorized"}})

    import aiohttp
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: session_factory())

    client = GrokAPIClient("bad_key")
    with pytest.raises(GrokAPIError) as ei:
        await client.send_query("Hi")
    assert "Authentication failed" in str(ei.value)


@pytest.mark.asyncio
async def test_send_query_malformed_response(monkeypatch):
    async def session_factory(*args, **kwargs):
        return DummySession(200, {"no_choices_here": True})

    import aiohttp
    monkeypatch.setattr(aiohttp, "ClientSession", lambda *a, **k: session_factory())

    client = GrokAPIClient("test_key")
    with pytest.raises(GrokAPIError) as ei:
        await client.send_query("Hi")
    assert "Malformed response" in str(ei.value)
