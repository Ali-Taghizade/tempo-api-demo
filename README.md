# Project Tempo — API Prototype (Assignment 2)

Prototype REST API for **Project Tempo**, an AI-assisted weekly scheduling system.
Built with **Python 3.10+**, **FastAPI** and **Uvicorn**, using in-memory mock data (no database).

> Work in progress — endpoints will be added in the next commits.

## Install

```bash
git clone <REPOSITORY_URL>
cd tempo-api
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Then open the Swagger UI at <http://localhost:8000/docs>.
