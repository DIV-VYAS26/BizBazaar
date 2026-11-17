# Remaining implementation work

Public deployment is paused at the user's request. Implement and verify locally before any launch.

- [x] Merchant signup, verification, login, recovery, session revocation and account browser flows.
- [x] Customers, verified marketing consent and scoped customer credit portal.
- [x] Append-only credit charges, repayments, reversals, acknowledgements and due-reminder queue.
- [x] Product/cost/stock catalog, manual sales and historical price/cost snapshots.
- [x] Deterministic offer comparison, minimum-margin checks and approved bounded redemption.
- [x] Loyalty ledger and consent-controlled retention drafts/outbox.
- [x] Worker retries, local encrypted mail preview and production SMTP adapter (no external send).
- [x] Readiness/metrics, encrypted backup/restore test and prepared production configuration.
- [x] Browser journeys, financial/authorization/concurrency tests and documentation updates.

Verification: 141 Python tests, 13 frontend unit tests, two browser journeys in development and
optimized local builds, schema/contracts/lint checks, npm production audit, local container smoke
checks and a populated synthetic backup restore. See implementation-status.md for exact limits.

Actual deployment, remote CI, real merchant interviews and native-speaker validation cannot be
reported complete through code alone. Do not publish, contact merchants or send external messages
while deployment is paused. Local preview/tests use explicitly labelled test data.
