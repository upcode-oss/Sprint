# Architecture

## Frontend

The [frontend](../frontend/) uses Next.js, React, and TypeScript. Routes live in
`app/`, domain-specific screens in `features/`, and shared UI in `components/`.
`services/api.ts` provides the API client and `types/api.ts` the API types.

Browser requests to `/api/` are forwarded by Next.js to the FastAPI backend.
`BACKEND_INTERNAL_URL` selects the upstream; Docker Compose defaults to
`http://backend:8000`. The frontend build receives this URL as a build argument.

## Backend

The [backend](../backend/) uses FastAPI, SQLAlchemy, Pydantic, and Alembic:

| Directory | Responsibility |
| --- | --- |
| `app/api/v1/` | HTTP routes for authentication and application features |
| `app/services/` | Domain logic and access checks |
| `app/models/` | SQLAlchemy database models |
| `app/schemas/` | Request and response models |
| `app/permissions/` | Permission catalog |
| `app/core/` | Configuration, security, installation state, and errors |
| `app/db/` | Database sessions and migration startup |
| `app/storage/` | Local file storage |
| `alembic/` | Versioned database migrations |
| `tests/` | Backend tests |

## Database and installation state

The setup wizard selects SQLite, PostgreSQL, or MariaDB/MySQL and creates the
organization and administrator. Installation state is stored in
`INSTALLATION_CONFIG_PATH`, including the encrypted selected database URL.
`APP_SECRET_KEY` must be preserved together with this file.

Alembic migrations run when setup initializes the selected database and on
backend startup once setup is complete. The permission catalog is synchronized
on startup after setup.

## Persistent files and health

Docker Compose mounts separate volumes for general application data, avatars,
and organization logos. Optional database services have their own volumes.

The backend exposes `/health` for process health and `/ready` for setup and
database readiness. `/ready` reports its result in the JSON body, including
`ready: false` when the database cannot be reached.
