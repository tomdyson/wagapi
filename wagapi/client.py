from __future__ import annotations

from typing import Any

import httpx

from wagapi.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    WagapiError,
)


class WagtailClient:
    """Synchronous HTTP client for the Wagtail Write API."""

    def __init__(self, url: str, token: str) -> None:
        self.base_url = url.rstrip("/")
        self.token = token
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Token {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def close(self) -> None:
        self._http.close()

    # -- low-level -----------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: Any = None,
        **kwargs: Any,
    ) -> Any:
        try:
            resp = self._http.request(
                method,
                path,
                params=params,
                json=json,
                **kwargs,
            )
        except httpx.ConnectError as exc:
            raise NetworkError(f"Could not connect to {self.base_url}: {exc}") from exc
        except httpx.TimeoutException as exc:
            raise NetworkError(f"Request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            raise NetworkError(str(exc)) from exc

        if resp.status_code == 204:
            return None

        if resp.status_code == 401:
            raise AuthError("Invalid or missing API token")
        if resp.status_code == 403:
            raise PermissionDeniedError(
                resp.json().get("detail", "Permission denied")
            )
        if resp.status_code == 404:
            raise NotFoundError(resp.json().get("detail", "Not found"))
        if resp.status_code in (400, 422):
            body = resp.json()
            msg = body.get("detail", body.get("message", str(body)))
            raise ValidationError(str(msg), details=body)

        if resp.status_code >= 400:
            raise WagapiError(
                f"Unexpected API error {resp.status_code}: {resp.text}"
            )

        if not resp.content:
            return None
        return resp.json()

    # -- schema --------------------------------------------------------------

    def list_page_types(self) -> list[dict]:
        data = self._request("GET", "/schema/page-types/")
        if isinstance(data, list):
            return data
        return data.get("items", data.get("results", [data]))

    def get_page_type_schema(self, page_type: str) -> dict:
        return self._request("GET", f"/schema/page-types/{page_type}/")

    # -- pages ---------------------------------------------------------------

    def list_pages(self, **filters: Any) -> dict:
        params = {k: v for k, v in filters.items() if v is not None}
        return self._request("GET", "/pages/", params=params)

    def get_page(self, page_id: int, *, version: str | None = None) -> dict:
        params = {}
        if version:
            params["version"] = version
        return self._request("GET", f"/pages/{page_id}/", params=params or None)

    def create_page(self, data: dict) -> dict:
        return self._request("POST", "/pages/", json=data)

    def update_page(self, page_id: int, data: dict) -> dict:
        return self._request("PATCH", f"/pages/{page_id}/", json=data)

    def delete_page(self, page_id: int) -> None:
        self._request("DELETE", f"/pages/{page_id}/")

    def publish_page(self, page_id: int) -> dict:
        return self._request("POST", f"/pages/{page_id}/publish/")

    def unpublish_page(self, page_id: int) -> dict:
        return self._request("POST", f"/pages/{page_id}/unpublish/")

    # -- images --------------------------------------------------------------

    def list_images(self, **filters: Any) -> dict:
        params = {k: v for k, v in filters.items() if v is not None}
        return self._request("GET", "/images/", params=params or None)

    def get_image(self, image_id: int) -> dict:
        return self._request("GET", f"/images/{image_id}/")
