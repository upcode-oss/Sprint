# Upcode Sprint – Agile Project Management

Upcode Sprint is a self-hosted project management platform built with Next.js
and FastAPI. It combines projects, teams, Kanban boards, Scrum sprints,
documents, meetings, and a shared calendar.

## Features

- Projects and teams with membership-based access and configurable roles
- Kanban tasks with comments, subtasks, activity history, and time tracking
- Scrum sprint planning and management
- Project documents, meetings, and calendar views
- User profiles, avatars, and presence
- Setup wizard for database selection, organization branding, and the first administrator
- SMTP configuration and password reset
- SQLite, PostgreSQL, and MariaDB/MySQL database support

## Getting started

From the Sprint repository root, with Docker and Docker Compose installed:

```bash
cp .env.example .env
# Edit .env and replace the CHANGE_ME values.
docker compose up --build -d
```

Open <http://localhost:3000/setup> to configure the database, organization, and
administrator. See [Installation & Deployment](docs/installation.md) for
database profiles, configuration, and persistent data.

## Project layout

```text
Sprint/
├── backend/           # FastAPI application, Alembic migrations, and tests
├── frontend/          # Next.js application
├── docs/              # Technical documentation
├── releases/          # Version-specific release notes
├── README.md          # Project overview
├── TODO.md            # Open work
├── RELEASE.md         # Current release notes
├── LICENSE            # MIT license
├── .env.example       # Configuration template
├── docker-compose.yml # Application and optional database services
└── Makefile           # Development and quality commands
```

## Documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Development & Checks](docs/development.md)
- [Open work](TODO.md)
- [Current release notes](RELEASE.md)
- [Release history](releases/README.md)

## License

Upcode Sprint is licensed under the [MIT License](LICENSE).
