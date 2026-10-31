# Upcode Sprint v0.1.0 – Initial Project Foundation

**Status:** Development snapshot; publication date not recorded.

The frontend package, backend package, and default application configuration
currently use version `0.1.0`. These notes describe the existing source tree
and do not indicate a published release.

## Highlights

- MCP is disabled by default and requires explicit activation under
  **Administration → System → MCP access**; disabling it hides key management
  and blocks new keys and existing MCP access immediately
- Personal MCP keys and Streamable HTTP tools for projects, tasks, documents and
  sprints, bounded by selected scopes, current user permissions and project/team
  membership; keys support expiration, revocation and password/2FA invalidation
- Self-hosted Next.js frontend and FastAPI backend with Docker Compose
- Initial setup for SQLite, PostgreSQL, or MariaDB/MySQL, organization branding,
  and the first administrator
- Setup can finish without SMTP, ignores unused email configuration, and shows
  field-specific validation errors on the affected wizard step
- Authentication, password reset, user profiles, avatars, and presence
- Optional authenticator-based 2FA in the profile, with local QR setup, ten
  single-use recovery codes, persistent verification lockout, and session renewal
  after factor changes; password resets preserve the enrolled second factor
- Forge instance pairing is deferred to a later release; its settings and API
  endpoints have been removed
- Teams, projects, membership-based access, roles, and permissions
- Kanban boards, tasks, comments, subtasks, activity history, and time tracking
- Scrum sprint management, project documents, meetings, and calendar views
- Alembic database migrations and backend tests
- Frontend security updates: Next.js and its ESLint configuration 16.4.2,
  source-map-js 1.2.2, brace-expansion 1.1.21/5.0.12, js-yaml 4.3.2,
  and sharp 0.35.5, with an updated npm lockfile
- Project documentation, an open-work checklist, and MIT licensing

## Installation and updates

Follow [Installation & Deployment](docs/installation.md) for a new installation.
Database migrations run during setup and on backend startup after setup is
complete. Back up the database, persistent files, installation configuration,
and application secret before updating an existing installation.

See [TODO.md](TODO.md) for pending validation and release preparation, and
[releases/0.1.0.md](releases/0.1.0.md) for the version-specific notes.
