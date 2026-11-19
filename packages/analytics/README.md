# BizBazaar analytics

Installable pure-Python calculations and summaries for the BizBazaar backend. The supplied Member 3
archive contained validation models only; the calculation modules were subsequently implemented
in this shared workspace at the user's request. The original ZIP is unchanged.

## Implemented

- Canonical input validation, single-merchant batches, duplicate rejection and backend money bounds.
- Exact integer-paise totals, half-up averages, status counts and merchant-local grouping.
- Explicit complete/missing-day handling, slow weekdays and consecutive-window average-value decline.
- Weekday-mean forecasts with a 28-complete-day minimum and three observations per predicted weekday.
- Seven-day temporal holdout evaluation versus a flat daily-mean baseline, without training leakage.
- Merchant-configured Nth-payment/threshold campaign suggestions; no action authority.
- Grounded English/Hindi text summaries and deterministic offline fallback.
- Optional injected provider chooses a vetted summary style only; its free text/numbers are never used.

No database, authentication, payment-provider or external-model connection exists in this package.
The default runtime needs no AI credential. Monetary calculations use Python integers; Decimal
is used for measured statistical percentages/errors. No trained model or real-world accuracy is claimed.

## Use

```python
from bizbazaar_analytics.api import run

result = run('dashboard', {
    'transactions': [],
    'config': {'timezone': 'Asia/Kolkata', 'start_date': '2026-11-01', 'end_date': '2026-11-01'},
    'context': {'as_of_timestamp': '2026-11-06T00:00:00Z', 'coverage': []},
    'merchant_settings': {},
})
```

Operations: dashboard, analytics, forecast, evaluation, recommendation, summary. The backend
OpenAPI defines the corresponding output shapes. Direct calculation functions are also exported.
Config dates are inclusive; context carries lookback, coverage, simulation inclusion, as-of clock,
forecast horizon and summary language. Unknown days are not silently converted to zero activity.

## Verification and limits

Run `make test` from the shared repository for package and PostgreSQL contract tests. Numerical
fixtures are explicitly synthetic test inputs with independently calculable expectations, not real
merchant outcomes. No foreign dataset is used. Authorized merchant data and usability validation
remain necessary before making adoption, forecast-quality, or growth claims. Hindi wording needs
native-speaker review before broad release.

`constraints-tested.txt` records the original contributor's historical environment, not this
workspace's dependency lock. Current shared dependencies are in `apps/api/requirements.lock`.
