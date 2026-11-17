# Project organization and daily GitHub uploads

The complete integrated project stays in this folder. Upload one existing file per day using
the numbered checklist. Keep each file at its current relative path on GitHub. Day numbers are
upload sessions, not claims about when the existing code was written.

On 17 November 2026, the requested first batch is the entire `docs/` folder. Subsequent uploads
can resume the one-file schedule, skipping documentation already published. The target repository
is `https://github.com/DIV-VYAS26/BizBazaar.git`; the local commit email is
`divvyas26@gmail.com`. Its pre-existing README is preserved in this documentation batch.

## Folder map

| Path | Contents |
| --- | --- |
| `apps/api/app/` | FastAPI routes, business services, database models and validation |
| `apps/api/alembic/` | Ordered database migrations; preserve filenames and revision relationships |
| `apps/api/tests/` | Backend verification |
| `apps/web/src/app/` | Next.js pages, layouts and styles |
| `apps/web/src/components/` | Shared interface components |
| `apps/web/src/lib/` | API adapters, generated contracts and utilities |
| `apps/web/src/tests/` | Frontend unit and adapter tests |
| `packages/analytics/` | Integrated analytics package and its tests |
| `contracts/` | API schemas and example requests/responses |
| `tests/` | Cross-package contract and browser tests |
| `scripts/` | Environment, contract export, database-role and backup tools |
| `infra/` | Container builds and future production configuration |
| `docs/` | Setup, architecture, verification, handoff and upload guidance |
| `.github/workflows/` | Remote verification workflow |
| Root configuration | Dependency manifests/locks, Makefile, Compose and environment templates |

These paths are already referenced by imports, npm workspaces, Python packaging, Docker builds
and tests. No application files were relocated for the upload schedule.

## Before the first upload

This project has a dedicated Git repository connected to the target repository. The enclosing
home-directory repository must not be used to stage this project. For a new, uninitialized copy
only, initialize a separate repository from this project folder:

```bash
cd /Users/divvyas/BizBazaar
git init -b main
git rev-parse --show-toplevel
```

The last command must print `/Users/divvyas/BizBazaar`. Stop if it prints your home directory.
Run initialization only once; if a dedicated repository already exists, inspect it instead.

For a new remote, create an empty GitHub repository without an automatically added README,
license or gitignore, then connect its actual URL with
`git remote add origin YOUR_REPOSITORY_URL`. For this existing remote, preserve its history;
do not initialize a replacement history or force-push. Setup commands are for future reference
and should not be repeated against an already configured checkout.

## First upload

The first checklist entry is `.gitignore`, which excludes local environment files, installed
dependencies, build outputs, test artifacts, secrets and backups. Only the two named environment
templates are allowed through the environment-file ignore rule.

The requested documentation batch precedes that checklist entry. Upload `.gitignore` on the next
single-file day; its local exclusions already apply while selecting today's documentation files.

```bash
git add -- .gitignore
git diff --cached --name-only
git diff --cached
git commit -m "chore: add project ignore rules"
git push -u origin main
```

Confirm that only the intended file is staged before committing. If other files are already
staged, unstage those files first. Do not use `git add .`, `git add -A` or `git commit -a` for this
one-file upload workflow.

## Each later upload day

1. Open the checklist and choose the next unchecked file. Check that the Git root is still this
   project and that `git remote -v` points to the intended repository.
2. Run `git status --short`. The remaining untracked project files are expected during this rollout.
   Preserve any unfinished edits before pulling. After the initial commit exists,
   `git stash push --include-untracked -m "local work before daily pull"` can save edits and untracked
   source files; restore them immediately after pulling with `git stash pop`. Ignored local files
   remain on disk. A stash is local, not an off-machine backup.
3. Run `git pull --ff-only origin main`. If it fails or restoring the stash produces conflicts,
   stop and resolve them before staging. Do not force-push or discard changes to bypass the error.
4. Review the selected file in the full local project and run checks appropriate to any edits.
5. Stage only its exact relative path, inspect the staged filename and diff, commit, then push.

For example, on the README upload day:

```bash
git add -- README.md
git diff --cached --name-only
git diff --cached
git commit -m "docs: add project overview"
git push origin main
```

The checklist supplies a suggested message for each initial file upload. Review it against the
actual staged content. Record progress outside the staged commit, or mark the local checklist
and keep that edit unstaged; uploading a checklist update together with the selected file would
make it a two-file commit. Before its own upload day, clear completed checkboxes in the staged
checklist if you want GitHub to receive a reusable blank template.

## Continuing development

Keep building and testing against the complete local source. When an unuploaded file changes,
its eventual first upload should contain the current reviewed version. When an already uploaded
file needs an improvement, use that day's single-file commit for the improvement and postpone
the next checklist entry. Use a message describing the actual change.

Some fixes require several files to change together, especially API contracts, migrations and
dependency updates. Finish and verify those changes locally; publish the related changes together
if you need GitHub to remain consistent. That requires relaxing the one-file rule for that fix.
Do not split a necessary coordinated fix while presenting the remote project as runnable.

## What the gradual upload means

- GitHub contains a partial source archive until all required files arrive. README links may lead
  to files that have not been uploaded yet. A fresh clone cannot be expected to install or run
  during the rollout.
- The workflow file is last so automatic verification is introduced after the source and tests.
  Its first remote run still needs to be checked; local historical results do not prove remote CI.
- Preserve dependency lockfiles, empty Python package initializers, environment templates and
  migration files. They are project files, even when small or generated.
- Never upload `.env`, real credentials, `node_modules`, `.venv`, `.next`, backups or local test
  output. Do not force-add ignored files.
- Use normal current commit dates and accurate messages for existing integrated work. Future
  improvements can describe the new work actually done that day.
- This schedule does not publish the website. Public deployment remains paused.

The checklist is a snapshot of upload candidates. Add newly created source files to the plan
as development continues. Its ordering groups files for review; it does not make each intermediate
commit a complete application.
