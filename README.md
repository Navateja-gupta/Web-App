# Kamareddy Wedding Services Marketplace

A local-first marketplace for discovering and booking wedding vendors (photographers, decorators, caterers, DJs and more) in Kamareddy, Telangana.

* Frontend: React + Vite + TypeScript + Tailwind → http://localhost:5173
* Backend: FastAPI + SQLAlchemy 2 + Alembic → http://localhost:8000 (docs: http://localhost:8000/docs)
* Database: PostgreSQL → localhost:5432

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design, API overview and business rules.

## What it does

| Role | Can |
|---|---|
| **Customer** | Browse and search vendors (service, location, price, declared availability, rating) · shortlist · send one enquiry to several vendors · compare quotations side by side · accept a quotation (creates a booking request) · track bookings · plan each function with a budget tracker · review vendors after completed bookings · report listings |
| **Vendor** | Create or claim a business profile (published after admin approval) · packages and prices · portfolio photos · availability · reply to enquiries with quotations · confirm, decline, cancel or complete bookings |
| **Administrator** | Overview statistics · add vendors on their behalf · approve / reject / suspend / verify · manage categories without code changes · manage users, enquiries, bookings, reviews and complaints · audit log |

## Day-to-day workflows

**Add a vendor you met in person** — Admin → Add vendor → fill the profile → add packages and photos → Approve.
It appears immediately in its category. To hand it over, open the vendor → *Generate claim code* → give the code to
the owner; they sign up as a vendor and enter it on *My business*.

**Add a new service (e.g. Mehendi Artists)** — Admin → Categories → New category. No code or database change needed.

**Customer journey** — Save vendors → *Request quotations* → vendors reply → *Compare quotations* → Accept →
vendor confirms the booking → after the event the vendor marks it completed → customer leaves a review.

## Notifications

Everyone gets in-app notifications (the bell icon in the header). Emails are optional.

| Event | Notified |
|---|---|
| New enquiry | Vendor (admins, if the vendor has no login yet) |
| Quotation received | Customer |
| Booking requested (quotation accepted or direct request) | Vendor (or admins) |
| Booking confirmed / not accepted | Customer |
| Booking cancelled | The other party (both, if an admin cancelled) |
| Vendor registered / resubmitted | Admins |
| Vendor approved / rejected / suspended | Vendor |
| Enquiry declined, booking completed, new complaint | In-app only |

**Turn on email (Gmail)**

1. On the Google account that will send emails, turn on 2-Step Verification.
2. Create an app password at https://myaccount.google.com/apppasswords.
3. In `backend\.env` set:
   ```
   EMAIL_ENABLED=true
   SMTP_USERNAME=your.address@gmail.com
   SMTP_PASSWORD=the 16-character app password
   ```
4. Restart the API, then use **Admin → Overview → Send test email to me**.

Emails are queued in the database and sent in the background (retried up to 5 times), so a slow or failing
mail server never breaks the website. Users can switch emails off under **Account → Notifications**.
Gmail allows roughly 500 emails a day; use a transactional email service when you outgrow that.

## Running every day

Two PowerShell windows:

```powershell
# Window 1, from Web-App\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Window 2, from Web-App\frontend
npm run dev
```

## Prerequisites (Windows)

| Tool | Version | Check (PowerShell) |
|---|---|---|
| Python | 3.10–3.13 | `py --list` |
| Node.js | 20 LTS or 22 LTS | `node --version` |
| npm | comes with Node | `npm --version` |
| Git | any recent | `git --version` |
| PostgreSQL | 15+ | `psql --version` |

If `psql` is not found, add `C:\Program Files\PostgreSQL\<version>\bin` to your PATH.

## 1. Create the databases (once)

Run from any directory and log in as the `postgres` superuser:

```powershell
psql -U postgres
```

Then, inside `psql` (choose your own strong password):

```sql
CREATE USER wedding_user WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE wedding_marketplace OWNER wedding_user;
CREATE DATABASE wedding_marketplace_test OWNER wedding_user;
\q
```

## 2. Backend setup

Run from `Web-App\backend`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend\.env` and replace `CHANGE_ME` with the password you chose.
If the password contains special characters (`@ : / %`), URL-encode them.

> If activation fails with "running scripts is disabled", run once:
> `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

Apply database migrations (from `Web-App\backend`, venv active):

```powershell
alembic upgrade head
```

Create an administrator (administrators cannot sign up through the website):

```powershell
python -m app.scripts.create_admin --email you@example.com --name "Your Name"
```

You will be prompted for the password (hidden input).

Start the API (from `Web-App\backend`, venv active):

```powershell
uvicorn app.main:app --reload --port 8000
```

Run the tests (from `Web-App\backend`, venv active):

```powershell
pytest
```

Tests only use `TEST_DATABASE_URL`. They refuse to run unless that database name ends in `_test`.

## 3. Frontend setup

Run from `Web-App\frontend`:

```powershell
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. The status card should show **Backend API: Running** and **Database: Connected**.

## Database migrations

Run from `Web-App\backend` with the venv active:

```powershell
alembic revision --autogenerate -m "describe change"   # create a migration after model changes
alembic upgrade head                                     # apply migrations
alembic downgrade -1                                     # roll back one migration
```

## Backups

```powershell
pg_dump -U wedding_user -d wedding_marketplace -F c -f backup.dump
pg_restore -U wedding_user -d wedding_marketplace --clean backup.dump
```
