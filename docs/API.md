# Project Tempo API — Documentation (v1)

Base URL: `http://localhost:8000`
Interactive Swagger UI: `http://localhost:8000/docs`

All data is mocked in memory and **resets when the server restarts**.

---

## 1. Resource: Task

A **task** is a weekly item in a user's routine. It repeats every week on the selected days
(e.g. "Gym — Mon/Wed/Fri 18:00–19:00"). One-off *events* that reshape a week are not part of this prototype.

| Field | Type | Required | Rules |
|---|---|---|---|
| `id` | string | read-only | Server-generated, format `task_<number>` |
| `ownerId` | string | no | Defaults to the caller. Admin may set any existing user. A regular user may only send their own id |
| `title` | string | **yes** | 3–100 characters; leading/trailing spaces are trimmed; cannot be only spaces |
| `description` | string \| null | no | Max 500 characters; empty string becomes `null` |
| `daysOfWeek` | string[] | **yes** | 1–7 unique values from `mon tue wed thu fri sat sun`; returned in week order |
| `startTime` | string | **yes** | `HH:MM` 24-hour format |
| `endTime` | string | **yes** | `HH:MM`, must be later than `startTime` |
| `category` | string | **yes** | `study`, `work`, `personal`, `health`, `other` |
| `priority` | string | no | `low`, `medium`, `high` — default `medium` |
| `isFixed` | boolean | no | `true` = binding commitment that cannot move — default `false` |
| `createdAt` | string | read-only | ISO 8601 UTC |
| `updatedAt` | string | read-only | ISO 8601 UTC |

Types are **strict**: `"isFixed": "yes"`, `"startTime": 7` or `"daysOfWeek": "mon"` are rejected.
Unknown fields are rejected (`Unknown field.`), and read-only fields in a body are rejected
(`This field is read-only and cannot be set.`).

### Conflict rule

A task **conflicts** (`409`) with another task when they have the same owner, share at least one day,
their time ranges overlap, and at least one of the two is `isFixed: true`.
Two flexible tasks may overlap. On update, a task is never compared with itself.

---

## 2. Authentication and authorization

Send the token in every `/api/v1/tasks` request:

```http
Authorization: Bearer user-a-token
```

| User | Token | userId | Role | Can do |
|---|---|---|---|---|
| User A | `user-a-token` | `user-a` | user | CRUD on own tasks only |
| User B | `user-b-token` | `user-b` | user | CRUD on own tasks only |
| Administrator | `admin-token` | `admin` | admin | CRUD on all tasks, create for any user |

| Situation | Result |
|---|---|
| No `Authorization` header, or not in `Bearer <token>` format | `401 AUTH_REQUIRED` |
| Unknown token | `401 INVALID_TOKEN` |
| Regular user reads/updates/deletes another user's task | `404 NOT_FOUND` |
| Regular user sends `ownerId` of another user (body or `?ownerId=` filter) | `403 FORBIDDEN` |

**Why 404 and not 403 for other users' tasks?** A `403` would confirm that the task ID exists and belongs
to somebody else, which leaks information about other users' data (an attacker could enumerate IDs).
With `404`, a task you don't own looks exactly like a task that doesn't exist.
We still use `403` where the user is clearly asking for something they are not allowed to do
(acting on behalf of another owner) — no hidden data is revealed in that case.

Authentication is checked before body validation, so a request without a token always gets `401`.

---

## 3. Response format

Success:

```json
{ "success": true, "message": "Task retrieved successfully.", "data": { "...": "..." } }
```

List (adds `meta`):

```json
{ "success": true, "message": "Tasks retrieved successfully.", "data": [], "meta": { "total": 0, "page": 1, "perPage": 10 } }
```

Error:

```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Task 'task_999' was not found." } }
```

`error.details` (list of `{ field, message }`) is present only for `VALIDATION_ERROR`.
Error messages never contain stack traces or internal details.

### Error codes

| HTTP | `error.code` | Meaning |
|---:|---|---|
| 400 | `VALIDATION_ERROR` | Invalid/missing body fields, query or path parameters, invalid JSON |
| 401 | `AUTH_REQUIRED` | Token missing or header in wrong format |
| 401 | `INVALID_TOKEN` | Token is not recognized |
| 403 | `FORBIDDEN` | Authenticated, but the action is not allowed for this role |
| 404 | `NOT_FOUND` | Task does not exist (or is not visible to this user) |
| 404 | `ROUTE_NOT_FOUND` | URL does not exist |
| 405 | `METHOD_NOT_ALLOWED` | HTTP method not supported on this URL (`Allow` header lists valid ones) |
| 409 | `CONFLICT` | Task overlaps a fixed task of the same owner |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 4. Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/greeting` | none | HTML page with project info, team, endpoints and status |
| GET | `/api/v1/tasks` | user / admin | List tasks |
| GET | `/api/v1/tasks/{id}` | owner / admin | Get one task |
| POST | `/api/v1/tasks` | user / admin | Create a task |
| PUT | `/api/v1/tasks/{id}` | owner / admin | Replace a task |
| DELETE | `/api/v1/tasks/{id}` | owner / admin | Delete a task |

---

### 4.1 GET `/api/v1/greeting`

- **Headers:** none. **Auth:** public.
- **Response:** `200`, `Content-Type: text/html; charset=utf-8` — a styled, responsive HTML page
  with project description, team members, endpoint list and API status/version.

---

### 4.2 GET `/api/v1/tasks` — list tasks

- **Headers:** `Authorization: Bearer <token>`
- **Visibility:** regular users see only their own tasks; admin sees all.
- **Query parameters** (all optional):

| Param | Type | Rules |
|---|---|---|
| `day` | string | one of `mon`…`sun`; only tasks happening that day |
| `category` | string | valid category |
| `priority` | string | valid priority |
| `ownerId` | string | admin: filter by owner. User: only own id allowed, otherwise `403` |
| `page` | integer | ≥ 1, default `1` |
| `perPage` | integer | 1–50, default `10` |

- **Sorting:** by first day of the week, then `startTime`.
- **Success:** `200` + `meta { total, page, perPage }`
- **Errors:** `400 VALIDATION_ERROR`, `401 AUTH_REQUIRED`, `401 INVALID_TOKEN`, `403 FORBIDDEN`

Request:

```http
GET /api/v1/tasks?day=mon
Authorization: Bearer user-a-token
```

Response `200`:

```json
{
  "success": true,
  "message": "Tasks retrieved successfully.",
  "data": [
    {
      "id": "task_101", "ownerId": "user-a", "title": "Data Structures lecture", "description": "Room 204",
      "daysOfWeek": ["mon", "wed"], "startTime": "09:00", "endTime": "10:30",
      "category": "study", "priority": "high", "isFixed": true,
      "createdAt": "2026-11-10T08:00:00Z", "updatedAt": "2026-11-10T08:00:00Z"
    },
    {
      "id": "task_102", "ownerId": "user-a", "title": "Gym", "description": null,
      "daysOfWeek": ["mon", "wed", "fri"], "startTime": "18:00", "endTime": "19:00",
      "category": "health", "priority": "medium", "isFixed": false,
      "createdAt": "2026-11-10T08:00:00Z", "updatedAt": "2026-11-10T08:00:00Z"
    }
  ],
  "meta": { "total": 2, "page": 1, "perPage": 10 }
}
```

Error `403` — `GET /api/v1/tasks?ownerId=user-b` as User A:

```json
{ "success": false, "error": { "code": "FORBIDDEN", "message": "Only administrators can list tasks of other users." } }
```

Error `400` — `GET /api/v1/tasks?perPage=abc`:

```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "The request contains invalid or missing fields.",
  "details": [ { "field": "perPage", "message": "Must be an integer." } ] } }
```

---

### 4.3 GET `/api/v1/tasks/{id}` — get one task

- **Headers:** `Authorization: Bearer <token>`
- **Path:** `id` — format `task_<number>`
- **Success:** `200` with the task
- **Errors:** `400` (bad id format), `401`, `404`

Request / response `200`:

```http
GET /api/v1/tasks/task_104
Authorization: Bearer admin-token
```

```json
{
  "success": true,
  "message": "Task retrieved successfully.",
  "data": {
    "id": "task_104", "ownerId": "user-b", "title": "Part-time job shift", "description": "Campus library",
    "daysOfWeek": ["tue", "thu"], "startTime": "13:00", "endTime": "17:00",
    "category": "work", "priority": "high", "isFixed": true,
    "createdAt": "2026-11-10T08:00:00Z", "updatedAt": "2026-11-10T08:00:00Z"
  }
}
```

Error `404` — User A requests User B's `task_104`, or anyone requests `task_999`:

```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Task 'task_104' was not found." } }
```

Error `400` — `GET /api/v1/tasks/abc`:

```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "The request contains invalid or missing fields.",
  "details": [ { "field": "id", "message": "Task ID must look like 'task_101'." } ] } }
```

---

### 4.4 POST `/api/v1/tasks` — create a task

- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Body:** see field table. Required: `title`, `daysOfWeek`, `startTime`, `endTime`, `category`.
- **Success:** `201` with the created task
- **Errors:** `400`, `401`, `403` (ownerId of another user), `409`

Request:

```http
POST /api/v1/tasks
Authorization: Bearer user-a-token
Content-Type: application/json

{
  "title": "Morning run",
  "daysOfWeek": ["tue", "thu"],
  "startTime": "07:00",
  "endTime": "07:45",
  "category": "health"
}
```

Response `201`:

```json
{
  "success": true,
  "message": "Task created successfully.",
  "data": {
    "id": "task_108", "ownerId": "user-a", "title": "Morning run", "description": null,
    "daysOfWeek": ["tue", "thu"], "startTime": "07:00", "endTime": "07:45",
    "category": "health", "priority": "medium", "isFixed": false,
    "createdAt": "2026-11-16T10:00:00Z", "updatedAt": "2026-11-16T10:00:00Z"
  }
}
```

Error `400`:

```json
{ "title": "Hi", "daysOfWeek": ["monday"], "startTime": "10:00", "endTime": "09:00",
  "category": "study", "isFixed": "yes", "color": "red" }
```

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request contains invalid or missing fields.",
    "details": [
      { "field": "title", "message": "Must contain at least 3 characters." },
      { "field": "daysOfWeek[0]", "message": "Must be one of: mon, tue, wed, thu, fri, sat, sun." },
      { "field": "endTime", "message": "endTime must be later than startTime." },
      { "field": "isFixed", "message": "Must be a boolean (true or false)." },
      { "field": "color", "message": "Unknown field." }
    ]
  }
}
```

Error `400` — empty body `{}`: one `This field is required.` entry for each of
`title`, `daysOfWeek`, `startTime`, `endTime`, `category`.

Error `403` — User A sends `"ownerId": "user-b"`:

```json
{ "success": false, "error": { "code": "FORBIDDEN", "message": "You can only create or update tasks for yourself." } }
```

Error `409` — User A creates a task on `mon` 09:30–10:00 (overlaps fixed `task_101`):

```json
{ "success": false, "error": { "code": "CONFLICT",
  "message": "Task overlaps 'Data Structures lecture' (task_101) on mon 09:00-10:30. Fixed tasks cannot overlap other tasks of the same owner." } }
```

---

### 4.5 PUT `/api/v1/tasks/{id}` — replace a task

- **Headers:** `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Path:** `id` — format `task_<number>`
- **Body:** the **full** task (same rules as POST). Missing required fields → `400`.
  If `ownerId` is omitted, the current owner is kept. Admin may move the task to another user.
- **Success:** `200` with the updated task (`id` and `createdAt` unchanged, `updatedAt` refreshed)
- **Errors:** `400`, `401`, `403`, `404`, `409`

Request:

```http
PUT /api/v1/tasks/task_102
Authorization: Bearer user-a-token
Content-Type: application/json

{
  "title": "Evening gym",
  "description": "Leg day on Friday",
  "daysOfWeek": ["mon", "wed", "fri"],
  "startTime": "18:30",
  "endTime": "19:30",
  "category": "health",
  "priority": "high"
}
```

Response `200`:

```json
{
  "success": true,
  "message": "Task updated successfully.",
  "data": {
    "id": "task_102", "ownerId": "user-a", "title": "Evening gym", "description": "Leg day on Friday",
    "daysOfWeek": ["mon", "wed", "fri"], "startTime": "18:30", "endTime": "19:30",
    "category": "health", "priority": "high", "isFixed": false,
    "createdAt": "2026-11-10T08:00:00Z", "updatedAt": "2026-11-16T10:05:00Z"
  }
}
```

Error `404` — User B updates `task_102` (owned by User A):

```json
{ "success": false, "error": { "code": "NOT_FOUND", "message": "Task 'task_102' was not found." } }
```

---

### 4.6 DELETE `/api/v1/tasks/{id}` — delete a task

- **Headers:** `Authorization: Bearer <token>`
- **Path:** `id` — format `task_<number>`
- **Success:** `200` with `data: null`
- **Errors:** `400`, `401`, `404`

```http
DELETE /api/v1/tasks/task_103
Authorization: Bearer user-a-token
```

```json
{ "success": true, "message": "Task deleted successfully.", "data": null }
```

---

### 4.7 Errors common to all endpoints

`401` — no token:

```json
{ "success": false, "error": { "code": "AUTH_REQUIRED", "message": "Authentication is required. Send 'Authorization: Bearer <token>'." } }
```

`401` — invalid token:

```json
{ "success": false, "error": { "code": "INVALID_TOKEN", "message": "The provided token is invalid." } }
```

`405` — `PATCH /api/v1/tasks/task_101` (response has header `Allow: GET, PUT, DELETE`):

```json
{ "success": false, "error": { "code": "METHOD_NOT_ALLOWED",
  "message": "Method PATCH is not allowed for '/api/v1/tasks/task_101'. Allowed: GET, PUT, DELETE." } }
```

`404` — unknown URL:

```json
{ "success": false, "error": { "code": "ROUTE_NOT_FOUND", "message": "The endpoint '/api/v1/nothing' does not exist." } }
```

`400` — malformed JSON body:

```json
{ "success": false, "error": { "code": "VALIDATION_ERROR", "message": "The request contains invalid or missing fields.",
  "details": [ { "field": "body", "message": "Request body must be valid JSON." } ] } }
```

---

## 5. Mock data

| ID | Owner | Title | Days | Time | Category | Priority | Fixed |
|---|---|---|---|---|---|---|---|
| `task_101` | user-a | Data Structures lecture | mon, wed | 09:00–10:30 | study | high | yes |
| `task_102` | user-a | Gym | mon, wed, fri | 18:00–19:00 | health | medium | no |
| `task_103` | user-a | Read a book | sun | 20:00–21:00 | personal | low | no |
| `task_104` | user-b | Part-time job shift | tue, thu | 13:00–17:00 | work | high | yes |
| `task_105` | user-b | Spanish practice | mon, fri | 19:00–19:30 | study | medium | no |
| `task_106` | user-b | Grocery shopping | sat | 11:00–12:00 | personal | low | no |
| `task_107` | admin | Server maintenance review | fri | 10:00–11:00 | work | high | yes |

- `task_999` never exists → use it for `404` demos.
- New tasks get IDs starting from `task_108`.
