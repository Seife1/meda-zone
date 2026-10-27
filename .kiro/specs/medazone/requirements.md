# Requirements Document

## Introduction

MedaZone is a mobile-first platform for players and organizers in Addis Ababa, Ethiopia, to discover nearby football (soccer) fields, check real-time slot availability, and book playing time — eliminating the friction of phone calls, physical visits, and uncertain availability. The platform refactors the FuelLink codebase, reusing spatial search, real-time availability, booking slot management, push notifications, and admin dashboard patterns. The system consists of three components: a Flutter mobile app for players, a FastAPI backend, and a React admin dashboard for field owners and super admins.

## Glossary

- **Player**: A registered mobile app user who discovers and books football fields.
- **Field_Owner**: A registered admin dashboard user who manages one or more football fields and their booking slots.
- **Super_Admin**: A privileged admin dashboard user who manages all fields, field owners, and platform settings.
- **Field**: A football (soccer) pitch registered in the system with a name, location, surface type, amenities, and pricing.
- **Slot**: A bookable time window on a specific field (e.g., 07:00–08:00 on a given date) with a defined capacity (typically 1 booking per slot for a full-field rental).
- **Booking**: A confirmed reservation by a Player for a specific Slot on a specific Field.
- **Availability**: The state of a Slot — one of: `available`, `booked`, or `closed`.
- **API_Server**: The FastAPI backend service that handles all business logic, data persistence, and real-time communication.
- **Mobile_App**: The Flutter application used by Players.
- **Admin_Dashboard**: The React web application used by Field_Owners and Super_Admins.
- **Notification_Service**: The component responsible for sending FCM push notifications to Players.
- **Location_Service**: The component that resolves a Player's GPS coordinates and performs spatial queries.
- **WebSocket_Server**: The component that pushes real-time slot availability updates to connected clients.
- **Cache**: The Redis-backed layer used for session data, slot availability state, and pub/sub messaging.
- **Offline_Cache**: The sqflite-backed local database on the Mobile_App used when network is unavailable.
- **Payment_Service**: The component that processes subscription payments via Chapa or ArifPay.
- **Subscription**: A contract between a Player and a Field_Owner that reserves a Recurring_Slot on a specific Field for a chosen period (1 month, 2 months, or 3 months). The subscription price is calculated as `hourly_rate × session_hours × total_sessions_in_period` and is paid upfront via Chapa or ArifPay to confirm the contract.
- **Subscription_Tier**: One of three available subscription durations — 1 month, 2 months, or 3 months — that determines the total number of sessions and the total price for a Subscription contract.
- **Recurring_Slot**: The agreed schedule that defines a Player's Subscription — specifically the day(s) of the week, session start time, and session duration (e.g., every Monday and Wednesday, 4:00–6:00 PM). The Recurring_Slot is negotiated between the Player and Field_Owner and recorded on the Subscription contract.
- **QR_Code**: A scannable code representing a confirmed Booking, used for on-site check-in verification.

---

## Requirements

### Requirement 1: User Registration and Authentication

**User Story:** As a Player, I want to register and log in with my phone number, so that I can manage my bookings across sessions.

#### Acceptance Criteria

1. WHEN a Player submits a valid Ethiopian phone number and OTP, THE Mobile_App SHALL authenticate the Player and store a JWT access token in flutter_secure_storage.
2. WHEN a Player's JWT access token expires, THE Mobile_App SHALL transparently refresh it using the refresh token without requiring re-login.
3. IF a Player submits an incorrect OTP three consecutive times, THEN THE API_Server SHALL lock the OTP verification for that phone number for 10 minutes.
4. WHEN a Player logs out, THE Mobile_App SHALL delete the stored JWT access token and refresh token from flutter_secure_storage.
5. THE API_Server SHALL issue JWT access tokens with a 24-hour expiry and refresh tokens with a 30-day expiry.
6. WHEN a Field_Owner or Super_Admin submits valid Firebase phone OTP credentials, THE Admin_Dashboard SHALL authenticate the user and restrict page access according to the user's role.
7. IF an unauthenticated request is made to a protected API endpoint, THEN THE API_Server SHALL return an HTTP 401 response.

---

### Requirement 2: Player Profile Management

**User Story:** As a Player, I want to manage my profile, so that the app can personalize my experience and pre-fill booking details.

#### Acceptance Criteria

1. THE Mobile_App SHALL allow a Player to set a display name, profile photo, and preferred playing positions.
2. WHEN a Player updates profile information, THE API_Server SHALL persist the changes and return the updated profile within 2 seconds.
3. THE Mobile_App SHALL display the Player's total confirmed bookings and upcoming bookings on the profile screen.

---

### Requirement 3: Field Discovery via Map

**User Story:** As a Player, I want to see football fields on a map near my location, so that I can quickly identify fields I can reach.

#### Acceptance Criteria

1. WHEN the Mobile_App obtains the Player's GPS coordinates, THE Location_Service SHALL query the API_Server for Fields within a 10 km radius using PostGIS `ST_DWithin`.
2. THE Mobile_App SHALL render discovered Fields as pins on an OpenStreetMap tile layer using flutter_map within 3 seconds of obtaining GPS coordinates.
3. WHEN a Player taps a Field pin on the map, THE Mobile_App SHALL display a summary card showing the Field name, distance, surface type, price per hour, and today's next available Slot.
4. IF the Player's device location permission is denied, THEN THE Mobile_App SHALL display a manual search bar allowing the Player to enter a neighborhood name or landmark in Addis Ababa.
5. WHERE a Field has paid for a sponsored placement, THE Mobile_App SHALL render the sponsored Field pin with a distinct visual indicator above non-sponsored pins.
6. THE Mobile_App SHALL cache the most recently fetched field list in the Offline_Cache so that Fields remain visible on the map when the network is unavailable.
7. WHEN the Player's network is unavailable, THE Mobile_App SHALL display a banner indicating offline mode and serve field data from the Offline_Cache.

---

### Requirement 4: Field Detail View

**User Story:** As a Player, I want to view full details of a field, so that I can decide whether to book it.

#### Acceptance Criteria

1. WHEN a Player navigates to a Field detail screen, THE Mobile_App SHALL display the Field name, address, surface type (grass / artificial / futsal), field size, amenities (changing rooms, lighting, parking, water), price per hour, photos, and operating hours.
2. WHEN a Player views a Field detail screen, THE Mobile_App SHALL display the availability calendar for the next 7 days with each Slot's status (`available`, `booked`, or `closed`).
3. WHEN a Player taps an `available` Slot, THE Mobile_App SHALL navigate to the booking confirmation screen pre-filled with that Slot's date, start time, and end time.
4. IF a Field has no `available` Slots in the next 7 days, THEN THE Mobile_App SHALL display a "No availability this week" message and offer a "Notify me when available" option.
5. THE Mobile_App SHALL display the average rating and the five most recent reviews for each Field.

---

### Requirement 5: Real-Time Slot Availability

**User Story:** As a Player, I want slot availability to update in real time, so that I don't book a slot that was just taken by someone else.

#### Acceptance Criteria

1. WHEN a Player views the Field detail screen, THE Mobile_App SHALL open a WebSocket connection to the WebSocket_Server and subscribe to slot availability updates for that Field.
2. WHEN a Slot's status changes, THE WebSocket_Server SHALL broadcast the updated Slot status to all connected clients subscribed to that Field within 500 ms of the state change.
3. WHEN the Mobile_App receives a slot status update via WebSocket, THE Mobile_App SHALL update the availability calendar display without requiring a page reload.
4. IF the WebSocket connection drops, THEN THE Mobile_App SHALL attempt reconnection with exponential backoff starting at 2 seconds, up to a maximum of 30 seconds between attempts.
5. WHILE a Player is on the booking confirmation screen for a specific Slot, THE Mobile_App SHALL hold a 5-minute soft reservation on that Slot so that other Players see it as `pending`.
6. IF the soft reservation expires without a confirmed payment, THEN THE API_Server SHALL release the Slot back to `available` status and notify the Player via an in-app message.

---

### Requirement 6: Booking Creation

**User Story:** As a Player with an active subscription, I want my recurring slot sessions to be recorded as confirmed bookings, so that I have a verified reservation for each session in my subscription period.

#### Acceptance Criteria

1. WHEN a Subscription contract is confirmed and payment is received, THE API_Server SHALL auto-generate individual Booking records for each session defined by the Subscription's Recurring_Slot schedule across the full Subscription period.
2. IF a Player without an active Subscription attempts to create a Booking, THEN THE API_Server SHALL return an HTTP 403 response with an error code of `SUBSCRIPTION_REQUIRED`, and THE Mobile_App SHALL display a prompt directing the Player to the subscription purchase screen.
3. WHEN a Subscription is activated, THE Mobile_App SHALL display all auto-generated Booking records for the Player, each showing the Field name, session date, start time, and end time derived from the Recurring_Slot.
4. WHEN a Booking record is created from a Subscription, THE API_Server SHALL mark the corresponding Slot as `booked` and return a unique booking reference for each session within 5 seconds of Subscription activation.
5. WHEN a Booking is confirmed, THE API_Server SHALL instruct the Notification_Service to send an FCM push notification to the Player containing the Field name, Slot date, start time, and booking reference.
6. WHEN a Booking is confirmed, THE Mobile_App SHALL generate and display a QR_Code encoding the booking reference for on-site check-in.
7. THE API_Server SHALL reject duplicate booking attempts for the same Slot using a database-level unique constraint on (field_id, slot_date, slot_start_time).
8. IF a Player holds an active Subscription, THEN THE API_Server SHALL reject any attempt by the Player to book Slots outside their designated Recurring_Slot schedule on that Field.

---

### Requirement 7: Booking Management

**User Story:** As a Player, I want to view and cancel my bookings, so that I can manage my schedule.

#### Acceptance Criteria

1. THE Mobile_App SHALL display a list of the Player's upcoming and past Bookings, sorted by Slot date descending.
2. WHEN a Player views a Booking, THE Mobile_App SHALL display the Field name, address, Slot date, start time, end time, booking reference, and QR_Code.
3. WHEN a Player cancels a Booking at least 2 hours before the Slot start time, THE API_Server SHALL mark the Booking as `cancelled` and release the Slot to `available` within 5 seconds.
4. IF a Player attempts to cancel a Booking less than 2 hours before the Slot start time, THEN THE API_Server SHALL reject the cancellation and return an error indicating the cancellation window has passed.
5. WHEN a Booking is cancelled, THE API_Server SHALL instruct the Notification_Service to send an FCM push notification to the Player confirming the cancellation.
6. THE API_Server SHALL record the cancellation reason (Player-initiated or Field_Owner-initiated) on the Booking record for audit purposes.

---

### Requirement 8: Push Notifications

**User Story:** As a Player, I want to receive push notifications about my bookings and field availability, so that I stay informed without checking the app constantly.

#### Acceptance Criteria

1. THE Notification_Service SHALL send an FCM push notification to the Player when a Booking is confirmed.
2. THE Notification_Service SHALL send an FCM push notification to the Player 1 hour before a booked Slot start time as a reminder.
3. THE Notification_Service SHALL send an FCM push notification to the Player when a Booking is cancelled by a Field_Owner.
4. WHEN a Player has enabled "Notify me when available" for a Field, THE Notification_Service SHALL send an FCM push notification to the Player within 1 minute of a Slot on that Field becoming `available`.
5. THE Mobile_App SHALL allow a Player to enable or disable each notification category independently in the notification settings screen.
6. WHEN a Player taps a push notification, THE Mobile_App SHALL navigate directly to the relevant Booking or Field detail screen.

---

### Requirement 9: Field Owner Dashboard — Field Management

**User Story:** As a Field_Owner, I want to manage my field's profile and settings from the admin dashboard, so that players see accurate information.

#### Acceptance Criteria

1. WHEN a Field_Owner logs in, THE Admin_Dashboard SHALL display only the Fields associated with that Field_Owner's account.
2. THE Admin_Dashboard SHALL allow a Field_Owner to create a Field by providing name, address, GPS coordinates (via Leaflet map picker), surface type, field size, amenities, photos, price per hour, and operating hours.
3. WHEN a Field_Owner submits valid field creation data, THE API_Server SHALL persist the Field record and return the created Field within 3 seconds.
4. THE Admin_Dashboard SHALL allow a Field_Owner to edit all Field attributes and save changes.
5. WHEN a Field_Owner sets a Field to `inactive`, THE API_Server SHALL mark all future `available` Slots on that Field as `closed` and send FCM push notifications to Players with upcoming Bookings on that Field.
6. IF a Field_Owner submits field creation data missing required fields (name, coordinates, price), THEN THE API_Server SHALL return an HTTP 422 response with a field-level error map.

---

### Requirement 10: Field Owner Dashboard — Slot Management

**User Story:** As a Field_Owner, I want to define and manage booking slots for my field, so that players can book the times I have available.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL allow a Field_Owner to generate recurring Slots for a Field by specifying a date range, operating hours, and slot duration (30, 60, or 90 minutes).
2. WHEN a Field_Owner generates Slots, THE API_Server SHALL create individual Slot records for each time window within the specified range, skipping dates where Slots already exist, and return the count of created Slots.
3. THE Admin_Dashboard SHALL allow a Field_Owner to manually close a specific Slot, changing its status from `available` to `closed`.
4. WHEN a Field_Owner closes a Slot that has an active Booking generated from a Subscription, THE API_Server SHALL cancel the associated Booking, mark the Slot as `closed`, send an FCM cancellation notification to the Player, and flag the affected Subscription session for rescheduling review by the Field_Owner.
5. THE Admin_Dashboard SHALL display a weekly calendar view of all Slots for the selected Field, color-coded by status (`available`, `booked`, `closed`).

---

### Requirement 11: Field Owner Dashboard — Bookings and Check-In

**User Story:** As a Field_Owner, I want to view incoming bookings and verify player check-ins on-site, so that I can manage field access.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL display today's Bookings for the selected Field in chronological order, showing Player name, Slot time, booking reference, and status.
2. WHEN a Field_Owner scans or manually enters a booking reference, THE Admin_Dashboard SHALL query the API_Server and return the Booking status and Player name within 2 seconds.
3. WHEN a valid QR_Code is verified, THE API_Server SHALL mark the Booking as `checked_in` and record the check-in timestamp.
4. IF a QR_Code is scanned for a Booking whose Slot start time is more than 30 minutes in the past or in the future, THEN THE API_Server SHALL return a warning indicating the check-in time mismatch while still allowing the Field_Owner to override and check in.

---

### Requirement 12: Super Admin Dashboard

**User Story:** As a Super_Admin, I want to manage all fields, field owners, and platform-wide settings, so that I can oversee the entire platform.

#### Acceptance Criteria

1. THE Admin_Dashboard SHALL restrict the Overview page, User Management page, and platform settings to users with the `SUPER_ADMIN` role.
2. THE Admin_Dashboard SHALL allow a Super_Admin to create, edit, and deactivate Field_Owner accounts.
3. THE Admin_Dashboard SHALL display platform-wide analytics including total active fields, total bookings in the last 30 days, total revenue in ETB in the last 30 days, and daily booking counts on a Recharts line chart.
4. THE Admin_Dashboard SHALL allow a Super_Admin to set a Field as `sponsored`, specifying a sponsorship start date and end date.
5. WHEN a Field's sponsorship end date passes, THE API_Server SHALL automatically remove the sponsored status from that Field via a scheduled APScheduler job running every 60 minutes.

---

### Requirement 13: Ratings and Reviews

**User Story:** As a Player, I want to rate and review a field after playing, so that other players can make informed booking decisions.

#### Acceptance Criteria

1. WHEN a Player's Booking Slot end time has passed and the Booking status is `checked_in`, THE Mobile_App SHALL prompt the Player to submit a rating (1–5 stars) and an optional text review.
2. WHEN a Player submits a rating, THE API_Server SHALL persist the review and recalculate the Field's average rating, returning the updated average within 2 seconds.
3. THE API_Server SHALL reject a review submission if the Player does not have a `checked_in` Booking for that Field's Slot.
4. THE Mobile_App SHALL display the average star rating and total review count on the Field detail screen and the map summary card.

---

### Requirement 14: Search and Filtering

**User Story:** As a Player, I want to filter fields by surface type, amenities, price range, and availability, so that I can find fields that match my needs.

#### Acceptance Criteria

1. THE Mobile_App SHALL provide a filter panel allowing a Player to filter Fields by surface type (grass, artificial, futsal), presence of amenities (lighting, changing rooms, parking), price range in ETB per hour, and availability on a specific date.
2. WHEN a Player applies filters, THE API_Server SHALL return only Fields matching all active filter criteria within 3 seconds.
3. WHEN a Player enters a text query in the search bar, THE API_Server SHALL return Fields whose name or neighborhood matches the query using a case-insensitive partial match.
4. THE Mobile_App SHALL persist the Player's most recently used filter settings in shared_preferences and restore them on the next app session.

---

### Requirement 15: Offline Mode

**User Story:** As a Player, I want the app to remain partially functional when I have no internet connection, so that I can view fields and bookings I've already loaded.

#### Acceptance Criteria

1. WHILE the Mobile_App has no network connectivity, THE Mobile_App SHALL serve the most recently cached Field list from the Offline_Cache.
2. WHILE the Mobile_App has no network connectivity, THE Mobile_App SHALL display the Player's upcoming Bookings from the Offline_Cache.
3. IF a Player attempts to create a Booking while offline, THEN THE Mobile_App SHALL display an error message stating that booking requires an active internet connection.
4. WHEN network connectivity is restored, THE Mobile_App SHALL automatically refresh the Field list and Booking list from the API_Server and update the Offline_Cache.

---

### Requirement 16: Background Jobs and System Maintenance

**User Story:** As the platform operator, I want automated background jobs to keep slot state and notifications accurate, so that the platform operates correctly without manual intervention.

#### Acceptance Criteria

1. THE API_Server SHALL run an APScheduler job every 2 minutes to expire soft reservations older than 5 minutes and release the associated Slots back to `available` status.
2. THE API_Server SHALL run an APScheduler job every 1 minute to identify Bookings whose Slot start time is 60 minutes away and dispatch reminder FCM push notifications via the Notification_Service.
3. THE API_Server SHALL run an APScheduler job every 60 minutes to expire Fields whose sponsorship end date has passed and remove their sponsored status.
4. WHEN an APScheduler job fails, THE API_Server SHALL log the error including job name, timestamp, and exception message to the application log.

---

### Requirement 17: Subscription Management

**User Story:** As a Player, I want to enter a subscription contract with a Field_Owner for a recurring playing slot, so that I have a guaranteed weekly session at my preferred field without negotiating separately each time.

#### Acceptance Criteria

1. WHEN a Field_Owner creates a Subscription contract proposal, THE Admin_Dashboard SHALL allow the Field_Owner to specify the target Player, the Field, the Recurring_Slot schedule (day(s) of week, session start time, and session duration in hours), and the Subscription_Tier (1 month, 2 months, or 3 months).
2. WHEN a Field_Owner submits a Subscription contract proposal, THE API_Server SHALL calculate the total price as `hourly_rate × session_hours × total_sessions_in_period`, where `total_sessions_in_period` is derived from the agreed days-per-week and the selected Subscription_Tier duration, and store the proposed contract with a `pending_payment` status.
3. WHEN a Subscription contract is proposed, THE API_Server SHALL instruct the Notification_Service to send an FCM push notification to the Player with the contract details including Field name, Recurring_Slot schedule, total sessions, subscription period, and total price in ETB.
4. WHEN a Player views a pending Subscription contract, THE Mobile_App SHALL display the Field name, Recurring_Slot schedule (days, time, duration), Subscription_Tier, total sessions, and calculated total price in ETB before presenting payment options.
5. WHEN a Player accepts a Subscription contract and initiates payment, THE Mobile_App SHALL process the subscription payment via Chapa or ArifPay as selectable options on the payment screen.
6. WHEN a subscription payment is completed successfully, THE API_Server SHALL set the Subscription status to `active`, record the `start_date` as the current date, calculate the `expiry_date` by adding the selected Subscription_Tier duration to the `start_date`, and trigger auto-generation of all Booking records per Requirement 6.1.
7. IF a subscription payment transaction fails, THEN THE API_Server SHALL return a descriptive error code to the Mobile_App and THE Mobile_App SHALL display an error message without activating the Subscription contract.
8. WHILE a Player's Subscription `expiry_date` is in the future, THE API_Server SHALL treat the Player's Subscription status as `active` and the Player's Recurring_Slot sessions SHALL remain reserved.
9. WHEN a Player's Subscription `expiry_date` is reached, THE API_Server SHALL set the Subscription status to `expired` and the Player SHALL no longer have reserved sessions on that Field until a new Subscription contract is established.
10. THE API_Server SHALL instruct the Notification_Service to send an FCM push notification to the Player 3 days before the Subscription `expiry_date`, informing the Player that the Subscription is about to expire.
11. THE API_Server SHALL instruct the Notification_Service to send an FCM push notification to the Player on the day the Subscription expires, informing the Player that the Subscription has expired and a new contract is required to continue.
12. WHEN a Player with an `expired` Subscription on a Field wishes to continue, THE Field_Owner SHALL initiate a new Subscription contract proposal per criteria 1–6 above.
13. THE Mobile_App SHALL provide a subscription management screen displaying the Player's current Subscription status, Field name, Recurring_Slot schedule, `start_date`, `expiry_date`, days remaining, total sessions, and a "Request Renewal" button that notifies the Field_Owner to initiate a new contract.
14. WHEN a Player or Field_Owner requests a change to the Recurring_Slot schedule of an active Subscription, THE API_Server SHALL require the Field_Owner to initiate the slot change and THE Mobile_App SHALL present the proposed new schedule to the Player for explicit approval before any Booking records are updated.
15. IF a Player has not approved a Recurring_Slot change within 48 hours, THEN THE API_Server SHALL expire the slot change proposal and retain the original Recurring_Slot schedule unchanged.
16. THE API_Server SHALL expose an endpoint that returns the count of currently active Subscriptions per Subscription_Tier and per Field, restricted to users with the `SUPER_ADMIN` role.
17. THE Admin_Dashboard SHALL display the count of active Subscriptions per Subscription_Tier on the platform analytics page, accessible to Super_Admins only.
18. THE API_Server SHALL store the full Subscription history per Player (all past and current Subscription records, including the Recurring_Slot schedule and total price for each) and expose it to the Player via an authenticated endpoint.

---

### Requirement 18: Brand Identity and Visual Design System

**User Story:** As a user, I want the app and dashboard to have a consistent, recognizable visual identity, so that the MedaZone brand is clear and the UI feels polished and trustworthy.

#### Acceptance Criteria

1. THE Mobile_App SHALL apply the official brand color palette throughout all screens: Primary Green (`#7DC832`) for interactive elements and highlights, Dark Green (`#1A5C2A`) for headers and dark surfaces, Dark Navy (`#1A1F3A`) for primary text, and White (`#FFFFFF`) for backgrounds and light surfaces.
2. WHEN the Mobile_App launches, THE Mobile_App SHALL display a splash screen with a Dark Green (`#1A5C2A`) background, the full white MedaZone logo centered, and the Amharic tagline ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ. displayed below the logo in white.
3. THE Mobile_App app icon SHALL use a rounded-square format with a white background and the icon-only logo (location pin with football) centered within the icon bounds.
4. THE Admin_Dashboard SHALL apply the same brand color palette as the Mobile_App, using Primary Green (`#7DC832`) for action buttons and active navigation states, and Dark Navy (`#1A1F3A`) for navigation chrome and body text.
5. WHEN a Player views any screen containing a primary action button (Book, Subscribe, Pay, or Confirm), THE Mobile_App SHALL render the button with Primary Green (`#7DC832`) as the background color and White (`#FFFFFF`) as the button label text color.
6. THE Mobile_App SHALL support a light mode using White (`#FFFFFF`) surfaces with Dark Navy (`#1A1F3A`) text, and a dark mode using Dark Green (`#1A5C2A`) surfaces with White (`#FFFFFF`) text, switching according to the device system setting.
7. THE Mobile_App and Admin_Dashboard SHALL apply consistent typography: bold italic weight for all headings and wordmark-style labels matching the MedaZone logotype style, and regular weight for all body text and supporting labels.
8. WHEN the Mobile_App renders Field pins on the map, THE Mobile_App SHALL display non-sponsored Field pins using the Primary Green (`#7DC832`) location-pin icon and sponsored Field pins using a gold/yellow variant to visually distinguish them from standard pins.
9. THE Mobile_App SHALL display the MedaZone wordmark in the app bar and header of every primary screen, rendering "Meda" in Dark Navy (`#1A1F3A`) bold and "Zone" in Primary Green (`#7DC832`) bold.
10. THE Mobile_App SHALL display the Amharic tagline ሚዳምን ያግኙ. ይዝዙ. ይጫወቱ. on the splash screen and on all onboarding screens.
