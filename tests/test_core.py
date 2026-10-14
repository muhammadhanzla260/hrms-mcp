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
        "HRMS_LOGIN_PATH": "/login",
        "HRMS_LOCATION_ID": "8", "HRMS_GMT_OFFSET": "+18000",
    }.items():
        monkeypatch.setenv(k, v)


def test_journal_dedupes():
    journal.add_task("A"); journal.add_task("A"); journal.add_task("B")
    assert journal.tasks_for() == ["A", "B"]


@responses.activate
def test_end_day_payload():
    responses.post("https://hrms.test/login", json={"success": True, "data": {"token": "t"}})
    responses.post("https://hrms.test/duty/end", json={"success": True})
    HRMSClient().end_day(["A", "B"], "n")
    sent = json.loads(responses.calls[1].request.body)
    assert sent["end_task"] == "A\nB" and sent["end_location_id"] == "8"
    assert responses.calls[1].request.headers["Authorization"] == "Bearer t"


@responses.activate
def test_start_day_payload():
    responses.post("https://hrms.test/login", json={"success": True, "data": {"token": "t"}})
    responses.post("https://hrms.test/duty/start", json={"success": True})
    HRMSClient().start_day(["A", "B"])
    sent = json.loads(responses.calls[1].request.body)
    assert sent == {"is_wfh": True, "start_task": "A\nB", "start_device_location": None,
                    "start_gmt_offset": "+18000", "start_location_id": "8"}


@responses.activate
def test_end_uses_open_duty_id():
    responses.post("https://hrms.test/login", json={"success": True, "data": {"token": "t"}})
    responses.post("https://hrms.test/duty/timeline", json={"success": True, "data": [
        {"id": 5, "end_time": "10:00"}, {"id": 7, "end_time": None}]})
    responses.post("https://hrms.test/duty/end/id/7", json={"success": True})
    c = HRMSClient()
    c.end_day(["A"], "", c.open_duty_id(c.timeline()))
    assert responses.calls[-1].request.url.endswith("/duty/end/id/7")


def test_open_duty_id_refuses_ambiguity():
    c = HRMSClient.__new__(HRMSClient)
    assert c.open_duty_id([{"id": 1}, {"id": 2}]) is None
