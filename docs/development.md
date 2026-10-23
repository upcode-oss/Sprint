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
| `make test` | Run backend pytest and frontend setup validation tests |
| `make lint` | Run Ruff, frontend ESLint, and TypeScript checks |
| `make build` | Create the frontend production build |
| `make format` | Format backend and frontend sources |

Activate the Python environment before running backend checks. Frontend checks
require the npm dependencies to be installed.

The existing test suite covers areas including authentication, permissions,
membership access, sprints, profiles, branding, calendar/meetings, database
portability, and task time tracking. Pending quality work is tracked in
[TODO.md](../TODO.md).

## Frontend dependency security

Run `npm audit` from `upcode-sprint/` to include development dependencies, or
`npm audit --omit=dev` to check the production dependency tree. Commit both
`package.json` and `package-lock.json` when updating dependencies, and verify
the lockfile with `npm ci` before running frontend checks and a production build.

As of 2026-10-23, the resolved production dependency tree has no npm audit
findings. The full audit still reports five high-severity package findings from
one unresolved development dependency chain:
`eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces`.
The underlying [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
has no patched release. This is distinct from `brace-expansion`, whose reported
vulnerabilities are fixed in the lockfile. Recheck the upstream packages when
updating the lint toolchain; an audit-forced downgrade of the Next.js ESLint
configuration is not part of this update.

## Maintaining release documentation

Keep [RELEASE.md](../RELEASE.md) focused on the current version. Maintain a
matching `releases/<version>.md` entry and add it to the
[release index](../releases/README.md). Record publication status and dates
explicitly, and keep version numbers aligned with `frontend/package.json`,
`backend/pyproject.toml`, and application configuration.
