from __future__ import annotations

import time
from typing import Any

import httpx

from everglades_monitor import USER_AGENT


class HttpError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class Fetcher:
    """Polite HTTP client with retries. Tests can substitute a fake."""

    def __init__(
        self,
        *,
        user_agent: str = USER_AGENT,
        timeout: float = 30.0,
        retries: int = 3,
        client: httpx.Client | None = None,
    ) -> None:
        self.retries = retries
        self._owns_client = client is None
        self.client = client or httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "*/*"},
            timeout=timeout,
            follow_redirects=True,
        )

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> Fetcher:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | list[tuple[str, str]] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = self.client.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(1.5 * (attempt + 1))
                continue
            if response.status_code in {429, 500, 502, 503, 504} and attempt + 1 < self.retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 1.5 * (attempt + 1)
                except ValueError:
                    delay = 1.5 * (attempt + 1)
                time.sleep(min(delay, 15))
                continue
            return response
        if last_error:
            raise HttpError(f"{method} {url} failed: {last_error}") from last_error
        raise HttpError(f"{method} {url} failed after retries")

    def get(
        self, url: str, *, params: dict[str, Any] | list[tuple[str, str]] | None = None
    ) -> httpx.Response:
        return self.request("GET", url, params=params)

    def get_json(
        self, url: str, *, params: dict[str, Any] | list[tuple[str, str]] | None = None
    ) -> Any:
        response = self.get(url, params=params)
        if response.status_code >= 400:
            raise HttpError(
                f"GET {url} returned {response.status_code}",
                status_code=response.status_code,
            )
        return response.json()

    def get_text(
        self, url: str, *, params: dict[str, Any] | list[tuple[str, str]] | None = None
    ) -> str:
        response = self.get(url, params=params)
        if response.status_code >= 400:
            raise HttpError(
                f"GET {url} returned {response.status_code}",
                status_code=response.status_code,
            )
        return response.text

    def post_json(
        self,
        url: str,
        payload: dict[str, Any],
        *,
        params: dict[str, Any] | list[tuple[str, str]] | None = None,
    ) -> Any:
        response = self.request("POST", url, params=params, json=payload)
        if response.status_code >= 400:
            raise HttpError(
                f"POST {url} returned {response.status_code}",
                status_code=response.status_code,
            )
        return response.json()
