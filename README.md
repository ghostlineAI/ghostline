# GhostLine

AI-powered ghost-writing platform that transforms source materials into professionally written books.

## Local Development Setup

### Prerequisites

- **Docker** - For PostgreSQL and Redis
- **Python 3.11+** - For the API
- **Poetry** - Python package manager
- **Node.js 20+** - For the frontend
- **npm** - Node package manager

### Quick Start

1. **Start the databases:**
   ```bash
   docker-compose up -d
   ```

2. **Set up the API:**
   ```bash
   cd ghostline/api
   cp env.example .env
   poetry install
   poetry run alembic upgrade head
   poetry run uvicorn app.main:app --reload
   ```

3. **Set up the frontend:**
   ```bash
   cd ghostline/web
   npm install
   npm run dev
   ```

4. **Access the app:**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Or use the setup script:

```bash
./scripts/local-dev.sh
```

## Configuration

### Local Development (Default)

Auth is **disabled** by default for local development. No login required.

Configuration is in `ghostline/api/.env`:

```env
DATABASE_URL=postgresql://ghostline:ghostline@localhost:5432/ghostline
REDIS_URL=redis://localhost:6379
AUTH_DISABLED=true
USE_LOCAL_STORAGE=true
```

### File Storage

- **Local dev**: Files stored in `ghostline/api/uploads/`
- **Production**: Files stored in S3 (set `USE_LOCAL_STORAGE=false`)

## Project Structure

```
GhostLine/
├── docker-compose.yml    # PostgreSQL + Redis for local dev
├── scripts/
│   └── local-dev.sh      # Setup script
└── ghostline/
    ├── api/              # FastAPI backend
    │   ├── app/          # Application code
    │   ├── alembic/      # Database migrations
    │   └── uploads/      # Local file storage
    ├── web/              # Next.js frontend
    ├── agents/           # AI agents (WIP)
    ├── infra/            # Terraform (production)
    └── docs/             # Documentation
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/projects/` | List projects |
| `POST /api/v1/projects/` | Create project |
| `GET /api/v1/projects/{id}` | Get project |
| `DELETE /api/v1/projects/{id}` | Delete project |
| `POST /api/v1/source-materials/upload` | Upload file |
| `GET /api/v1/projects/{id}/source-materials` | List materials |

## Development

### Running Tests

```bash
# API tests
cd ghostline/api
poetry run pytest

# Frontend tests
cd ghostline/web
npm test
```

### Database Migrations

```bash
cd ghostline/api

# Create a new migration
poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head

# Rollback
poetry run alembic downgrade -1
```

## License

Copyright © 2025 GhostLine. All rights reserved.



