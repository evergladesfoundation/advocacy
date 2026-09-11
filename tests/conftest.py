from __future__ import annotations

from typing import Any


class FakeResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_data: Any = None,
        text: str = "",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_data
        self.text = text
        self.headers = headers or {}

    def json(self) -> Any:
        return self._json


class FakeFetcher:
    def __init__(self, routes: dict[str, FakeResponse | dict | str | list] | None = None) -> None:
        self.routes = routes or {}
        self.calls: list[tuple[str, str]] = []

    def add(self, needle: str, value: FakeResponse | dict | str | list) -> None:
        self.routes[needle] = value

    def _lookup(self, url: str) -> FakeResponse:
        for needle, value in self.routes.items():
            if needle in url:
                if isinstance(value, FakeResponse):
                    return value
                if isinstance(value, str):
                    return FakeResponse(text=value)
                return FakeResponse(json_data=value)
        return FakeResponse(status_code=404, json_data={"error": "not found"}, text="not found")

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url))
        return self._lookup(url)

    def get(self, url: str, *, params: Any = None) -> FakeResponse:
        return self.request("GET", url, params=params)

    def get_json(self, url: str, *, params: Any = None) -> Any:
        response = self.get(url, params=params)
        if response.status_code >= 400:
            from everglades_monitor.http_client import HttpError

            raise HttpError(f"GET {url} returned {response.status_code}", status_code=response.status_code)
        return response.json()

    def get_text(self, url: str, *, params: Any = None) -> str:
        response = self.get(url, params=params)
        if response.status_code >= 400:
            from everglades_monitor.http_client import HttpError

            raise HttpError(f"GET {url} returned {response.status_code}", status_code=response.status_code)
        return response.text

    def post_json(self, url: str, payload: dict[str, Any], *, params: Any = None) -> Any:
        response = self.request("POST", url, json=payload, params=params)
        if response.status_code >= 400:
            from everglades_monitor.http_client import HttpError

            raise HttpError(f"POST {url} returned {response.status_code}", status_code=response.status_code)
        return response.json()
