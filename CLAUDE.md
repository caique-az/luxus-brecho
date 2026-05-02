# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Luxus Brechó is a fullstack second-hand clothing e-commerce platform with three independent layers:

| Layer | Stack |
|-------|-------|
| **Backend** | Python 3.10+, Flask 3, MongoDB (PyMongo), JWT |
| **Frontend** | React 19, Vite 6, Zustand, Axios, React Router v7 |
| **Mobile** | Expo 54, React Native, TypeScript, NativeWind (Tailwind), Expo Router |

## Commands

### Backend (`backend/`)

```bash
# Install dependencies
pip install -r requirements.txt

# Run dev server (http://localhost:5000/api)
python run.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_users.py

# Run a single test function
pytest tests/test_users.py::test_create_user -v
```

### Frontend (`frontend/`)

```bash
npm install
npm run dev          # http://localhost:5173
npm test             # watch mode
npm run test:coverage
npm run lint
npm run build
```

### Mobile (`mobile/`)

```bash
npm install
npx expo start --clear     # or: npm start
npm run android
npm run ios
npm test
npm run test:coverage
```

### Root (network sync for mobile on physical device)

```bash
# Syncs local IP into mobile/network-config.json so Expo Go can reach the backend
npm run dev
```

## Architecture

### Backend

**App factory** — `backend/app/__init__.py` creates the Flask app, connects MongoDB, registers blueprints, and sets up CORS/rate limiting/compression. The MongoDB handle is stored at `app.db` (accessible as `current_app.db` inside requests).

**Request flow:** `routes/` → `controllers/` → `models/`

- `routes/` — Flask blueprints, define URL rules and call controller functions.
- `controllers/` — Business logic, receive `db` as argument, return Flask responses.
- `models/` — PyMongo collection helpers (`get_collection`, `ensure_*` schema functions).
- `services/` — Cross-cutting concerns: `jwt_service` (auth decorators), `cache_service`, `email_service`, `supabase_storage` (image uploads).

**Auth decorators** (from `app/services/jwt_service.py`):
- `@jwt_required` — validates Bearer token, sets `g.user_id`, `g.user_type`, `g.user_email`.
- `@admin_required` — same as above but also enforces `type == "Administrador"`.
- `@jwt_optional` — sets g fields if token present, continues without error if absent.
- `@owner_or_admin_required(user_id_param)` — allows resource owner or admin.

User types are the strings `"Cliente"` and `"Administrador"`.

**Configuration** — `backend/config.py` defines `DevelopmentConfig`, `ProductionConfig`, `TestingConfig`. Selected via `FLASK_ENV` env var. `JWT_SECRET_KEY` is required in production (raises `ValueError` if missing).

**Optional dependencies** — `flask-compress` and `flask-limiter` are imported with try/except; the app works without them but rate limiting and gzip compression are disabled.

### Frontend

Single-page app. Entry point is `src/main.jsx` → `src/App.jsx` (React Router v7 routes).

- `src/store/` — Zustand stores: `authStore.js`, `cartStore.js`, `favoritesStore.js`.
- `src/services/` — API modules. `api.js` is the central Axios instance; it automatically refreshes expired access tokens (queuing concurrent requests during refresh) and redirects to `/login` on failure.
- `src/pages/` — One directory per route, mirroring the URL structure.
- `src/schemas/` — Zod validation schemas shared with forms (react-hook-form + @hookform/resolvers).

`VITE_API_URL` env var sets the backend base URL (defaults to `/api`).

### Mobile

Uses **Expo Router** (file-based routing). `mobile/app/_layout.tsx` defines the Stack navigator; screen files under `mobile/app/` map directly to routes. Tabs live in `mobile/app/(tabs)/`.

- `mobile/store/` — Zustand stores: `authStore.ts`, `cartStore.ts`, `favoritesStore.ts`, `filterStore.ts`.
- `mobile/services/` — API calls.
- `EXPO_PUBLIC_API_URL` env var points to the backend (uses IP from `network-config.json` for physical devices).
- Styling via **NativeWind** (Tailwind class names on React Native components). Config in `tailwind.config.js` and `global.css`.

### Data model notes

- Products are unique items (no quantity tracking in cart — adding a product marks it as in-cart).
- MongoDB collections are initialized with `ensure_*` functions called at startup; indexes are created via `app/utils/db_indexes.py`.
- Images are stored in **Supabase Storage** (`supabase_storage` service), not in MongoDB.

## Environment Variables

### Backend (`.env`)

```ini
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=luxus_brecho_db
JWT_SECRET_KEY=your-secret-key
FLASK_DEBUG=True
FLASK_ENV=development
SUPABASE_URL=...
SUPABASE_KEY=...
SMTP_USER=...
SMTP_PASSWORD=...
FRONTEND_ORIGIN=http://localhost:5173   # comma-separated for multiple
```

### Mobile (`.env`)

```ini
EXPO_PUBLIC_API_URL=http://YOUR_IP:5000/api
```

Frontend uses `VITE_API_URL` (optional, defaults to `/api`).
