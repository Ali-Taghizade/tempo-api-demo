"""In-memory mock data. Everything resets when the server restarts."""

import copy

# Predefined users. The token is the only "credential" in this prototype.
USERS_BY_TOKEN: dict[str, dict] = {
    "user-a-token": {"id": "user-a", "name": "User A", "role": "user"},
    "user-b-token": {"id": "user-b", "name": "User B", "role": "user"},
    "admin-token": {"id": "admin", "name": "Administrator", "role": "admin"},
}

USER_IDS: set[str] = {user["id"] for user in USERS_BY_TOKEN.values()}

_SEED_TIME = "2026-11-10T08:00:00Z"


def _task(task_id, owner_id, title, description, days, start, end, category, priority, is_fixed):
    return {
        "id": task_id,
        "ownerId": owner_id,
        "title": title,
        "description": description,
        "daysOfWeek": days,
        "startTime": start,
        "endTime": end,
        "category": category,
        "priority": priority,
        "isFixed": is_fixed,
        "createdAt": _SEED_TIME,
        "updatedAt": _SEED_TIME,
    }


_SEED_TASKS = [
    _task("task_101", "user-a", "Data Structures lecture", "Room 204", ["mon", "wed"], "09:00", "10:30", "study", "high", True),
    _task("task_102", "user-a", "Gym", None, ["mon", "wed", "fri"], "18:00", "19:00", "health", "medium", False),
    _task("task_103", "user-a", "Read a book", "At least 30 pages", ["sun"], "20:00", "21:00", "personal", "low", False),
    _task("task_104", "user-b", "Part-time job shift", "Campus library", ["tue", "thu"], "13:00", "17:00", "work", "high", True),
    _task("task_105", "user-b", "Spanish practice", None, ["mon", "fri"], "19:00", "19:30", "study", "medium", False),
    _task("task_106", "user-b", "Grocery shopping", None, ["sat"], "11:00", "12:00", "personal", "low", False),
    _task("task_107", "admin", "Server maintenance review", "Check logs and alerts", ["fri"], "10:00", "11:00", "work", "high", True),
]

# task_999 is intentionally never created: use it to demonstrate 404 Not Found.
NON_EXISTENT_TASK_ID = "task_999"

tasks: dict[str, dict] = {}
_next_id = 0


def reset_data() -> None:
    """Restore the seed data (called on startup and by the tests)."""
    global _next_id
    tasks.clear()
    for task in _SEED_TASKS:
        tasks[task["id"]] = copy.deepcopy(task)
    _next_id = 108


def next_task_id() -> str:
    global _next_id
    task_id = f"task_{_next_id}"
    _next_id += 1
    return task_id


reset_data()
