"""Helpers that build the JSON envelope used by every JSON response."""

from fastapi.responses import JSONResponse


def success(data, message: str, status_code: int = 200, meta: dict | None = None) -> JSONResponse:
    body = {"success": True, "message": message, "data": data}
    if meta is not None:
        body["meta"] = meta
    return JSONResponse(status_code=status_code, content=body)


def error(status_code: int, code: str, message: str, details: list | None = None, headers: dict | None = None) -> JSONResponse:
    err = {"code": code, "message": message}
    if details:
        err["details"] = details
    return JSONResponse(status_code=status_code, content={"success": False, "error": err}, headers=headers)
