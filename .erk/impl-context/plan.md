# Delete erkdesk

## Context
The `erkdesk/` Electron desktop app is no longer needed. Remove the directory and all references across CI, docs, config, and build files.

## Plan

### 1. Delete erkdesk directory
- `rm -rf erkdesk/`

### 2. Clean build/config files

**`Makefile`** — Remove erkdesk targets and `.PHONY` entries:
- `erkdesk-install`, `erkdesk-start`, `erkdesk-package`, `erkdesk-make`, `erkdesk-test`, `erkdesk-test-watch` (lines 170-186)

**`.github/workflows/ci.yml`** — Remove:
- `erkdesk-tests` job (lines 162-182)
- `erkdesk-tests` from `check-results` needs array (line 468)
- `needs.erkdesk-tests.result == 'failure'` from check-results condition (line 484)

**`.gitignore`** — Remove erkdesk section (lines 30-34)

**`.prettierignore`** — Remove erkdesk section (lines 5-15)

### 3. Delete erkdesk-only docs
- `docs/learned/desktop-dash/` — entire directory (21 files)
- `docs/learned/cli/erkdesk-makefile-targets.md`
- `docs/learned/testing/erkdesk-component-testing.md`
- `docs/learned/testing/vitest-fake-timers-with-promises.md`
- `docs/learned/testing/vitest-jsdom-stubs.md`
- `docs/learned/testing/window-mock-patterns.md`
- `docs/learned/architecture/typescript-multi-config.md`

### 4. Remove erkdesk references from shared docs
Edit to remove erkdesk mentions:
- `docs/learned/index.md` — remove desktop-dash category line
- `docs/learned/tripwires-index.md` — remove desktop-dash row
- `docs/learned/architecture/index.md`
- `docs/learned/architecture/state-derivation-pattern.md`
- `docs/learned/architecture/selection-preservation-by-value.md`
- `docs/learned/testing/index.md`
- `docs/learned/testing/tripwires.md`
- `docs/learned/cli/index.md`
- `docs/learned/documentation/index.md`
- `docs/learned/documentation/tripwires.md`
- `docs/learned/documentation/language-scope-auditing.md`
- `docs/learned/ci/tripwires.md`
- `docs/learned/ci/github-actions-workflow-patterns.md`
- `docs/learned/ci/autofix-job-needs.md`

## Verification
- `grep -r erkdesk .` returns no matches (outside git history)
- CI workflow parses correctly (no dangling job references)
