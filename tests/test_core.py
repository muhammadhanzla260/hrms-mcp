import json
import os

import pytest
import responses  # noqa: F401  (pip install responses)

from hrms_mcp import journal
from hrms_mcp.client import HRMSClient


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("HRMS_MCP_HOME", str(tmp_path))
    for k, v in {
        "HRMS_BASE_URL": "https://hrms.test", "HRMS_EMAIL": "a@b.c", "HRMS_PASSWORD": "x",
        "HRMS_LOGIN_PATH": "/login", "HRMS_START_PATH": "/start", "HRMS_END_PATH": "/end",
        "HRMS_LOCATION_ID": "8", "HRMS_GMT_OFFSET": "+18000",
    }.items():
        monkeypatch.setenv(k, v)


def test_journal_dedupes():
    journal.add_task("A"); journal.add_task("A"); journal.add_task("B")
    assert journal.tasks_for() == ["A", "B"]


@responses.activate
def test_end_day_payload():
    responses.post("https://hrms.test/login", json={"success": True, "data": {"token": "t"}})
    responses.post("https://hrms.test/end", json={"success": True})
    HRMSClient().end_day(["A", "B"], "n")
    sent = json.loads(responses.calls[1].request.body)
    assert sent["end_task"] == "A\nB" and sent["end_location_id"] == "8"
    assert responses.calls[1].request.headers["Authorization"] == "Bearer t"


@responses.activate
def test_start_day_payload():
    responses.post("https://hrms.test/login", json={"success": True, "data": {"token": "t"}})
    responses.post("https://hrms.test/start", json={"success": True})
    HRMSClient().start_day(["A", "B"])
    sent = json.loads(responses.calls[1].request.body)
    assert sent == {"is_wfh": True, "start_task": "A\nB", "start_device_location": None,
                    "start_gmt_offset": "+18000", "start_location_id": "8"}
