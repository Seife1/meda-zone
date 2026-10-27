# ⚽ MedaZone — Football Field Booking Platform for Addis Ababa

> **ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ.**
>
> MedaZone is a mobile-first platform that helps players in Addis Ababa discover nearby football fields, check real-time slot availability, and book playing time via subscription contracts — eliminating the friction of phone calls, physical visits, and uncertain availability.

---

## 🗂 Project Structure

```
medazone/
├── backend/          # FastAPI + PostgreSQL/PostGIS + Redis
├── admin-web/        # React + Vite + TypeScript admin dashboard
├── mobile/           # Flutter player mobile app
├── infra/            # Docker Compose + Nginx configs
├── logo/             # Brand assets (logo_light.png, logo_dark.png)
└── docs/             # Setup guides, API reference, technical docs
```

---

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker Desktop + Docker Compose v2
- Node.js 20+ (for admin web dev)
- Flutter 3.x (for mobile dev)

### 1. Configure environment
```bash
cp .env.example .env
# Required: SECRET_KEY, FIREBASE_CREDENTIALS_PATH
# Optional: CHAPA_SECRET, ARIFPAY_SECRET for payments
```

### 2. Start all services
```bash
cd infra
docker compose up -d

# Apply database migrations
docker exec -it medazone_backend alembic upgrade head
```

| Service      | URL                       |
|-------------|---------------------------|
| API Docs    | http://localhost:8001/docs |
| Admin Web   | http://localhost:5174      |
| PostgreSQL  | localhost:5432             |
| Redis       | localhost:6379             |

### 3. Create first Super Admin
Use the API directly to create the first admin user, or use the Firebase console to set a custom claim `role: SUPER_ADMIN` on a phone number account, then log in via the admin dashboard.

---

## 🏗 Architecture

```
Flutter Mobile ──► Nginx ──► FastAPI (uvicorn, port 8000)
React Admin  ────►              ├──► PostgreSQL 16 + PostGIS 3.4
                                ├──► Redis 7 (pub/sub + cache)
                                └──► Firebase Admin SDK (FCM)

WebSocket ──────────────────► FastAPI ──► Redis pub/sub ──► All WS clients
Chapa / ArifPay ─────────────► FastAPI (webhook) ──► Subscription activation
```

### Key Design Decisions
| Concern | Solution |
|---------|----------|
| Auth (Players) | Custom OTP via backend — no Firebase Auth for players |
| Auth (Admins) | Firebase Phone OTP → backend JWT exchange |
| Real-time slots | Redis pub/sub → WebSocket fanout per field |
| Spatial search | PostGIS `ST_DWithin` with GIST index |
| Offline resilience | sqflite cache (fields + bookings) with 10-min TTL |
| Push notifications | Firebase Admin SDK (FCM v1) |
| Subscription model | Field Owner proposes → Player pays (Chapa/ArifPay) → Auto-generate bookings |
| Background jobs | APScheduler — 5 jobs (soft reservation expiry, reminders, sponsorship expiry, subscription expiry, slot-change proposal expiry) |

---

## 📱 Mobile App (Flutter)

### Features
- 🗺 OpenStreetMap via `flutter_map` — no billing
- 📍 GPS-based field discovery (10 km radius) with manual search fallback
- ⚽ Field detail: photos, amenities, 7-day slot calendar
- 🔴🟢 Real-time slot status via WebSocket (live updates)
- 📋 Subscription management (view, pay, request renewal)
- 🎫 Booking list with QR code for on-site check-in
- 🔔 FCM push notifications (booking confirmed, reminder, slot available, subscription expiry)
- 💾 Offline mode — cached fields and bookings via sqflite

### Run mobile app
```bash
cp .env.example .env
# Set DEV_HOST=your LAN IP (or 10.0.2.2 for Android emulator)

cd mobile
flutter pub get
flutter run --dart-define=DEV_HOST=192.168.1.x
```

> ⚠️ **Firebase setup required** — see [`docs/firebase-setup.md`](docs/firebase-setup.md) before running.

### Production APK
```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://api.medazone.et/api/v1 \
  --dart-define=WS_BASE_URL=wss://api.medazone.et
```

---

## 🖥 Admin Dashboard (React)

### Features
- 🔐 Firebase Phone OTP login (Field Owners and Super Admins only)
- ⚽ Field management (create, edit, activate/deactivate)
- 🗓 Slot management — generate recurring slots, weekly calendar view
- 📋 Today's bookings list
- ✅ Check-in scanner — verify booking by reference
- 🔄 Subscription proposals with price preview
- 📊 Analytics (Recharts charts — bookings, revenue, subscription stats)
- 👥 User management — create/deactivate Field Owner accounts (Super Admin)

### Run admin web
```bash
cd admin-web
npm install
npm run dev    # http://localhost:5174
npm run build  # production build → dist/
```

---

## ⚙️ Backend API

**Base URL:** `http://localhost:8001/api/v1`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/request-otp` | — | Send OTP to player phone |
| POST | `/auth/verify-otp` | — | Verify OTP, get JWT tokens |
| POST | `/auth/refresh` | — | Refresh access token |
| POST | `/auth/admin/login` | — | Firebase token → admin JWT |
| GET | `/fields` | Optional | Spatial field search + filters |
| POST | `/fields` | Field Owner | Create a field |
| GET | `/fields/{id}/slots` | Optional | 7-day slot calendar |
| POST | `/fields/{id}/slots/generate` | Field Owner | Generate recurring slots |
| POST | `/subscriptions` | Field Owner | Propose subscription contract |
| GET | `/subscriptions/player/me` | Player | My subscriptions |
| POST | `/payments/chapa/initialize` | Player | Start Chapa payment |
| POST | `/payments/arifpay/initialize` | Player | Start ArifPay payment |
| GET | `/bookings/me` | Player | My bookings list |
| DELETE | `/bookings/{id}` | Player | Cancel booking |
| POST | `/bookings/{id}/checkin` | Field Owner | Check-in player |
| POST | `/reviews` | Player | Submit a review |
| GET | `/admin/analytics` | Super Admin | Platform analytics |

Full reference → [`docs/api.md`](docs/api.md)

### WebSocket
```
ws://localhost:8001/ws/fields/{field_id}
```
Broadcasts slot status changes in real-time:
```json
{
  "type": "slot_update",
  "slot_id": "...",
  "status": "booked",
  "slot_date": "2025-07-14",
  "start_time": "16:00",
  "end_time": "17:00"
}
```

---

## 🗄 Database Schema

```
users                  → id, phone_number, role (PLAYER/FIELD_OWNER/SUPER_ADMIN)
fields                 → id, location (PostGIS POINT), surface_type, price_per_hour, amenities (JSONB)
slots                  → id, field_id, slot_date, start_time, end_time, status
subscriptions          → id, player_id, field_id, recurring_days, tier, total_price
bookings               → id, subscription_id, slot_id, reference, status
slot_change_proposals  → id, subscription_id, new schedule, expires_at
reviews                → id, player_id, field_id, rating, review_text
notification_prefs     → id, player_id, per-category bool flags
```

Migrations managed by **Alembic**. Run `alembic upgrade head` to apply.

---

## 🔔 Push Notifications (FCM)

Uses **Firebase Admin SDK** (service account JSON). Configure `FIREBASE_CREDENTIALS_PATH` in `.env`.

| Trigger | Notification |
|---------|-------------|
| Booking confirmed | ✅ "Your booking at {field} is confirmed. Ref: MZ-..." |
| 1 hour reminder | ⏰ "Your game starts in 1 hour at {field}" |
| Booking cancelled | ❌ "Your booking at {field} has been cancelled" |
| Slot available | 🟢 "A slot just opened at {field}" |
| Subscription proposed | 📋 "New subscription proposal from {field}" |
| Subscription expiring | ⚠️ "Your subscription at {field} expires in 3 days" |
| Subscription expired | 🔴 "Your subscription at {field} has expired" |

---

## 💳 Payments

MedaZone supports two Ethiopian payment gateways for subscription payments:
- **Chapa** — `CHAPA_SECRET` + `CHAPA_WEBHOOK_SECRET` in `.env`
- **ArifPay** — `ARIFPAY_SECRET` in `.env`

Both follow an initialize-then-webhook pattern. Payment webhooks are received at:
- `POST /api/v1/payments/chapa/webhook`
- `POST /api/v1/payments/arifpay/webhook`

---

## 🌍 Production Deployment

```bash
cd infra
docker compose -f docker-compose.prod.yml up -d
```

### Required environment variables for production
```env
SECRET_KEY=<64-char-random>
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
FIREBASE_CREDENTIALS_PATH=/app/firebase-credentials.json
CHAPA_SECRET=<your-chapa-secret>
CHAPA_WEBHOOK_SECRET=<your-chapa-webhook-secret>
ARIFPAY_SECRET=<your-arifpay-secret>
API_BASE_URL=https://api.medazone.et
BACKEND_CORS_ORIGINS=https://admin.medazone.et
```

---

## 🔥 Firebase Setup

See **[`docs/firebase-setup.md`](docs/firebase-setup.md)** for the complete guide on:
- Creating a new Firebase project for MedaZone
- Replacing the FuelLink `google-services.json` with MedaZone's
- Enabling Phone Authentication
- Generating a service account for the backend
- Configuring the admin web Firebase SDK

---

## 📄 License
MIT — Built for Addis Ababa, Ethiopia 🇪🇹
