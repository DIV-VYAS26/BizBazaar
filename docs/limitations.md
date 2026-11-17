# Current limits

- Merchant account registration/recovery is implemented and locally tested. Public deployment,
  actual SMTP deliverability, domain/TLS and external monitoring remain unverified and paused.
- Simulated payments/rewards never move money. CSV records are authorized merchant inputs, not
  independent bank verification or complete coverage of every shop channel.
- Product/basket gross profit uses recorded unit costs, excluding taxes/overheads; missing costs
  remain unknown. It is not a complete accounting, tax, stock valuation or settlement system.
- Do not import the same payment again under another ID after recording it manually: different
  source IDs cannot establish that two records describe the same real payment.
- Loyalty earns on immediately paid sales; credit repayments do not retrospectively award points.
  Voids may claw back already-spent points, leaving an unavailable negative balance.
- Due-reminder queueing and retention preview currently process up to 100 customers per batch.
  The SMTP worker is at-least-once and may duplicate a notice after uncertain server acceptance.
- Broad request throttling is per-process; account limits are shared in PostgreSQL. Public hosting
  should add provider-specific ingress controls. Merchant-row locking favors correctness over
  high per-merchant throughput; no production load capacity has been measured.
- Forecasts require explicit complete-day evidence and use a weekday-mean baseline. No calibrated
  prediction intervals, annual seasonality, trained ML or guaranteed uplift is claimed.
- Historical analytics use current transaction statuses; later refunds can change past totals.
- Default summaries are deterministic. No external LLM is configured; optional provider injection
  selects a vetted wording style only, with deterministic monetary rendering.
- Hindi templates have numerical/encoding tests but still need native-speaker usability validation.
- Synthetic test cases prove selected correctness properties, not real merchant adoption or accuracy.
- Remote GitHub CI and teammate approval remain unverified until a project repository is supplied.
