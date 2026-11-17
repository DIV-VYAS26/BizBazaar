# Learning the BizBazaar backend while building it

This guide covers your Developer 2 responsibilities. Read it with the linked source files.

## 1. What an API does

The website sends an HTTP request such as `POST /api/v1/campaigns`. FastAPI selects a route,
validates the body, checks the merchant session, calls a service, and returns JSON.
The browser never connects directly to PostgreSQL: the API is where we enforce permissions.

Start with `app/main.py` and `app/routers/api.py`. Open `/docs` when the server runs to see the
generated interface. OpenAPI is a machine-readable contract Developer 1 can use to generate
TypeScript types. It is not a separate server.

## 2. Schemas, models, and migrations have different jobs

`app/schemas/api.py` describes acceptable HTTP data. Pydantic rejects unexpected fields and invalid
types. The client can request a budget; it cannot submit how much has already been spent.

`app/db/models.py` describes stored records and relationships. SQLAlchemy translates Python
queries to parameterized SQL. Database constraints protect against mistakes from other writers
as well as this API. Do not confuse input validation with database integrity: we need both.

Alembic migrations describe changes to the actual database. Changing a Python model alone does
not update a teammate's existing tables. The checked-in migration makes that change repeatable.

## 3. Sessions answer 'who is making this request?'

The local CLI creates a private, one-time demo credential. The exchange endpoint replaces it with
a browser cookie. PostgreSQL stores the token's hash, so reading the table does not reveal usable
session cookies. Expiry and revocation are checked on requests.

HttpOnly prevents JavaScript from reading the session cookie. Cookies are automatically sent
by browsers, so mutations also need CSRF proof. CORS controls which browser origins can read
responses; it is not a substitute for CSRF or merchant authorization.

The merchant ID comes from the session, never from a trusted-looking JSON field. Every private
lookup uses that merchant ID. Returning 404 for another merchant's campaign avoids disclosing
whether the campaign exists.

## 4. Transactions answer 'what if something fails halfway?'

Suppose a payment advances the counter, consumes budget, creates a reward, and writes an audit
entry. If creating the reward fails, leaving the counter changed would corrupt future decisions.
A database transaction commits all those changes together or rolls them all back.

Read `app/services/transactions.py`, then `app/services/rewards.py`. The service commits only
after the whole operation succeeds. It does not make external network calls while holding locks.

## 5. Locks answer 'what if two requests happen together?'

Imagine only ₹100 of reward budget remains and two eligible payments arrive. Without locking,
both might read ₹100 and both issue a ₹100 reward. The merchant-row lock makes the operations
take turns. The second reads the first operation's committed spending and skips its reward.

The database also enforces uniqueness and nonnegative budget arithmetic. This layered approach
is stronger than a Python `if` check alone. Per-merchant serialization is deliberately simple;
later performance measurements may justify smaller lock scopes.

## 6. Idempotency answers 'what if the browser retries?'

Networks can lose a response after the server commits. Retrying must not issue a second reward.
An event ID and canonical payload fingerprint identify the request. An identical replay returns
the stored decision; the same ID with changed data returns 409.

A transaction ID is separate: a client cannot evade event deduplication by giving the same
transaction a new event ID. Imported history is also excluded from simulated reward processing.

## 7. Time and money need explicit meanings

Money is integer paise, so ₹8,500 is 850000. P3 handles average rounding; the backend never uses
binary floats for financial decisions. UTC is the storage timezone; merchant-local dates determine
day boundaries. Server time after locking determines reward eligibility, not a client timestamp.

Refunding a simulated successful payment changes current net metrics, but it preserves an issued
reward and its historical acceptance decision. A report must state which measure it shows.

## 8. Analytics is another developer's module

Your adapter fetches authorized records and passes them to P3. P3 computes totals, trends,
forecasts and summaries. The adapter adds reporting dates, historical lookback, coverage and
settings. It never gives the analytics package database credentials.

Missing dates are not automatically zero-sales dates. A complete zero-transaction day and an
unknown day mean different things. The package now supplies those calculations. Insufficient forecast history is an honest result,
while configured foundation mode can still intentionally disable calculations.

## 9. Tests demonstrate behavior

Schema tests exercise malicious/invalid inputs. PostgreSQL integration tests exercise actual
constraints and transactions. Concurrent tests deliberately send competing events. Failure
injection proves the rollback boundary. SQLite would not demonstrate PostgreSQL's row locks.

CI runs the checks on changes so teammates discover incompatible merges early. A green local run
is evidence for tested behavior; it is not proof of public production readiness.

## Suggested reading order

1. Run the health endpoint and inspect `main.py`.
2. Read `CampaignCreate` and compare it with `Campaign`.
3. Trace create -> approve -> activate through route and service.
4. Trace a simulated payment and its replay.
5. Read the final-budget race and injected-failure tests.
6. Inspect the analytics adapter and teammate contract.

## 10. Connecting teammates without weakening backend rules

An adapter translates one interface into another. Member 1's screens originally expected
`spent_budget_paise`; the database/API uses `consumed_paise`. We map the field at the browser API
boundary. We do not remove authorization or change budget arithmetic to match a mock implementation.
The actual wire types now come from FastAPI's generated OpenAPI, while presentation types remain
separate. A generated-type drift check makes an incompatible server change visible in CI.

Member 3's models forbid extra fields. We send exactly their five transaction fields and three
config fields; coverage and history go into a separate context. The user subsequently authorized completing the calculation package. `real` mode now executes
those functions and checks their output schemas; `foundation` remains a validation-only diagnostic mode.

Day coverage is authenticated metadata with provenance. It is scoped to whether simulations are
included, and new activity invalidates a previous COMPLETE declaration. This prevents a forecast
from treating incomplete exports as complete zero-sales days. A merchant declaration still does
not independently verify bank settlement or every shop channel.

The browser test exercises the browser's actual cookie/CORS/CSRF behavior, the API and PostgreSQL.
That catches integration mistakes that a Python TestClient cannot, such as forgetting
`credentials: 'include'`. It uses a separate test database and loopback ports 13001/18001. The
one-time credential stays in memory; traces are disabled to avoid recording credentials/cookies.

## 11. What changed when analytics became executable

Your backend responsibilities remain data ownership, database consistency and action authorization.
The new analytics entry point consumes the authorized snapshot and returns ordinary JSON. It does
not query PostgreSQL or change campaigns. The backend checks the response schema before the browser
receives it. Forecasting is a weekday baseline with explicit coverage requirements; evaluation
withholds later dates from training. Default summaries need no API key and render verified amounts.
An optional provider can select a vetted wording style, but cannot replace the numerical facts.

## 12. Accounts: password hashing and revocable sessions

Passwords use Argon2id, a memory-hard one-way hash. Encryption would allow a stolen decryption key
to reveal every password; ordinary fast hashing would make guessing cheaper. Each hash stores
its salt and parameters. Password work has bounded concurrency and account attempts use shared
PostgreSQL rate buckets. Email verification and recovery use random expiring, hashed single-use
tokens. Resetting a password revokes existing sessions in the same transaction.

The browser receives an opaque HttpOnly cookie. Compared with browser-stored JWTs, this keeps
the credential out of JavaScript and makes logout/reset revocation immediate at the database.
Mutation requests also need the readable CSRF proof and exact Origin. These controls serve
different purposes: authentication identifies the session; CSRF/origin checks protect its use.

## 13. Credit is a ledger, and collections are a different measure

A ₹400 credit sale records ₹400 owed and no collected payment. A ₹100 repayment adds ₹100 to
collections and leaves ₹300 owed. Recording the credit sale itself as a successful payment would
count money before receipt, then count it again on repayment.

Charges and repayments are immutable entries. A correction adds an opposite reversal instead of
rewriting history. The database rejects updates/deletes even if a future route is written badly.
Repayments allocate to the earliest due charges when calculating overdue balances. Acknowledging
a charge means the customer reviewed it; it does not reduce debt. Private customer links grant
access to one customer's ledger and acknowledgement actions, without a merchant session.

Sale voids reverse their linked accounting and restock together. Generic ledger reversal refuses
a linked sale charge so these related records cannot diverge. Idempotency keys bind an operation
to its input fingerprint; retrying the same body returns the saved result, while changing that
body under the same key returns a conflict. Refresh reads current state after a replay.

## 14. Historical cost and safe offer arithmetic

Each sale line stores the product name, quantity, price and cost used at sale time. Reading today's
catalog cost for an old sale would silently rewrite past profit. Gross profit is sale revenue
minus recorded product cost; it excludes rent, wages and taxes. Missing cost stays unknown.

For a ₹400 item with ₹320 cost, a ₹50 discount leaves ₹350 revenue and ₹30 gross profit. That is
about 8.57% margin, which fails a 20% minimum. The backend checks `(revenue - cost) * 10000 >=
minimum_margin_bps * revenue` using integers, avoiding floating-point boundary errors. A language
model cannot approve or override this decision. Rules can be compared deterministically; draft,
approval and activation remain separate. Price/cost edits invalidate an approved product version.

Loyalty redemptions use the same known-cost and minimum-margin checks. Voiding an earning sale
after its points were spent can leave a negative point ledger; available points stay zero until
the balance is earned back. Reversing history must not create another spending opportunity.

## 15. Why a database outbox rather than sending email inside a route

A route commits the business action and encrypted mail entry together. This avoids reporting a
successful sale/account action while losing its notification. A separate worker handles slow SMTP
and retries. A broker such as Celery/Redis could scale work distribution, but PostgreSQL row locks
and durable rows are sufficient for this MVP and avoid another operated service.

SMTP has no universal idempotency API, so we document at-least-once delivery and stable Message-IDs
rather than claiming exactly-once mail. Consent/email/cooldown checks run again before marketing
delivery because a customer can opt out after a campaign is queued. Preview mode never sends.

## 16. Production preparation is different from deployment evidence

Migrations run with an owner role; the app uses a role that cannot own tables or rewrite financial
history. HTTPS termination belongs at the proxy. Browser script nonces reduce script injection
opportunities; they require dynamic rendering so cached HTML does not reuse a nonce. Secrets stay
out of NEXT_PUBLIC variables and source control. Backups are encrypted and restored into a new
disposable database during verification. A backup file alone does not prove recovery works.

These files and local tests prepare deployment. Actual TLS, SMTP delivery, monitoring and remote
backup operation still need evidence from the future hosting environment.
