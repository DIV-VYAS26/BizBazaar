# BizBazaar integrated API contracts

Integration draft for backend version 0.1.0. The supplied frontend now consumes this contract
through a typed adapter. This verifies compatibility locally; it does not claim that both teammates
have approved the draft or that Member 3 has implemented calculations.

`contracts/openapi.yaml` is generated from FastAPI/Pydantic. `make contracts` also generates
`apps/web/src/lib/generated/backend.ts`, the actual wire types used by the live client.
`apps/web/src/lib/generated/types.ts` contains Member 1's presentation types, not generated API
contracts. The adapter in `lib/api/live.ts` deliberately maps between the two.

## Common rules

- `/api/v1`; snake_case; integer paise; INR; UTC storage; merchant-local reporting dates.
- Lists: `{items,total,limit,offset}`, maximum 100 per request.
- Errors: `{error:{code,message,details,request_id}}`.
- Cookie session required for private routes. Mutations also require permitted Origin and
  `X-CSRF-Token`; the browser must use `credentials: 'include'`.
- 401 invalid session; 403 origin/CSRF; 404 absent/cross-merchant object; 409 state/duplicate
  conflict; 413 resource limit; 422 validation; 429 local rate limit; 503 provider/busy failure.

## Browser integration

`/connect` exchanges a one-time CLI credential for browser cookies. It does not store credentials
in localStorage. Live mode is the default; mock mode must be explicitly selected and never acts
as an automatic fallback. The imported reference backend was not adopted.

The adapter handles campaign pagination, import issue/count mapping, reward IDs and amounts,
server decision enums, explicit dates, and the stable simulation event ID. It does not infer
customer contacts, payment methods, forecast confidence, replay detection, or merchant profit.
The backend returns reward cost/budget/counter snapshots in the stored event decision, so a
replay does not accidentally report the current state of a later campaign.

Analytics endpoints require `start_date`/`end_date` (inclusive merchant-local reporting dates),
except summary (`report_date`). The frontend defaults to the last 30 local calendar dates.
A 90-day lookback is passed separately from the reporting window. Forecast horizon is 1-14 days.
Each operation now has its own typed envelope/result in `app/schemas/analytics.py`.

Disabled analytics produces `status=UNAVAILABLE`, `result=null`, and a limitation. The browser
shows this explicitly. Missing recommendations do not block manual campaigns; missing summaries
do not hide persisted reward and campaign reports.

## CSV input

```csv
transaction_id,amount_paise,currency,timestamp,status
EXAMPLE_ID,100000,INR,2026-11-01T10:00:00+05:30,SUCCESS
```

The example is labelled demonstration input, not an actual merchant outcome. Optional
`merchant_id` must equal the session's merchant UUID. Customer VPA/note columns from Member 1's
old sample are not silently dropped or treated as consent; unsupported headers are rejected.
Identical reimports are duplicates; changed values conflict. Imported rows cannot trigger rewards.

## Coverage and settings

`POST /coverage` accepts `{items:[{date,status,provenance,includes_simulated}]}`.
Statuses are COMPLETE, PARTIAL, UNKNOWN. No future-day declaration is accepted; only past days
can be COMPLETE. Duplicate date/scope entries in a batch are rejected. `GET /coverage` filters
by date range and simulation scope. Missing records mean UNKNOWN, not a complete zero day.
Completeness describes the recorded dataset, not all sales channels or independently verified
bank activity. Merchant declarations are evidence claims with provenance, not source verification.
New recorded activity invalidates applicable COMPLETE declarations to PARTIAL and records an audit.

`GET/POST /settings/promotion` reads/writes type, rule_parameters, reward_cost_paise,
budget_cap_paise, and duration_days. Inputs reuse strict campaign rule validation. There are no
AI-generated or browser-supplied approval/counter/spend fields.

## Completed analytics integration

The supplied archive contained input models only. At the user's request, this workspace now
implements calculate_metrics, analyze_trends, forecast_collections, evaluate_forecast,
recommend_campaign and generate_daily_summary. The original source ZIP remains unchanged.
`ANALYTICS_MODE=real` enables these functions; Make and Compose use real mode. Foundation mode is
an explicit validation-only diagnostic mode, not the default local run configuration.

The five canonical transaction fields are merchant_id, transaction_id, amount_paise, timestamp,
and status. Config remains exactly timezone, start_date, end_date. Context carries historical
lookback, simulation inclusion, explicit coverage, server as-of clock, horizon and locale.
The batch boundary rejects mixed merchants and duplicate records. Canonical amounts are positive
strict integers up to the backend limit; control-character or oversized IDs are rejected.

```python
# bizbazaar_analytics/api.py
# operation: dashboard | analytics | forecast | evaluation | recommendation | summary
# dataset: transactions, config, context, merchant_settings
def run(operation: str, dataset: dict) -> dict:
    ...
```

The backend materializes a consistent authorized dataset, releases its database snapshot, invokes
pure calculations, and validates operation-specific output. It never passes database access or
campaign authority to analytics. No external AI service is configured or called by default.

Return contracts: dashboard -> MetricsResult; analytics -> TrendsResult; forecast -> ForecastResult;
evaluation -> ForecastEvaluationResult; recommendation -> RecommendationResult; summary -> SummaryResult.
All are exported in OpenAPI and generated TypeScript. ForecastResult includes the server-calculated
projected_total_paise; the frontend does not calculate an authoritative forecast total.

The analytics endpoint accepts `decline_threshold_percent=1..100` (default 10).

Additional endpoints:

- `GET /forecast/evaluation?start_date=...&end_date=...`: seven-calendar-day holdout with
  weekday-mean and flat-baseline MAE; insufficient data yields no invented accuracy score.
- `GET /summaries/daily?report_date=...&locale=en-IN|hi-IN`: deterministic grounded text. The
  reports screen supports both languages and selects the corresponding browser speech locale.

Forecasts require 28 complete training days and at least three complete observations per predicted
weekday. Complete zero days are valid; unknown days are not zeros. Current/future days do not train
predictions. Suggested campaigns copy saved merchant parameters and still require explicit approval
and activation. No cost/profit/uplift claim is inferred from recorded collections.

## Reviewed lifecycle decisions

Exhausted campaigns remain active until expiry/completion and return SKIPPED_BUDGET on qualifying
events. Replays preserve their original committed decision across refunds/completion/new campaigns.
Simulator full refunds change current transaction status without revoking rewards or accepted
historical counters. No real payments, messages or refunds are initiated.

## Account and commerce endpoints

OpenAPI and `apps/web/src/lib/generated/backend.ts` contain the complete typed bodies. New groups:

| Group | Main endpoints | Boundary |
|---|---|---|
| Merchant accounts | `/auth/register`, `/verify`, `/login`, `/forgot-password`, `/reset-password`, `/logout-all` | Exact Origin; shared attempt limits; single-use account tokens; cookie sessions |
| Customer contacts | `/customers`, `/customers/{id}`, `/portal-link`, `/consent-link`, `/marketing-revoke` | Authenticated merchant scope; contact changes revoke consent/links |
| Customer portal | `/portal`, `/portal/acknowledge`, `/public/consent` | Customer-specific bearer capability or purpose-specific consent token |
| Catalog | `/products`, `/products/{id}` | Integer paise; nullable cost/stock; optimistic edit version |
| Credit | `/credit/{customer_id}`, `/charges`, `/repayments`, `/credit/events/{id}/reverse`, `/credit/reminders/queue` | Append-only entries, idempotent posting, no overpayment; due notices queued explicitly |
| Sales | `/sales`, `/sales/{id}/void` | Atomic stock, snapshots, debt/collections, points and audit |
| Offers | `/offers/evaluate`, `/offers`, `/offers/{id}/approve|activate|complete` | Known-cost margin/budget/date/version checks; separate approval |
| Loyalty | `/loyalty/settings`, `/loyalty/{customer_id}` | Merchant-controlled policy and append-only point movements |
| Retention | `/retention/preview`, `/retention/campaigns`, `/approve`, `/queue` | Confirmed opt-in, inactivity, cooldown and separate delivery |
| Operations | `/outbox`, `/health/ready`, `/metrics` | Merchant-safe outbox metadata; protected global gauges |

All paths are under `/api/v1`; abbreviated suffixes attach to the relevant parent resource.
Commerce uses the same merchant cookie/CSRF rules as campaigns. Credit posting, sales, reversals
and voids require a request_key. Reusing it with a different body or resource returns 409.
`TransactionView.source` now includes MANUAL; `SessionView.is_demo` is a boolean. Collection
reports include manual paid sales and repayments but exclude unpaid credit sale charges.
