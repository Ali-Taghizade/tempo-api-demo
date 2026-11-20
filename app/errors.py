"""Custom API errors and the exception handlers that turn every error into the JSON envelope."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match

from app.responses import error

logger = logging.getLogger("tempo")

READ_ONLY_FIELDS = {"id", "createdAt", "updatedAt"}

# Python parameter names shown to clients under their public names.
PARAM_NAMES = {"task_id": "id"}


class ApiError(Exception):
    """Raise anywhere in the app to return a structured error response."""

    def __init__(self, status_code: int, code: str, message: str, details: list | None = None, headers: dict | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


class AuthRequired(ApiError):
    def __init__(self, message: str = "Authentication is required. Send 'Authorization: Bearer <token>'."):
        super().__init__(401, "AUTH_REQUIRED", message, headers={"WWW-Authenticate": "Bearer"})


class InvalidToken(ApiError):
    def __init__(self):
        super().__init__(401, "INVALID_TOKEN", "The provided token is invalid.", headers={"WWW-Authenticate": "Bearer"})


class Forbidden(ApiError):
    def __init__(self, message: str):
        super().__init__(403, "FORBIDDEN", message)


class NotFound(ApiError):
    def __init__(self, message: str):
        super().__init__(404, "NOT_FOUND", message)


class Conflict(ApiError):
    def __init__(self, message: str):
        super().__init__(409, "CONFLICT", message)


class ValidationFailed(ApiError):
    def __init__(self, details: list[dict]):
        super().__init__(400, "VALIDATION_ERROR", "The request contains invalid or missing fields.", details)


# ---------- validation error formatting ----------

def _field_name(loc: tuple) -> str:
    """('body', 'daysOfWeek', 0) -> 'daysOfWeek[0]'; ('query', 'page') -> 'page'."""
    parts = list(loc[1:]) if loc and loc[0] in ("body", "query", "path", "header") else list(loc)
    name = ""
    for part in parts:
        if isinstance(part, int):
            name += f"[{part}]"
        else:
            name += f".{part}" if name else str(part)
    return name or "body"


def _friendly_message(err: dict, field: str) -> str:
    err_type = err.get("type", "")
    ctx = err.get("ctx") or {}

    if err_type == "missing":
        return "Request body is required." if field == "body" else "This field is required."
    if err_type == "extra_forbidden":
        return "This field is read-only and cannot be set." if field in READ_ONLY_FIELDS else "Unknown field."
    if err_type == "json_invalid":
        return "Request body must be valid JSON."
    if err_type in ("model_attributes_type", "dict_type", "model_type"):
        return "Request body must be a JSON object."
    if err_type == "string_type":
        return "Must be a string."
    if err_type == "bool_type":
        return "Must be a boolean (true or false)."
    if err_type in ("int_type", "int_parsing"):
        return "Must be an integer."
    if err_type == "list_type":
        return "Must be an array."
    if err_type == "string_too_short":
        return f"Must contain at least {ctx.get('min_length')} characters."
    if err_type == "string_too_long":
        return f"Must contain at most {ctx.get('max_length')} characters."
    if err_type == "too_short":
        return f"Must contain at least {ctx.get('min_length')} item(s)."
    if err_type == "too_long":
        return f"Must contain at most {ctx.get('max_length')} items."
    if err_type == "greater_than_equal":
        return f"Must be greater than or equal to {ctx.get('ge')}."
    if err_type == "less_than_equal":
        return f"Must be less than or equal to {ctx.get('le')}."
    if err_type == "literal_error":
        expected = str(ctx.get("expected", "")).replace("'", "").replace(" or ", ", ")
        return f"Must be one of: {expected}."
    if err_type == "string_pattern_mismatch":
        if field in ("startTime", "endTime"):
            return "Must be a time in HH:MM 24-hour format (e.g. 09:30)."
        if field == "id":
            return "Task ID must look like 'task_101'."
        return "Has an invalid format."
    if err_type == "value_error":
        # Messages raised from our own validators.
        return str(ctx.get("error", err.get("msg", "Invalid value.")))
    return "Invalid value."


def format_validation_errors(errors) -> list[dict]:
    details = []
    for err in errors:
        if err.get("type") == "json_invalid":
            field = "body"
        else:
            field = _field_name(tuple(err.get("loc", ())))
            field = PARAM_NAMES.get(field, field)
        details.append({"field": field, "message": _friendly_message(err, field)})
    return details


# ---------- handlers ----------

async def api_error_handler(request: Request, exc: ApiError):
    return error(exc.status_code, exc.code, exc.message, exc.details, exc.headers)


async def request_validation_handler(request: Request, exc: RequestValidationError):
    # FastAPI uses 422 by default; this API returns 400 for every validation error.
    return error(400, "VALIDATION_ERROR", "The request contains invalid or missing fields.",
                 format_validation_errors(exc.errors()))


def _allowed_methods(request: Request) -> list[str]:
    """Methods that would match this path (Starlette's own Allow header lists only the first route)."""
    allowed = []
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        scope = {**request.scope, "method": method}
        if any(route.matches(scope)[0] == Match.FULL for route in request.app.routes):
            allowed.append(method)
    return allowed


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return error(404, "ROUTE_NOT_FOUND", f"The endpoint '{request.url.path}' does not exist.")
    if exc.status_code == 405:
        allowed = _allowed_methods(request)
        return error(405, "METHOD_NOT_ALLOWED",
                     f"Method {request.method} is not allowed for '{request.url.path}'. Allowed: {', '.join(allowed)}.",
                     headers={"Allow": ", ".join(allowed)})
    return error(exc.status_code, "HTTP_ERROR", str(exc.detail), headers=exc.headers)


async def unhandled_exception_handler(request: Request, exc: Exception):
    # Log the real problem for developers, return a generic message to the client.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error(500, "INTERNAL_ERROR", "An unexpected error occurred. Please try again later.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
