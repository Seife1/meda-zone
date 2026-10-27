# Implementation Plan: MedaZone

## Overview

Full-stack implementation of MedaZone: a FastAPI backend with PostgreSQL/PostGIS/Redis, a Flutter mobile app, and a React admin dashboard. Tasks follow a strict dependency order: infrastructure → backend models/services/routes → mobile → admin web → property-based tests.

## Tasks

- [x] 1. Infrastructure and project scaffolding
  - [x] 1.1 Update `infra/docker-compose.yml` and `infra/docker-compose.prod.yml` for MedaZone
    - Rename services from FuelLink to MedaZone; add `medazone_backend`, `medazone_postgres`, `medazone_redis`, `medazone_admin` containers
    - Add `postgis/postgis:16-3.4-alpine` with PostGIS extension enabled, `redis:7-alpine`, Nginx reverse proxy config routing `/api/v1` and `/ws` to backend
    - Write `infra/nginx/nginx.conf` with upstream definitions and WebSocket upgrade headers
    - _Requirements: 1.5, 3.1, 5.1_

  - [x] 1.2 Create backend project skeleton
    - Create `backend/app/main.py` (FastAPI app, lifespan, CORS from env, router registration stubs)
    - Create `backend/app/config.py` (pydantic-settings reading root `.env`: SECRET_KEY, DATABASE_URL, REDIS_URL, FIREBASE_CREDENTIALS_PATH, CHAPA_SECRET, ARIFPAY_SECRET, CHAPA_WEBHOOK_SECRET)
    - Create `backend/app/database.py` (SQLAlchemy 2.0 async engine + `AsyncSession` factory)
    - Create `backend/app/redis_client.py` (aioredis connection helpers, lifespan open/close)
    - Create `backend/requirements.txt` and `backend/Dockerfile`
    - _Requirements: 1.5, 16.4_

  - [x] 1.3 Initialize Alembic for migrations
    - Run `alembic init alembic` inside `backend/`, configure `alembic/env.py` to use async SQLAlchemy engine and import all ORM models
    - _Requirements: 6.7, 10.2_

- [x] 2. Database ORM models and migrations
  - [x] 2.1 Implement all SQLAlchemy ORM models
    - Create `backend/app/models/user.py` — `User` model with fields: `id`, `phone_number`, `display_name`, `profile_photo_url`, `preferred_positions` (ARRAY), `role`, `fcm_token`, `refresh_token_hash`, `is_active`, timestamps
    - Create `backend/app/models/field.py` — `Field` model with `location` as `Geometry("POINT", srid=4326, spatial_index=True)`, `amenities` (JSONB), `operating_hours` (JSONB), `photo_urls` (ARRAY), `is_sponsored`, `sponsorship_start`, `sponsorship_end`
    - Create `backend/app/models/slot.py` — `Slot` model with `UniqueConstraint("field_id", "slot_date", "start_time")`, `soft_reserved_until`, `soft_reserved_by` FK
    - Create `backend/app/models/booking.py` — `Booking` model with `UniqueConstraint("field_id", "slot_date", "slot_start_time")`, `reference` unique field, `cancellation_reason`, `checked_in_at`
    - Create `backend/app/models/subscription.py` — `Subscription` model with `recurring_days` (ARRAY), `tier`, `total_sessions`, `total_price`, `status`, `start_date`, `expiry_date`, `payment_tx_ref`
    - Create `backend/app/models/slot_change_proposal.py` — `SlotChangeProposal` model with `expires_at`, `status` (pending/approved/rejected/expired)
    - Create `backend/app/models/review.py` — `Review` model with `UniqueConstraint("player_id", "booking_id")`
    - Create `backend/app/models/notification_preference.py` — `NotificationPreference` model with per-category bool flags and `watched_field_ids` (ARRAY)
    - _Requirements: 1.5, 6.7, 7.6, 10.2, 13.2, 17.2_

  - [x] 2.2 Generate and apply initial Alembic migration
    - Run `alembic revision --autogenerate -m "initial_medazone_schema"` and verify generated SQL includes PostGIS geometry column, all unique constraints, and array columns
    - Apply with `alembic upgrade head` inside Docker
    - _Requirements: 6.7, 10.2_


- [x] 3. Backend Pydantic schemas
  - [x] 3.1 Create all request/response Pydantic v2 schemas
    - `backend/app/schemas/auth.py` — `OtpRequest`, `OtpVerifyRequest`, `TokenResponse`, `RefreshRequest`, `AdminLoginRequest`
    - `backend/app/schemas/field.py` — `FieldCreate`, `FieldUpdate`, `FieldResponse` (with `distance_km`, `next_available_slot`), `FieldSummary`, `SponsorshipPatch`, `FieldFilterParams`
    - `backend/app/schemas/slot.py` — `SlotResponse`, `SlotGenerateRequest`, `SlotStatusPatch`, `SlotUpdateMessage` (WebSocket message)
    - `backend/app/schemas/booking.py` — `BookingResponse`, `BookingCancelRequest`, `CheckInResponse`, `BookingVerifyResponse`
    - `backend/app/schemas/subscription.py` — `SubscriptionCreate`, `SubscriptionResponse`, `SlotChangeProposalCreate`, `SlotChangeProposalResponse`, `SubscriptionStatsResponse`
    - `backend/app/schemas/review.py` — `ReviewCreate`, `ReviewResponse`
    - `backend/app/schemas/notification.py` — `NotificationPreferenceResponse`, `NotificationPreferenceUpdate`
    - `backend/app/schemas/payment.py` — `ChapaInitRequest`, `ChapaCheckoutResponse`, `ArifPayInitRequest`, `ArifPaySessionResponse`
    - `backend/app/schemas/admin.py` — `UserCreateByAdmin`, `UserUpdateByAdmin`, `AnalyticsResponse`, `SubscriptionStatsItem`
    - _Requirements: 1.1, 2.2, 6.4, 9.6, 17.2_


- [x] 4. Auth service and routes
  - [x] 4.1 Implement `auth_service.py`
    - OTP generation (6-digit), store in Redis key `otp:{phone}` with 5-min TTL
    - OTP verification with lockout: increment failure counter; after 3 failures set Redis key `otp_lock:{phone}` with 10-min TTL; return `OTP_LOCKED` (HTTP 423)
    - `create_access_token(subject, issued_at)` — `exp = iat + 24h` using python-jose; `create_refresh_token` — `exp = iat + 30d`
    - Refresh token hashing (bcrypt), store hash in `user.refresh_token_hash`; revocation via Redis key `session:{jti}`
    - Admin Firebase token exchange: verify Firebase ID token via Firebase Admin SDK, look up or create user with role FIELD_OWNER or SUPER_ADMIN
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [x] 4.2 Implement `routers/auth.py`
    - `POST /auth/request-otp`, `POST /auth/verify-otp`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/admin/login`
    - JWT middleware dependency (`get_current_user`) that extracts and validates Bearer token; returns HTTP 401 `UNAUTHORIZED` for missing/invalid/expired tokens
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7_

  - [ ]* 4.3 Write property test for token expiry claims
    - **Property 1: Token expiry claims are always correct**
    - **Validates: Requirements 1.5**
    - Use Hypothesis `@given(st.datetimes(timezones=st.just(timezone.utc)))` to generate arbitrary `issued_at` values; assert `exp == iat + 24h` for access tokens and `exp == iat + 30d` for refresh tokens
    - Tag: `# Feature: medazone, Property 1: Token expiry claims are always correct`

  - [ ]* 4.4 Write property test for OTP lockout
    - **Property 2: Three failed OTPs lock the phone number**
    - **Validates: Requirements 1.3**
    - Use Hypothesis `@given(st.text())` for phone number; simulate exactly 3 consecutive failures; assert next attempt returns HTTP 423 `OTP_LOCKED`
    - Tag: `# Feature: medazone, Property 2: Three failed OTPs lock the phone number`

  - [ ]* 4.5 Write property test for unauthenticated access rejection
    - **Property 3: Unauthenticated access is always rejected**
    - **Validates: Requirements 1.7**
    - Use Hypothesis `@given(st.sampled_from(PROTECTED_ENDPOINTS))` to parametrize over all protected routes; assert HTTP 401 for requests with no/invalid/expired token
    - Tag: `# Feature: medazone, Property 3: Unauthenticated access is always rejected`


- [x] 5. Field service and routes
  - [x] 5.1 Implement `field_service.py`
    - `search(lat, lng, radius_km, surface_type, amenities, min_price, max_price, available_date, q)` — compose PostGIS `ST_DWithin` query on `GEOGRAPHY` column; apply all filter predicates; sort sponsored fields first, then by distance; return distance_km per result
    - `create_field`, `update_field`, `set_field_status` (marks future available slots closed, sends FCM when deactivated), `set_sponsorship`
    - _Requirements: 3.1, 3.2, 3.5, 9.2, 9.3, 9.4, 9.5, 9.6, 14.1, 14.2, 14.3_

  - [x] 5.2 Implement `routers/fields.py`
    - `GET /fields`, `GET /fields/{field_id}`, `POST /fields`, `PUT /fields/{field_id}`, `PATCH /fields/{field_id}/status`, `PATCH /fields/{field_id}/sponsor`
    - _Requirements: 3.1, 9.2, 9.3, 9.5, 12.4_

  - [ ]* 5.3 Write property test for spatial search radius
    - **Property 4: Spatial search returns only in-radius fields**
    - **Validates: Requirements 3.1**
    - Use Hypothesis with custom `lat_lng_strategy()` and `field_with_location_strategy()`; insert fields at varying distances; assert every returned field is ≤ 10 km and no in-radius field is omitted
    - Tag: `# Feature: medazone, Property 4: Spatial search returns only in-radius fields`

  - [ ]* 5.4 Write property test for sponsored field ordering
    - **Property 5: Sponsored fields precede non-sponsored in results**
    - **Validates: Requirements 3.5**
    - Use Hypothesis to generate mixed lists of sponsored/non-sponsored fields; assert all sponsored entries appear before all non-sponsored in the response array
    - Tag: `# Feature: medazone, Property 5: Sponsored fields precede non-sponsored in results`

  - [ ]* 5.5 Write property test for field filter correctness
    - **Property 17: Field filter returns only matching results**
    - **Validates: Requirements 14.2**
    - Use Hypothesis to generate arbitrary combinations of active filter criteria; assert every returned field satisfies all active filters simultaneously
    - Tag: `# Feature: medazone, Property 17: Field filter returns only matching results`

  - [ ]* 5.6 Write property test for case-insensitive text search
    - **Property 18: Text search is case-insensitive partial match**
    - **Validates: Requirements 14.3**
    - Use Hypothesis `@given(st.text())` for query string; assert any field whose name/neighborhood contains query (case-insensitively) appears in results
    - Tag: `# Feature: medazone, Property 18: Text search is case-insensitive partial match`


- [x] 6. Slot service and routes
  - [x] 6.1 Implement `slot_service.py`
    - `generate_slots(field_id, start_date, end_date, slot_duration_minutes, open_time, close_time)` — iterate date range, create time windows skipping existing slots; return `created_count` and `skipped_count`
    - `change_slot_status(slot_id, new_status)` — validate transition; publish `SlotUpdateMessage` to Redis channel `field:{field_id}:slots`; if closing a booked slot, trigger booking cancellation and flag subscription for rescheduling
    - `create_soft_reservation(slot_id, player_id)` — `SET soft_res:{slot_id} {player_id} EX 300`; update slot status to `pending`; publish WebSocket update
    - `release_soft_reservation(slot_id)` — delete Redis key, set slot to `available`, publish update
    - `get_slots_for_field(field_id)` — 7-day window from today inclusive
    - _Requirements: 5.5, 5.6, 10.1, 10.2, 10.3, 10.4_

  - [x] 6.2 Implement `routers/slots.py`
    - `GET /fields/{field_id}/slots`, `POST /fields/{field_id}/slots/generate`, `PATCH /slots/{slot_id}/status`, `POST /slots/{slot_id}/reserve`, `DELETE /slots/{slot_id}/reserve`
    - _Requirements: 4.2, 5.5, 10.1, 10.3_

  - [ ]* 6.3 Write property test for slot calendar window
    - **Property 6: Slot calendar covers exactly 7 days**
    - **Validates: Requirements 4.2**
    - Use Hypothesis `@given(st.dates())` for today's date; generate slots for a field; assert response contains exactly dates `[today, today+6]` with no slots outside that window
    - Tag: `# Feature: medazone, Property 6: Slot calendar covers exactly 7 days`

  - [ ]* 6.4 Write property test for soft reservation round-trip
    - **Property 7: Soft reservation round-trip — slot becomes available after expiry**
    - **Validates: Requirements 5.5, 5.6**
    - Use Hypothesis to generate slot and player IDs; create soft reservation; simulate TTL expiry (freeze time via `freezegun`); run expiry job; assert slot status is `available` and no reservation metadata remains
    - Tag: `# Feature: medazone, Property 7: Soft reservation round-trip — slot becomes available after expiry`

  - [ ]* 6.5 Write property test for slot generation idempotency
    - **Property 14: Slot generation is idempotent on existing slots**
    - **Validates: Requirements 10.2**
    - Use Hypothesis to generate date ranges with overlapping pre-existing slots; run generation twice; assert `created_count` is accurate and no duplicate slots exist
    - Tag: `# Feature: medazone, Property 14: Slot generation is idempotent on existing slots`


- [x] 7. Subscription service and routes
  - [x] 7.1 Implement `subscription_service.py` — price calculation and proposal
    - `calculate_total_sessions(tier, days_per_week)` — `round(days_per_week × 4.33 × months)`
    - `calculate_price(hourly_rate, session_hours, total_sessions)` — `(hourly_rate × session_hours × total_sessions).quantize(Decimal("0.01"))`
    - `propose_subscription(field_owner_id, player_id, field_id, recurring_days, session_start_time, session_duration_hours, tier)` — compute total_sessions and total_price, persist with status `pending_payment`, send FCM notification to player
    - _Requirements: 17.1, 17.2, 17.3_

  - [x] 7.2 Implement `subscription_service.py` — activation and lifecycle
    - `activate(sub_id)` — set status=`active`, start_date=today, expiry_date=today+tier_months; call `booking_service.generate_bookings_for_subscription`; publish WebSocket updates for all affected slots; send summary FCM notification
    - `get_subscription(sub_id)`, `list_player_subscriptions(player_id)`, `get_history(player_id)`
    - `request_renewal(sub_id, player_id)` — send FCM to field owner
    - `propose_slot_change(sub_id, field_owner_id, new_days, new_start_time, new_duration)` — create `SlotChangeProposal` with `expires_at = now() + 48h`
    - `respond_to_slot_change(proposal_id, player_id, approved: bool)` — if approved: update subscription recurring fields, regenerate future bookings; if rejected: set proposal status=`rejected`
    - _Requirements: 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.12, 17.13, 17.14, 17.15, 17.18_

  - [x] 7.3 Implement `routers/subscriptions.py`
    - `POST /subscriptions`, `GET /subscriptions/{sub_id}`, `GET /subscriptions/player/me`, `POST /subscriptions/{sub_id}/pay`, `GET /subscriptions/{sub_id}/history`, `POST /subscriptions/{sub_id}/request-renewal`, `POST /subscriptions/{sub_id}/slot-change`, `PATCH /subscriptions/{sub_id}/slot-change/{proposal_id}`, `GET /subscriptions/stats`
    - _Requirements: 17.1, 17.4, 17.13, 17.16_

  - [ ]* 7.4 Write property test for subscription price determinism
    - **Property 19: Subscription price calculation is deterministic**
    - **Validates: Requirements 17.2**
    - Use Hypothesis `@given(hourly_rate, session_hours, tier, days)` with sampled types; assert `calculate_price` returns exactly `hourly_rate × session_hours × total_sessions` for all inputs
    - Tag: `# Feature: medazone, Property 19: Subscription price calculation is deterministic`

  - [ ]* 7.5 Write property test for subscription activation date bounds
    - **Property 20: Subscription activation sets correct date bounds**
    - **Validates: Requirements 17.6**
    - Use Hypothesis `@given(st.dates(), st.sampled_from(["1_month","2_months","3_months"]))` as activation date and tier; assert `start_date == D` and `expiry_date == D + tier_months` and `status == active`
    - Tag: `# Feature: medazone, Property 20: Subscription activation sets correct date bounds`

  - [ ]* 7.6 Write property test for subscription history immutability
    - **Property 21: Subscription history is complete and immutable**
    - **Validates: Requirements 17.18**
    - Use Hypothesis to generate a sequence of subscription creations for a player; assert history endpoint returns all records with `total_price`, `recurring_days`, `tier` matching creation-time values
    - Tag: `# Feature: medazone, Property 21: Subscription history is complete and immutable`


- [x] 8. Booking service and routes
  - [x] 8.1 Implement `booking_service.py`
    - `generate_bookings_for_subscription(sub)` — iterate all session dates from recurring_days schedule across subscription period; create `Booking` records with auto-generated references (`MZ-{date}-{4_chars}`); mark each `Slot` as `booked`; return list of bookings
    - `get_booking(booking_id, player_id)`, `list_player_bookings(player_id)` sorted by slot_date descending
    - `cancel_booking(booking_id, player_id, reason)` — enforce 2-hour cancellation window; set status=`cancelled`, release slot to `available`, publish WebSocket update, send FCM cancellation notification; record `cancellation_reason`
    - `check_in(booking_id, field_owner_id)` — set status=`checked_in`, record `checked_in_at`; warn if slot start time is >30 min past or future
    - `verify_by_reference(reference, field_owner_id)` — look up booking by unique reference
    - Reject: player without active subscription → HTTP 403 `SUBSCRIPTION_REQUIRED`; duplicate (field_id, slot_date, slot_start_time) → HTTP 409 `DUPLICATE_BOOKING`; booking outside recurring schedule → HTTP 403 `OUT_OF_SCHEDULE`
    - _Requirements: 6.1, 6.2, 6.4, 6.5, 6.7, 6.8, 7.1, 7.3, 7.4, 7.6, 11.2, 11.3, 11.4_

  - [x] 8.2 Implement `routers/bookings.py`
    - `GET /bookings/me`, `GET /bookings/{booking_id}`, `DELETE /bookings/{booking_id}`, `POST /bookings/{booking_id}/checkin`, `GET /bookings/verify/{reference}`
    - _Requirements: 6.6, 7.1, 7.2, 11.1, 11.2, 11.3_

  - [ ]* 8.3 Write property test for subscription generates exactly N bookings
    - **Property 8: Subscription generates exactly N bookings**
    - **Validates: Requirements 6.1**
    - Use Hypothesis `@given(sub=subscription_strategy())` with varying tiers and recurring_days; assert `len(generated_bookings) == sub.total_sessions`
    - Tag: `# Feature: medazone, Property 8: Subscription generates exactly N bookings`

  - [ ]* 8.4 Write property test for booking without subscription
    - **Property 9: Booking without subscription returns 403**
    - **Validates: Requirements 6.2**
    - Use Hypothesis `@given(player_without_subscription_strategy())` to generate players without active subscriptions; assert every booking attempt returns HTTP 403 `SUBSCRIPTION_REQUIRED`
    - Tag: `# Feature: medazone, Property 9: Booking without subscription returns 403`

  - [ ]* 8.5 Write property test for duplicate booking rejection
    - **Property 10: No duplicate bookings for the same slot**
    - **Validates: Requirements 6.7**
    - Use Hypothesis `@given(slot_strategy())` to generate a slot; create first booking; assert second attempt is rejected with HTTP 409 `DUPLICATE_BOOKING` and first booking is unaffected
    - Tag: `# Feature: medazone, Property 10: No duplicate bookings for the same slot`

  - [ ]* 8.6 Write property test for out-of-schedule booking rejection
    - **Property 11: Subscription player cannot book outside their recurring schedule**
    - **Validates: Requirements 6.8**
    - Use Hypothesis `@given(subscription_strategy(), out_of_schedule_slot_strategy())` to generate booking attempts outside the recurring schedule; assert HTTP 403 `OUT_OF_SCHEDULE`
    - Tag: `# Feature: medazone, Property 11: Subscription player cannot book outside their recurring schedule`

  - [ ]* 8.7 Write property test for timely cancellation
    - **Property 12: Timely cancellation releases the slot**
    - **Validates: Requirements 7.3**
    - Use Hypothesis `@given(booking_strategy(), st.timedeltas(min_value=timedelta(hours=2, minutes=1)))` for cancellation time offset; assert booking status=`cancelled` and slot status=`available`
    - Tag: `# Feature: medazone, Property 12: Timely cancellation releases the slot`

  - [ ]* 8.8 Write property test for late cancellation rejection
    - **Property 13: Late cancellation is rejected**
    - **Validates: Requirements 7.4**
    - Use Hypothesis `@given(booking_strategy(), st.timedeltas(max_value=timedelta(hours=2)-timedelta(seconds=1)))` for cancellation offset; assert API rejects with `CANCELLATION_WINDOW_PASSED` and booking/slot statuses are unchanged
    - Tag: `# Feature: medazone, Property 13: Late cancellation is rejected`


- [x] 9. Review service and routes
  - [x] 9.1 Implement `review_service.py` and `routers/reviews.py`
    - `submit_review(player_id, field_id, booking_id, rating, review_text)` — verify player has a `checked_in` booking for the field's slot; reject otherwise with HTTP 403; persist review; recalculate `average_rating = sum(ratings) / count` and update `review_count` on `Field`
    - `list_reviews(field_id, page, page_size)` — return paginated reviews sorted by `created_at` desc
    - Routes: `POST /reviews`, `GET /fields/{field_id}/reviews`
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 9.2 Write property test for review eligibility enforcement
    - **Property 15: Review requires a checked-in booking**
    - **Validates: Requirements 13.3**
    - Use Hypothesis `@given(player_strategy(), field_strategy())` to generate players without checked-in bookings; assert review submission returns HTTP 403 and field average_rating/review_count are unchanged
    - Tag: `# Feature: medazone, Property 15: Review requires a checked-in booking`

  - [ ]* 9.3 Write property test for average rating correctness
    - **Property 16: Average rating is always mathematically correct**
    - **Validates: Requirements 13.2**
    - Use Hypothesis `@given(st.lists(st.integers(min_value=1, max_value=5), min_size=1, max_size=200))`; submit all ratings; assert `average_rating == round(sum/count, 2)` within tolerance
    - Tag: `# Feature: medazone, Property 16: Average rating is always mathematically correct`


- [x] 10. Notification service and preferences routes
  - [x] 10.1 Implement `notification_service.py`
    - `send_booking_confirmed(booking)` — build FCM payload with field name, slot date, start time, booking reference; dispatch via Firebase Admin SDK; respect player's `booking_confirmed` preference
    - `send_booking_reminder(booking)` — FCM reminder 60 min before slot; respect `booking_reminder` preference
    - `send_booking_cancelled(booking, reason)` — FCM on cancellation; respect `booking_cancelled` preference
    - `send_slot_available(field_id)` — FCM to all players watching the field (`watched_field_ids`); respect `slot_available` preference; dispatch within 1 min of slot becoming available
    - `send_subscription_expiring_soon(subscription)` — FCM 3 days before expiry
    - `send_subscription_expired(subscription)` — FCM on expiry day
    - `send_subscription_proposed(subscription)` — FCM to player with contract details
    - All dispatch calls: log errors and retry once; do NOT roll back the triggering transaction on FCM failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 17.3, 17.10, 17.11_

  - [x] 10.2 Implement `routers/notifications.py`
    - `GET /notifications/preferences`, `PUT /notifications/preferences`, `POST /notifications/watch/{field_id}`, `DELETE /notifications/watch/{field_id}`, `PUT /users/me/fcm-token`
    - _Requirements: 8.4, 8.5_


- [ ] 11. Payment integration
  - [ ] 11.1 Implement `chapa_service.py`
    - `initialize_payment(sub)` — call Chapa REST API v1 `POST /transaction/initialize` with `amount`, `tx_ref = MZ-{sub.id}-{timestamp}`, `callback_url`; return `ChapaCheckoutResponse`
    - `verify_webhook(payload, signature)` — HMAC-SHA256 verification using `CHAPA_WEBHOOK_SECRET`; return bool
    - `handle_success(tx_ref)` — find subscription by tx_ref, call `subscription_service.activate(sub_id)`
    - _Requirements: 17.5, 17.6, 17.7_

  - [x] 11.2 Implement `arifpay_service.py`
    - `initialize_payment(sub)` — call ArifPay API with equivalent fields; return `ArifPaySessionResponse`
    - `verify_webhook(payload, signature)` — ArifPay signature verification
    - `handle_success(session_id)` — activate subscription
    - _Requirements: 17.5, 17.6, 17.7_

  - [x] 11.3 Implement `routers/payments.py`
    - `POST /payments/chapa/initialize`, `POST /payments/chapa/webhook` (no auth, HMAC-verified), `POST /payments/arifpay/initialize`, `POST /payments/arifpay/webhook`
    - On payment failure: return HTTP 400 with `PAYMENT_FAILED` error code; do not activate subscription
    - _Requirements: 17.5, 17.7_


- [x] 12. WebSocket server
  - [x] 12.1 Implement `websockets/slots.py`
    - `field_slot_ws(websocket, field_id, redis)` — accept WebSocket; SUBSCRIBE to Redis channel `field:{field_id}:slots`; forward messages to client; UNSUBSCRIBE on `WebSocketDisconnect`
    - Register route `/ws/fields/{field_id}` in `main.py`
    - _Requirements: 5.1, 5.2, 5.3_

  - [x] 12.2 Wire slot status changes to Redis pub/sub in `slot_service.py`
    - Every call to `change_slot_status` and `create_soft_reservation` / `release_soft_reservation` publishes a `SlotUpdateMessage` JSON to `field:{field_id}:slots` within the same async operation
    - _Requirements: 5.2, 5.3_


- [x] 13. APScheduler background jobs
  - [x] 13.1 Implement all 5 APScheduler jobs in `tasks/scheduler.py`
    - **Job 1** `expire_soft_reservations` (every 2 min): query slots WHERE `status='pending' AND soft_reserved_until < NOW()`; bulk update to `available`; publish WebSocket updates; log count
    - **Job 2** `send_booking_reminders` (every 1 min): query confirmed bookings WHERE slot datetime ∈ `[now+55min, now+65min]`; fetch FCM token + preference; dispatch via `notification_service.send_booking_reminder`; log dispatched and errors
    - **Job 3** `expire_sponsorships` (every 60 min): query fields WHERE `is_sponsored=True AND sponsorship_end < today`; set `is_sponsored=False`, clear `sponsorship_start/end`; log count
    - **Job 4** `process_subscription_expiry` (every 60 min): find subscriptions with `expiry_date = today+3` → send "expiring soon" FCM; find subscriptions with `expiry_date = today AND status='active'` → set `status='expired'`, send "expired" FCM
    - **Job 5** `expire_slot_change_proposals` (every 30 min): find `SlotChangeProposal` WHERE `status='pending' AND expires_at < now()`; set `status='expired'`
    - Wrap all jobs in try/except; log `{job_id, timestamp, exception}` on failure; set `misfire_grace_time=30`
    - Register scheduler in FastAPI lifespan in `main.py`
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 17.9, 17.10, 17.11, 17.15, 12.5_


- [x] 14. Admin service and routes
  - [x] 14.1 Implement `analytics_service.py` and `routers/admin.py`
    - `get_platform_analytics()` — total active fields; total bookings last 30 days; total revenue ETB last 30 days; daily booking counts array for Recharts
    - `get_subscription_stats()` — active subscription count per tier and per field
    - `list_users(role_filter)`, `create_field_owner(data)`, `update_user(user_id, data)` (edit + deactivate)
    - Routes: `GET /admin/users`, `POST /admin/users`, `PATCH /admin/users/{user_id}`, `GET /admin/analytics`, `GET /admin/analytics/subscriptions` — all SUPER_ADMIN only
    - _Requirements: 12.1, 12.2, 12.3, 17.16, 17.17_

- [ ] 15. Backend checkpoint — ensure tests pass
  - Ensure all pytest unit tests pass, all property tests pass with `max_examples=100`, and `alembic upgrade head` succeeds cleanly. Ask the user if any questions arise.


- [ ] 16. Mobile app core setup
  - [ ] 16.1 Configure `mobile/pubspec.yaml` and core files
    - Add all dependencies: `flutter_riverpod`, `riverpod_annotation`, `go_router`, `dio`, `retrofit`, `json_serializable`, `sqflite`, `shared_preferences`, `flutter_secure_storage`, `flutter_map`, `latlong2`, `geolocator`, `permission_handler`, `firebase_messaging`, `flutter_local_notifications`, `web_socket_channel`, `google_fonts`, `cached_network_image`, `shimmer`, `lottie`, `qr_flutter`, `build_runner`, `riverpod_generator`, `retrofit_generator`, `flutter_lints`
    - Create `mobile/lib/core/constants.dart` — `API_BASE_URL`, `WS_BASE_URL`, brand colors (`kPrimaryGreen = Color(0xFF7DC832)`, `kDarkGreen = Color(0xFF1A5C2A)`, `kDarkNavy = Color(0xFF1A1F3A)`)
    - Create `mobile/lib/core/api_client.dart` — Dio singleton with `connectTimeout: 10s`, `receiveTimeout: 15s`; JWT Bearer interceptor; 401 → trigger token refresh → on refresh failure emit unauthenticated event
    - _Requirements: 1.1, 1.2, 15.3_

  - [ ] 16.2 Implement `core/theme.dart`, `core/router.dart`, and `main.dart`
    - `AppTheme.light` — White surfaces, Dark Navy text; `AppTheme.dark` — Dark Green surfaces, White text; primary color Primary Green in both
    - `GoRouter` with all routes defined: `/splash`, `/login`, `/otp`, `/register`, `/map`, `/fields/:id`, `/fields/:id/book/:slot_id`, `/bookings`, `/bookings/:id`, `/subscriptions/:id`, `/subscriptions/manage`, `/payment/:sub_id`, `/notifications/settings`, `/profile`
    - Redirect logic: unauthenticated → `/login`; authenticated on `/login` → `/map`
    - `main.dart` — `ProviderScope`, Firebase initialization, `MaterialApp.router`
    - _Requirements: 1.1, 18.1, 18.6, 18.7_

  - [ ] 16.3 Implement `core/local_db.dart`, `core/location_service.dart`, `core/fcm_handler.dart`
    - `local_db.dart` — sqflite: `fields_cache` and `bookings_cache` tables; `upsert`, `getAll`, `clearExpired` methods (TTL 10 min for fields)
    - `location_service.dart` — geolocator wrapper with permission request; returns `Position`; throws `LocationPermissionDeniedException` if denied
    - `fcm_handler.dart` — FCM token registration (`PUT /users/me/fcm-token`); foreground/background message handlers; notification tap routing via GoRouter; flutter_local_notifications for foreground display
    - _Requirements: 3.4, 8.5, 8.6, 15.1, 15.4_

  - [ ] 16.4 Create all shared data models with JSON serialization
    - `shared/models/user.dart`, `field.dart`, `slot.dart`, `booking.dart`, `subscription.dart`, `review.dart` — all annotated with `@JsonSerializable()`; run `dart run build_runner build`
    - Create `shared/widgets/brand_app_bar.dart` — renders "Meda" in Dark Navy bold + "Zone" in Primary Green bold
    - Create `shared/widgets/primary_button.dart` — Primary Green background, white label
    - Create `shared/widgets/offline_banner.dart` — shown when offline
    - _Requirements: 18.5, 18.7, 18.9_


- [ ] 17. Mobile auth feature
  - [ ] 17.1 Implement auth feature screens and provider
    - `features/auth/auth_provider.dart` — `AuthNotifier extends AsyncNotifier<AuthState>`; `requestOtp(phone)`, `verifyOtp(phone, otp)`, `logout()`; persist tokens in `flutter_secure_storage`; expose `authState` with statuses: loading/authenticated/unauthenticated
    - `features/auth/splash_screen.dart` — Dark Green background, white MedaZone logo centered, Amharic tagline ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ. in white; transition to `/map` or `/login` based on authState
    - `features/auth/login_screen.dart` — phone number input with +251 prefix; BrandAppBar; PrimaryButton "Send OTP"
    - `features/auth/otp_screen.dart` — 6-digit OTP entry; 10-min lockout error display; resend timer
    - `features/auth/register_screen.dart` — display name + profile photo; completes registration
    - _Requirements: 1.1, 1.3, 1.4, 18.2, 18.10_


- [ ] 18. Mobile map / field discovery feature
  - [ ] 18.1 Implement map feature
    - `features/map/map_provider.dart` — `locationProvider` (wraps `location_service.dart`); `nearbyFieldsProvider` (calls `GET /fields?lat=&lng=&radius_km=10`); cache result to `fields_cache` via `local_db.dart`; `networkStatusProvider` to detect offline
    - `features/map/map_screen.dart` — `flutter_map` with OpenStreetMap tile layer; render field pins using Primary Green location-pin icon for standard fields and gold variant for sponsored; sponsored pins rendered above non-sponsored; tapping pin opens `FieldSummaryCard` bottom sheet showing name, distance, surface type, price/hr, next available slot; filter FAB opens filter panel (surface type, amenities, price range, available date); search bar for manual text entry when location denied; offline banner when offline (serve from cache); BrandAppBar
    - Persist most recently used filter settings in `shared_preferences`; restore on next session
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 14.1, 14.4, 18.1, 18.8_


- [ ] 19. Mobile field detail + WebSocket slot calendar
  - [ ] 19.1 Implement field detail feature
    - `features/field/field_provider.dart` — `fieldDetailProvider(fieldId)` calls `GET /fields/{id}`; `slotCalendarProvider(fieldId)` calls `GET /fields/{field_id}/slots`; `slotWsProvider(fieldId)` manages `web_socket_channel` to `/ws/fields/{field_id}`; reconnect with exponential backoff (2s→4s→8s, cap 30s); on reconnect perform REST reconciliation; dispose on screen unmount
    - `features/field/field_detail_screen.dart` — photos carousel with `cached_network_image`; amenities chips; price/hr; operating hours; 7-day slot calendar color-coded by status (available/booked/closed); live WebSocket updates update calendar without reload; "No availability this week" message + "Notify me when available" button if no available slots; average rating + 5 most recent reviews; BrandAppBar
    - `features/field/field_summary_card.dart` — bottom sheet triggered from map pin tap
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 8.4_


- [ ] 20. Mobile booking flow
  - [ ] 20.1 Implement booking feature
    - `features/booking/booking_provider.dart` — `bookingProvider`: calls `POST /slots/{slot_id}/reserve` on screen enter; calls booking cancel endpoint; handles HTTP 403 `SUBSCRIPTION_REQUIRED` → emit error state; `bookingsListProvider`: `GET /bookings/me`, cache to `bookings_cache`
    - `features/booking/booking_confirm_screen.dart` — pre-filled field name, slot date, start/end time; 5-minute countdown timer showing soft reservation; PrimaryButton "Confirm & Pay" (navigates to `/payment/:sub_id`); on expiry show "Slot no longer reserved" and redirect back
    - `features/booking/bookings_list_screen.dart` — upcoming and past bookings sorted by slot_date desc; serve from `bookings_cache` when offline; refresh on network restore
    - `features/booking/booking_detail_screen.dart` — field name, address, slot date, start/end time, booking reference, QR code via `qr_flutter` encoding booking reference
    - _Requirements: 5.5, 5.6, 6.3, 6.5, 6.6, 7.1, 7.2, 7.3, 15.2, 15.3_


- [ ] 21. Mobile subscription flow
  - [ ] 21.1 Implement subscription feature
    - `features/subscription/subscription_provider.dart` — `pendingSubscriptionProvider`: `GET /subscriptions/{id}` for proposed contracts; `activeSubscriptionProvider`: `GET /subscriptions/player/me` filtered to active; `requestRenewalProvider`
    - `features/subscription/subscription_detail_screen.dart` — display field name, recurring days, session time/duration, tier, total sessions, total price in ETB; Chapa / ArifPay selection; PrimaryButton "Pay Now" → navigate to `/payment/:sub_id`
    - `features/subscription/subscription_management_screen.dart` — current subscription status, field name, recurring schedule, start/expiry dates, days remaining, total sessions; "Request Renewal" button; pending slot-change proposal display with approve/reject actions
    - _Requirements: 17.4, 17.5, 17.8, 17.9, 17.13, 17.14_


- [ ] 22. Mobile payment screen
  - [ ] 22.1 Implement payment feature
    - `features/payment/payment_provider.dart` — `POST /payments/chapa/initialize` or `/payments/arifpay/initialize` based on user selection; handle payment failure (HTTP 400) → emit error state; poll or listen for subscription activation after WebView closes
    - `features/payment/payment_screen.dart` — Chapa / ArifPay selector buttons; open checkout URL in WebView (`webview_flutter`); on WebView navigation to success/failure callback URL, close WebView and update payment state; show error message on failure without activating subscription
    - _Requirements: 17.5, 17.7_

- [ ] 23. Mobile notifications settings and profile screens
  - [ ] 23.1 Implement notifications and profile features
    - `features/notifications/notif_prefs_provider.dart` — `GET /notifications/preferences`; `PUT /notifications/preferences`; `POST /notifications/watch/{field_id}`
    - `features/notifications/notification_settings_screen.dart` — toggle per category (booking_confirmed, booking_reminder, booking_cancelled, slot_available, subscription_expiry) independently; BrandAppBar
    - `features/profile/profile_provider.dart` — `GET /users/me`; `PUT /users/me` for display name, photo, preferred positions; total confirmed bookings count; upcoming bookings count
    - `features/profile/profile_screen.dart` — avatar, display name, preferred positions chips; total/upcoming booking counts; edit profile form; logout button
    - _Requirements: 2.1, 2.2, 2.3, 8.5_


- [ ] 24. Mobile offline mode
  - [ ] 24.1 Wire offline mode throughout the app
    - Create `networkStatusProvider` (Riverpod `StreamProvider`) using `connectivity_plus`; broadcast offline state app-wide
    - `map_screen.dart` — show `OfflineBanner` when offline; serve from `fields_cache`
    - `bookings_list_screen.dart` — serve from `bookings_cache` when offline
    - `booking_confirm_screen.dart` — show error "Booking requires active internet connection" if offline and user taps confirm
    - On network restore: `networkStatusProvider` triggers background refresh of `fields_cache` and `bookings_cache` from API
    - _Requirements: 3.6, 3.7, 15.1, 15.2, 15.3, 15.4_

- [ ] 25. Mobile checkpoint — ensure all widget and unit tests pass
  - Run `flutter test` and `flutter analyze`. Fix any analysis warnings. Ask the user if questions arise.


- [ ] 26. Admin web core setup
  - [ ] 26.1 Configure admin-web project for MedaZone
    - Update `admin-web/package.json` to verify deps: `react 18`, `typescript 5`, `vite 5`, `react-router-dom v6`, `axios`, `react-query v3`, `react-leaflet`, `recharts`, `firebase`, `react-hot-toast`, `lucide-react`
    - Create `admin-web/src/firebase.ts` — Firebase JS SDK init for phone OTP (project config from env)
    - Create `admin-web/src/api/client.ts` — Axios instance with base URL from env; 401 interceptor (redirect to login); attach Bearer token from localStorage
    - Create domain API files: `api/auth.ts`, `api/fields.ts`, `api/slots.ts`, `api/bookings.ts`, `api/subscriptions.ts`, `api/admin.ts`
    - Create `admin-web/src/hooks/useAuth.ts` — Firebase auth state, extract role from custom claims; expose `{ user, role, loading }`
    - Create `admin-web/src/context/FieldContext.tsx` — active `field_id` shared across scoped pages
    - _Requirements: 1.6, 9.1, 18.4_

  - [ ] 26.2 Implement `App.tsx` with routing and role-based guards
    - `BrowserRouter` with all routes; `<ProtectedRoute>` wrapper checks `useAuth().role`; SUPER_ADMIN-only routes: `/`, `/analytics`, `/users`; FIELD_OWNER routes: `/fields`, `/fields/new`, `/fields/:id/slots`, etc.
    - `Sidebar.tsx` — Primary Green active nav state, Dark Navy chrome; brand wordmark; role-dependent nav items
    - _Requirements: 1.6, 9.1, 12.1, 18.4_


- [ ] 27. Admin web auth
  - [ ] 27.1 Implement `LoginPage.tsx`
    - Phone number input with Firebase `signInWithPhoneNumber`; OTP entry; on success call `POST /auth/admin/login` with Firebase ID token; store backend JWT in localStorage; redirect to `/` or `/fields` based on role
    - _Requirements: 1.6_

- [ ] 28. Admin web field management
  - [ ] 28.1 Implement `FieldsPage.tsx` and `FieldCreatePage.tsx`
    - `FieldsPage.tsx` — react-query `useQuery` to `GET /fields` scoped to current owner; table listing fields with name, status, price; Create Field button; Edit / deactivate actions
    - `FieldCreatePage.tsx` — form with name, address, neighborhood, surface type, field size, amenities checkboxes, photo URL inputs, price per hour, operating hours; `react-leaflet` `MapContainer` centered on Addis Ababa (8.9806°N, 38.7578°E) with draggable `Marker` writing `{lat, lng}` to form state; submit calls `POST /fields`; 422 validation errors displayed per field
    - Edit mode: `PUT /fields/{id}`; status toggle: `PATCH /fields/{id}/status`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_


- [ ] 29. Admin web slot management
  - [ ] 29.1 Implement `SlotsPage.tsx` with `SlotCalendar.tsx`
    - `SlotsPage.tsx` — reads active `field_id` from `FieldContext`; slot generation form (date range, operating hours, slot duration 30/60/90 min) calling `POST /fields/{id}/slots/generate`; displays `created_count` and `skipped_count` toast; embeds `SlotCalendar`
    - `SlotCalendar.tsx` — weekly grid view of all slots for selected field; color-coded by status: available (Primary Green), booked (Dark Navy), closed (gray); close slot action on available slot calls `PATCH /slots/{id}/status`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 30. Admin web bookings and check-in
  - [ ] 30.1 Implement `BookingsPage.tsx` and `CheckInPage.tsx`
    - `BookingsPage.tsx` — today's bookings for selected field in chronological order; columns: player name, slot time, booking reference, status; react-query with 30s refetch interval
    - `CheckInPage.tsx` — text input for booking reference OR future QR scanner integration stub; on submit call `GET /bookings/verify/{reference}`; display player name + booking status; confirm check-in button calls `POST /bookings/{id}/checkin`; display warning if time mismatch (>30 min) but allow override
    - _Requirements: 11.1, 11.2, 11.3, 11.4_


- [ ] 31. Admin web subscription management
  - [ ] 31.1 Implement `SubscriptionsPage.tsx` with `SubscriptionForm.tsx`
    - `SubscriptionForm.tsx` — player ID input, field selector, recurring day checkboxes (Mon–Sun), session start time, session duration, tier picker (1/2/3 months); real-time price preview computed from `calculate_price`; submit calls `POST /subscriptions`
    - `SubscriptionsPage.tsx` — list active subscriptions for selected field; propose new contract via `SubscriptionForm`; slot-change proposal form (new days/time/duration) calling `POST /subscriptions/{id}/slot-change`; display pending slot-change proposals
    - _Requirements: 17.1, 17.2, 17.14_

- [ ] 32. Admin web analytics
  - [ ] 32.1 Implement `OverviewPage.tsx` and `AnalyticsPage.tsx`
    - `OverviewPage.tsx` (SUPER_ADMIN) — `AnalyticsCard` components for: total active fields, total bookings last 30 days, total revenue ETB last 30 days; Recharts `LineChart` for daily booking counts (30-day rolling window) with `XAxis` date + `YAxis` count + `Tooltip`; Recharts `BarChart` for daily revenue; data from `GET /admin/analytics` (react-query, 5-min stale)
    - `AnalyticsPage.tsx` (SUPER_ADMIN) — Recharts `PieChart` for active subscriptions per tier; counts per field table; data from `GET /admin/analytics/subscriptions`
    - _Requirements: 12.3, 17.17_

- [ ] 33. Admin web user management
  - [ ] 33.1 Implement `UserManagementPage.tsx`
    - SUPER_ADMIN only; user table with role filter; Create Field Owner form (name, phone, role=FIELD_OWNER) calling `POST /admin/users`; Edit user modal with `PATCH /admin/users/{id}`; Deactivate toggle (sets `is_active=false`); set Field as `sponsored` with start/end date picker calling `PATCH /fields/{id}/sponsor`
    - _Requirements: 12.1, 12.2, 12.4_

- [ ] 34. Admin web checkpoint — ensure Vitest tests pass
  - Run `npm run lint` and `npm run build` in `admin-web/`. Fix any TypeScript or lint errors. Ask the user if questions arise.


- [ ] 35. Brand and visual design system
  - [ ] 35.1 Apply brand identity across mobile and admin web
    - Mobile splash screen: Dark Green (`#1A5C2A`) background, white MedaZone logo centered, Amharic tagline ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ. in white; configure app icon as rounded-square with white background and location-pin-with-football icon
    - Verify Primary Green (`#7DC832`) is applied to all PrimaryButton instances, active navigation states, and field map pins
    - Verify Dark Navy (`#1A1F3A`) is applied to all body text, headers, and Sidebar chrome in admin web
    - Verify typography: bold italic for all headings/wordmark labels, regular for body text across mobile and admin web
    - Verify light/dark mode switching follows device system setting
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10_


- [ ] 36. Backend integration tests
  - [ ]* 36.1 Write payment webhook integration tests
    - Test Chapa webhook: valid HMAC signature → subscription activates; invalid signature → HTTP 400 rejected
    - Test ArifPay webhook: same pattern
    - Use `httpx.AsyncClient` with FastAPI app; verify subscription status change in DB
    - _Requirements: 17.5, 17.6, 17.7_

  - [ ]* 36.2 Write WebSocket fanout integration test
    - Connect `web_socket_channel` test client to `/ws/fields/{id}`; publish slot update via Redis; assert client receives correct `SlotUpdateMessage` JSON within 500 ms
    - _Requirements: 5.2, 5.3_

  - [ ]* 36.3 Write APScheduler job integration tests
    - Soft reservation expiry: insert `pending` slot with `soft_reserved_until` in past; run `expire_soft_reservations()`; assert slot is `available` and Redis key deleted
    - Sponsorship expiry: insert sponsored field with past `sponsorship_end`; run `expire_sponsorships()`; assert `is_sponsored=False`
    - _Requirements: 16.1, 16.3_

- [ ] 37. Mobile integration tests
  - [ ]* 37.1 Write auth flow integration test
    - Mock API: OTP request → OTP verify → assert token stored in `flutter_secure_storage`
    - _Requirements: 1.1_

  - [ ]* 37.2 Write booking flow integration test
    - Mock API: field detail → slot tap → booking confirm screen (with soft reservation); assert QR code renders on booking detail screen
    - _Requirements: 5.5, 6.6_

- [ ] 38. Admin web integration tests
  - [ ]* 38.1 Write field creation integration test
    - Render `FieldCreatePage` with Leaflet map; simulate map click; assert `{lat, lng}` in form state; submit and assert correct payload sent to `POST /fields`
    - _Requirements: 9.2_

  - [ ]* 38.2 Write check-in flow integration test
    - Render `CheckInPage`; enter booking reference; assert API call to `GET /bookings/verify/{reference}`; confirm check-in; assert `POST /bookings/{id}/checkin` called
    - _Requirements: 11.2, 11.3_

- [ ] 39. Final checkpoint — full system validation
  - Ensure all backend pytest tests pass (`pytest --asyncio-mode=auto`), all Flutter tests pass (`flutter test`), and admin web builds cleanly (`npm run build`). Ask the user if questions arise.


## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP build
- Each task references specific requirements for traceability to requirements.md
- All 21 correctness properties from design.md are covered by property test sub-tasks (tasks 4.3–4.5, 5.3–5.6, 6.3–6.5, 7.4–7.6, 8.3–8.8, 9.2–9.3)
- Backend language: Python 3.11 (FastAPI); Mobile: Flutter/Dart; Admin Web: TypeScript/React
- Property tests use Hypothesis (`@given`, `@settings(max_examples=100)`) for backend and `glados` for Flutter
- Checkpoints at tasks 15, 25, 34, and 39 validate incremental progress before proceeding
- Infrastructure (task 1) must complete before any backend tasks; backend services (tasks 4–14) must complete before mobile/admin web tasks
- Code-generated files (`.g.dart`, `.freezed.dart`) should be committed after each `build_runner` run


## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.2"]
    },
    {
      "id": 1,
      "tasks": ["1.3", "2.1"]
    },
    {
      "id": 2,
      "tasks": ["2.2", "3.1"]
    },
    {
      "id": 3,
      "tasks": ["4.1", "5.1", "6.1", "7.1", "8.1", "9.1", "10.1", "11.1", "11.2"]
    },
    {
      "id": 4,
      "tasks": ["4.2", "5.2", "6.2", "7.2", "8.2", "10.2", "11.3", "12.1", "13.1", "14.1"]
    },
    {
      "id": 5,
      "tasks": ["4.3", "4.4", "4.5", "5.3", "5.4", "5.5", "5.6", "6.3", "6.4", "6.5", "7.3", "12.2"]
    },
    {
      "id": 6,
      "tasks": ["7.4", "7.5", "7.6", "8.3", "8.4", "8.5", "8.6", "8.7", "8.8", "9.2", "9.3"]
    },
    {
      "id": 7,
      "tasks": ["16.1", "26.1", "36.1", "36.2", "36.3"]
    },
    {
      "id": 8,
      "tasks": ["16.2", "16.3", "16.4", "26.2"]
    },
    {
      "id": 9,
      "tasks": ["17.1", "27.1", "28.1"]
    },
    {
      "id": 10,
      "tasks": ["18.1", "29.1", "30.1"]
    },
    {
      "id": 11,
      "tasks": ["19.1", "20.1", "21.1", "31.1"]
    },
    {
      "id": 12,
      "tasks": ["22.1", "23.1", "24.1", "32.1", "33.1"]
    },
    {
      "id": 13,
      "tasks": ["35.1", "37.1", "37.2", "38.1", "38.2"]
    }
  ]
}
```
