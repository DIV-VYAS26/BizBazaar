# Local operations and prepared launch configuration

Public deployment is paused. Nothing in this document authorizes publishing, starting SMTP
delivery, registering a domain, or contacting customers. The production files are preparation.

## Local mail

Run `scripts/create_local_env.py` after installing dependencies. It creates independent Fernet
mail/backup keys and a metrics token in private `.env` without printing them. Local Compose passes
that file only to the API. Browser code receives no secrets.

With `MAIL_DELIVERY_MODE=outbox`, all messages remain encrypted in PostgreSQL. The account and
customer screens expose a development-only email preview; the endpoint requires local/test mode,
enabled demos, outbox mode and the exact allowed Origin. Production returns 404 for this endpoint.
Verification/recovery links are single-use and expire after 30 minutes. Customer portal links
expire after seven days, consent invitations after two days and unsubscribe links after 90 days.

The worker can be checked safely in preview mode:

```bash
.venv/bin/python -m app.services.worker --once
```

It reports PREVIEW_ONLY and does not connect to SMTP. Only a separately configured SMTP worker
attempts delivery. Queueing a reminder/retention message is separate from sending it. SMTP uses
STARTTLS, a timeout, stable Message-IDs, five maximum attempts and exponential retry delays.
Expired SENDING leases can be recovered. Delivery is at-least-once: a worker crash after SMTP
acceptance but before committing SENT can duplicate a notice. Exactly-once external email needs
a provider idempotency API; ordinary SMTP cannot guarantee it.

Marketing delivery additionally requires `MARKETING_DELIVERY_ENABLED=true`, current confirmed
consent, an unchanged email, and the cooldown. Revoked messages are suppressed. Transactional due
notices do not depend on marketing opt-in. Due notices are explicitly queued from the ledger page,
with daily deduplication; the current MVP processes up to 100 customers per queue action.

## Health, monitoring and backups

- `/api/v1/health` is liveness. `/api/v1/health/ready` checks PostgreSQL; production also rejects
  superuser/owner/create-role/create-database/bypass-RLS runtime privileges.
- `/api/v1/metrics` needs `Authorization: Bearer <METRICS_TOKEN>`. Current gauges count pending and
  failed outbox records without customer/merchant identifiers. Alert routing is not configured.
- Errors expose request IDs, not SQL, passwords, tokens or message bodies. Protect database and
  infrastructure logs and never enable request-body tracing on account/customer routes.

```bash
.venv/bin/python scripts/backup_database.py backup backups/local.backup.enc
.venv/bin/python scripts/backup_database.py verify backups/local.backup.enc
```

The local tool uses Compose's `db` service, encrypts before writing the archive, refuses overwrite,
uses mode 0600 and caps backup size at 200 MiB. Verification generates its own disposable database,
restores there, checks migration metadata and record counts, and removes only that temporary DB.
`--test-source` selects the isolated synthetic `test-db` service. It never accepts an existing
restore destination. Keep backup keys separately from archives; no lost-key recovery is possible.
Production backup scheduling, off-machine storage, retention and recovery objectives must be set
with the chosen hosting provider at launch. No production backup schedule is active now.

## Prepared launch sequence — execute only after deployment is requested

1. Review `infra/compose.production.yaml`, `infra/Caddyfile` and `.env.production.example` against
   the chosen provider. Configure the owner's domain and provider-specific ingress protections.
2. Put only runtime values in private `.env.production`. Generate independent production keys,
   configure a verified SMTP sender, and leave marketing delivery disabled until intentionally
   enabled. Use HTTPS origins and secure cookies; keep demos disabled.
3. Put the owner DB password in private `secrets/db_owner_password`. Keep the owner URL and
   `RUNTIME_DB_PASSWORD` as setup-only environment values, not in the API/worker env file.
4. Start only the private database, then run the setup-profile migration service with
   `MIGRATION_DATABASE_URL` referring to `bizbazaar_owner`. Its command is `alembic upgrade head`.
   Run the same one-off image with `python /srv/scripts/provision_runtime_role.py`, supplying the
   setup-only runtime password. The script grants application DML but revokes financial/audit
   updates/deletes and schema ownership. Repeat privilege provisioning after future migrations.
5. Set the API/worker DATABASE_URL to `bizbazaar_runtime`, never the owner. The prepared proxy is
   the only published service; PostgreSQL/API/web have no production host-port exposure.
6. Verify readiness, TLS, headers, account recovery and sender deliverability in staging. Configure
   protected metric scraping, alert routing, encrypted scheduled backups and a restore drill.
7. Run the tests and provider-specific security/load checks before any public launch.

The frontend uses per-response script nonces and dynamic rendering; CSP forbids untrusted script
origins, framing, object embedding and external form submission. Development alone allows
unsafe-eval for the dev server. Style attributes remain allowed for chart positioning; script
attributes do not receive this exception. Customer token fragments are cleared from the URL and
Referrer-Policy is no-referrer. Production browser journeys exercise these nonce headers locally.

No remote CI run, public TLS certificate, SMTP acceptance, alert delivery or production restore
has been observed in this workspace. Those outcomes must be verified after deployment is requested.
