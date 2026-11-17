# Teammate source integration

Sources supplied by the user:

- Member 1: `Biz Bazaar.zip`, Next.js frontend and mock/reference API contracts.
- Member 3: `BizBazaar - Copy.zip`, installable input-validation package.

Imported only source/config/test files. Bundled virtual environments, node_modules, build outputs,
foreign raw datasets, Git metadata, and Member 1's in-memory reference backend were excluded.
The source archives in Downloads remain unchanged.

## Changes made at the integration boundary

Member 1's layout/screens are retained. Changes concern branding, live session connection,
credentialed requests, CSRF, request dates, wire-to-view mapping, supported CSV examples, and
independent loading of campaigns/reports when analytics is unavailable. Backend OpenAPI now
actually generates the TypeScript wire types; the original view interfaces no longer claim
that they directly match OpenAPI. The imported mock remains explicitly separate.

The original Member 3 archive contained validation models only. Subsequently, the user authorized
completing its missing work in this workspace. The package now contains deterministic metrics,
trends, weekday forecasts, historical evaluation, configured suggestions and grounded English/Hindi
summaries. Canonical validation has been aligned with backend bounds. This is newly implemented
work, not a claim that those modules were present in the supplied archive.

## What each teammate needs to do next

Member 1: review the integration changes and UI behavior for unavailable insights. Public
account-registration/recovery screens remain a separate release task.

Member 3: review the completed calculation modules, interface decisions and documented test evidence.
Authorized merchant-data reconciliation and native-language usability checks remain unperformed.
The package supports arbitrary valid canonical inputs; labelled test fixtures do not establish
real-world forecast accuracy.

Member 2: maintain these interfaces and verification. Human teammate approval cannot be inferred
from passing local tests. There is no project-specific GitHub remote available, so remote CI and
PR review remain pending; no attempt is made to commit this project through the parent home-directory
Git repository.
