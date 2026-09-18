# Development & Checks

Run commands from the Sprint repository root unless stated otherwise.
Use Python 3.11 or newer and Node.js 22, matching the frontend container.

## Project language

Use English for all project-maintained text, including the interface,
accessibility labels, API messages, emails, documentation, comments, and examples.
Use the shared frontend `APP_LOCALE` (`en-US`) for date and time display so
calendar labels remain English regardless of the browser language. User-entered
content is preserved as written.

## Install development dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './backend[dev]'
cd frontend
npm ci
cd ..
```

## Existing commands

| Command | Purpose |
| --- | --- |
| `make dev` | Build and run the Compose services in the foreground |
| `make compose-up` | Start Compose services in the background |
| `make compose-build` | Build the service images |
| `make test` | Run backend pytest tests |
| `make lint` | Run Ruff, frontend ESLint, and TypeScript checks |
| `make build` | Create the frontend production build |
| `make format` | Format backend and frontend sources |

Activate the Python environment before running backend checks. Frontend checks
require the npm dependencies to be installed.

The existing test suite covers areas including authentication, permissions,
membership access, sprints, profiles, branding, calendar/meetings, database
portability, and task time tracking. Pending quality work is tracked in
[TODO.md](../TODO.md).

## Maintaining release documentation

Keep [RELEASE.md](../RELEASE.md) focused on the current version. Maintain a
matching `releases/<version>.md` entry and add it to the
[release index](../releases/README.md). Record publication status and dates
explicitly, and keep version numbers aligned with `frontend/package.json`,
`backend/pyproject.toml`, and application configuration.
