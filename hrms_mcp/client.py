"""Thin HRMS HTTP client. Endpoints and auth come from the environment."""
import os
from pathlib import Path

import requests


class HRMSError(RuntimeError):
    pass


def _env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "").strip()
    if required and not val:
        raise HRMSError(f"Missing config {name}; see .env.example / README.")
    return val


def _dig(data, dotted: str):
    for part in dotted.split("."):
        data = data[part]
    return data


class HRMSClient:
    def __init__(self):
        self.base = _env("HRMS_BASE_URL").rstrip("/")
        self.http = requests.Session()
        self.http.headers["Accept"] = "application/json"
        self._authed = False

    def _url(self, path_env: str) -> str:
        return self.base + "/" + _env(path_env).lstrip("/")

    def _check(self, resp: requests.Response) -> dict:
        try:
            body = resp.json()
        except ValueError:
            raise HRMSError(f"HTTP {resp.status_code}: non-JSON response")
        if resp.status_code >= 400 or body.get("success") is False:
            raise HRMSError(f"HTTP {resp.status_code}: {body}")
        return body

    def login(self) -> None:
        token = _env("HRMS_TOKEN", required=False)
        if token:
            self.http.headers["Authorization"] = f"Bearer {token}"
        else:
            resp = self.http.post(
                self._url("HRMS_LOGIN_PATH"),
                json={"email": _env("HRMS_EMAIL"), "password": _env("HRMS_PASSWORD")},
                timeout=30,
            )
            body = self._check(resp)
            field = _env("HRMS_TOKEN_FIELD", required=False) or "data.token"
            try:
                self.http.headers["Authorization"] = f"Bearer {_dig(body, field)}"
            except (KeyError, TypeError):
                # Cookie-based session: nothing more to do.
                if not self.http.cookies:
                    raise HRMSError(f"No token at '{field}' and no session cookie.")
        self._authed = True

    def _post(self, path_env: str, payload: dict) -> dict:
        if not self._authed:
            self.login()
        resp = self.http.post(self._url(path_env), json=payload, timeout=30)
        if resp.status_code == 401:  # token expired: re-login once
            self._authed = False
            self.login()
            resp = self.http.post(self._url(path_env), json=payload, timeout=30)
        return self._check(resp)

    def start_day(self) -> dict:
        return self._post("HRMS_START_PATH", {"gmt_offset": _env("HRMS_GMT_OFFSET")})

    def end_day(self, tasks: list[str], notes: str = "") -> dict:
        return self._post(
            "HRMS_END_PATH",
            {
                "end_task": "\n".join(tasks),
                "end_notes": notes,
                "end_device_location": None,
                "end_gmt_offset": _env("HRMS_GMT_OFFSET"),
                "end_location_id": _env("HRMS_LOCATION_ID"),
            },
        )
