# FuelLink — Tech Stack & Build System

## Architecture Overview

Three independently deployable components behind Nginx, all orchestrated via Docker Compose.

```
Flutter Mobile ──► Nginx ──► FastAPI (uvicorn)
Admin Web (React) ──►            ├──► PostgreSQL + PostGIS
                                 ├──► Redis (pub/sub + cache)
                                 └──► Firebase Admin SDK (FCM)
```

---

## Backend (`backend/`)

| Concern | Choice |
|---|---|
| Framework | FastAPI 0.111 (async) |
| Server | Uvicorn with standard extras |
| ORM | SQLAlchemy 2.0 (async) |
| DB | PostgreSQL 16 + PostGIS 3.4 |
| Spatial queries | GeoAlchemy2 + PostGIS `ST_DWithin` |
| Cache / pub-sub | Redis 7 via aioredis |
| Migrations | Alembic |
| Auth | JWT (python-jose) + bcrypt/passlib; access token 24h, refresh 30d |
| Validation | Pydantic v2 + pydantic-settings |
| Push notifications | Firebase Admin SDK v6 (FCM v1) |
| Background jobs | APScheduler — stale entry expiry (2 min), near-turn alerts (1 min) |
| WebSocket | Starlette WebSocket + Redis pub/sub fanout |
| Python | 3.11+ |

### Backend Commands
```bash
# Run with Docker (recommended)
cd infra && docker compose up -d
docker exec -it fuellink_backend alembic upgrade head

# Run locally
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

---

## Mobile App (`mobile/`)

| Concern | Choice |
|---|---|
| Framework | Flutter (Dart SDK >=3.3.0) |
| State management | Riverpod 2 (`flutter_riverpod`, `riverpod_annotation`) |
| Navigation | go_router 13 |
| HTTP client | Dio 5 + Retrofit 4 |
| Code generation | build_runner + json_serializable + riverpod_generator + retrofit_generator |
| Local storage | sqflite (offline cache), shared_preferences, flutter_secure_storage |
| Maps | flutter_map 6 (OpenStreetMap, no billing) + latlong2 |
| Location | geolocator + permission_handler |
| Push notifications | firebase_messaging + flutter_local_notifications |
| WebSocket | web_socket_channel 3 |
| UI extras | google_fonts, cached_network_image, shimmer, lottie, qr_flutter |
| Linting | flutter_lints |

### Mobile Commands
```bash
cd mobile
flutter pub get

# Run dev (reads DEV_HOST from root .env)
# Windows:
..\scripts\run-mobile-dev.ps1
# macOS/Linux:
../scripts/run-mobile-dev.sh

# Regenerate code (Riverpod, Retrofit, JSON serialization)
dart run build_runner build --delete-conflicting-outputs
# Watch mode during development:
dart run build_runner watch --delete-conflicting-outputs

# Analyze
flutter analyze

# Test
flutter test

# Production APK
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.fuellink.et/api/v1 \
  --dart-define=WS_BASE_URL=wss://api.fuellink.et
```

---

## Admin Web (`admin-web/`)

| Concern | Choice |
|---|---|
| Framework | React 18 + TypeScript 5 |
| Build tool | Vite 5 |
| Routing | react-router-dom v6 |
| HTTP | Axios |
| Data fetching | react-query v3 |
| Maps | Leaflet + react-leaflet |
| Charts | Recharts |
| Auth | Firebase JS SDK (phone OTP) |
| Notifications | react-hot-toast |
| Icons | lucide-react |

### Admin Web Commands
```bash
cd admin-web
npm install
npm run dev        # dev server at http://localhost:5174
npm run build      # tsc + vite build → dist/
npm run preview    # preview production build
npm run lint       # eslint src
```

---

## Infrastructure (`infra/`)

| Service | Image | Port |
|---|---|---|
| PostgreSQL + PostGIS | postgis/postgis:16-3.4-alpine | 5432 |
| Redis | redis:7-alpine | 6379 |
| FastAPI backend | custom Dockerfile | 8000 |
| Admin web (dev) | node:20-alpine (Vite) | 5174 |

### Infra Commands
```bash
# Development
cd infra
docker compose up -d
docker compose down          # stop (keep volumes)
docker compose down -v       # ⚠️ DESTROYS postgres_data volume

# Production
docker compose -f docker-compose.prod.yml up -d

# View logs
docker compose logs -f backend
```

---

## Environment Configuration

Single source of truth: **root `.env`** (copy from `.env.example`).

Key variables:
- `DEV_HOST` — LAN IP for mobile dev (use `10.0.2.2` for Android emulator)
- `DEV_API_PORT` — backend port (default 8000)
- `SECRET_KEY` — JWT signing key (64-char random for prod)
- `FIREBASE_CREDENTIALS_PATH` — path to service account JSON
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD` — prod credentials

The root `.env` is read by Docker Compose, mobile scripts, and the backend simultaneously.
