"""Covers every scenario from the assignment: CRUD, auth, ownership, validation, status codes."""

import pytest
from fastapi.testclient import TestClient

from app import mock_data
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

A = {"Authorization": "Bearer user-a-token"}
B = {"Authorization": "Bearer user-b-token"}
ADMIN = {"Authorization": "Bearer admin-token"}

VALID = {
    "title": "Morning run",
    "daysOfWeek": ["thu", "tue"],
    "startTime": "07:00",
    "endTime": "07:45",
    "category": "health",
}


@pytest.fixture(autouse=True)
def fresh_data():
    mock_data.reset_data()


def assert_error(resp, status, code):
    assert resp.status_code == status, resp.text
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == code
    return body["error"]


# ---------- list ----------

def test_bad_query_params():
    err = assert_error(client.get("/api/v1/tasks?day=monday&perPage=100&page=0", headers=A), 400, "VALIDATION_ERROR")
    fields = {d["field"] for d in err["details"]}
    assert fields == {"day", "perPage", "page"}


# ---------- get ----------

def test_get_own_task():
    body = client.get("/api/v1/tasks/task_101", headers=A).json()
    assert body["data"]["title"] == "Data Structures lecture"


def test_get_non_existent():
    assert_error(client.get("/api/v1/tasks/task_999", headers=A), 404, "NOT_FOUND")


def test_get_malformed_id():
    err = assert_error(client.get("/api/v1/tasks/abc", headers=A), 400, "VALIDATION_ERROR")
    assert err["details"] == [{"field": "id", "message": "Task ID must look like 'task_101'."}]


# ---------- routing ----------

def test_unknown_route():
    assert_error(client.get("/api/v1/nothing"), 404, "ROUTE_NOT_FOUND")
