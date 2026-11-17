# BizBazaar backend architecture

## Boundaries

Developer 1 owns the browser; Developer 2 owns HTTP, authorization, persistence, campaign actions,
and infrastructure; Developer 3 owns analytical calculations and grounded summaries.

The backend is a FastAPI application with PostgreSQL and an in-process analytics adapter.
A separate worker process handles the durable mail outbox. No broker, payment integration,
or AI action permissions are introduced.

## Decisions and alternatives

| Choice | Why | Alternative / tradeoff |
|---|---|---|
| FastAPI + Pydantic | Typed validation and generated API contract; same language as analytics | Django has more built-in account/admin features but adds a larger application structure |
| PostgreSQL | Transactions, row locks, partial unique indexes, relational tenant constraints | SQLite cannot verify the same locking behavior; document databases are unnecessary here |
| Synchronous SQLAlchemy + sync routes | Simple transaction boundaries; FastAPI runs sync handlers in its thread pool | Async DB access can improve I/O scaling but adds lifecycle complexity; measure before switching |
| Alembic migrations | Versioned schema shared by all developers | Startup `create_all` does not evolve or document an existing schema |
| Integer paise | Exact sums and comparisons | Fixed-precision decimals also work; binary floats are unsuitable for money |
| Opaque cookie sessions | Server-side revocation, expiry and logout | JWTs require separate revocation decisions; bearer storage exposes tokens to browser JS |
| Merchant-row serialization | Consistent lock order and simple correctness across actions/imports | Finer-grained locking improves per-shop throughput at a complexity cost |
| Code-generated OpenAPI snapshot | One authoritative schema plus reviewable changes | Hand-maintaining independent schemas risks drift |
| Pure analytics package with validated inputs/outputs | No fabricated metrics or duplication of P3's ownership | A stub could help UI development, but must not be confused with real calculations |

## Mutation transaction

Authenticate and validate input; acquire merchant lock; recheck session; acquire campaign lock
when needed; recheck current server time/state; mutate and audit; commit; return the result.
All mutation services use this ordering. A failed mutation rolls back all writes.
Transient deadlock/serialization failures retry the whole transaction at most twice.

The session lookup before the lock establishes the actor. Session expiry/revocation is checked
again after acquiring the merchant lock. Browser actions also require valid origin and CSRF proof.

All simulated events for a merchant serialize before deduplication. The second identical request
therefore sees the first committed decision. Database uniqueness remains a second safeguard;
unexpected integrity errors roll back and return a safe 409 rather than using an aborted transaction.

## Campaign semantics

- Creation produces DRAFT; approval and activation are separate actions.
- Exactly one ACTIVE campaign per merchant, enforced by a partial unique index.
- `starts_at <= server_now < ends_at`; client timestamps do not establish eligibility.
- Expiry is reconciled during activation/event mutations, without relying on a scheduler.
- GET can show persisted ACTIVE after its end time until reconciliation; clients must also display dates.
- Exhaustion stops issuance, not counting: the campaign remains ACTIVE until completion/expiry.
- Repeating the current lifecycle target returns its state without an additional transition audit.
- Active parameters cannot be edited; no edit endpoint is provided.

Nth rewards use accepted successful count modulo N. Threshold rewards use
`previous < threshold <= current`, once. Acceptance order is assigned under the lock.
The remaining budget is cap minus consumed minus reserved; reserved is zero for synchronous simulation.

## Transaction lifecycle

CSV establishes immutable recorded history. Identical reimports are duplicates, changed values
are conflicts, and invalid rows are reported. CSV records cannot trigger simulated rewards.
Simulator events create new transactions. An external transaction ID cannot be reused by a later
event or campaign, even if its original event received no reward.

A simulator-only full-refund operation changes SUCCESS to REFUNDED, idempotently. It preserves
original event replay decisions, issued rewards, and campaign accepted counters. Thus current net
analytics and historical campaign activity are intentionally distinct measures.

## Analytics consistency

Related reads run in one PostgreSQL repeatable-read, read-only snapshot. Inputs include up to
90 days of lookback before the selected reporting start, explicit coverage, settings, timezone,
and simulation inclusion. Missing coverage means UNKNOWN. No imported file implicitly establishes
a complete business day. P3 decides whether history is sufficient and supplies calculations.

## Security limits

Merchant accounts use Argon2id passwords, verified email and opaque revocable sessions. Demo
identity/simulator endpoints are disabled by production configuration. Account attempts use shared
PostgreSQL limits; Argon2 operations have bounded per-process concurrency.
Body, CSV row/field, report range/row, horizon, and pagination limits bound work.
The local limiter is bounded in memory and per process; it is not distributed abuse protection.
Errors do not include raw inputs, SQL or credentials. Audit updates/deletes are rejected by a DB
trigger; a database owner can bypass that trigger, so it is not protection against a compromised DBA.
The prepared runtime role cannot alter audit/ledger records and does not own schema tables.
Public launch still requires actual credentials, TLS/domain setup, operational monitoring,
hosting-specific ingress controls and validation. Configuration alone is not a deployed service.

## Commerce and customer boundaries

Paid manual sales create collection transactions. Credit sales create debt; repayments create
collection transactions. Price and cost snapshots remain immutable after catalog edits. Reversals
append credit/loyalty entries; sale voids restock and reverse accounting together. Request keys
bind the operation and complete input to a stored result, making retries safe.

Offer approval requires known costs, exact integer margin comparisons and a budget covering the
maximum configured redemptions. Activation and redemption recheck product versions and dates.
Voids do not restore promotion limits. Loyalty discounts also preserve minimum margin.

Customer portal links are bearer capabilities limited to one customer's ledger and acknowledgement
actions. They expire; changing contact email revokes old links. Raw tokens are hashed in token
tables, encrypted in the outbox, sent in URL fragments, cleared from browser history and thereafter
transmitted only in Authorization headers. Consent is confirmed by the customer, not set by a
merchant checkbox. Marketing queue/delivery recheck consent, destination and cooldown.

SMTP is at-least-once: retries have stable Message-IDs, but a crash after SMTP acceptance can
cause a duplicate notice. Preview mode performs no delivery. See operations.md for this tradeoff.

## Integration update

The supplied frontend and Member 3 validation package are now in this workspace. See
`integration-handoff.md` for the exact ownership-boundary changes. The analytics package now implements deterministic calculations and grounded summaries under
user authorization; its operation-specific outputs are checked at the API boundary. Read-only analytics snapshots are materialized and released
before provider execution. Coverage is separately scoped by simulation inclusion.
