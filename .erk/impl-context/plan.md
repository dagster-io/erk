# Add git pre-push hook for type/format checks

## Context

No pre-push validation exists. Type errors and formatting issues are only caught by CI after push. Since `gt submit` respects git hooks via `--verify` (enabled by default), a single git pre-push hook covers both `git push` and `gt submit`.

## Plan

### 1. Create tracked hooks directory and pre-push script

Create `githooks/pre-push` with:
- `uv run ruff check` (lint)
- `uv run ruff format --check` (format)
- `uv run ty check` (type check)

All fast. No unit tests (those stay in CI). Runs all three, reports all failures (doesn't bail on first).

Bypassable with `--no-verify` on either `git push` or `gt submit`.

### 2. Set `core.hooksPath` to tracked directory

Update `.git/config` to point `core.hooksPath` to `githooks/` so the hook is version-controlled and works across worktrees.

### 3. Add Makefile target

Add `make install-hooks` (or just document the git config command) for setup after clone. Alternatively, just set it once since this is single-developer.

## Files

- **Create**: `githooks/pre-push` (shell script)
- **Modify**: Makefile (add `pre-push-check` target the hook can call)

## Verification

- `git push --dry-run` to a test branch triggers the hook
- `gt submit --no-interactive --dry-run` triggers the hook
- Introduce a type error, confirm push is blocked
- `--no-verify` bypasses the hook
