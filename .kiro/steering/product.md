# FuelLink — Product Overview

FuelLink is a mobile-first platform for drivers in Addis Ababa, Ethiopia, to discover nearby gas stations with real fuel availability and join digital queues — eliminating physical wait times.

## Core Problem
Drivers in Addis Ababa waste hours waiting in physical fuel queues with no visibility into availability or wait times.

## Solution
- Real-time fuel stock levels per station (Petrol / Diesel / EV)
- Digital queue system with time-window batching (30-min slots)
- Push notifications for queue position updates
- Live estimated wait times via WebSocket

## Users
- **Drivers** — find fuel, join queues, track position via mobile app
- **Station Admins** — manage fuel stock, call next driver, control queue via web dashboard
- **Super Admins** — manage all stations and admin users

## Key Features
- OpenStreetMap-based station discovery with GPS
- One-tap queue joining with ticket system
- FCM push notifications (called, near-turn, fuel finished, queue paused/resumed, station closed)
- WebSocket real-time queue updates + SQLite offline cache fallback
- Vehicle profiles (type, make, model, tank size)
- EV charging support (kWh stock, 1hr service time)
- Flash Move — alert drivers when a slot opens early

## V1 Monetization
Sponsored station pins, in-app ads while queuing, and station partnerships.
