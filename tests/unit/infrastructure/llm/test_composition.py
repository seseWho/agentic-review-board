from __future__ import annotations

from typing import Any

import httpx
import pytest

from agentic_review_board.infrastructure.llm.composition import _create_http_client


def test_http_client_constructor_uses_only_approved_explicit_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200))
    captured: dict[str, object] = {}
    client_marker = object()

    def capture_client(**kwargs: Any) -> object:
        captured.update(kwargs)
        return client_marker

    monkeypatch.setattr(httpx, "Client", capture_client)

    result = _create_http_client(transport)

    assert result is client_marker
    assert captured == {
        "trust_env": True,
        "follow_redirects": False,
        "transport": transport,
    }
    assert {
        "auth",
        "base_url",
        "cookies",
        "headers",
        "timeout",
    }.isdisjoint(captured)


def test_http_client_constructor_omits_transport_when_not_supplied(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}
    client_marker = object()

    def capture_client(**kwargs: Any) -> object:
        captured.update(kwargs)
        return client_marker

    monkeypatch.setattr(httpx, "Client", capture_client)

    result = _create_http_client()

    assert result is client_marker
    assert captured == {"trust_env": True, "follow_redirects": False}


def test_http_client_does_not_follow_redirects() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": "https://redirect-target.example/final"},
        )

    transport = httpx.MockTransport(handler)
    with _create_http_client(transport) as client:
        response = client.get("https://original-target.example/start")

    assert response.status_code == 302
    assert [str(request.url) for request in requests] == [
        "https://original-target.example/start"
    ]
