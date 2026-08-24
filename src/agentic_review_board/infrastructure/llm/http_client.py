from __future__ import annotations

import httpx


def _create_http_client(
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    if transport is None:
        return httpx.Client(
            trust_env=True,
            follow_redirects=False,
        )
    return httpx.Client(
        trust_env=True,
        follow_redirects=False,
        transport=transport,
    )
