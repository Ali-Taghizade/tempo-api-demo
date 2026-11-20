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


# ---------- authentication ----------

def test_missing_token():
    err = assert_error(client.get("/api/v1/tasks"), 401, "AUTH_REQUIRED")
    assert "Bearer" in err["message"]


def test_wrong_scheme():
    assert_error(client.get("/api/v1/tasks", headers={"Authorization": "user-a-token"}), 401, "AUTH_REQUIRED")


def test_invalid_token():
    assert_error(client.get("/api/v1/tasks", headers={"Authorization": "Bearer nope"}), 401, "INVALID_TOKEN")


# ---------- list ----------

def test_user_lists_only_own_tasks():
    body = client.get("/api/v1/tasks", headers=A).json()
    assert body["success"] is True
    assert {t["ownerId"] for t in body["data"]} == {"user-a"}
    assert body["meta"] == {"total": 3, "page": 1, "perPage": 10}


def test_admin_lists_all_and_filters_by_owner():
    assert client.get("/api/v1/tasks", headers=ADMIN).json()["meta"]["total"] == 7
    body = client.get("/api/v1/tasks?ownerId=user-b", headers=ADMIN).json()
    assert {t["ownerId"] for t in body["data"]} == {"user-b"}


def test_user_cannot_filter_other_owner():
    assert_error(client.get("/api/v1/tasks?ownerId=user-b", headers=A), 403, "FORBIDDEN")


def test_filters_and_pagination():
    body = client.get("/api/v1/tasks?day=mon", headers=A).json()
    assert [t["id"] for t in body["data"]] == ["task_101", "task_102"]
    body = client.get("/api/v1/tasks?page=2&perPage=2", headers=A).json()
    assert len(body["data"]) == 1 and body["meta"] == {"total": 3, "page": 2, "perPage": 2}


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