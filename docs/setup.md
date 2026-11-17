# BizBazaar backend setup

This is the integrated local BizBazaar application. Merchant registration, verification,
password recovery and bookkeeping use PostgreSQL. Mail defaults to encrypted local preview;
no external payment, email or AI credential is needed. Public deployment is paused.

## Requirements

- Python 3.12 and a running Docker engine.
- Docker Compose. This machine has `docker-compose`; elsewhere use `docker compose`.
- Ports 8000, 55432 and 55433 available on localhost.

Run from the repository root:

```bash
make install
.venv/bin/python scripts/create_local_env.py
make db
make migrate
make test
make run
```

If Compose is available as a subcommand, use `make db COMPOSE='docker compose'`.
If Colima is your engine and is stopped, run `colima start` first.
Development database data persists in a Docker volume. The test database is disposable.
Never point tests at a database you want to keep: tests truncate application tables and require
a database name ending in `_test`.

API documentation: <http://localhost:8000/docs>. Health: <http://localhost:8000/api/v1/health>.

Alternatively run the backend in a container:

```bash
docker-compose up -d --build web
```

This applies migrations before starting the API and binds it to localhost only.

## Start a local demo merchant session

In a separate terminal:

```bash
DEMO_ENABLED=true .venv/bin/python -m app.cli create-demo-session --merchant-name 'Demo Shop'
```

The command prints a one-time private credential. Exchange it through
`POST /api/v1/demo/session` with JSON `{"token":"<credential>"}` and the header
`Origin: http://localhost:3000`. A successful exchange consumes the credential and sets:

- `bizbazaar_session`: HttpOnly session cookie; never accessible to frontend JavaScript.
- `bizbazaar_csrf`: readable CSRF proof. Send its value as `X-CSRF-Token` on mutations.

Use the intended browser origin, `credentials: 'include'`, and these cookies for subsequent
requests. `GET /api/v1/session` returns identity and expiry, never credentials.
`POST /api/v1/session/logout` revokes the session and clears cookies.
The CLI is local provisioning, not a public signup or a merchant selector.

If running entirely in Docker, run the same CLI with:

```bash
docker-compose exec api python -m app.cli create-demo-session --merchant-name 'Demo Shop'
```

## Configuration

Run `scripts/create_local_env.py` once to create private local keys in `.env`; it preserves existing
values and prints no secrets. `.env.example` documents defaults. Never commit a filled environment
file or encryption keys. If an existing key is lost, its encrypted mail cannot be recovered.

- `DEMO_ENABLED=true` enables demo exchange and simulation endpoints.
- `ANALYTICS_MODE=real` enables the completed analytics engine (the default in Make/Compose).
- `ANALYTICS_MODE=foundation` deliberately validates inputs without executing calculations.
- `ANALYTICS_MODE=unavailable` disables provider integration.
- `ALLOWED_ORIGINS` is an explicit JSON array of frontend origins.
- `COOKIE_SECURE=true` is required when using HTTPS.
- `MAIL_DELIVERY_MODE=outbox` never sends mail; the development inbox requires local/test mode,
  enabled demos, and the exact browser origin. It is unavailable in production.
- `APP_ENV=production` requires secure cookies, disabled demos, HTTPS, private mail/metrics keys,
  SMTP with STARTTLS, and a private database URL. Readiness rejects an owner/superuser runtime role.

## Verification

```bash
make lint
make check-contracts
make test
.venv/bin/alembic -c apps/api/alembic.ini check
```

The final command checks the development schema after `make migrate`.
CI provisions separate PostgreSQL, runs tests, and checks schema/contract drift.
Plain `pytest` without `TEST_DATABASE_URL` runs non-database tests and explicitly skips
database tests; use `make test` for complete verification.

Stop containers without removing development data:

```bash
docker-compose --profile test stop
```

## Integrated frontend

Member 1's source is now included. Install dependencies with `npm ci --ignore-scripts`, run
`npm run dev`, and open <http://localhost:3000/account>. Register and confirm the verification
link through the local email preview, then sign in. `/connect` remains available for CLI demo
credentials. No credential belongs in a NEXT_PUBLIC environment variable.

Live mode is the default. Dashboard/trends/summaries use calculated records; forecasts require
explicit complete-day coverage. Transaction/campaign/reward features remain independent. Select mock mode only
when intentionally reviewing Member 1's fixture-driven reference screens.

Run the authenticated real-browser journey after `make test`:

```bash
npx playwright install chromium
make test-live
```

The browser test launches isolated servers on ports 13001/18001, uses the test database and
creates a unique demo merchant. Run it after Python database tests, not concurrently, because
Python tests truncate test tables. If browsers were installed in a custom directory, set
`PLAYWRIGHT_BROWSERS_PATH` to the same directory for both install and test.
