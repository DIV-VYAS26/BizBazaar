# One existing file per upload day

Follow the [GitHub upload guide](github-upload-guide.md) before using this checklist.
The first requested batch on 17 November 2026 contains the complete `docs/` folder.
Those entries are marked below; resume with the remaining unchecked files afterward.
The remote already has a README; its existing content is preserved in the documentation batch.
Preserve every relative path. Each row is one initial file upload, using its current reviewed
contents; it does not claim that the file was developed that day. Days are sequential upload
sessions rather than calendar dates. Improvement days can postpone the remaining entries.

The local project remains complete. The GitHub copy will be incomplete during this rollout.
No application files have been renamed or moved. Only publish the CI workflow once all other
required files have arrived. Keep checklist progress unstaged on other files' upload days.

This snapshot contains **176 files**. Add future source files as needed.

| Done | Upload day | Exact relative path | Suggested commit message |
| --- | ---: | --- | --- |
| ☐ | 1 | `.gitignore` | `chore: add project ignore rules` |
| ☐ | 2 | `README.md` | `docs: add project overview` |
| ☑ | 3 | `docs/github-upload-guide.md` | `docs: add docs/github-upload-guide.md` |
| ☑ | 4 | `docs/daily-upload-checklist.md` | `docs: add docs/daily-upload-checklist.md` |
| ☐ | 5 | `.dockerignore` | `chore: add .dockerignore` |
| ☐ | 6 | `package.json` | `build: add package.json` |
| ☐ | 7 | `package-lock.json` | `build: add package-lock.json` |
| ☐ | 8 | `Makefile` | `build: add Makefile` |
| ☐ | 9 | `compose.yaml` | `build: add compose.yaml` |
| ☐ | 10 | `.env.example` | `chore: add .env.example` |
| ☐ | 11 | `.env.production.example` | `chore: add .env.production.example` |
| ☑ | 12 | `docs/analytics-methodology.md` | `docs: add docs/analytics-methodology.md` |
| ☑ | 13 | `docs/api-contracts.md` | `docs: add docs/api-contracts.md` |
| ☑ | 14 | `docs/architecture.md` | `docs: add docs/architecture.md` |
| ☑ | 15 | `docs/developer-2-learning.md` | `docs: add docs/developer-2-learning.md` |
| ☑ | 16 | `docs/evaluation.md` | `docs: add docs/evaluation.md` |
| ☑ | 17 | `docs/implementation-status.md` | `docs: add docs/implementation-status.md` |
| ☑ | 18 | `docs/integration-handoff.md` | `docs: add docs/integration-handoff.md` |
| ☑ | 19 | `docs/limitations.md` | `docs: add docs/limitations.md` |
| ☑ | 20 | `docs/operations.md` | `docs: add docs/operations.md` |
| ☑ | 21 | `docs/remaining-work-plan.md` | `docs: add docs/remaining-work-plan.md` |
| ☑ | 22 | `docs/setup.md` | `docs: add docs/setup.md` |
| ☐ | 23 | `contracts/enums.json` | `chore: add contracts/enums.json` |
| ☐ | 24 | `contracts/examples/campaign-create.json` | `chore: add contracts/examples/campaign-create.json` |
| ☐ | 25 | `contracts/examples/import-report.json` | `chore: add contracts/examples/import-report.json` |
| ☐ | 26 | `contracts/examples/payment-request.json` | `chore: add contracts/examples/payment-request.json` |
| ☐ | 27 | `contracts/openapi.yaml` | `chore: add contracts/openapi.yaml` |
| ☐ | 28 | `contracts/schemas/api.json` | `chore: add contracts/schemas/api.json` |
| ☐ | 29 | `packages/analytics/README.md` | `docs: add packages/analytics/README.md` |
| ☐ | 30 | `packages/analytics/bizbazaar_analytics/__init__.py` | `feat: add packages/analytics/bizbazaar_analytics/__init__.py` |
| ☐ | 31 | `packages/analytics/bizbazaar_analytics/ai/__init__.py` | `feat: add packages/analytics/bizbazaar_analytics/ai/__init__.py` |
| ☐ | 32 | `packages/analytics/bizbazaar_analytics/ai/base.py` | `feat: add packages/analytics/bizbazaar_analytics/ai/base.py` |
| ☐ | 33 | `packages/analytics/bizbazaar_analytics/ai/external.py` | `feat: add packages/analytics/bizbazaar_analytics/ai/external.py` |
| ☐ | 34 | `packages/analytics/bizbazaar_analytics/ai/fallback.py` | `feat: add packages/analytics/bizbazaar_analytics/ai/fallback.py` |
| ☐ | 35 | `packages/analytics/bizbazaar_analytics/api.py` | `feat: add packages/analytics/bizbazaar_analytics/api.py` |
| ☐ | 36 | `packages/analytics/bizbazaar_analytics/context.py` | `feat: add packages/analytics/bizbazaar_analytics/context.py` |
| ☐ | 37 | `packages/analytics/bizbazaar_analytics/evaluation.py` | `feat: add packages/analytics/bizbazaar_analytics/evaluation.py` |
| ☐ | 38 | `packages/analytics/bizbazaar_analytics/forecast.py` | `feat: add packages/analytics/bizbazaar_analytics/forecast.py` |
| ☐ | 39 | `packages/analytics/bizbazaar_analytics/metrics.py` | `feat: add packages/analytics/bizbazaar_analytics/metrics.py` |
| ☐ | 40 | `packages/analytics/bizbazaar_analytics/recommendations.py` | `feat: add packages/analytics/bizbazaar_analytics/recommendations.py` |
| ☐ | 41 | `packages/analytics/bizbazaar_analytics/schemas.py` | `feat: add packages/analytics/bizbazaar_analytics/schemas.py` |
| ☐ | 42 | `packages/analytics/bizbazaar_analytics/summaries.py` | `feat: add packages/analytics/bizbazaar_analytics/summaries.py` |
| ☐ | 43 | `packages/analytics/bizbazaar_analytics/trends.py` | `feat: add packages/analytics/bizbazaar_analytics/trends.py` |
| ☐ | 44 | `packages/analytics/constraints-tested.txt` | `feat: add packages/analytics/constraints-tested.txt` |
| ☐ | 45 | `packages/analytics/pyproject.toml` | `build: add packages/analytics/pyproject.toml` |
| ☐ | 46 | `packages/analytics/tests/test_calculations.py` | `test: add packages/analytics/tests/test_calculations.py` |
| ☐ | 47 | `packages/analytics/tests/test_input_validation.py` | `test: add packages/analytics/tests/test_input_validation.py` |
| ☐ | 48 | `apps/api/alembic.ini` | `feat: add apps/api/alembic.ini` |
| ☐ | 49 | `apps/api/alembic/env.py` | `feat: add apps/api/alembic/env.py` |
| ☐ | 50 | `apps/api/alembic/script.py.mako` | `feat: add apps/api/alembic/script.py.mako` |
| ☐ | 51 | `apps/api/alembic/versions/6f5f4d2be035_initial_merchant_campaign_and_audit_.py` | `feat: add apps/api/alembic/versions/6f5f4d2be035_initial_merchant_campaign_and_audit_.py` |
| ☐ | 52 | `apps/api/alembic/versions/b2_coverage_scope.py` | `feat: add apps/api/alembic/versions/b2_coverage_scope.py` |
| ☐ | 53 | `apps/api/alembic/versions/cc5456b01d6d_merchant_accounts_and_business_ledgers.py` | `feat: add apps/api/alembic/versions/cc5456b01d6d_merchant_accounts_and_business_ledgers.py` |
| ☐ | 54 | `apps/api/app/__init__.py` | `feat: add apps/api/app/__init__.py` |
| ☐ | 55 | `apps/api/app/cli.py` | `feat: add apps/api/app/cli.py` |
| ☐ | 56 | `apps/api/app/core/__init__.py` | `feat: add apps/api/app/core/__init__.py` |
| ☐ | 57 | `apps/api/app/core/config.py` | `feat: add apps/api/app/core/config.py` |
| ☐ | 58 | `apps/api/app/core/errors.py` | `feat: add apps/api/app/core/errors.py` |
| ☐ | 59 | `apps/api/app/core/middleware.py` | `feat: add apps/api/app/core/middleware.py` |
| ☐ | 60 | `apps/api/app/core/security.py` | `feat: add apps/api/app/core/security.py` |
| ☐ | 61 | `apps/api/app/db/__init__.py` | `feat: add apps/api/app/db/__init__.py` |
| ☐ | 62 | `apps/api/app/db/commerce.py` | `feat: add apps/api/app/db/commerce.py` |
| ☐ | 63 | `apps/api/app/db/models.py` | `feat: add apps/api/app/db/models.py` |
| ☐ | 64 | `apps/api/app/db/session.py` | `feat: add apps/api/app/db/session.py` |
| ☐ | 65 | `apps/api/app/main.py` | `feat: add apps/api/app/main.py` |
| ☐ | 66 | `apps/api/app/routers/__init__.py` | `feat: add apps/api/app/routers/__init__.py` |
| ☐ | 67 | `apps/api/app/routers/accounts.py` | `feat: add apps/api/app/routers/accounts.py` |
| ☐ | 68 | `apps/api/app/routers/api.py` | `feat: add apps/api/app/routers/api.py` |
| ☐ | 69 | `apps/api/app/routers/commerce.py` | `feat: add apps/api/app/routers/commerce.py` |
| ☐ | 70 | `apps/api/app/routers/metadata.py` | `feat: add apps/api/app/routers/metadata.py` |
| ☐ | 71 | `apps/api/app/routers/operations.py` | `feat: add apps/api/app/routers/operations.py` |
| ☐ | 72 | `apps/api/app/schemas/__init__.py` | `feat: add apps/api/app/schemas/__init__.py` |
| ☐ | 73 | `apps/api/app/schemas/accounts.py` | `feat: add apps/api/app/schemas/accounts.py` |
| ☐ | 74 | `apps/api/app/schemas/analytics.py` | `feat: add apps/api/app/schemas/analytics.py` |
| ☐ | 75 | `apps/api/app/schemas/api.py` | `feat: add apps/api/app/schemas/api.py` |
| ☐ | 76 | `apps/api/app/schemas/commerce.py` | `feat: add apps/api/app/schemas/commerce.py` |
| ☐ | 77 | `apps/api/app/services/__init__.py` | `feat: add apps/api/app/services/__init__.py` |
| ☐ | 78 | `apps/api/app/services/accounts.py` | `feat: add apps/api/app/services/accounts.py` |
| ☐ | 79 | `apps/api/app/services/analytics_adapter.py` | `feat: add apps/api/app/services/analytics_adapter.py` |
| ☐ | 80 | `apps/api/app/services/business.py` | `feat: add apps/api/app/services/business.py` |
| ☐ | 81 | `apps/api/app/services/campaigns.py` | `feat: add apps/api/app/services/campaigns.py` |
| ☐ | 82 | `apps/api/app/services/catalog.py` | `feat: add apps/api/app/services/catalog.py` |
| ☐ | 83 | `apps/api/app/services/credit.py` | `feat: add apps/api/app/services/credit.py` |
| ☐ | 84 | `apps/api/app/services/csv_import.py` | `feat: add apps/api/app/services/csv_import.py` |
| ☐ | 85 | `apps/api/app/services/customers.py` | `feat: add apps/api/app/services/customers.py` |
| ☐ | 86 | `apps/api/app/services/loyalty.py` | `feat: add apps/api/app/services/loyalty.py` |
| ☐ | 87 | `apps/api/app/services/mail.py` | `feat: add apps/api/app/services/mail.py` |
| ☐ | 88 | `apps/api/app/services/metadata.py` | `feat: add apps/api/app/services/metadata.py` |
| ☐ | 89 | `apps/api/app/services/offers.py` | `feat: add apps/api/app/services/offers.py` |
| ☐ | 90 | `apps/api/app/services/retention.py` | `feat: add apps/api/app/services/retention.py` |
| ☐ | 91 | `apps/api/app/services/rewards.py` | `feat: add apps/api/app/services/rewards.py` |
| ☐ | 92 | `apps/api/app/services/sales.py` | `feat: add apps/api/app/services/sales.py` |
| ☐ | 93 | `apps/api/app/services/transactions.py` | `feat: add apps/api/app/services/transactions.py` |
| ☐ | 94 | `apps/api/app/services/worker.py` | `feat: add apps/api/app/services/worker.py` |
| ☐ | 95 | `apps/api/pyproject.toml` | `build: add apps/api/pyproject.toml` |
| ☐ | 96 | `apps/api/requirements.lock` | `build: add apps/api/requirements.lock` |
| ☐ | 97 | `apps/api/tests/conftest.py` | `test: add apps/api/tests/conftest.py` |
| ☐ | 98 | `apps/api/tests/test_commerce.py` | `test: add apps/api/tests/test_commerce.py` |
| ☐ | 99 | `apps/api/tests/test_contracts.py` | `test: add apps/api/tests/test_contracts.py` |
| ☐ | 100 | `apps/api/tests/test_credit_sales.py` | `test: add apps/api/tests/test_credit_sales.py` |
| ☐ | 101 | `apps/api/tests/test_integration_contracts.py` | `test: add apps/api/tests/test_integration_contracts.py` |
| ☐ | 102 | `apps/api/tests/test_operations.py` | `test: add apps/api/tests/test_operations.py` |
| ☐ | 103 | `apps/api/tests/test_postgres.py` | `test: add apps/api/tests/test_postgres.py` |
| ☐ | 104 | `apps/api/tests/test_real_analytics.py` | `test: add apps/api/tests/test_real_analytics.py` |
| ☐ | 105 | `apps/api/tests/test_validation.py` | `test: add apps/api/tests/test_validation.py` |
| ☐ | 106 | `apps/api/tests/test_worker.py` | `test: add apps/api/tests/test_worker.py` |
| ☐ | 107 | `apps/web/AGENTS.md` | `feat: add apps/web/AGENTS.md` |
| ☐ | 108 | `apps/web/next-env.d.ts` | `feat: add apps/web/next-env.d.ts` |
| ☐ | 109 | `apps/web/next.config.mjs` | `feat: add apps/web/next.config.mjs` |
| ☐ | 110 | `apps/web/package.json` | `feat: add apps/web/package.json` |
| ☐ | 111 | `apps/web/postcss.config.mjs` | `feat: add apps/web/postcss.config.mjs` |
| ☐ | 112 | `apps/web/src/app/account/page.tsx` | `feat: add apps/web/src/app/account/page.tsx` |
| ☐ | 113 | `apps/web/src/app/analytics/page.tsx` | `feat: add apps/web/src/app/analytics/page.tsx` |
| ☐ | 114 | `apps/web/src/app/campaigns/page.tsx` | `feat: add apps/web/src/app/campaigns/page.tsx` |
| ☐ | 115 | `apps/web/src/app/campaigns/simulate/page.tsx` | `feat: add apps/web/src/app/campaigns/simulate/page.tsx` |
| ☐ | 116 | `apps/web/src/app/connect/page.tsx` | `feat: add apps/web/src/app/connect/page.tsx` |
| ☐ | 117 | `apps/web/src/app/customer/page.tsx` | `feat: add apps/web/src/app/customer/page.tsx` |
| ☐ | 118 | `apps/web/src/app/customers/page.tsx` | `feat: add apps/web/src/app/customers/page.tsx` |
| ☐ | 119 | `apps/web/src/app/dashboard/page.tsx` | `feat: add apps/web/src/app/dashboard/page.tsx` |
| ☐ | 120 | `apps/web/src/app/globals.css` | `feat: add apps/web/src/app/globals.css` |
| ☐ | 121 | `apps/web/src/app/layout.tsx` | `feat: add apps/web/src/app/layout.tsx` |
| ☐ | 122 | `apps/web/src/app/ledger/page.tsx` | `feat: add apps/web/src/app/ledger/page.tsx` |
| ☐ | 123 | `apps/web/src/app/loyalty/page.tsx` | `feat: add apps/web/src/app/loyalty/page.tsx` |
| ☐ | 124 | `apps/web/src/app/offers/page.tsx` | `feat: add apps/web/src/app/offers/page.tsx` |
| ☐ | 125 | `apps/web/src/app/page.tsx` | `feat: add apps/web/src/app/page.tsx` |
| ☐ | 126 | `apps/web/src/app/products/page.tsx` | `feat: add apps/web/src/app/products/page.tsx` |
| ☐ | 127 | `apps/web/src/app/reports/page.tsx` | `feat: add apps/web/src/app/reports/page.tsx` |
| ☐ | 128 | `apps/web/src/app/retention/page.tsx` | `feat: add apps/web/src/app/retention/page.tsx` |
| ☐ | 129 | `apps/web/src/app/sales/page.tsx` | `feat: add apps/web/src/app/sales/page.tsx` |
| ☐ | 130 | `apps/web/src/app/settings/page.tsx` | `feat: add apps/web/src/app/settings/page.tsx` |
| ☐ | 131 | `apps/web/src/app/transactions/page.tsx` | `feat: add apps/web/src/app/transactions/page.tsx` |
| ☐ | 132 | `apps/web/src/components/common/AppShell.tsx` | `feat: add apps/web/src/components/common/AppShell.tsx` |
| ☐ | 133 | `apps/web/src/components/common/BasketEditor.tsx` | `feat: add apps/web/src/components/common/BasketEditor.tsx` |
| ☐ | 134 | `apps/web/src/components/common/BusinessUI.tsx` | `feat: add apps/web/src/components/common/BusinessUI.tsx` |
| ☐ | 135 | `apps/web/src/components/common/CustomerPicker.tsx` | `feat: add apps/web/src/components/common/CustomerPicker.tsx` |
| ☐ | 136 | `apps/web/src/components/common/DisclaimerBanner.tsx` | `feat: add apps/web/src/components/common/DisclaimerBanner.tsx` |
| ☐ | 137 | `apps/web/src/components/common/Navbar.tsx` | `feat: add apps/web/src/components/common/Navbar.tsx` |
| ☐ | 138 | `apps/web/src/components/common/Sidebar.tsx` | `feat: add apps/web/src/components/common/Sidebar.tsx` |
| ☐ | 139 | `apps/web/src/components/ui/Alert.tsx` | `feat: add apps/web/src/components/ui/Alert.tsx` |
| ☐ | 140 | `apps/web/src/components/ui/Badge.tsx` | `feat: add apps/web/src/components/ui/Badge.tsx` |
| ☐ | 141 | `apps/web/src/components/ui/Button.tsx` | `feat: add apps/web/src/components/ui/Button.tsx` |
| ☐ | 142 | `apps/web/src/components/ui/Card.tsx` | `feat: add apps/web/src/components/ui/Card.tsx` |
| ☐ | 143 | `apps/web/src/components/ui/Input.tsx` | `feat: add apps/web/src/components/ui/Input.tsx` |
| ☐ | 144 | `apps/web/src/components/ui/Modal.tsx` | `feat: add apps/web/src/components/ui/Modal.tsx` |
| ☐ | 145 | `apps/web/src/lib/api/business.ts` | `feat: add apps/web/src/lib/api/business.ts` |
| ☐ | 146 | `apps/web/src/lib/api/client.ts` | `feat: add apps/web/src/lib/api/client.ts` |
| ☐ | 147 | `apps/web/src/lib/api/live.ts` | `feat: add apps/web/src/lib/api/live.ts` |
| ☐ | 148 | `apps/web/src/lib/api/mock.ts` | `feat: add apps/web/src/lib/api/mock.ts` |
| ☐ | 149 | `apps/web/src/lib/api/types.ts` | `feat: add apps/web/src/lib/api/types.ts` |
| ☐ | 150 | `apps/web/src/lib/generated/backend.ts` | `chore: add apps/web/src/lib/generated/backend.ts` |
| ☐ | 151 | `apps/web/src/lib/generated/types.ts` | `chore: add apps/web/src/lib/generated/types.ts` |
| ☐ | 152 | `apps/web/src/lib/utils.ts` | `feat: add apps/web/src/lib/utils.ts` |
| ☐ | 153 | `apps/web/src/proxy.ts` | `feat: add apps/web/src/proxy.ts` |
| ☐ | 154 | `apps/web/src/tests/campaign-rules.test.ts` | `test: add apps/web/src/tests/campaign-rules.test.ts` |
| ☐ | 155 | `apps/web/src/tests/canonical-metrics.test.ts` | `test: add apps/web/src/tests/canonical-metrics.test.ts` |
| ☐ | 156 | `apps/web/src/tests/csv-import.test.ts` | `test: add apps/web/src/tests/csv-import.test.ts` |
| ☐ | 157 | `apps/web/src/tests/live-api.test.ts` | `test: add apps/web/src/tests/live-api.test.ts` |
| ☐ | 158 | `apps/web/src/tests/setup.ts` | `test: add apps/web/src/tests/setup.ts` |
| ☐ | 159 | `apps/web/tailwind.config.ts` | `feat: add apps/web/tailwind.config.ts` |
| ☐ | 160 | `apps/web/tsconfig.json` | `feat: add apps/web/tsconfig.json` |
| ☐ | 161 | `apps/web/vitest.config.ts` | `feat: add apps/web/vitest.config.ts` |
| ☐ | 162 | `scripts/backup_database.py` | `chore: add scripts/backup_database.py` |
| ☐ | 163 | `scripts/create_local_env.py` | `chore: add scripts/create_local_env.py` |
| ☐ | 164 | `scripts/export_contracts.py` | `chore: add scripts/export_contracts.py` |
| ☐ | 165 | `scripts/provision_runtime_role.py` | `chore: add scripts/provision_runtime_role.py` |
| ☐ | 166 | `infra/Caddyfile` | `build: add infra/Caddyfile` |
| ☐ | 167 | `infra/Dockerfile.api` | `build: add infra/Dockerfile.api` |
| ☐ | 168 | `infra/Dockerfile.web` | `build: add infra/Dockerfile.web` |
| ☐ | 169 | `infra/compose.production.yaml` | `build: add infra/compose.production.yaml` |
| ☐ | 170 | `tests/contract/test_analytics_input_shape.py` | `test: add tests/contract/test_analytics_input_shape.py` |
| ☐ | 171 | `tests/e2e/business-journey.spec.ts` | `test: add tests/e2e/business-journey.spec.ts` |
| ☐ | 172 | `tests/e2e/live-journey.spec.ts` | `test: add tests/e2e/live-journey.spec.ts` |
| ☐ | 173 | `tests/e2e/live.config.ts` | `test: add tests/e2e/live.config.ts` |
| ☐ | 174 | `tests/e2e/merchant-journey.spec.ts` | `test: add tests/e2e/merchant-journey.spec.ts` |
| ☐ | 175 | `tests/e2e/playwright.config.ts` | `test: add tests/e2e/playwright.config.ts` |
| ☐ | 176 | `.github/workflows/backend.yml` | `ci: add .github/workflows/backend.yml` |
