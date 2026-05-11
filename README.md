<div align="center">

# ⚡ Real-Time Analytics & Reporting Platform

### A production-grade, full-stack analytics platform built with FastAPI, Next.js, and modern async Python

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000?logo=next.js&logoColor=white)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Tests](https://img.shields.io/badge/Tests-70%20Passed-10b981?logo=pytest&logoColor=white)](#testing)
[![License](https://img.shields.io/badge/License-MIT-6366f1)](#license)

### 🔗 Live Demo

| 🌐 [Frontend (Vercel)](https://wexa-ai-assignment-six.vercel.app) | 🔌 [API Docs (Swagger)](https://wexa-ai-assignment-production.up.railway.app/docs) | 💚 [Health Check](https://wexa-ai-assignment-production.up.railway.app/health) |
|---|---|---|

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [API Documentation](#-api-documentation)
- [Testing](#-testing)
- [Design Patterns](#-design-patterns)
- [Security](#-security)
- [Screenshots](#-screenshots)

---

## Overview

A **full-stack Real-Time Analytics & Reporting Platform** designed to demonstrate expertise in Python architecture, async processing, efficient data pipelines, and the ability to handle complex business logic at scale.

The platform enables organizations to **ingest events**, **visualize data** through customizable dashboards, **set intelligent alerts**, **receive live updates** via WebSockets, and **schedule automated reports** — all within a multi-tenant, role-based access controlled environment.

---

## 🚀 Key Features

### 🔐 Authentication & Multi-Tenancy
- **JWT Authentication** with short-lived access tokens + long-lived refresh tokens (HTTP-only cookies)
- **OAuth2-ready** Google sign-in integration endpoint
- **Organization creation** during signup with invite-based team onboarding
- **Role hierarchy**: `Owner → Admin → Analyst → Viewer` with permission guards via dependency injection
- **Org-level data isolation** at the database query layer — every query is scoped by `org_id`
- **API Key management** — generate, revoke, and rotate keys per organization

### 📊 Data Ingestion & Sources
- **REST API** for single and batch event ingestion (up to 1000 events per batch)
- **CSV file upload** with automatic parsing and validation
- **Webhook receivers** for external event sources
- **Pydantic v2 validation** on all incoming event schemas
- **Async processing** via Celery + Redis background task queue
- **Rate limiting** per endpoint (slowapi + Redis): 500/min ingestion, 100/min queries
- **Time-series optimized** storage with composite indexes on `(org_id, created_at)`

### 📈 Dashboards & Visualizations
- **Custom dashboards** with drag-and-drop widget placement (react-grid-layout)
- **Widget types**: Line charts, Bar charts, Pie charts, KPI cards, Tables
- **Configurable time ranges**: 1h, 24h, 7d, 30d, 90d with custom start/end
- **Dashboard sharing** — public read-only links or team-only access
- **Auto-refresh** at configurable intervals (30s, 1m, 5m)
- **Dashboard templates** for common use cases: Web Analytics, Sales, DevOps
- **Full-screen presentation mode** with browser Fullscreen API

### 🚨 Alerts & Notifications
- **Configurable alert rules** — event name, metric (count/sum/avg), operator, threshold, time window
- **Multi-channel notifications**: in-app, email (SMTP), webhook (Slack/Discord/custom)
- **Alert lifecycle**: active → triggered → resolved, with mute/unmute support
- **Alert history** with triggered values and timestamps
- **Celery Beat** automated evaluation every 60 seconds

### 📋 Scheduled Reports
- **Recurring schedules**: daily, weekly, monthly with auto-calculated `next_run_at`
- **Report generation** via background Celery tasks (every 5 minutes)
- **HTML report snapshots** (extensible to PDF/PNG via headless browser)
- **Email delivery** to team members and external stakeholders
- **Report history** with file sizes and download archive

### ⚡ Real-Time Features
- **WebSocket-powered** live dashboard updates via FastAPI/Starlette
- **Multi-tenant connection manager** — events scoped by `org_id`
- **Live event stream viewer** — tail incoming events in real-time
- **Bi-directional communication**: client auth/ping, server push alerts/events
- **Automatic reconnection** with exponential backoff on the frontend

### 🔬 Observability & Monitoring
- **Structured logging** with `structlog` (ISO timestamps, context vars, log levels)
- **Correlation IDs** on every request via `CorrelationIDMiddleware` → `X-Correlation-ID` header
- **Health check** endpoint (`/health`) for load balancers
- **Metrics endpoint** (`/metrics`) — uptime, WebSocket connections, route count
- **Redis caching** for expensive aggregation queries (30s TTL, org-scoped keys)

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 16)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │
│  │  Zustand  │  │ TanStack │  │ Recharts │  │   WebSocket      │ │
│  │  (State)  │  │  Query   │  │ (Charts) │  │ (Auto-reconnect) │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘ │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST API / WebSocket
┌──────────────────────────┴──────────────────────────────────────┐
│                     API GATEWAY (FastAPI)                         │
│  ┌────────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Rate Limit │  │   CORS   │  │  Auth    │  │ Correlation   │  │
│  │ (slowapi)  │  │Middleware│  │  (JWT)   │  │ ID Middleware │  │
│  └────────────┘  └──────────┘  └──────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                     ROUTERS (API Layer)                           │
│  auth.py │ events.py │ dashboards.py │ alerts.py │ reports.py    │
├─────────────────────────────────────────────────────────────────┤
│                     SERVICES (Business Logic)                    │
│  AuthService │ EventService │ DashboardService │ ReportService   │
├─────────────────────────────────────────────────────────────────┤
│                     MODELS (SQLAlchemy 2.0 Async)                │
│  User │ Organization │ Event │ Dashboard │ Alert │ Report        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────┴──────┐  ┌─────┴─────┐  ┌──────┴──────┐
   │ PostgreSQL  │  │   Redis   │  │   Celery    │
   │  (Primary)  │  │  (Cache/  │  │  (Workers   │
   │  SQLite     │  │  Broker)  │  │  + Beat)    │
   │  (Dev)      │  │           │  │             │
   └─────────────┘  └───────────┘  └─────────────┘
```

### Clean Architecture — Layered Separation

```
Routers (API)  →  Services (Business Logic)  →  Models (Data Access)
     │                    │                           │
  FastAPI            Async/Await               SQLAlchemy 2.0
  Depends          Custom Exceptions          Async Sessions
  Pydantic v2      structlog logging          Alembic Migrations
```

---

## 🛠 Tech Stack

### Backend (Python)
| Component | Technology |
|---|---|
| Framework | FastAPI ≥ 0.111 |
| Language | Python 3.11+ with type hints throughout |
| Database | PostgreSQL + SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Task Queue | Celery + Redis (with Celery Beat) |
| Caching | Redis (query results, rate limiting) |
| Real-Time | WebSockets via FastAPI/Starlette |
| Validation | Pydantic v2 models |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Logging | structlog (structured, JSON-compatible) |
| Rate Limiting | slowapi + Redis |
| Testing | pytest + pytest-asyncio + httpx |

### Frontend (TypeScript)
| Component | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| UI | React 19 + TypeScript 5 |
| State | Zustand 5 |
| Styling | Tailwind CSS 4 |
| Charts | Recharts 3 |
| Data Fetching | TanStack Query (React Query) 5 |
| Layout | react-grid-layout (drag-and-drop) |
| Icons | Lucide React |
| Real-Time | Native WebSocket with auto-reconnect |

---

## 📁 Project Structure

```
wexa/
├── backend/
│   ├── app/
│   │   ├── api/v1/              # API Routers
│   │   │   ├── auth.py          # Auth, signup, login, API keys, OAuth2
│   │   │   ├── events.py        # Event ingestion, queries, CSV upload
│   │   │   ├── dashboards.py    # Dashboard CRUD, widgets, templates
│   │   │   ├── alerts.py        # Alert rules, notifications, history
│   │   │   ├── reports.py       # Scheduled reports, manual trigger
│   │   │   └── websocket.py     # WebSocket live stream manager
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings (env vars)
│   │   │   ├── security.py      # JWT encode/decode, password hashing
│   │   │   ├── dependencies.py  # FastAPI Depends (auth, roles)
│   │   │   ├── exceptions.py    # Custom exception hierarchy
│   │   │   ├── middleware.py     # Correlation ID + request tracing
│   │   │   └── cache.py         # Redis async cache layer
│   │   ├── models/              # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/             # Pydantic v2 request/response schemas
│   │   ├── services/            # Business logic layer
│   │   ├── workers/             # Celery tasks + Beat schedules
│   │   ├── db/                  # Database session + engine
│   │   └── main.py              # FastAPI app factory + middleware
│   ├── alembic/                 # Database migrations
│   ├── scripts/                 # Seed data scripts
│   ├── tests/                   # Automated test suite (70 tests)
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── dashboard/       # Dashboard list, detail, create
│   │   │   ├── events/          # Event explorer + query builder
│   │   │   ├── alerts/          # Alert management
│   │   │   ├── live/            # Live event stream (WebSocket)
│   │   │   ├── settings/        # Org settings, API keys
│   │   │   ├── login/           # Login page
│   │   │   └── signup/          # Signup page
│   │   ├── components/
│   │   │   ├── charts/          # LineChart, BarChart, PieChart, KPICard
│   │   │   └── layout/          # AppShell, Sidebar
│   │   ├── lib/                 # API client, WebSocket hook, providers
│   │   └── store/               # Zustand auth store
│   └── package.json
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Redis** (for Celery + caching)
- **PostgreSQL 15+** (production) or SQLite (development)

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/analytics-platform.git
cd analytics-platform
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations (PostgreSQL)
alembic upgrade head

# OR auto-create tables (SQLite dev mode)
# Tables are created automatically on startup when using SQLite

# Seed demo data (optional)
python -m scripts.seed_data

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

### 4. Background Workers (Optional)

```bash
cd backend
source .venv/bin/activate

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Start Celery Beat scheduler (in separate terminal)
celery -A app.workers.celery_app beat --loglevel=info
```

### 5. Access the Application

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health Check | http://localhost:8000/health |
| Metrics | http://localhost:8000/metrics |

---

## 🔑 Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | Async database connection string | `sqlite+aiosqlite:///./analytics.db` |
| `SYNC_DATABASE_URL` | Sync database URL (for Alembic) | `sqlite:///./analytics.db` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT signing secret key | `change-me-in-production` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `CELERY_BROKER_URL` | Celery message broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend URL | `redis://localhost:6379/1` |
| `SMTP_HOST` | Email server host | `smtp.gmail.com` |
| `SMTP_PORT` | Email server port | `587` |
| `SMTP_USER` | Email username | — |
| `SMTP_PASSWORD` | Email password | — |
| `GOOGLE_CLIENT_ID` | OAuth2 Google client ID | — |
| `GOOGLE_CLIENT_SECRET` | OAuth2 Google client secret | — |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000/api/v1` |

---

## 📖 API Documentation

The API provides **50+ endpoints** across 6 modules. Full interactive documentation is available at `/docs` (Swagger) when the server is running.

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/signup` | Register new user + create organization |
| `POST` | `/auth/login` | Authenticate and receive JWT tokens |
| `POST` | `/auth/refresh` | Refresh access token |
| `POST` | `/auth/logout` | Clear refresh token cookie |
| `GET` | `/auth/me` | Get current user profile |
| `POST` | `/auth/invite` | Invite user to organization |
| `POST` | `/auth/api-keys` | Generate API key |
| `GET` | `/auth/api-keys` | List API keys |
| `DELETE` | `/auth/api-keys/{id}` | Revoke API key |
| `POST` | `/auth/api-keys/{id}/rotate` | Rotate API key |
| `GET` | `/auth/google/login` | OAuth2 Google sign-in |

### Events (`/api/v1/events`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/events/ingest` | Ingest single event |
| `POST` | `/events/ingest/batch` | Ingest batch events (up to 1000) |
| `POST` | `/events/ingest/csv` | Upload CSV file |
| `GET` | `/events/query` | Query events with aggregation |
| `GET` | `/events/names` | List distinct event names |
| `GET` | `/events/recent` | Get recent events |
| `POST` | `/events/queries` | Create saved query |
| `GET` | `/events/queries` | List saved queries |

### Dashboards (`/api/v1/dashboards`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/dashboards/` | Create dashboard |
| `GET` | `/dashboards/` | List dashboards |
| `GET` | `/dashboards/templates` | List dashboard templates |
| `POST` | `/dashboards/from-template/{id}` | Create from template |
| `GET` | `/dashboards/{id}` | Get dashboard detail |
| `PATCH` | `/dashboards/{id}` | Update dashboard |
| `DELETE` | `/dashboards/{id}` | Delete dashboard |
| `GET` | `/dashboards/public/{slug}` | View public dashboard |
| `POST` | `/dashboards/{id}/widgets` | Add widget |
| `PATCH` | `/dashboards/{id}/widgets/{wid}` | Update widget |
| `DELETE` | `/dashboards/{id}/widgets/{wid}` | Delete widget |

### Alerts (`/api/v1/alerts`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/alerts/` | Create alert rule |
| `GET` | `/alerts/` | List alerts |
| `GET` | `/alerts/notifications` | List notifications |
| `PATCH` | `/alerts/notifications/{id}/read` | Mark notification read |
| `GET` | `/alerts/{id}` | Get alert detail |
| `PATCH` | `/alerts/{id}` | Update alert |
| `DELETE` | `/alerts/{id}` | Delete alert |
| `POST` | `/alerts/{id}/mute` | Mute alert |
| `GET` | `/alerts/{id}/history` | Alert trigger history |

### Reports (`/api/v1/reports`)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/reports/` | Create scheduled report |
| `GET` | `/reports/` | List reports |
| `GET` | `/reports/{id}` | Get report detail |
| `PATCH` | `/reports/{id}` | Update report |
| `DELETE` | `/reports/{id}` | Delete report |
| `POST` | `/reports/{id}/run` | Manually trigger report |
| `GET` | `/reports/{id}/history` | Report execution history |

### WebSocket (`/ws`)
| Endpoint | Description |
|---|---|
| `ws://localhost:8000/ws/live` | Live event stream + alert notifications |

---

## 🧪 Testing

The project includes **70 automated tests** covering all API endpoints.

```bash
cd backend
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run specific module
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_events.py -v
python -m pytest tests/test_dashboards.py -v
python -m pytest tests/test_alerts.py -v
python -m pytest tests/test_reports.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Test Coverage

| Module | Tests | Coverage |
|---|---|---|
| Authentication & Multi-Tenancy | 21 | Signup, login, JWT refresh, roles, API keys, OAuth2, cookies |
| Data Ingestion & Events | 13 | Single/batch ingest, CSV upload, queries, saved queries |
| Dashboards & Widgets | 17 | CRUD, widgets, public sharing, org isolation, templates |
| Alerts & Notifications | 13 | CRUD, mute, history, notifications, health, metrics |
| Scheduled Reports | 8 | CRUD, manual trigger, execution history |
| **Total** | **70** | **All passing ✅** |

---

## 🏛 Design Patterns

### Clean Architecture
```
Routers → Services → Models
   ↓          ↓          ↓
FastAPI    Business    SQLAlchemy
Depends    Logic       Async ORM
```

### Async Throughout
- All endpoints are `async def`
- Database queries use `await` with `AsyncSession`
- Celery tasks bridge async/sync with `_run_async()` helper
- WebSocket connections managed asynchronously

### Error Handling
- **Custom exception hierarchy**: `AppException` → `AuthenticationError`, `AuthorizationError`, `NotFoundError`, `ConflictError`, `ValidationError`, `RateLimitError`
- **Centralized handlers** in `main.py` producing structured JSON responses
- **Correlation IDs** attached to every error response for debugging

### Background Processing
- Celery workers for heavy computation (event batch processing, report generation)
- Celery Beat for scheduled tasks (alert evaluation every 60s, report generation every 5m)
- Exponential backoff retry strategies (`countdown = 10 * 2^retries`)
- Dead letter handling — logs failed tasks after max retries without re-raising

---

## 🔒 Security

| Measure | Implementation |
|---|---|
| **Authentication** | JWT access + refresh tokens, bcrypt password hashing |
| **Authorization** | Role-based guards via `Depends()` — Owner, Admin, Analyst, Viewer |
| **Input Validation** | Pydantic v2 with `min_length`, `EmailStr`, `Field(ge=...)` |
| **CORS** | Configured with explicit allowed origins |
| **Rate Limiting** | slowapi — per-endpoint: 500/min, 100/min, 20/min, 10/min |
| **SQL Injection** | 100% ORM queries — zero raw SQL |
| **XSS Prevention** | JSON-only API, no HTML rendering in responses |
| **Data Isolation** | Every query filtered by `org_id` at the ORM layer |
| **API Key Security** | Keys hashed with SHA-256, only prefix exposed |

---

## 📸 Screenshots

### Dashboard Overview
> KPI cards, time-series charts, and dashboard grid with live data

### Event Explorer
> Query builder with aggregation, time ranges, and event filtering

### Alert Management
> Create rules, view trigger history, multi-channel notifications

### Live Event Stream
> Real-time WebSocket-powered event tail with filtering

### Swagger API Docs
> Interactive API documentation with 50+ endpoints

---

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    depends_on: [postgres, redis]

  worker:
    build: ./backend
    command: celery -A app.workers.celery_app worker --loglevel=info
    depends_on: [postgres, redis]

  beat:
    build: ./backend
    command: celery -A app.workers.celery_app beat --loglevel=info
    depends_on: [redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: analyticsdb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
```

---

## 📄 License

This project is built as a **technical assessment** demonstrating full-stack development capabilities with Python, FastAPI, Next.js, and modern async architecture patterns.

---

<div align="center">

**Built with ❤️ using FastAPI + Next.js**

</div>
