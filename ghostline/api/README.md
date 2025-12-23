# GhostLine API Service

This repository contains the backend API service for the GhostLine ghost-writing platform.

## Overview

The GhostLine API provides:
- RESTful endpoints for frontend communication
- User authentication and authorization
- Project and asset management
- Token usage tracking and billing
- Integration with AI agent orchestration
- Real-time notifications via WebSocket/SSE

## Tech Stack

- **Framework**: FastAPI 0.111
- **Database**: PostgreSQL with pgvector
- **ORM**: SQLAlchemy
- **Authentication**: JWT with AWS Cognito
- **Task Queue**: Celery with Redis
- **Containerization**: Docker

## Getting Started

```bash
# Install dependencies
poetry install

# Run database migrations
alembic upgrade head

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest

# Build Docker image
docker build -t ghostline-api .
```

## Project Structure

```
api/
├── app/
│   ├── api/           # API endpoints
│   ├── models/        # Database models
│   ├── schemas/       # Pydantic schemas
│   ├── services/      # Business logic
│   ├── db/            # Database configuration
│   └── utils/         # Utility functions
├── alembic/           # Database migrations
├── tests/             # Test files
└── docs/              # API documentation
```

## API Documentation

Once running, API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

Please see our [Contributing Guide](../docs/CONTRIBUTING.md) for details.

## License

Copyright © 2025 GhostLine. All rights reserved. # Deployment test - Sat Jun 28 18:26:10 PDT 2025

<!-- Data layer checkpoint: 2025-06-29 02:38 UTC -->
