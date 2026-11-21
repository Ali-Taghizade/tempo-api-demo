# Project Tempo — API Prototype (Assignment 2)

Prototype REST API for **Project Tempo**, an AI-assisted weekly scheduling system.
This version exposes the **tasks** resource (a user's weekly routine items) with:

- Full CRUD on `/api/v1/tasks`
- Mock token authentication and role-based authorization (two users + one admin)
- Strict validation and structured JSON error responses
- An HTML greeting page at `/api/v1/greeting`

> **Mock data:** everything is stored in memory. All changes are lost and the seed data is restored
> **every time the server restarts.**

Built with **Python 3.10+**, **FastAPI** and **Uvicorn**. No database is used.

---

## Install

```bash
git clone https://github.com/Ali-Taghizade/tempo-api-demo.git
cd tempo-api-demo
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

- Greeting page: <http://localhost:8000/api/v1/greeting>
- Swagger UI: <http://localhost:8000/docs>

## Try it

```bash
curl -H "Authorization: Bearer user-a-token" http://localhost:8000/api/v1/tasks
```

| User | Token | Role |
|---|---|---|
| User A | `user-a-token` | user — manages only own tasks |
| User B | `user-b-token` | user — manages only own tasks |
| Admin | `admin-token` | admin — manages all tasks |

Example requests for every scenario (CRUD, 401, 403, 404, 405, 409, validation errors):

- [`docs/tempo.postman_collection.json`](docs/tempo.postman_collection.json) — import into Postman
- [`docs/requests.http`](docs/requests.http) — run from VS Code (REST Client) or JetBrains IDEs

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Documentation

Full API documentation: [`docs/API.md`](docs/API.md) — resource fields, validation rules, auth rules,
every endpoint with request/response examples, and all error codes.

Short version:

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/greeting` | HTML page (public) |
| GET | `/api/v1/tasks` | List tasks (`day`, `category`, `priority`, `ownerId`, `page`, `perPage`) |
| GET | `/api/v1/tasks/{id}` | Get one task |
| POST | `/api/v1/tasks` | Create a task → `201` |
| PUT | `/api/v1/tasks/{id}` | Replace a task |
| DELETE | `/api/v1/tasks/{id}` | Delete a task |

A regular user asking for another user's task gets **404** (not 403), so the API does not reveal that the task exists.
See [docs/API.md](docs/API.md#2-authentication-and-authorization) for the full reasoning.

## Project structure

```
app/
├── main.py            # FastAPI app, routers, exception handlers
├── auth.py            # Bearer token -> user, ownership checks
├── schemas.py         # Task request model and validation rules
├── mock_data.py       # In-memory users and tasks (reset on restart)
├── responses.py       # JSON envelope helpers
├── errors.py          # Custom errors + handlers (400/401/403/404/405/409/500)
└── routers/
    ├── tasks.py       # CRUD endpoints
    └── greeting.py    # HTML greeting page
docs/                  # API.md, Postman collection, .http examples
tests/                 # pytest suite covering every scenario
```

## Demo video

YouTube: <DEMO_VIDEO_LINK>

## Team and contributions

| Member | Student ID | Worked on |
|---|---|---|
| Ali Taghizade | `20425` | Project setup, response envelope, error handlers, validation schema and create endpoint with tests, API documentation |
| Emil Jafarov | `20416` | Mock data, list and get endpoints with filtering and pagination, HTML greeting page, their tests, README |
| Nuran Bayramov | `20546` | Token authentication and role checks, update and delete endpoints, conflict rule, their tests, example requests and Postman collection |

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for details.

### `git shortlog -sn --all`

```
     8	Emil Jafarov
     6	Ali Taghizade
     6	Nuran Bayramov
```
