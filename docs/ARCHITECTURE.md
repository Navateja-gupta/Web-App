# Architecture — Kamareddy Wedding Marketplace

## Overview

```
React (Vite, TS, Tailwind)  ──HTTP/JSON + HTTP-only cookie──►  FastAPI (/api/v1)
  public site                                                   routers  → thin, validation + auth
  customer dashboard                                            services → business rules, transactions
  vendor dashboard                                              models   → SQLAlchemy 2.x (sync)
  admin dashboard                                                   │
                                                                    ▼
                                                              PostgreSQL (Alembic migrations)
                                                              Local filesystem media (behind a storage interface)
```

* **Modular monolith**: one FastAPI app, split by domain (auth, categories, vendors, quotations, bookings, plans).
* **Sync SQLAlchemy 2.x + psycopg 3**: one consistent DB pattern; FastAPI runs sync endpoints in a threadpool.
* **All vendor/category data lives in the database.** The frontend never hardcodes vendors, categories, prices or counts.
* **Authorization is enforced on the backend.** Frontend role checks only hide UI.
* **Configuration comes from environment variables** (`backend/.env`, `frontend/.env`), so the app can move to containers/cloud later.

## Auth / token strategy

| Piece | Choice |
|---|---|
| Password hashing | Argon2id via `pwdlib`; hashes upgraded automatically on login if parameters change |
| Access token | JWT (HS256), 15 min, cookie `access_token` (`HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when `COOKIE_SECURE=true`) |
| Refresh token | Random 64-char token, 7 days, cookie `refresh_token` scoped to `Path=/api/v1/auth`; only its SHA-256 hash is stored (`refresh_tokens` table) |
| Rotation | Every `/auth/refresh` revokes the old refresh token and issues a new pair |
| Theft detection | Replaying an already-rotated refresh token (outside a 30 s grace window) revokes all of that user's sessions |
| Revocation | Logout revokes the refresh token. Password change and admin deactivation set `users.tokens_valid_after`, which instantly invalidates all existing access tokens |
| CSRF | `SameSite=Lax` cookies + JSON-only APIs; cross-site forms cannot send credentials |
| Tools | `POST /auth/token` (OAuth2 password form) returns a bearer token for Swagger/Postman |
| Rate limits | In-memory, per IP: login 10 / 5 min, register 10 / hour. Replace with a shared store if several server processes are ever used |
| Roles | `customer`, `vendor`, `admin`. Admins are created only via `python -m app.scripts.create_admin` |

Tokens are never placed in `localStorage`. The frontend only shows/hides UI by role; every rule is enforced by the backend.

## Auth API

| Method | Path | Who |
|---|---|---|
| POST | `/api/v1/auth/register` | anyone (role `customer` or `vendor`) |
| POST | `/api/v1/auth/login` | anyone |
| POST | `/api/v1/auth/token` | anyone (Swagger/Postman) |
| POST | `/api/v1/auth/refresh` | holder of refresh cookie |
| POST | `/api/v1/auth/logout` | anyone |
| GET/PATCH | `/api/v1/auth/me` | signed-in user |
| POST | `/api/v1/auth/change-password` | signed-in user |
| GET | `/api/v1/admin/users` | admin |
| PATCH | `/api/v1/admin/users/{id}` | admin (activate/deactivate) |

## Schema decisions

* Status/role columns are `VARCHAR` + `CHECK` constraints rather than native PostgreSQL enums, so adding a state later is a simple migration.
* Constraint names follow a fixed naming convention (`app/db/base.py`) so migrations are stable.
* `vendors` has a case-insensitive unique index on `(category_id, lower(business_name))`.
* Packages must have a price unless `pricing_type = quote_on_request`; `price_max` (range) must be ≥ `price`.
* Customer-owned history (bookings, enquiries, reviews) uses `ON DELETE RESTRICT`: users are deactivated, not deleted.

## Categories & vendor management (Phase 3)

### Who can do what

| Path prefix | Who | Purpose |
|---|---|---|
| `/api/v1/categories` | anyone | Active categories with live vendor counts; `/{slug}` for one |
| `/api/v1/vendors` | anyone | Approved + active vendors in active categories only. Filters: `category`, `q`, `location` (town or service area), `min_price`, `max_price`, `sort` (`newest`, `price_low`, `price_high`, `name`), `page`, `size`. `/{slug}`, `/{slug}/packages`, `/{slug}/portfolio`, `/{slug}/availability` |
| `/api/v1/me/vendor` | vendor | Create/read/update **own** profile; `/claim` to link an admin-created profile |
| `/api/v1/admin/categories` | admin | List all, create, edit, activate/deactivate, delete (only if unused) |
| `/api/v1/admin/vendors` | admin | List/search/filter, `status-counts`, create on behalf, edit, `approve`, `reject`, `suspend`, `verification`, `claim-code` |

Packages (`/packages`), photos (`/portfolio`) and availability (`/availability/{date}`) are mounted under both
`/me/vendor` and `/admin/vendors/{id}` from one router (`api/v1/vendor_resources.py`). Every lookup is scoped to
the resolved vendor, so a vendor guessing another vendor's package/photo id gets `404`.

### Approval workflow

```
            approve                 suspend
 pending ─────────────► approved ─────────────► suspended
    │                     ▲   ▲                     │
    │ reject (reason)     │   └──── approve ────────┘
    ▼                     │        (reinstate)
 rejected ── approve ─────┘
    │
    └── vendor edits profile ──► pending (resubmitted)
```

* New profiles (self-registered or admin-created) always start as `pending`.
* `is_active` is a separate on/off switch controlled by admins; approval is kept when deactivated.
* An approved vendor who changes category goes back to `pending`.
* Every transition is written to `audit_logs` with the reason.

### Admin-created profiles and ownership

Admins can create a profile with no linked account. To hand it over, the admin generates a one-time claim
code (10 characters, valid 7 days, only its SHA-256 hash stored) and gives it to the owner through a verified
channel. The owner signs up as a vendor and enters the code at `/vendor`. Claiming is rate-limited.

### Uploads

* Only JPEG, PNG and WebP, max 5 MB, max 30 photos per vendor (configurable).
* The file type is decided by decoding the image with Pillow, not by its name or Content-Type.
* Every image is re-encoded: EXIF/GPS metadata and anything hidden in the file are dropped.
* Stored under `backend/media/portfolio/{vendor_id}/{random}.{ext}`; the uploaded filename is never used.
* Served by FastAPI static files with `X-Content-Type-Options: nosniff`.
* Storage sits behind `MediaStorage` (`services/storage.py`); swap `LocalMediaStorage` for cloud storage later.

## Folder structure

```
Web-App/
├── backend/
│   ├── app/
│   │   ├── main.py              app factory, CORS, error handlers
│   │   ├── core/                config, security
│   │   ├── db/                  engine/session, declarative Base
│   │   ├── models/              SQLAlchemy ORM models
│   │   ├── schemas/             Pydantic v2 request/response models
│   │   ├── services/            business logic (approval, booking transitions, storage…)
│   │   ├── dependencies/        current user, role guards, pagination
│   │   └── api/v1/              routers
│   ├── alembic/                 migrations
│   ├── tests/                   pytest + HTTPX (separate *_test database)
│   ├── media/                   local uploads (git-ignored)
│   ├── alembic.ini, pytest.ini, requirements.txt, .env.example
├── frontend/
│   ├── src/
│   │   ├── lib/                 axios client, helpers
│   │   ├── components/          reusable UI (cards, tables, filters, status badges)
│   │   ├── pages/               public / customer / vendor / admin
│   │   └── App.tsx              routes
│   ├── package.json, vite.config.ts, .env.example
└── docs/
```

## Entity relationships

```
User (role: customer | vendor | admin)
 ├─1:0..1─ Vendor ──N:1── ServiceCategory
 │           ├─1:N─ VendorPackage
 │           ├─1:N─ VendorPortfolio
 │           ├─1:N─ VendorAvailability   (unique vendor_id + date)
 │           └─1:N─ Review
 ├─1:N─ CustomerShortlist ──N:1── Vendor   (unique customer_id + vendor_id)
 ├─1:N─ QuotationRequest ──N:1── Vendor
 │           └─1:N─ Quotation
 ├─1:N─ WeddingPlan
 │           └─1:N─ WeddingPlanItem ──N:0..1── Vendor / VendorPackage
 ├─1:N─ Booking ──N:1── Vendor; 0..1 → VendorPackage, Quotation, WeddingPlan
 │           └─1:0..1─ Review              (unique booking_id)
 └─1:N─ AuditLog (actor)
```

* `Vendor.user_id` is nullable: an admin can create a profile before the vendor has an account,
  and the profile can be claimed later through ownership verification.
* `approval_status` (pending/approved/rejected/suspended) is separate from `is_active`.
* Public listings = `approval_status = approved AND is_active AND category.is_active`.
* Money uses `NUMERIC(12,2)`. Categories are deactivated, never hard-deleted when referenced.

## Phases

1. **Foundation**: project skeleton, config, DB connectivity, Alembic setup, health checks, frontend scaffold.
2. **Data model + Auth**: all models + initial migration, Argon2, cookie JWT, roles, admin seed.
3. **Categories + Vendor management**: dynamic categories, vendor registration, admin "Add Vendor", approvals, packages, portfolio, availability, audit log, admin/vendor dashboards.
4. **Customer marketplace**: home, category pages, server-side search/filter/sort/pagination, vendor profiles, shortlist.
5. **Quotations, planning, bookings**: quotation requests/responses/comparison, wedding plans and budget, booking state machine, reviews, reports, final hardening.
