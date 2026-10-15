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

## Auth / token strategy (implemented in Phase 2)

* Passwords hashed with Argon2 via `pwdlib`.
* Short-lived JWT access token (≈30 min) in an `HttpOnly`, `SameSite=Lax` cookie (`Secure` in production).
* Refresh tokens stored server-side (hashed) so logout and admin deactivation can revoke them.
* Tokens are never placed in `localStorage`. The OAuth2 bearer header is also accepted for Swagger/Postman testing.

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
