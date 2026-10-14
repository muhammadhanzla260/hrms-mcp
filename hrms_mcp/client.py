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

    def _url(self, path: str) -> str:
        return self.base + "/" + path.lstrip("/")

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
                self._url(_env("HRMS_LOGIN_PATH")),
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

    def _post(self, path: str, payload: dict) -> dict:
        if not self._authed:
            self.login()
        resp = self.http.post(self._url(path), json=payload, timeout=30)
        if resp.status_code == 401:  # token expired: re-login once
            self._authed = False
            self.login()
            resp = self.http.post(self._url(path), json=payload, timeout=30)
        return self._check(resp)

    def timeline(self) -> list[dict]:
        body = self._post("/duty/timeline", {"gmt_offset": _env("HRMS_GMT_OFFSET")})
        data = body.get("data", [])
        return data if isinstance(data, list) else []

    def open_duty_id(self, records: list[dict]) -> str | None:
        """Id of today's still-open duty, or None if it can't be determined.

        The timeline's field names are unverified; we only trust a record that
        has an id and no end-like value, and only when exactly one matches.
        """
        end_keys = ("end_time", "end_at", "ended_at", "check_out", "end_date_time")
        open_ = [
            r for r in records
            if r.get("id") and not any(r.get(k) for k in end_keys)
        ]
        return str(open_[0]["id"]) if len(open_) == 1 else None

    def start_day(self, tasks: list[str], is_wfh: bool = True) -> dict:
        return self._post(
            "/duty/start",
            {
                "is_wfh": is_wfh,
                "start_task": "\n".join(tasks),
                "start_device_location": None,
                "start_gmt_offset": _env("HRMS_GMT_OFFSET"),
                "start_location_id": _env("HRMS_LOCATION_ID"),
            },
        )

    def end_payload(self, tasks: list[str], notes: str = "") -> dict:
        return {
            "end_task": "\n".join(tasks),
            "end_notes": notes,
            "end_device_location": None,
            "end_gmt_offset": _env("HRMS_GMT_OFFSET"),
            "end_location_id": _env("HRMS_LOCATION_ID"),
        }

    def end_day(self, tasks: list[str], notes: str = "", duty_id: str | None = None) -> dict:
        path = f"/duty/end/id/{duty_id}" if duty_id else "/duty/end"
        return self._post(path, self.end_payload(tasks, notes))
