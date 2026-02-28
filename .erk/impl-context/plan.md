# Rename `markdown-fix` to `fix-formatting` and add ruff format step

## Context

The `markdown-fix` CI job auto-fixes markdown formatting (prettier + docs-sync) on PRs. A recent master commit (`2ed31d08`) introduced ruff format violations in a test file that weren't caught because the `format` check job is check-only — it fails but doesn't auto-fix. Adding `ruff format` to the autofix job would have prevented this.

The rename from `markdown-fix` to `fix-formatting` reflects the broader scope: the job now fixes both Python formatting (ruff) and markdown formatting (prettier).

## Changes

### 1. `.github/workflows/ci.yml` — Rename job + add ruff format step

**Job definition (line 55):**
- Rename `markdown-fix:` to `fix-formatting:`
- Add `uv run ruff format` step after docs-sync, before prettier

**Steps update:**
- After "Sync documentation" step, add: `uv run ruff format`
- Update error message on master push: "Files need formatting or docs are out of sync"
- Update `git add` from `'*.md'` to `'*.md' '*.py'`
- Update commit message: `"Auto-fix formatting (docs-sync + ruff + Prettier)"`

**All references in the file** (9 occurrences):
- Line 201: `autofix.needs` array → `fix-formatting`
- Line 218: `autofix.if` condition → `needs.fix-formatting.result`
- Line 367: `failures` step → `needs.fix-formatting.result`
- Line 389: `errors` step → `needs.fix-formatting.result`
- Line 390-391: error collection for fix-formatting failures — keep as-is (prettier check still useful as the markdown-specific error context)
- Line 422: `--var` → `"fix-formatting=${{ needs.fix-formatting.result }}"`
- Line 463: `ci-summarize.needs` array → `fix-formatting`
- Line 479: `ci-summarize.if` condition → `needs.fix-formatting.result`

### 2. `.github/prompts/ci-autofix.md` — Update variable name

- Line 9: `markdown-fix: {{ markdown-fix }}` → `fix-formatting: {{ fix-formatting }}`

### 3. Makefile — No changes needed

The existing `fix` target (line 15-18) already runs `ruff check --fix`, `ruff format`, and `prettier --write`. No Makefile changes required.

## Files to modify

1. `.github/workflows/ci.yml`
2. `.github/prompts/ci-autofix.md`

## Verification

- Search for any remaining `markdown-fix` references: `grep -r "markdown.fix" .github/`
- Review the diff to ensure all 9 ci.yml references were updated
- Verify the new ruff format step uses `uv run ruff format` (consistent with Makefile)
