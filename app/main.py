"""Project Tempo API prototype — application entry point.

Run with:  uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI

from app.errors import register_exception_handlers

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Project Tempo API",
    version="1.0.0",
    description="Prototype REST API for weekly tasks with mocked data, token auth and role-based access.",
)

register_exception_handlers(app)
