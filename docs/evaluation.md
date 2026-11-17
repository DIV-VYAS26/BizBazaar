# Evaluation evidence and limits

The analytics package and backend now execute real calculations over their supplied records.
Tests use explicitly labelled synthetic inputs; no merchant accuracy or commercial benefit is claimed.

Independent numerical checks include:

- Canonical totals: 850000 paise, six successes, average 141667 paise.
- Half-up edge case: amounts 1 and 2 paise average to 2 paise.
- Merchant-local midnight and inclusive reporting windows.
- Complete zero days distinguished from missing days; current days excluded from training.
- A 35-day synthetic weekly pattern: 28 training days, seven holdout days, weekday MAE 0 and
  flat-baseline MAE 17142.86 paise. This expected result demonstrates the algorithm on a deliberately
  periodic test pattern; it is not a measured real-world performance result.
- Changing only the held-out amounts leaves predictions unchanged and changes measured error.
- Missing coverage, insufficient history, duplicate/mixed-merchant records and invalid amounts.
- Recommendations preserve configured terms and do not create/activate campaigns.
- English/Hindi amounts match metrics; provider timeouts/malformed output preserve fallback.

The API exposes `GET /api/v1/forecast/evaluation` with the usual report date parameters. Evaluation
uses the current-status dataset; it does not reconstruct historical settlement states after refunds.
A real merchant study, data reconciliation and native-language usability review remain unperformed.
