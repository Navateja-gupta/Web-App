# Kamareddy Wedding Services Marketplace

A local-first marketplace for discovering and booking wedding vendors (photographers, decorators, caterers, DJs and more) in Kamareddy, Telangana.

* Frontend: React + Vite + TypeScript + Tailwind → http://localhost:5173
* Backend: FastAPI + SQLAlchemy 2 + Alembic → http://localhost:8000 (docs: http://localhost:8000/docs)
* Database: PostgreSQL → localhost:5432

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design and phase plan.

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
