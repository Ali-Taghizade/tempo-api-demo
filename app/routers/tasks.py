"""CRUD endpoints for the task resource."""

from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, Path, Query

from app import mock_data
from app.auth import can_access, get_current_user, is_admin
from app.errors import Conflict, Forbidden, NotFound, ValidationFailed
from app.responses import success
from app.schemas import DAY_ORDER, Category, Day, Priority, TaskIn

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

TaskId = Path(pattern=r"^task_\d+$", description="Task ID, e.g. task_101")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sort_key(task: dict):
    return (min(DAY_ORDER.index(d) for d in task["daysOfWeek"]), task["startTime"], task["id"])


def _find_task(task_id: str, user: dict) -> dict:
    """Return the task if it exists AND the user may access it.

    A regular user asking for another user's task gets 404 (not 403) so the API
    does not reveal that the task exists.
    """
    task = mock_data.tasks.get(task_id)
    if task is None or not can_access(user, task):
        raise NotFound(f"Task '{task_id}' was not found.")
    return task


def _resolve_owner(body: TaskIn, user: dict, current_owner: str | None = None) -> str:
    """Decide who owns the task after a create/update."""
    requested = body.ownerId
    if requested is None:
        return current_owner or user["id"]
    if not is_admin(user) and requested != user["id"]:
        raise Forbidden("You can only create or update tasks for yourself.")
    if requested not in mock_data.USER_IDS:
        raise ValidationFailed([{"field": "ownerId", "message": f"User '{requested}' does not exist."}])
    return requested


def _check_conflict(candidate: dict, ignore_id: str | None = None) -> None:
    """409 if the task overlaps a fixed task of the same owner (or is fixed and overlaps any of their tasks)."""
    for other in mock_data.tasks.values():
        if other["id"] == ignore_id or other["ownerId"] != candidate["ownerId"]:
            continue
        if not (candidate["isFixed"] or other["isFixed"]):
            continue  # two flexible tasks may overlap
        shared_days = set(candidate["daysOfWeek"]) & set(other["daysOfWeek"])
        overlaps = candidate["startTime"] < other["endTime"] and other["startTime"] < candidate["endTime"]
        if shared_days and overlaps:
            days = ", ".join(sorted(shared_days, key=DAY_ORDER.index))
            raise Conflict(
                f"Task overlaps '{other['title']}' ({other['id']}) on {days} "
                f"{other['startTime']}-{other['endTime']}. Fixed tasks cannot overlap other tasks of the same owner."
            )


@router.get("", summary="List tasks")
def list_tasks(
    user: dict = Depends(get_current_user),
    day: Day | None = Query(default=None, description="Only tasks that happen on this day"),
    category: Category | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    owner_id: str | None = Query(default=None, alias="ownerId", description="Admin only: filter by owner"),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50, alias="perPage"),
):
    if is_admin(user):
        visible = list(mock_data.tasks.values())
        if owner_id is not None:
            visible = [t for t in visible if t["ownerId"] == owner_id]
    else:
        if owner_id is not None and owner_id != user["id"]:
            raise Forbidden("Only administrators can list tasks of other users.")
        visible = [t for t in mock_data.tasks.values() if t["ownerId"] == user["id"]]

    if day is not None:
        visible = [t for t in visible if day in t["daysOfWeek"]]
    if category is not None:
        visible = [t for t in visible if t["category"] == category]
    if priority is not None:
        visible = [t for t in visible if t["priority"] == priority]

    visible.sort(key=_sort_key)
    start = (page - 1) * per_page
    return success(
        visible[start:start + per_page],
        "Tasks retrieved successfully.",
        meta={"total": len(visible), "page": page, "perPage": per_page},
    )


@router.get("/{task_id}", summary="Get one task")
def get_task(task_id: str = TaskId, user: dict = Depends(get_current_user)):
    return success(_find_task(task_id, user), "Task retrieved successfully.")


@router.post("", status_code=201, summary="Create a task")
def create_task(body: TaskIn = Body(...), user: dict = Depends(get_current_user)):
    owner_id = _resolve_owner(body, user)
    now = _now()
    task = {
        "id": None,  # assigned after the conflict check so no IDs are wasted
        "ownerId": owner_id,
        **body.model_dump(exclude={"ownerId"}),
        "createdAt": now,
        "updatedAt": now,
    }
    _check_conflict(task)
    task["id"] = mock_data.next_task_id()
    mock_data.tasks[task["id"]] = task
    return success(task, "Task created successfully.", status_code=201)


@router.put("/{task_id}", summary="Replace a task")
def update_task(task_id: str = TaskId, body: TaskIn = Body(...), user: dict = Depends(get_current_user)):
    existing = _find_task(task_id, user)
    owner_id = _resolve_owner(body, user, current_owner=existing["ownerId"])
    updated = {
        "id": existing["id"],
        "ownerId": owner_id,
        **body.model_dump(exclude={"ownerId"}),
        "createdAt": existing["createdAt"],
        "updatedAt": _now(),
    }
    _check_conflict(updated, ignore_id=task_id)
    mock_data.tasks[task_id] = updated
    return success(updated, "Task updated successfully.")


@router.delete("/{task_id}", summary="Delete a task")
def delete_task(task_id: str = TaskId, user: dict = Depends(get_current_user)):
    _find_task(task_id, user)
    del mock_data.tasks[task_id]
    return success(None, "Task deleted successfully.")