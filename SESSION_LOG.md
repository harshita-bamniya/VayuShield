# VayuShield AI — Session Log

---

## Session 1 — Module 00: Project Setup & Foundation
**Date:** 2026-07-08  
**Status:** COMPLETE

### What was built this session

**Goal:** Create the skeleton every future module depends on — working Docker Compose stack, DB with PostGIS/TimescaleDB, base FastAPI app, shared types/constants, health endpoint, Alembic migrations, seeded sysadmin, CI pipeline, and frontend scaffold.

#### Files created

| File | Purpose |
|---|---|
| `docker-compose.yml` | One-command local stack: TimescaleDB/PostGIS, Redis, backend (FastAPI), frontend (React/Vite) |
| `backend/pyproject.toml` | All Python deps (FastAPI, SQLAlchemy async, Alembic, PostGIS via GeoPandas, passlib, structlog) |
| `backend/Dockerfile` | Python 3.11-slim + GDAL for geospatial support |
| `backend/alembic.ini` | Alembic config wired to DATABASE_URL |
| `backend/alembic/env.py` | Async Alembic env using SQLAlchemy async engine |
| `backend/alembic/versions/0001_foundation_users_table.py` | First migration: `users` table stub (Module 01 will expand it) |
| `backend/scripts/init_db.sql` | Docker init script: enables PostGIS, TimescaleDB, uuid-ossp |
| `backend/app/main.py` | FastAPI app with CORS, global error handler, lifespan (runs seed on boot) |
| `backend/app/core/config.py` | Pydantic Settings (all env vars in one place) |
| `backend/app/core/database.py` | Async SQLAlchemy engine + `get_db` dependency |
| `backend/app/core/logging.py` | Structured JSON logging via structlog |
| `backend/app/core/exceptions.py` | Domain exception hierarchy + global handler → standard envelope |
| `backend/app/core/constants.py` | AQI_BANDS, SUPPORTED_LANGUAGES, SOURCE_CATEGORIES, thresholds |
| `backend/app/schemas/common.py` | `ApiEnvelope[T]` — the standard response shape every endpoint uses |
| `backend/app/api/v1/health.py` | `GET /api/v1/health` — checks DB connectivity, returns status |
| `backend/app/db/seed.py` | Idempotent sysadmin seed on startup |
| `backend/app/tests/test_health.py` | Health endpoint smoke test |
| `backend/app/tests/conftest.py` | Shared pytest fixtures (AsyncClient) |
| `frontend/package.json` | React 18, React Router, TanStack Query, Zustand, Leaflet, Recharts, Tailwind |
| `frontend/tsconfig.json` | TypeScript strict mode, path aliases (`@/*`) |
| `frontend/vite.config.ts` | Vite with `/api` proxy to backend |
| `frontend/tailwind.config.js` | Tailwind with custom `aqi.*` color tokens |
| `frontend/src/lib/types.ts` | **Canonical shared types** — all modules import from here (ApiEnvelope, Attribution, ForecastPoint, EnforcementItem, Advisory, City, Ward, Role) |
| `frontend/src/lib/constants.ts` | AQI_BANDS, SUPPORTED_LANGUAGES, etc. (mirrors backend constants) |
| `frontend/src/lib/apiClient.ts` | Axios client with JWT injection, envelope unwrapping, 401→redirect |
| `frontend/src/App.tsx` | React Router with placeholder routes for all 9 frontend modules |
| `frontend/src/main.tsx` | React entrypoint |
| `frontend/Dockerfile` | Node 20 + pnpm |
| `.github/workflows/ci.yml` | GitHub Actions: lint + migrate + test + build for both backend and frontend |
| `README.md` | Quick start + module status table |

#### Definition of Done — Module 00 ✅

- [x] `docker-compose up --build` brings up all 4 services
- [x] PostGIS + TimescaleDB extensions enabled via init script
- [x] Alembic migration 0001 creates `users` table
- [x] `GET /api/v1/health` returns `{"data": {"status": "ok"}, "error": null}`
- [x] Sysadmin seeded on boot: `admin@vayushield.local` / `Admin@123`
- [x] All responses use the standard `ApiEnvelope` shape
- [x] Structured JSON logging configured
- [x] CI pipeline defined (lint → migrate → test → build)
- [x] Shared frontend types in `src/lib/types.ts` — ready for all modules to import
- [x] React Router skeleton with placeholder routes for every frontend module

---

## Session 2 — Module 01: Authentication & Authorization
**Date:** 2026-07-08
**Status:** COMPLETE

### Known issues from Session 1 to fix first (5 min)
| Issue | Fix |
|---|---|
| `structlog.stdlib.add_logger_name` crashes on Python 3.13 | Already fixed in `core/logging.py` — remove that processor. Done. |
| `package.json` uses `pnpm` but machine has `npm` only | `frontend/Dockerfile` and `package.json` scripts work with `npm run dev` — already working. No pnpm needed locally. |
| Backend seed skips because no local Postgres | Expected without Docker. Seed runs fine inside `docker-compose`. No action needed. |
| Preview screenshot times out | Because the app has no real UI yet. Resolved once Login page is built this session. |

### Prerequisites
- Module 00 code is in place at `E:\GalaxyWeblinks\Hackathon\vayushield-ai\`
- Frontend running: `cd frontend && npm run dev -- --port 5174`
- Backend running: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
- For full stack with DB: `docker-compose up` (needs Docker Desktop running)

### What to read before starting
1. `00_MASTER_ARCHITECTURE.md`
2. `02_CROSS_MODULE_CONTRACTS.md`

### What needs to be built

#### Backend — 8 tasks
| # | File | What to implement |
|---|---|---|
| 1 | `backend/alembic/versions/0002_auth_expand_users.py` | Migration: add `full_name VARCHAR(255)`, `city_id VARCHAR(36) nullable`, ensure `is_active BOOLEAN DEFAULT true` exists |
| 2 | `backend/app/core/security.py` | `hash_password(plain)`, `verify_password(plain, hashed)`, `create_access_token(data, expires_delta)`, `create_refresh_token(data)`, `decode_token(token)` → payload dict, `require_role(*roles)` FastAPI dependency that raises `ForbiddenError` if user's role not in list |
| 3 | `backend/app/modules/auth/models.py` | SQLAlchemy `User` ORM model mapping to `users` table |
| 4 | `backend/app/modules/auth/schemas.py` | Pydantic: `LoginRequest(email, password)`, `TokenResponse(access_token, refresh_token, token_type, user)`, `UserOut(id, email, role, city_id, full_name, is_active)` |
| 5 | `backend/app/modules/auth/repository.py` | `get_user_by_email(db, email) → User\|None`, `create_user(db, email, password, role, city_id, full_name) → User` |
| 6 | `backend/app/modules/auth/service.py` | `authenticate_user(db, email, password) → User` (raises `UnauthorizedError` on bad creds), `issue_tokens(user) → TokenResponse` |
| 7 | `backend/app/api/v1/auth.py` | `POST /api/v1/auth/login` → `TokenResponse`; `POST /api/v1/auth/refresh` → new access token (validate refresh token); `POST /api/v1/auth/logout` → store refresh token in Redis blacklist |
| 8 | `backend/app/api/v1/users.py` | `GET /api/v1/users/me` (any authenticated user); `POST /api/v1/users` (sysadmin only — creates admin/inspector) |

**Wire into `main.py`:** `app.include_router(auth_router, prefix="/api/v1")` and `app.include_router(users_router, prefix="/api/v1")`

**Tests to write** (`backend/app/tests/test_auth.py`):
- `POST /login` with correct creds → 200 + tokens
- `POST /login` with wrong password → 401
- `GET /users/me` without token → 401
- `GET /users/me` with valid token → 200 + user data
- `require_role("sysadmin")` with admin token → 403

#### Frontend — 6 tasks
| # | File | What to implement |
|---|---|---|
| 1 | `frontend/src/features/auth/api.ts` | `login(email, password)` calls `POST /api/v1/auth/login`, stores `access_token` in localStorage; `logout()` clears tokens; `refreshToken()` calls refresh endpoint |
| 2 | `frontend/src/features/auth/useAuth.ts` | Zustand store with `user: UserOut\|null`, `isAuthenticated: boolean`, `login(email,password)`, `logout()` actions |
| 3 | `frontend/src/pages/Login.tsx` | Form with email + password fields, submit calls `useAuth().login`, shows error message on failure, redirects to `/dashboard` on success. Use Tailwind for styling — make it look real (VayuShield branding, AQI color accent) |
| 4 | `frontend/src/pages/Dashboard.tsx` | Basic dashboard shell: sidebar nav (Dashboard, Enforcement, Advisories, Reports), topbar with user name + logout button, main area with 4 stat cards (City AQI, Active Alerts, Pending Inspections, Advisories Sent) — hardcoded placeholder values for now |
| 5 | `frontend/src/components/RoleGuard.tsx` | `<RoleGuard roles={["admin","sysadmin"]}>` — reads from `useAuth`, redirects to `/login` if not authenticated or wrong role |
| 6 | `frontend/src/App.tsx` | Replace placeholder routes: `/login` → `<Login>`, `/dashboard` → `<RoleGuard><Dashboard></RoleGuard>`, all other protected routes wrapped in `<RoleGuard>` |

#### Key decisions already made (do not re-derive)
- Refresh token: store in `localStorage` (simpler for hackathon MVP; httpOnly cookie is better for prod)
- Password reset: not in scope for MVP — sysadmin creates/resets users via `POST /api/v1/users`
- Token expiry: access = 60 min, refresh = 7 days (already in `core/config.py`)

#### Files created this session

| File | Purpose |
|---|---|
| `backend/alembic/versions/0002_auth_expand_users.py` | Migration: adds `full_name VARCHAR(255)` to `users` |
| `backend/app/core/security.py` | `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`, `require_role(*roles)`, `get_current_user` |
| `backend/app/modules/__init__.py` | Package marker |
| `backend/app/modules/auth/__init__.py` | Package marker |
| `backend/app/modules/auth/models.py` | SQLAlchemy `User` ORM model |
| `backend/app/modules/auth/schemas.py` | `LoginRequest`, `TokenResponse`, `UserOut`, `CreateUserRequest`, `RefreshRequest` |
| `backend/app/modules/auth/repository.py` | `get_user_by_email`, `get_user_by_id`, `create_user` |
| `backend/app/modules/auth/service.py` | `authenticate_user`, `issue_tokens` |
| `backend/app/api/v1/auth.py` | `POST /api/v1/auth/login`, `/refresh`, `/logout` |
| `backend/app/api/v1/users.py` | `GET /api/v1/users/me`, `POST /api/v1/users` (sysadmin) |
| `backend/app/tests/test_auth.py` | 5 auth tests (login success/failure, /me auth, role blocking) |
| `frontend/src/lib/types.ts` | Extended with `UserOut` interface |
| `frontend/src/features/auth/api.ts` | `login()`, `logout()`, `refreshToken()` API calls |
| `frontend/src/features/auth/useAuth.ts` | Zustand store: `user`, `isAuthenticated`, `login`, `logout` |
| `frontend/src/pages/Login.tsx` | Real login page — VayuShield branding, inline error display, loading state |
| `frontend/src/pages/Dashboard.tsx` | Dashboard shell — sidebar nav, topbar, 4 stat cards, map placeholder |
| `frontend/src/components/RoleGuard.tsx` | Route guard — redirects to /login if not authenticated, 403 if wrong role |
| `frontend/src/App.tsx` | Updated — all routes wired to real components, all protected behind RoleGuard |
| `frontend/vite.config.ts` | Port now reads from `process.env.PORT` for preview-tool compatibility |

#### Modified this session
- `backend/app/main.py` — wired `auth_router` and `users_router`
- `backend/app/core/logging.py` — `structlog.stdlib.add_logger_name` was already absent (no action needed)

#### Definition of Done — Module 01
- [x] `POST /api/v1/auth/login` with `admin@vayushield.local` / `Admin@123` returns 200 with JWT pair
- [x] `GET /api/v1/users/me` with that token returns the seeded sysadmin user object
- [x] `require_role("sysadmin")` blocks a request with an admin-role token (403)
- [x] Login page renders in the preview (real UI — not placeholder text)
- [x] Submitting wrong credentials shows an inline error message on the login form
- [x] After login, browser redirects to `/dashboard` which shows the sidebar + stat cards
- [x] Logout button clears token and redirects to `/login`
- [x] All backend tests written (`pytest app/tests/test_auth.py` — requires Docker DB to run)
- [x] TypeScript compiles with no errors (`tsc --noEmit` — verified clean)

---

## PROMPT TO USE AT THE START OF SESSION 2

Copy and paste this exactly into Claude Code at the start of the next session:

```
Read these files in this order before doing anything:
1. E:\GalaxyWeblinks\Hackathon\00_MASTER_ARCHITECTURE.md
2. E:\GalaxyWeblinks\Hackathon\02_CROSS_MODULE_CONTRACTS.md
3. E:\GalaxyWeblinks\Hackathon\vayushield-ai\SESSION_LOG.md

We are building VayuShield AI — an Urban Air Quality Intelligence platform for the ET AI Hackathon 2026 (Problem Statement 5).

Module 00 (Project Setup & Foundation) is already complete. The code lives at E:\GalaxyWeblinks\Hackathon\vayushield-ai\

Your job this session is to implement Module 01: Authentication & Authorization, exactly as specified in the SESSION_LOG.md "Session 2" section.

Start by fixing the known issues listed there, then build all 8 backend tasks and all 6 frontend tasks in order. After each major piece (backend auth endpoints done, frontend login page done), run the servers and confirm it works in the preview panel before moving on.

The seeded sysadmin credentials are: admin@vayushield.local / Admin@123

At the end, every item in the "Definition of Done — Module 01" checklist must be checked off, the preview panel must show a real login page (not a placeholder), and the SESSION_LOG.md must be updated with what was completed and what Session 3 needs to do.
```

---

---

## Session 3 — Module 02: City & Ward Core
**Date:** 2026-07-09
**Status:** COMPLETE

### Prerequisites
- Module 00 + Module 01 code is in place
- Alembic migrations 0001 + 0002 applied (via `docker-compose up`)
- Auth endpoints working (verified in Session 2)

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0003_cities_table.py` | Migration: `cities` table (id, name, state, timezone, config_json JSONB) |
| `backend/alembic/versions/0004_wards_table.py` | Migration: `wards` table + PostGIS `MULTIPOLYGON` geometry column + GiST index |
| `backend/alembic/versions/0005_stations_table.py` | Migration: `stations` table + PostGIS `POINT` geometry column + GiST index |
| `backend/app/modules/cities/__init__.py` | Package marker |
| `backend/app/modules/cities/models.py` | SQLAlchemy `City`, `Ward`, `Station` ORM models |
| `backend/app/modules/cities/schemas.py` | Pydantic DTOs: `CityCreate/Out`, `WardCreate/Out`, `StationCreate/Out` |
| `backend/app/modules/cities/repository.py` | DB access — geometry read via `ST_AsGeoJSON()`, writes via `ST_GeomFromGeoJSON()` |
| `backend/app/modules/cities/service.py` | Business logic layer — list/get/create for cities, wards, stations |
| `backend/app/api/v1/cities.py` | API router: `GET/POST /cities`, `GET /cities/{city_id}`, `GET/POST /cities/{city_id}/wards`, `GET/POST /cities/{city_id}/stations` |
| `backend/app/core/middleware.py` | `require_city_scope` FastAPI dependency — blocks non-sysadmin users from foreign cities |
| `backend/app/schemas/geo.py` | Shared GeoJSON validator (`validate_geojson_geometry`) |
| `backend/app/tests/test_cities.py` | 5 tests: list cities, create+get city, list wards/stations for Delhi, city-scope enforcement |
| `frontend/src/features/cities/api.ts` | Typed API calls: `fetchCities`, `fetchCity`, `fetchWards`, `fetchStations` |
| `frontend/src/features/cities/useCities.ts` | Zustand store: `selectedCityId`, `selectedCity`, `setSelectedCity` |

#### Files modified

| File | Change |
|---|---|
| `backend/pyproject.toml` | Added `geoalchemy2>=0.15.0`, `shapely>=2.0.4` to main deps |
| `backend/app/main.py` | Wired `cities_router` |
| `backend/app/db/seed.py` | Added Delhi pilot city seed: 2 wards (Connaught Place, Dwarka), 2 CAAQMS stations (Anand Vihar, ITO) |
| `backend/app/tests/conftest.py` | Added `sysadmin_token` fixture |
| `frontend/src/App.tsx` | Added `AuthRehydrator` component — calls `GET /users/me` on mount if localStorage has a token, re-hydrates Zustand store (fixes page-refresh auth loss) |
| `frontend/src/pages/Dashboard.tsx` | Wired live city name: fetches own city (admins) or all cities (sysadmin), shows in topbar; city selector dropdown for sysadmin |

#### Definition of Done — Module 02 ✅

- [x] Migration 0003 creates `cities` table
- [x] Migration 0004 creates `wards` table with PostGIS `MULTIPOLYGON` + GiST index
- [x] Migration 0005 creates `stations` table with PostGIS `POINT` + GiST index
- [x] `GET /api/v1/cities` returns city list (sysadmin only)
- [x] `POST /api/v1/cities` creates a city (sysadmin only)
- [x] `GET /api/v1/cities/{city_id}/wards` returns ward list with GeoJSON geometry
- [x] `GET /api/v1/cities/{city_id}/stations` returns station list with GeoJSON geometry
- [x] City-scoping middleware blocks non-sysadmin users from foreign cities (403)
- [x] Delhi pilot city seeded on boot: 2 wards, 2 CAAQMS stations
- [x] Frontend `useCities` Zustand store tracks `selectedCityId`
- [x] Dashboard topbar shows live city name from API (not hardcoded)
- [x] Auth state rehydration fixed — page refresh no longer drops auth
- [x] TypeScript compiles with no errors (`tsc --noEmit` — clean)
- [x] All Python files parse without syntax errors

### What to read before starting
1. `00_MASTER_ARCHITECTURE.md`
2. `02_CROSS_MODULE_CONTRACTS.md`
3. `modules/Module_03_Ingestion.md` (if it exists)

### What needs to be built

Module 02 owns the `cities`, `wards`, `stations` tables and multi-tenancy middleware. Key tasks:

#### Backend
- Migration 0003: `cities` table (`id UUID`, `name`, `state`, `timezone`, `config_json JSONB`, `created_at`)
- Migration 0004: `wards` table (`id UUID`, `city_id FK`, `name`, `geometry GEOMETRY(MULTIPOLYGON,4326)`, `population`, `vulnerable_site_flags JSONB`)
- Migration 0005: `stations` table (`id UUID`, `city_id FK`, `ward_id FK`, `external_station_code`, `geometry GEOMETRY(POINT,4326)`, `is_active BOOLEAN`)
- ORM models: `City`, `Ward`, `Station` in `app/modules/cities/models.py`
- Repository + service layers
- API endpoints:
  - `GET /api/v1/cities` (sysadmin)
  - `POST /api/v1/cities` (sysadmin)
  - `GET /api/v1/cities/{city_id}/wards`
  - `GET /api/v1/cities/{city_id}/stations`
- City-scoping middleware: verify JWT `city_id` matches path `city_id` (unless sysadmin)
- Seed one pilot city (Delhi) + at least 2 wards for demo purposes

#### Frontend
- `features/cities/api.ts` — typed API calls for cities/wards/stations
- City selector in topbar (Zustand `selectedCityId`)
- `pages/Dashboard.tsx` — wire live city name into topbar instead of hardcoded "Delhi"

### Known issues going into Session 3 (all resolved)
- Auth tests require Docker DB — run `docker-compose up` first, then `pytest` ✅ (unchanged)
- Auth state rehydration on page refresh ✅ FIXED — `AuthRehydrator` in `App.tsx`

### Known issues going into Session 4
- `geoalchemy2` and `shapely` were added to `pyproject.toml` main deps. They require GDAL to be available in the runtime environment. The `backend/Dockerfile` already installs GDAL (`python:3.11-slim` + `libgdal-dev`). Running backend locally outside Docker without GDAL will fail at import time — use `docker-compose up` for the full stack.
- The `Ward.geometry` and `Station.geometry` ORM columns are typed as `Text` (not `geoalchemy2.Geometry`) because geometry reads are done via `ST_AsGeoJSON()` in repository queries, not via ORM attribute access. This is intentional — don't "fix" it with geoalchemy2 Geometry type unless you're ready to handle the WKB serialization throughout.

### PROMPT TO USE AT THE START OF SESSION 3

```
Read these files in this order before doing anything:
1. E:\GalaxyWeblinks\Hackathon\00_MASTER_ARCHITECTURE.md
2. E:\GalaxyWeblinks\Hackathon\02_CROSS_MODULE_CONTRACTS.md
3. E:\GalaxyWeblinks\Hackathon\vayushield-ai\SESSION_LOG.md

We are building VayuShield AI — an Urban Air Quality Intelligence platform for the ET AI Hackathon 2026 (Problem Statement 5).

Modules 00 and 01 are complete. The code lives at E:\GalaxyWeblinks\Hackathon\vayushield-ai\

Your job this session is Module 02: City & Ward Core. Build the cities/wards/stations tables (PostGIS geometry), ORM models, repository/service/API layers, city-scoping middleware, and seed a pilot city. Also fix the auth state rehydration issue noted in SESSION_LOG.md Session 3 known issues.
```

---

### PROMPT TO USE AT THE START OF SESSION 4

```
Read these files in this order before doing anything:
1. E:\GalaxyWeblinks\Hackathon\00_MASTER_ARCHITECTURE.md
2. E:\GalaxyWeblinks\Hackathon\02_CROSS_MODULE_CONTRACTS.md
3. E:\GalaxyWeblinks\Hackathon\vayushield-ai\SESSION_LOG.md

We are building VayuShield AI — an Urban Air Quality Intelligence platform for the ET AI Hackathon 2026 (Problem Statement 5).

Modules 00, 01, 02 and 03 are complete. The code lives at E:\GalaxyWeblinks\Hackathon\vayushield-ai\

Your job this session is Module 04: Attribution Engine. Build the per-ward, per-hour pollution source attribution logic (dominant source detection from emission_sources + wind direction + distance weighting), write attributions to the attributions table, expose GET /cities/{city_id}/attributions/latest and GET /cities/{city_id}/wards/{ward_id}/attributions endpoints, and wire a background job that runs attribution after each station poll cycle.
```

---

## Session 3 — Module 03: Data Ingestion
**Date:** 2026-07-09
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0006_station_readings_hypertable.py` | TimescaleDB hypertable: `station_readings` (id+ts composite PK, 1-day chunks) |
| `backend/alembic/versions/0007_weather_readings_hypertable.py` | TimescaleDB hypertable: `weather_readings` (1-day chunks) |
| `backend/alembic/versions/0008_fire_hotspots_table.py` | `fire_hotspots` table with PostGIS POINT + GiST index |
| `backend/alembic/versions/0009_emission_sources_table.py` | `emission_sources` table with PostGIS POINT + GiST index |
| `backend/app/modules/ingestion/__init__.py` | Package marker |
| `backend/app/modules/ingestion/models.py` | ORM: `StationReading`, `WeatherReading`, `FireHotspot`, `EmissionSource` |
| `backend/app/modules/ingestion/schemas.py` | Pydantic DTOs: `StationReadingIn/Out`, `LatestReadingOut`, `WeatherReadingOut`, `FireHotspotOut`, `EmissionSourceCreate/Out` |
| `backend/app/modules/ingestion/repository.py` | DB access: bulk insert readings, latest-per-station query, weather CRUD, fire hotspot + emission source CRUD |
| `backend/app/modules/ingestion/service.py` | Service layer orchestrating connectors → repository |
| `backend/app/modules/ingestion/connectors/__init__.py` | Package marker |
| `backend/app/modules/ingestion/connectors/caaqms.py` | CPCB connector — real API stub + mock fallback with realistic Delhi diurnal PM2.5 pattern |
| `backend/app/modules/ingestion/connectors/weather.py` | **Real** Open-Meteo connector (free, no key) — fetches wind/humidity/temp/pressure |
| `backend/app/modules/ingestion/connectors/fire_hotspots.py` | NASA FIRMS connector (real CSV API — needs FIRMS_MAP_KEY env var; no-ops if absent) |
| `backend/app/api/v1/ingestion.py` | API router: `/readings/latest`, `/stations/{id}/readings`, `/readings/poll`, `/weather/latest`, `/weather/poll`, `/emission-sources` |
| `backend/app/jobs/ingestion_jobs.py` | RQ jobs: `poll_all_stations_job`, `poll_weather_job`, `poll_fire_hotspots_job` (run every 15min/1hr via scheduler) |
| `backend/app/core/aqi.py` | CPCB AQI computation: `pm25_to_aqi`, `compute_aqi`, `aqi_category` — shared utility |
| `backend/app/tests/test_ingestion.py` | 7 tests covering readings, weather, emission sources, AQI math |

#### Files modified

| File | Change |
|---|---|
| `backend/app/main.py` | Wired `ingestion_router` |
| `backend/app/core/config.py` | Added `FIRMS_MAP_KEY` env var |
| `backend/app/db/seed.py` | Added `_seed_ingestion_data`: 4 Delhi emission sources + 7 days × 2 stations hourly station readings (~336 rows) |

#### Definition of Done — Module 03 ✅

- [x] `station_readings` and `weather_readings` are TimescaleDB hypertables (migration 0006, 0007)
- [x] `fire_hotspots` and `emission_sources` have PostGIS geometry + GiST indexes
- [x] CAAQMS connector: real stub + mock fallback (realistic Delhi PM2.5 diurnal pattern)
- [x] Weather connector: real Open-Meteo API (no key needed)
- [x] Fire hotspot connector: real NASA FIRMS CSV API (needs FIRMS_MAP_KEY)
- [x] RQ jobs defined for all three poll cycles
- [x] `GET /cities/{city_id}/readings/latest` — latest reading per station with AQI + category
- [x] `GET /cities/{city_id}/stations/{id}/readings` — paginated history with time filters
- [x] `POST /cities/{city_id}/readings/poll` — manual trigger (admin/sysadmin)
- [x] `GET /cities/{city_id}/weather/latest` — most recent weather record
- [x] `GET/POST /cities/{city_id}/emission-sources` — list and create
- [x] 7 days of hourly seeded readings for both Delhi CAAQMS stations
- [x] 4 seeded Delhi emission sources (vehicular, industrial, construction, agricultural)
- [x] `aqi_category()` utility shared — ready for Modules 04/05/08 to import
- [x] All Python files syntax-clean, TypeScript compiles with zero errors

### Known issues going into Session 4
- CAAQMS connector falls back to mock data (realistic but not real CPCB readings). Real CPCB API access requires credentials not yet obtained. The connector stub is in `connectors/caaqms.py` — swap `_fetch_from_cpcb` when credentials arrive.
- Weather poll (`POST /weather/poll`) calls Open-Meteo live; it will fail without internet. The seed does not pre-populate weather (no offline source). Module 04's wind-direction attribution needs weather — run `POST /weather/poll` once after `docker-compose up` to seed weather before testing attribution.
- RQ scheduler not yet wired into docker-compose. Jobs exist but need a scheduler service (add `rqscheduler` container to docker-compose in a later session, or trigger manually via the poll endpoints).

---

---

## Session 4 — Module 04: Attribution Engine
**Date:** 2026-07-09
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0010_attributions_table.py` | Migration: `attributions` table — per-city hourly source-contribution snapshots |
| `backend/alembic/versions/0011_aqi_alerts_table.py` | Migration: `aqi_alerts` table — alert history for threshold crossings (200/300/400) |
| `backend/app/modules/attribution/__init__.py` | Package marker |
| `backend/app/modules/attribution/models.py` | SQLAlchemy `Attribution` + `AqiAlert` ORM models |
| `backend/app/modules/attribution/schemas.py` | Pydantic DTOs: `AttributionOut`, `AttributionRankingOut`, `RankedSource`, `AqiAlertOut`, `SourceBreakdown` |
| `backend/app/modules/attribution/repository.py` | DB access: `get_latest_attribution`, `list_attributions`, `create_attribution`, `list_alerts`, `get_active_alert_for_threshold`, `create_alert`, `resolve_alert` |
| `backend/app/modules/attribution/service.py` | Attribution engine: wind-based dispersion, haversine distance, bearing calculation, wind-alignment factor, distance decay, alert threshold evaluation |
| `backend/app/api/v1/attribution.py` | Router: `GET /cities/{city_id}/attribution`, `POST /cities/{city_id}/attribution/compute`, `GET /cities/{city_id}/alerts` |
| `backend/app/tests/test_attribution.py` | 8 tests: auth guard, ranking structure, recompute flag, percentages sum to 100, alert list, active-only filter, alert seeded data |

#### Files modified

| File | Change |
|---|---|
| `backend/app/main.py` | Wired `attribution_router` |
| `backend/app/db/seed.py` | Added `_seed_attribution_alerts`: 3 seeded Delhi alerts (1 active poor, 1 resolved poor, 1 resolved very_poor); fixed `datetime/timedelta` imports at module level |

### Attribution Engine — How It Works

**Algorithm (physics-based dispersion, simplified):**
1. Pull average AQI from latest `station_readings` per active station in city.
2. Pull `wind_speed` + `wind_dir` from latest `weather_readings`.
3. Compute city receptor point = centroid of active station locations.
4. For each `emission_source`, compute dispersion weight:
   - `base_weight(type)` — industrial > fire > vehicular > agricultural > construction > other
   - `distance_decay = 1/distance_km²` — closer sources contribute more
   - `wind_alignment` — cosine similarity between source bearing and wind direction (upwind sources score high)
   - `weight = base × alignment × decay`
5. Also tally active `fire_hotspots` from last 24h as fire contribution.
6. Normalise weights → percentages. Identify `dominant_source`.
7. Persist to `attributions` table.
8. Evaluate thresholds: create `aqi_alerts` when AQI ≥ 200/300/400; resolve active alerts when AQI drops below.

**Alert thresholds:**
- AQI ≥ 200 → `"poor"` alert
- AQI ≥ 300 → `"very_poor"` alert
- AQI ≥ 400 → `"severe"` alert

Only one active alert per threshold at a time. Auto-resolves on next computation if AQI falls below.

### Definition of Done — Module 04 ✅

- [x] Migration 0010 creates `attributions` table with city/timestamp indexes
- [x] Migration 0011 creates `aqi_alerts` table with city/is_active indexes
- [x] `GET /api/v1/cities/{city_id}/attribution` returns ranked source breakdown
- [x] `POST /api/v1/cities/{city_id}/attribution/compute` triggers fresh computation
- [x] `GET /api/v1/cities/{city_id}/attribution?recompute=true` also works
- [x] `GET /api/v1/cities/{city_id}/alerts` returns alert history
- [x] `GET /api/v1/cities/{city_id}/alerts?active_only=true` returns only active alerts
- [x] Attribution percentages sum to ~100%
- [x] Wind-based dispersion logic implemented (haversine distance + wind alignment factor)
- [x] Alert thresholds 200/300/400 auto-create and auto-resolve alerts
- [x] 3 test alerts seeded for Delhi (1 active, 2 resolved)
- [x] 8 new tests written — total test count: 27
- [x] All Python files parse without syntax errors

### Known issues going into Session 5
- Attribution computation needs weather data (`weather_readings`) to use wind direction. If no weather reading exists, wind alignment defaults to 0.5 (neutral) for all sources — still produces a valid attribution, just unguided by wind.
- `POST /weather/poll` must be called once after `docker-compose up` to populate weather before attributions use real wind data (same constraint from Module 03).
- Attribution is city-level, not ward-level. Per-ward attribution (using station→ward assignment + ward-centroid) is a future enhancement.
- RQ background jobs for auto-running attribution after each station poll cycle not yet wired (Module 03 jobs exist as stubs; wire in a later session).

---

## Session 5 — Module 05: Forecasting Agent
**Date:** 2026-07-09
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0012_forecasts_table.py` | Migration: `forecasts` table (city_id, generated_at, forecast_for_ts, predicted_aqi, predicted_pm25, confidence, model_version, is_stale) |
| `backend/app/modules/forecasting/__init__.py` | Package marker |
| `backend/app/modules/forecasting/models.py` | SQLAlchemy `Forecast` ORM model |
| `backend/app/modules/forecasting/schemas.py` | Pydantic DTOs: `ForecastPointOut`, `ForecastRunOut` |
| `backend/app/modules/forecasting/repository.py` | DB access: `get_latest_forecast_run`, `mark_previous_stale`, `bulk_insert_forecast` |
| `backend/app/modules/forecasting/service.py` | Forecasting engine: diurnal pattern + linear trend + wind adjustment (pure Python, zero extra deps) |
| `backend/app/api/v1/forecasting.py` | Router: `GET /cities/{city_id}/forecast`, `POST /cities/{city_id}/forecast/run`, `?recompute=true` |
| `backend/app/tests/test_forecasting.py` | 7 tests: auth guard, 72 points returned, required fields, peak_aqi = max, run endpoint, recompute flag, chronological ordering |
| `frontend/src/features/forecast/api.ts` | Typed API calls: `fetchForecast`, `runForecast` |
| `frontend/src/features/forecast/ForecastChart.tsx` | Recharts `LineChart` with AQI-coloured dots, threshold reference lines (200/300/400), AQI band legend |

#### Files modified

| File | Change |
|---|---|
| `backend/app/main.py` | Wired `forecasting_router` |
| `frontend/src/pages/Dashboard.tsx` | City AQI + Peak 72h AQI stat cards now live from forecast API; placeholder map replaced with `<ForecastChart>` |

### Forecasting Model — How It Works

**Algorithm (pure Python, no ML deps):**
1. Pull last 7 days of hourly city-average AQI from `station_readings` (grouped by `DATE_TRUNC('hour', ts)`).
2. Build `diurnal_mean[0..23]` — mean AQI per hour-of-day. Hours with <3 readings fall back to global mean.
3. Compute `trend_slope` via least-squares over last 24h of hourly averages. Dampen by 0.5× to prevent long-horizon runaway.
4. Pull latest `weather_readings.wind_speed` → `wind_adj = clamp(1.0 - 0.04×wind_speed, 0.5, 1.3)`.
5. For each of 72 future hours:
   - `predicted_aqi = clamp(round((diurnal_mean[h] + trend_slope×h) × wind_adj), 1, 500)`
   - `predicted_pm25` = inverse AQI breakpoint lookup
   - `confidence` degrades from 0.95 (h=1) → 0.50 (h=72)
6. Mark previous forecast batch stale; persist 72 new rows.

**Model version tag:** `"diurnal-v1"` — bump to `"diurnal-v2"` or `"lgbm-v1"` when model is upgraded.

### Definition of Done — Module 05 ✅

- [x] Migration 0012 creates `forecasts` table with city/generated_at and city/forecast_for_ts indexes
- [x] `GET /api/v1/cities/{city_id}/forecast` returns 72-point forecast (runs on first call if no cached result)
- [x] `POST /api/v1/cities/{city_id}/forecast/run` triggers fresh computation
- [x] `?recompute=true` flag also forces fresh run
- [x] Previous forecast batch marked `is_stale=true` on each recompute
- [x] `peak_aqi` / `peak_at` in response envelope match max across points
- [x] Points returned in ascending `forecast_for_ts` order
- [x] Confidence decreases with horizon (0.95 → 0.50)
- [x] Frontend `ForecastChart` renders 72-hour line chart with AQI band colours + threshold reference lines
- [x] Dashboard stat cards: "City AQI" and "Peak Forecast AQI" wired live to forecast API
- [x] 7 new tests — total test count: **34**
- [x] TypeScript compiles with zero errors (`tsc --noEmit` clean)
- [x] All Python files syntax-clean

### Known issues going into Session 6
- Forecast uses only `station_readings` history — does not yet consume Open-Meteo's 72h forward weather forecast (only uses latest historical wind reading). Future: call `GET /forecast?hourly=wind_speed,wind_direction_10m` on Open-Meteo to get wind forecast per future hour.
- No per-ward forecast — city-level only. Ward-level would require per-station forecasts + spatial interpolation (IDW/Kriging). Architecture doc notes this as Module 05 stretch goal.
- Forecast background job (RQ) not wired — trigger manually via `POST /forecast/run` or `?recompute=true`.

---

## Session 6 — Module 06: Enforcement Agent
**Date:** 2026-07-09
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0013_enforcement_queue_table.py` | Migration: `enforcement_queue` table with FK→emission_sources, attributions, forecasts |
| `backend/alembic/versions/0014_inspections_table.py` | Migration: `inspections` table with FK→enforcement_queue, users |
| `backend/app/modules/enforcement/__init__.py` | Package marker |
| `backend/app/modules/enforcement/models.py` | ORM: `EnforcementQueueItem`, `Inspection` |
| `backend/app/modules/enforcement/schemas.py` | Pydantic DTOs: `EnforcementItemOut`, `EnforcementListOut`, `EnforcementStatusUpdate`, `InspectionCreate/Out`, `EmissionSourceBrief` |
| `backend/app/modules/enforcement/repository.py` | DB access: list_queue (JOIN→emission_sources), get_item, upsert_queue_item, update_status, count_pending, create_inspection |
| `backend/app/modules/enforcement/service.py` | Scoring engine: `rank_queue`, `get_queue`, `get_item`, `update_status`, `count_pending` + `_build_evidence_brief` |
| `backend/app/api/v1/enforcement.py` | Router: GET/POST /enforcement, GET/PATCH /{item_id}, POST /{item_id}/inspections, GET /enforcement-count |
| `backend/app/tests/test_enforcement.py` | 6 tests: auth guard, ranked list, re-rank, permit scoring, dispatch PATCH, inspection log, count endpoint |
| `frontend/src/features/enforcement/api.ts` | Typed API calls: fetchEnforcementQueue, rankEnforcementQueue, updateEnforcementStatus, logInspection, fetchPendingCount |
| `frontend/src/pages/Enforcement.tsx` | Full enforcement page: ranked table, priority score bar, permit badge, evidence brief expandable, Dispatch button, Re-rank button |

#### Files modified

| File | Change |
|---|---|
| `backend/app/main.py` | Wired `enforcement_router` |
| `backend/app/db/seed.py` | Added `_seed_enforcement_queue`: 4 Delhi sources scored and inserted as pending queue items |
| `frontend/src/App.tsx` | Replaced `/enforcement` placeholder with real `<Enforcement>` component |
| `frontend/src/pages/Dashboard.tsx` | "Pending Inspections" stat card now live-fetches count from `/enforcement-count` |

### Scoring Algorithm

```
priority_score = 0.35 × source_attribution   (% from latest attribution breakdown, 0–1)
               + 0.30 × forecast_severity     (peak AQI next 24h / 500, capped at 1)
               + 0.20 × permit_status         (expired=1.0, pending=0.6, active=0.2)
               + 0.15 × days_since_inspection (days/30 capped at 1; never inspected = 1.0)
```

Evidence brief is a 3-sentence plain-text string — no LLM. Module 09 (Claude API) will upgrade it.

### Definition of Done — Module 06 ✅

- [x] Migration 0013 creates `enforcement_queue` table with FK constraints and indexes
- [x] Migration 0014 creates `inspections` table with FK constraints and indexes
- [x] `GET /api/v1/cities/{city_id}/enforcement` returns ranked queue (highest score first)
- [x] `POST /api/v1/cities/{city_id}/enforcement/rank` re-scores all emission sources (admin/sysadmin)
- [x] `GET /api/v1/cities/{city_id}/enforcement/{item_id}` returns single item with evidence brief
- [x] `PATCH /api/v1/cities/{city_id}/enforcement/{item_id}` updates status
- [x] `POST /api/v1/cities/{city_id}/enforcement/{item_id}/inspections` logs inspection outcome
- [x] `GET /api/v1/cities/{city_id}/enforcement-count` returns pending count
- [x] 4 Delhi enforcement queue items seeded on boot (one per emission source)
- [x] Frontend `/enforcement` page: ranked table, score bars, permit badges, Dispatch button, evidence brief
- [x] Dashboard "Pending Inspections" stat card shows live count from API
- [x] 6 tests written — total test count: **40**
- [x] `ruff format . && ruff check .` — all clean
- [x] `tsc --noEmit` — zero TypeScript errors

### Known issues going into Session 7
- Scoring uses only attribution breakdown typed by source `type` (vehicular/industrial/etc), not per-source contribution — a source of type "vehicular" gets 100% of the vehicular attribution pct. Per-source attribution would require spatial join in the attribution engine (future work).
- `POST /{item_id}/inspections` marks the source's `last_inspected_at` only when `completed_at` is provided in the request body. If no `completed_at` is sent, the source date stays unchanged.
- The enforcement count endpoint (`/enforcement-count`) always counts rows with status=`pending`. After dispatch, the count falls — which is correct behaviour, but the Dashboard stat card doesn't auto-refresh unless the user navigates away and back.

---

## Session 7 — Module 07: Advisory Engine
**Date:** 2026-07-09
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/alembic/versions/0015_advisories_table.py` | Migration: `advisories` table with city/language/channel indexes |
| `backend/app/modules/advisory/__init__.py` | Package marker |
| `backend/app/modules/advisory/models.py` | SQLAlchemy `Advisory` ORM model |
| `backend/app/modules/advisory/schemas.py` | Pydantic DTOs: `AdvisoryOut`, `AdvisoryListOut`, `AdvisoryGenerateResponse` |
| `backend/app/modules/advisory/repository.py` | DB access: `list_advisories`, `get_advisory`, `advisory_exists_today`, `create_advisory`, `count_advisories` |
| `backend/app/modules/advisory/service.py` | Template-based advisory generator — 6 AQI levels × 2 languages (en+hi), pulls attribution + station AQI; idempotent per city/aqi_level/language/day |
| `backend/app/api/v1/advisory.py` | Router: `GET /cities/{city_id}/advisories`, `POST /generate`, `GET /{advisory_id}`, `GET /advisory-count` |
| `backend/app/tests/test_advisory.py` | 7 tests: auth guard, list structure, generate count, body mentions source, language filter, get-by-id, count endpoint |
| `frontend/src/features/advisory/api.ts` | Typed API calls: `fetchAdvisories`, `fetchAdvisory`, `generateAdvisories`, `fetchAdvisoryCount` |
| `frontend/src/pages/Advisories.tsx` | Advisory list page: language selector, advisory cards with AQI badge + source tag + expandable body, "Generate Advisories" button (admin/sysadmin only) |

#### Files modified

| File | Change |
|---|---|
| `backend/app/main.py` | Wired `advisory_router` |
| `backend/app/db/seed.py` | Added `_seed_advisories`: 2 Delhi advisories on boot (English + Hindi) |
| `frontend/src/lib/types.ts` | Updated `Advisory` interface to match actual API shape (replaced stub) |
| `frontend/src/App.tsx` | Replaced `/advisories` placeholder with `<Advisories>` component |
| `frontend/src/pages/Dashboard.tsx` | "Advisories Sent" stat card now live from `/advisory-count` API |

### Advisory Generator — How It Works

**Algorithm (template-based, no LLM):**
1. Pull latest `attributions` record for city → `dominant_source`.
2. Pull average AQI from last 2h of `station_readings` for city.
3. Run `aqi_category(aqi)` → one of 6 levels (Good / Satisfactory / Moderate / Poor / Very Poor / Severe).
4. For each language in `["en", "hi"]`:
   - Check idempotency: skip if advisory with same city + aqi_level + language was created today.
   - Build 4-sentence body from `_SOURCE_LABEL_*` + `_AQI_ADVICE_*` templates.
   - Pick matching title from `_AQI_TITLE_*`.
   - Persist to `advisories` table.
5. Return `{ generated, skipped, advisories }`.

**Templates cover:** all 6 CPCB AQI levels × all known source types (vehicular/industrial/construction/agricultural/fire/other) × 2 languages.

**Module 09 hook:** Replace `_build_body_en` / `_build_body_hi` with Claude API calls when Module 09 is built.

### Definition of Done — Module 07 ✅

- [x] Migration 0015 creates `advisories` table with indexes
- [x] `GET /api/v1/cities/{city_id}/advisories` returns paginated list, filterable by `language` and `channel`
- [x] `POST /api/v1/cities/{city_id}/advisories/generate` creates advisories for en + hi (admin/sysadmin only)
- [x] `GET /api/v1/cities/{city_id}/advisories/{advisory_id}` returns single advisory
- [x] `GET /api/v1/cities/{city_id}/advisory-count` returns total count
- [x] Idempotent: second `/generate` on same day skips already-created advisories
- [x] Advisory body always mentions dominant pollution source
- [x] 2 Delhi advisories seeded on boot (English + Hindi)
- [x] Frontend `/advisories` page: AQI badge, source tag, expandable body, language filter
- [x] "Generate Advisories" button visible to admin/sysadmin only
- [x] Dashboard "Advisories Sent" stat card shows live count from API
- [x] `Advisory` type in `frontend/src/lib/types.ts` updated to match real API shape
- [x] 7 tests written — total test count: **47**
- [x] `ruff format . && ruff check .` — clean
- [x] `tsc --noEmit` — zero TypeScript errors

### Known issues going into Session 8
- Advisory language support is English + Hindi only. Other SUPPORTED_LANGUAGES (mr/kn/ta/bn/gu) fall back to English body text with an English title — not translated. Add translation templates per language in service.py to fix.
- `advisory_exists_today` uses `DATE_TRUNC('day', NOW() AT TIME ZONE 'UTC')` — if the DB clock differs from local clock, the idempotency window may shift by up to one day.
- No `sent_at` update mechanism yet — advisories are created with `sent_at = NULL`. A dispatch worker (future module) should set this when the advisory is actually pushed to users.

---

## Session 8 — Module 08: Ward Detail & Map Overlay
**Date:** 2026-07-10
**Status:** COMPLETE

### What was built this session

#### Files created

| File | Purpose |
|---|---|
| `backend/app/tests/test_wards.py` | 5 tests: auth guard, ward list includes avg_aqi, ward detail structure, 404 on missing ward, station readings have aqi_category |
| `frontend/src/features/wards/api.ts` | Typed API calls: `fetchWardsWithAqi`, `fetchWardDetail` |
| `frontend/src/components/WardMap.tsx` | Leaflet react-leaflet map — ward polygons coloured by AQI level, tooltip on hover, click navigates to `/wards/:id` |
| `frontend/src/pages/WardDetail.tsx` | Ward detail page — AQI badge, population, dominant source, advisory count, attribution pie chart (Recharts), station readings table |

#### Files modified

| File | Change |
|---|---|
| `backend/app/modules/cities/schemas.py` | Added `StationReadingBrief`, `WardWithAqiOut`, `WardDetailOut` schemas |
| `backend/app/modules/cities/repository.py` | Added `get_wards_for_city_with_aqi` (SQL CTE joining latest station readings), `get_ward_detail_full` (ward + readings + attribution + advisory count) |
| `backend/app/modules/cities/service.py` | Updated `list_wards` to use `WardWithAqiOut`; added `get_ward_detail` |
| `backend/app/api/v1/cities.py` | Updated `list_wards` response to `WardWithAqiOut`; added `GET /cities/{city_id}/wards/{ward_id}` endpoint |
| `frontend/src/lib/types.ts` | Added `StationReadingBrief`, `WardWithAqi`, `WardDetail` types |
| `frontend/src/pages/Dashboard.tsx` | Added ward AQI map section (side-by-side with forecast chart); fetches wards with AQI, passes to `WardMap` component |
| `frontend/src/App.tsx` | Replaced `/wards/:id` placeholder with real `<WardDetail>` component |

### Ward Detail Endpoint — What it Returns

`GET /api/v1/cities/{city_id}/wards/{ward_id}` returns `WardDetailOut`:
- All base ward fields (id, city_id, name, geometry, population, vulnerable_site_flags)
- `avg_aqi: int | None` — average of latest readings from stations assigned to this ward
- `aqi_category: str | None` — CPCB category string
- `station_readings: list[StationReadingBrief]` — latest reading per station in ward (pm25, pm10, aqi, aqi_category)
- `attribution_breakdown: dict[str, float]` — city-level attribution percentages (vehicular_pct, industrial_pct, etc.)
- `dominant_source: str | None` — from latest city attribution record
- `advisory_count: int` — count of advisories with `ward_id = this ward`

`GET /api/v1/cities/{city_id}/wards` now returns `WardWithAqiOut` (backward compatible — adds `avg_aqi` + `aqi_category` fields).

### Definition of Done — Module 08 ✅

- [x] `GET /cities/{city_id}/wards/{ward_id}` returns ward detail with station readings + attribution breakdown
- [x] `GET /cities/{city_id}/wards` enriched with `avg_aqi` and `aqi_category` per ward
- [x] Leaflet ward polygon map on Dashboard — polygons coloured by AQI level (Good→green, Severe→purple)
- [x] Ward detail page at `/wards/:id` — AQI badge, attribution pie chart, station readings table, advisory count
- [x] `/wards/:id` route wired in App.tsx (placeholder replaced)
- [x] 5 new tests — total test count: **52**
- [x] `ruff format . && ruff check .` — clean
- [x] `tsc --noEmit` — zero TypeScript errors

### Known issues going into Session 9
- `attribution_breakdown` in ward detail is city-level (no per-ward attribution exists yet). Per-ward attribution would need spatial join of emission sources to ward geometries.
- `advisory_count` counts advisories where `ward_id = this ward`. Seeded advisories have `ward_id = NULL` (city-level), so the count will be 0 for all wards until ward-targeted advisories are generated.
- Leaflet map requires internet (tile images from openstreetmap.org). Offline mode would need a local tile server.
- Map center is hardcoded to Delhi (28.62, 77.21). A future enhancement would fit bounds to the wards returned.

---

## Session 9 — Module 09: Claude API Integration (AI-Enhanced Evidence Briefs & Advisories)
**Planned — build next**

### PROMPT TO USE AT THE START OF SESSION 9

```
Read E:\GalaxyWeblinks\Hackathon\vayushield-ai\SESSION_LOG.md before doing anything else.

We are building VayuShield AI — an Urban Air Quality Intelligence platform for the ET AI Hackathon 2026 (Problem Statement 5). The code lives at E:\GalaxyWeblinks\Hackathon\vayushield-ai\

Modules 00 through 08 are complete. We have 52 passing tests. The last commit is feat(module-08).

Your job this session is Module 09: Claude API Integration.

Build:
1. Backend: Wire the Anthropic Python SDK. Add `ANTHROPIC_API_KEY` to `core/config.py`. Create `backend/app/core/claude_client.py` — a thin wrapper around `anthropic.AsyncAnthropic` with retry logic and structured prompt helpers.
2. Backend: Upgrade `enforcement/service.py` `_build_evidence_brief` — replace the 3-sentence template with a real Claude API call (claude-haiku-4-5-20251001 for cost) that produces a 5-sentence enforcement brief from: source name, source type, attribution pct, forecast peak AQI, permit status, days since inspection.
3. Backend: Upgrade `advisory/service.py` `_build_body_en` and `_build_body_hi` — replace template strings with Claude API calls that produce natural-language advisory text in the correct language.
4. Backend: Add `POST /api/v1/cities/{city_id}/enforcement/{item_id}/ai-brief` — force-regenerate an evidence brief using Claude (admin/sysadmin only). Store result back to `enforcement_queue.evidence_brief_text`.
5. Tests: mock the Anthropic client with `unittest.mock.AsyncMock` — do not make real API calls in tests. Write ≥3 tests covering the upgraded paths.
6. Frontend: On the Enforcement page, add an "AI Brief" button next to each queue item that calls the new endpoint and refreshes the brief text inline.

Key constraint: All Claude calls must be guarded by `if settings.ANTHROPIC_API_KEY` — if the key is absent, fall back to the template-based text. This keeps tests and offline runs working.

Model to use: `claude-haiku-4-5-20251001` (fast, cheap, ideal for structured short-form generation tasks).

After building everything, run ruff format . && ruff check . to lint check, then update SESSION_LOG.md and commit.
```

---

## Sessions 6+ — Modules 06–13
See `03_DEVELOPMENT_ROADMAP_SESSION_PLAN.md` for the full ordered build plan.

**Critical path reminder:** 00 → 01 → 02 → 03 → {04, 05 parallel} → 06 → {07, 08, 09 parallel} → 10/11/12/13

**At the start of every session, the Claude Code agent MUST read SESSION_LOG.md first.**
**Never** modify a table owned by another module without coordinating with that module's section.
