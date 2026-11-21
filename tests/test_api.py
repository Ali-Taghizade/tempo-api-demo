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


def test_auth_checked_before_validation():
    assert_error(client.post("/api/v1/tasks", json={"title": "x"}), 401, "AUTH_REQUIRED")


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


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_user_a_cannot_touch_user_b_task(method):
    kwargs = {"json": VALID} if method == "put" else {}
    assert_error(getattr(client, method)("/api/v1/tasks/task_104", headers=A, **kwargs), 404, "NOT_FOUND")
    assert "task_104" in mock_data.tasks


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_user_b_cannot_touch_user_a_task(method):
    kwargs = {"json": VALID} if method == "put" else {}
    assert_error(getattr(client, method)("/api/v1/tasks/task_102", headers=B, **kwargs), 404, "NOT_FOUND")


# ---------- create ----------

def test_create_task():
    resp = client.post("/api/v1/tasks", headers=A, json=VALID)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["id"] == "task_108" and data["ownerId"] == "user-a"
    assert data["daysOfWeek"] == ["tue", "thu"]  # sorted
    assert data["priority"] == "medium" and data["isFixed"] is False and data["description"] is None


def test_user_cannot_create_for_other_user():
    assert_error(client.post("/api/v1/tasks", headers=A, json={**VALID, "ownerId": "user-b"}), 403, "FORBIDDEN")


def test_admin_creates_for_user():
    resp = client.post("/api/v1/tasks", headers=ADMIN, json={**VALID, "ownerId": "user-b"})
    assert resp.status_code == 201 and resp.json()["data"]["ownerId"] == "user-b"


def test_admin_unknown_owner():
    err = assert_error(client.post("/api/v1/tasks", headers=ADMIN, json={**VALID, "ownerId": "ghost"}), 400, "VALIDATION_ERROR")
    assert err["details"][0]["field"] == "ownerId"


def test_create_validation_errors():
    bad = {"title": "Hi", "daysOfWeek": ["monday"], "startTime": "10:00", "endTime": "09:00",
           "category": "study", "color": "red", "id": "task_1", "isFixed": "yes"}
    err = assert_error(client.post("/api/v1/tasks", headers=A, json=bad), 400, "VALIDATION_ERROR")
    by_field = {d["field"]: d["message"] for d in err["details"]}
    assert set(by_field) == {"title", "daysOfWeek[0]", "endTime", "color", "id", "isFixed"}
    assert by_field["color"] == "Unknown field."
    assert "read-only" in by_field["id"]


def test_create_missing_fields():
    err = assert_error(client.post("/api/v1/tasks", headers=A, json={}), 400, "VALIDATION_ERROR")
    assert {d["field"] for d in err["details"]} == {"title", "daysOfWeek", "startTime", "endTime", "category"}


def test_create_wrong_types_and_blank_title():
    err = assert_error(client.post("/api/v1/tasks", headers=A,
                                   json={**VALID, "title": "     ", "daysOfWeek": "mon", "startTime": 7}),
                       400, "VALIDATION_ERROR")
    assert {d["field"] for d in err["details"]} == {"title", "daysOfWeek", "startTime"}


def test_create_duplicate_days_and_bad_time():
    err = assert_error(client.post("/api/v1/tasks", headers=A,
                                   json={**VALID, "daysOfWeek": ["mon", "mon"], "endTime": "25:00"}),
                       400, "VALIDATION_ERROR")
    assert {d["field"] for d in err["details"]} == {"daysOfWeek", "endTime"}


def test_invalid_json_and_non_object():
    resp = client.post("/api/v1/tasks", headers={**A, "Content-Type": "application/json"}, content="{bad json")
    err = assert_error(resp, 400, "VALIDATION_ERROR")
    assert err["details"] == [{"field": "body", "message": "Request body must be valid JSON."}]
    assert_error(client.post("/api/v1/tasks", headers=A, json=[1, 2]), 400, "VALIDATION_ERROR")


def test_conflict_with_fixed_task():
    err = assert_error(client.post("/api/v1/tasks", headers=A,
                                   json={**VALID, "daysOfWeek": ["mon"], "startTime": "09:30", "endTime": "10:00"}),
                       409, "CONFLICT")
    assert "task_101" in err["message"]
    assert "task_108" not in mock_data.tasks


def test_flexible_tasks_may_overlap():
    resp = client.post("/api/v1/tasks", headers=A,
                       json={**VALID, "daysOfWeek": ["mon"], "startTime": "18:30", "endTime": "19:30"})
    assert resp.status_code == 201


def test_other_users_fixed_tasks_do_not_conflict():
    resp = client.post("/api/v1/tasks", headers=A,
                       json={**VALID, "daysOfWeek": ["tue"], "startTime": "14:00", "endTime": "15:00"})
    assert resp.status_code == 201


# ---------- update ----------

def test_update_own_task():
    resp = client.put("/api/v1/tasks/task_102", headers=A, json={**VALID, "title": "Evening gym"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["id"] == "task_102" and data["title"] == "Evening gym"
    assert data["createdAt"] == "2026-11-10T08:00:00Z" and data["updatedAt"] != data["createdAt"]


def test_update_fixed_task_does_not_conflict_with_itself():
    body = {"title": "Data Structures lecture", "daysOfWeek": ["mon", "wed"], "startTime": "09:00",
            "endTime": "11:00", "category": "study", "isFixed": True}
    assert client.put("/api/v1/tasks/task_101", headers=A, json=body).status_code == 200


def test_update_requires_full_body():
    assert_error(client.put("/api/v1/tasks/task_102", headers=A, json={"title": "Only title"}), 400, "VALIDATION_ERROR")


def test_update_non_existent():
    assert_error(client.put("/api/v1/tasks/task_999", headers=A, json=VALID), 404, "NOT_FOUND")


def test_admin_updates_any_task():
    resp = client.put("/api/v1/tasks/task_104", headers=ADMIN,
                      json={**VALID, "daysOfWeek": ["mon"], "title": "Moved shift"})
    assert resp.status_code == 200
    assert resp.json()["data"]["ownerId"] == "user-b"  # owner kept when ownerId omitted


# ---------- delete ----------

def test_delete_own_task():
    resp = client.delete("/api/v1/tasks/task_103", headers=A)
    assert resp.status_code == 200 and resp.json()["data"] is None
    assert_error(client.get("/api/v1/tasks/task_103", headers=A), 404, "NOT_FOUND")


def test_admin_deletes_any_task():
    assert client.delete("/api/v1/tasks/task_105", headers=ADMIN).status_code == 200
    assert "task_105" not in mock_data.tasks


# ---------- routing ----------

def test_method_not_allowed():
    resp = client.patch("/api/v1/tasks/task_101", headers=A, json={})
    assert_error(resp, 405, "METHOD_NOT_ALLOWED")
    assert "PUT" in resp.headers["allow"]
    assert_error(client.delete("/api/v1/tasks", headers=A), 405, "METHOD_NOT_ALLOWED")


def test_unknown_route():
    assert_error(client.get("/api/v1/nothing"), 404, "ROUTE_NOT_FOUND")