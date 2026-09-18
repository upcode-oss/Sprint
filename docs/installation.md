# Installation & Deployment

## Docker Compose

Run these commands from the Sprint repository root with Docker and its Compose
plugin installed:

```bash
cp .env.example .env
```

Edit `.env`, replacing all `CHANGE_ME` values. Generate an application secret
with `openssl rand -hex 32` and use it as `APP_SECRET_KEY`.

```bash
docker compose up --build -d
docker compose ps
```

The frontend is available at <http://localhost:3000>. Open `/setup`, select the
database, configure the organization, and create the first administrator.
The backend is exposed on port `8000` with API documentation at `/docs`.

## Database selection

SQLite is the default and can use `/data/sprint.db` in the setup wizard.
To start one of the bundled database services:

```bash
docker compose --profile postgres up --build -d
# Alternatively:
docker compose --profile mariadb up --build -d
```

In setup, use host `postgres` and port `5432`, or host `mariadb` and port `3306`.
Use the database name, username, and password configured for that service.
PostgreSQL variables are included in `.env.example`. For MariaDB, add
`MARIADB_DATABASE`, `MARIADB_USER`, `MARIADB_PASSWORD`, and
`MARIADB_ROOT_PASSWORD` to `.env` before starting the service.

The wizard persists the selected connection in the installation configuration;
`DATABASE_URL` is the initial connection setting before setup is complete.

## Configuration

Administrators can select and save the organization timezone under
**Administration → Organization → Timezone**. The searchable list contains the
IANA timezones supported by the backend, including `Europe/Vienna`. New and
existing organizations default to `UTC`. The setting is stored separately from
personal profile preferences; date rendering currently continues to use the
browser timezone.

See [.env.example](../.env.example) for application settings and
[docker-compose.yml](../docker-compose.yml) for service configuration.

For HTTPS deployment, configure a reverse proxy, set `PUBLIC_APP_URL` and
`BACKEND_CORS_ORIGINS` to the public origin, and enable `COOKIE_SECURE=true`.
Set `APP_ENV=production`; startup then rejects placeholder or short application
secrets. The supplied Compose file publishes ports `3000` and `8000` on the
host, so adjust port bindings to match the deployment network.

## Persistence and updates

| Compose volume | Contents |
| --- | --- |
| `sprint_data` | `/data`, including SQLite and `installation.json` by default |
| `avatar_data` | User avatars |
| `organization_logo_data` | Organization logos |
| `postgres_data` | Optional PostgreSQL database |
| `mariadb_data` | Optional MariaDB database |

Preserve `.env`, especially `APP_SECRET_KEY`, alongside the installation
configuration, uploaded files, and a consistent database backup. An external
database needs its own backup. `docker compose down` retains named volumes;
adding `--volumes` deletes them.

Before updating, read the [release notes](../RELEASE.md) and back up persistent
state. After checking out the intended version, rebuild with
`docker compose up --build -d` (including the database profile if used).
Backend startup applies Alembic migrations after setup is complete. Rolling
back application files alone does not undo database migrations.
