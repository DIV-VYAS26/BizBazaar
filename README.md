# BizBazaar

Independent merchant software. This workspace combines Member 2's PostgreSQL backend, Member 1's
Next.js frontend, and the completed merchant analytics package.

For the folder map and daily Git workflow, see the [GitHub upload guide](docs/github-upload-guide.md)
and [one-file-per-day checklist](docs/daily-upload-checklist.md).

The local app supports verified merchant accounts, customers and consent, product costs and stock,
paid/credit sales, credit acknowledgements and repayments, reviewed offers, loyalty, retention
drafts and an encrypted mail outbox. It also supports CSV imports, simulated reward campaigns,
calculated analytics and English/Hindi summaries. Forecasts require explicitly complete history.
BizBazaar records payments received separately; it does not process payments.

## Local start

Requires Python 3.12, Node.js, and running Docker with Compose.

```bash
make install
.venv/bin/python scripts/create_local_env.py
make db
make migrate
npm ci --ignore-scripts
make run
```

In another terminal run `npm run dev`, then open <http://localhost:3000/account>.
Register, use the development-only email preview to verify, and sign in. Messages remain local;
no SMTP credentials are needed. The private `.env` contains encryption keys and is ignored by Git.

For a separate local demo, open <http://localhost:3000/connect> after generating a credential:

```bash
DEMO_ENABLED=true .venv/bin/python -m app.cli create-demo-session --merchant-name 'Demo Shop'
```

Paste it only into the local connection page. Credentials are exchanged for HttpOnly cookies;
this CLI flow provisions only demo sessions. Account signup is separate.

Alternatively: `docker-compose up -d --build web`. API docs: <http://localhost:8000/docs>.

## Verification

```bash
make lint
make check-contracts
make test
npm run typecheck
npm test
npm run build
npx playwright install chromium
make test-live
```

Tests require the disposable `bizbazaar_test` database; they must never target merchant data.
The live browser tests start isolated servers on ports 13001/18001 and use unique test merchants.
`PLAYWRIGHT_PRODUCTION=true make test-live` exercises an optimized local frontend and strict CSP.
The older mock walkthrough is separate and is not evidence of backend integration.

Read [setup](docs/setup.md), [contracts](docs/api-contracts.md),
[Developer 2 learning guide](docs/developer-2-learning.md), and
[current status](docs/implementation-status.md).

Public deployment is paused. [Operations and future launch setup](docs/operations.md) are prepared
for later review; no hosting account, domain or external email delivery has been activated.
