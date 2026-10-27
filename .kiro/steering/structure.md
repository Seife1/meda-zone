# FuelLink — Project Structure

## Repository Layout

```
fuellink/
├── backend/          # Python FastAPI API server
├── admin-web/        # React + TypeScript admin dashboard
├── mobile/           # Flutter driver mobile app
├── infra/            # Docker Compose + Nginx configs
├── docs/             # API reference and technical docs
├── scripts/          # Dev helper scripts (run-mobile-dev.ps1/.sh)
├── .env              # Root env — single source of truth for all services
└── .env.example      # Template for .env
```

---

## Backend (`backend/`)

Follows a layered architecture: **routers → services → models/schemas**.

```
backend/
├── app/
│   ├── main.py           # FastAPI app, lifespan, CORS, router registration
│   ├── config.py         # Pydantic settings (reads from .env)
│   ├── database.py       # SQLAlchemy async engine + session factory
│   ├── redis_client.py   # Redis connection init/close helpers
│   ├── routers/          # Route handlers (thin — delegate to services)
│   │   ├── auth.py
│   │   ├── stations.py
│   │   ├── queue.py
│   │   ├── admin.py
│   │   ├── user.py
│   │   └── payments.py
│   ├── services/         # Business logic
│   │   ├── auth_service.py
│   │   ├── station_service.py
│   │   ├── queue_service.py
│   │   ├── notification_service.py
│   │   ├── user_service.py
│   │   ├── chapa_service.py
│   │   └── arifpay_service.py
│   ├── models/           # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── station.py
│   │   └── queue.py
│   ├── schemas/          # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── station.py
│   │   ├── queue.py
│   │   └── user.py
│   ├── websockets/       # WebSocket handlers (Redis pub/sub fanout)
│   ├── tasks/            # APScheduler background jobs
│   └── middleware/       # Custom middleware
├── alembic/              # Migration env and script template
├── migrations/           # Alembic migration versions
├── requirements.txt
└── Dockerfile
```

**Conventions:**
- Routers are thin — call service functions, return schemas
- Service layer owns all business logic and DB queries
- ORM models live in `models/`, Pydantic schemas in `schemas/` — keep them separate
- All DB access is async (SQLAlchemy 2.0 async sessions)
- Spatial queries use GeoAlchemy2 + PostGIS functions (`ST_DWithin`, `ST_AsGeoJSON`)
- All routes prefixed `/api/v1`; WebSocket routes under `/ws/`

---

## Mobile App (`mobile/`)

Feature-first structure with a shared core layer. Uses Riverpod for all state.

```
mobile/lib/
├── main.dart                 # App entry point, Firebase init, ProviderScope
├── core/                     # App-wide singletons and config
│   ├── api_client.dart       # Dio singleton with auth interceptor
│   ├── constants.dart        # API base URLs, timeouts, etc.
│   ├── router.dart           # GoRouter definition (routerProvider)
│   ├── theme.dart            # AppTheme (light + dark)
│   ├── local_db.dart         # sqflite offline cache helpers
│   ├── location_service.dart # Geolocator wrapper
│   └── fcm_handler.dart      # FCM setup, local notifications, tap routing
├── features/                 # One folder per product feature
│   ├── auth/
│   │   ├── auth_provider.dart        # StateNotifierProvider<AuthNotifier, AuthState>
│   │   ├── login_screen.dart
│   │   ├── register_screen.dart
│   │   └── forgot_password_screen.dart
│   ├── map/                   # Station discovery map
│   ├── station/               # Station detail view
│   ├── queue/                 # Queue joining + live ticket
│   ├── notifications/         # Notification settings
│   ├── profile/               # Driver profile / vehicle settings
│   └── splash/                # Auth-gate splash screen
└── shared/
    ├── models/                # JSON-serializable data models (json_annotation)
    │   ├── user.dart
    │   ├── station.dart
    │   └── queue_entry.dart
    └── theme/                 # Shared theme extensions/widgets
```

**Conventions:**
- Each feature folder contains its screens and its own provider(s)
- Providers use `StateNotifierProvider` for mutable state; `Provider` for derived/config values
- `AuthState` is the single source of auth truth — all redirects read `authProvider`
- `GoRouter` redirect logic lives exclusively in `core/router.dart`
- Code-generated files (`.g.dart`, `.freezed.dart`) are committed; regenerate with `build_runner`
- API base URL and WS URL are injected at build time via `--dart-define`; read through `constants.dart`
- `core/api_client.dart` is a singleton — never create a new `Dio` instance in features

---

## Admin Web (`admin-web/`)

Page-per-route structure with shared context and hooks.

```
admin-web/src/
├── main.tsx              # React entry, root render
├── App.tsx               # BrowserRouter, route definitions, auth guard (ProtectedApp)
├── firebase.ts           # Firebase JS SDK init
├── index.css             # Global styles
├── api/                  # Axios API call functions (grouped by domain)
│   ├── client.ts         # Axios instance with auth interceptor
│   ├── auth.ts
│   ├── stations.ts
│   ├── queue.ts
│   └── ...
├── pages/                # One file per route
│   ├── LoginPage.tsx
│   ├── OverviewPage.tsx       # Super admin only
│   ├── StationPage.tsx
│   ├── QueuePage.tsx
│   ├── AnalyticsPage.tsx
│   ├── CreateStationPage.tsx
│   ├── UserManagementPage.tsx # Super admin only
│   └── TicketVerificationPage.tsx
├── components/           # Reusable UI components
│   ├── Sidebar.tsx
│   ├── AnalyticsCard.tsx
│   └── Icons.tsx
├── context/
│   └── StationContext.tsx # Active station selection, shared across pages
└── hooks/
    └── useAuth.ts         # Auth state + role helpers
```

**Conventions:**
- Role-based route rendering: check `role === 'SUPER_ADMIN'` in `App.tsx`; pages themselves should not re-check role for visibility
- `StationContext` provides the currently selected station ID — use it in all station-scoped queries
- API calls are grouped in `api/` by domain; pages/components import from there, not from inline fetch calls
- WebSocket connections are opened per-page where live data is needed (QueuePage)
- `react-query` for server state; local UI state in `useState`

---

## Infrastructure (`infra/`)

```
infra/
├── docker-compose.yml        # Development stack
├── docker-compose.prod.yml   # Production stack
├── nginx/                    # Nginx config files
└── README.md
```

- `docker compose down -v` **destroys the `postgres_data` volume** — avoid in dev
- The backend container mounts `../backend` as a volume for hot-reload in dev (`--reload`)
- CORS origins are set via env var in docker-compose, not hardcoded in the app
