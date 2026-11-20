"""CRUD endpoints for the task resource."""

from fastapi import APIRouter, Path, Query

from app import mock_data
from app.errors import NotFound
from app.responses import success
from app.schemas import DAY_ORDER, Category, Day, Priority

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

TaskId = Path(pattern=r"^task_\d+$", description="Task ID, e.g. task_101")


def _sort_key(task: dict):
    return (min(DAY_ORDER.index(d) for d in task["daysOfWeek"]), task["startTime"], task["id"])


def _find_task(task_id: str) -> dict:
    """Return the task or raise 404."""
    task = mock_data.tasks.get(task_id)
    if task is None:
        raise NotFound(f"Task '{task_id}' was not found.")
    return task


@router.get("", summary="List tasks")
def list_tasks(
    day: Day | None = Query(default=None, description="Only tasks that happen on this day"),
    category: Category | None = Query(default=None),
    priority: Priority | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=10, ge=1, le=50, alias="perPage"),
):
    visible = list(mock_data.tasks.values())

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
def get_task(task_id: str = TaskId):
    return success(_find_task(task_id), "Task retrieved successfully.")
