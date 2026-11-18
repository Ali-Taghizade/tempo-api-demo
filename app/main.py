"""Project Tempo API prototype — application entry point.

Run with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI

app = FastAPI(
    title="Project Tempo API",
    version="1.0.0",
    description="Prototype REST API for weekly tasks with mocked data, token auth and role-based access.",
)
