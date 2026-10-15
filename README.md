# Upcode Sprint - Agile Project Management

<p align="center">
  <img src="upcode-sprint/public/logo.png" alt="Upcode Sprint Logo" width="400">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-16.x-black.svg)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)

A self-hosted project management platform with projects, teams, Kanban boards, Scrum sprints, documents, meetings, and a shared calendar. Upcode Sprint brings agile planning and team collaboration together in a modern, user-friendly interface built with Next.js and FastAPI.

## 🚀 Features

- 👥 **Projects & Teams** - Membership-based access and configurable roles
- 📋 **Kanban Boards** - Tasks with comments, subtasks, activity history, and time tracking
- 🏃 **Scrum Sprints** - Sprint planning and management
- 📝 **Project Documents** - Shared project documentation
- 📅 **Meetings & Calendar** - Project meetings and calendar views
- 👤 **User Profiles** - Avatars and presence
- ⚙️ **Setup Wizard** - Database selection, organization branding, and the first administrator
- ✉️ **Email Configuration** - SMTP configuration and password reset
- 🗄️ **Database Support** - SQLite, PostgreSQL, and MariaDB/MySQL

## Local quality gates

Run the existing checks from the repository root after installing the development dependencies and activating the Python environment:

```bash
make test
make lint
make build
```

These commands run the backend pytest suite, Ruff, frontend ESLint and TypeScript checks, and the frontend production build. See [Development & Checks](docs/development.md) for further details. Install the backend development dependencies from `./upcode-sprint-service[dev]` and the frontend dependencies from `upcode-sprint/`.

## 📋 Prerequisites

- **Docker & Docker Compose**: Required for the container-based installation
- **Python**: 3.11 or higher for local backend development
- **Node.js**: 22 for local frontend development, matching the frontend container
- **Database**: SQLite by default; PostgreSQL and MariaDB/MySQL are also supported

## ⚡ Installation

### Quick Installation

```bash
# Clone repository
git clone https://github.com/upcode-oss/Sprint.git
cd Sprint

# Prepare configuration
cp .env.example .env
# Edit .env and replace all CHANGE_ME values.
# Generate APP_SECRET_KEY with: openssl rand -hex 32

# Build and start the application
docker compose up --build -d
```

After startup, open <http://localhost:3000/setup> to configure the database, organization, and first administrator. The backend API documentation is available at <http://localhost:8000/docs>.

See [Installation & Deployment](docs/installation.md) for database profiles, configuration, HTTPS deployment, and persistent data.

### Project Layout

```text
Sprint/
├── upcode-sprint-service/ # FastAPI application, Alembic migrations, and tests
├── upcode-sprint/         # Next.js application
├── docs/                 # Technical documentation
├── releases/             # Version-specific release notes
├── README.md             # Project overview
├── TODO.md               # Open work
├── RELEASE.md            # Current release notes
├── LICENSE               # MIT license
├── .env.example          # Configuration template
├── docker-compose.yml    # Application and optional database services
└── Makefile              # Development and quality commands
```

### Documentation

- [Documentation index](docs/README.md)
- [Architecture](docs/architecture.md)
- [Development & Checks](docs/development.md)
- [Open work](TODO.md)
- [Current release notes](RELEASE.md)
- [Release history](releases/README.md)

## 💝 Support

Want to support the project? Here are some ways to help:

### ⭐ GitHub Star

Give the project a star on [GitHub](https://github.com/upcode-oss/Sprint) - it helps others discover it!

### 🐛 Issues & Feedback

- Report bugs via [GitHub Issues](https://github.com/upcode-oss/Sprint/issues)
- Share feature requests and suggestions
- Help improve the documentation

### 🤝 Contribute

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Create a Pull Request

### 💰 Sponsoring

Support development financially:

- [GitHub Sponsors](https://github.com/sponsors/upcode-at)

### 📢 Spread the Word

- Share the project on social media
- Write a blog post about it
- Recommend it to friends and colleagues

Every contribution helps make Upcode Sprint better! 🙏

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact & Community

- **GitHub**: [upcode-oss/Sprint](https://github.com/upcode-oss/Sprint)
- **Issues**: [Bug Reports & Feature Requests](https://github.com/upcode-oss/Sprint/issues)
- **Discussions**: [GitHub Discussions](https://github.com/upcode-oss/Sprint/discussions)

---

**Upcode Sprint** - Agile project management made easy 🚀
