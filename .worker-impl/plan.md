# Plan: Audit HIGH Priority Docs (Phases 2-3)

**Objective:** #6767 — Audit HIGH Priority Docs (60 docs)
**Steps:** 2.1-2.10 (Phase 2) and 3.1-3.10 (Phase 3) = 20 docs total
**Approach:** Batch audit with `--auto-apply` mode

## Goal

Audit 20 docs from the HIGH priority list (scores 11-12), stamping each with audit metadata and applying any recommended simplifications.

## Status

- **Phase 1 (1.1-1.10)**: COMPLETE via PR #6769 (8 docs modified, 2 deleted)
- **Phase 2 (2.1-2.10)**: Pending - this plan
- **Phase 3 (3.1-3.10)**: Pending - this plan

## Docs to Audit

### Phase 2 (Steps 2.1-2.10) — 10 docs

| Step | Doc Path | Score |
|------|----------|-------|
| 2.1 | `commands/command-rename-pattern.md` | 12 |
| 2.2 | `desktop-dash/main-process-startup.md` | 12 |
| 2.3 | `desktop-dash/vitest-setup.md` | 12 |
| 2.4 | `desktop-dash/webview-api.md` | 12 |
| 2.5 | `planning/metadata-field-workflow.md` | 12 |
| 2.6 | `pr-operations/template-synchronization.md` | 12 |
| 2.7 | `testing/hook-testing.md` | 12 |
| 2.8 | `architecture/tripwires.md` | 11 |
| 2.9 | `ci/containerless-ci.md` | 11 |
| 2.10 | `ci/review-spec-format.md` | 11 |

### Phase 3 (Steps 3.1-3.10) — 10 docs

Need to identify from audit-scan. Run `/local:audit-scan` to get the next 10 HIGH priority docs after Phase 2.

## Implementation

### Step 1: Run Batch Audit for Phase 2

Execute `/local:audit-doc --auto-apply` for Phase 2 docs:

```bash
/local:audit-doc commands/command-rename-pattern.md --auto-apply
/local:audit-doc desktop-dash/main-process-startup.md --auto-apply
/local:audit-doc desktop-dash/vitest-setup.md --auto-apply
/local:audit-doc desktop-dash/webview-api.md --auto-apply
/local:audit-doc planning/metadata-field-workflow.md --auto-apply
/local:audit-doc pr-operations/template-synchronization.md --auto-apply
/local:audit-doc testing/hook-testing.md --auto-apply
/local:audit-doc architecture/tripwires.md --auto-apply
/local:audit-doc ci/containerless-ci.md --auto-apply
/local:audit-doc ci/review-spec-format.md --auto-apply
```

### Step 2: Identify Phase 3 Docs

Run `/local:audit-scan` to get the current HIGH priority list. Select docs 21-30 (or next 10 after Phase 2 docs are audited).

### Step 3: Run Batch Audit for Phase 3

Execute `/local:audit-doc --auto-apply` for the 10 Phase 3 docs.

### Step 4: Commit Changes

After all audits complete, commit all modified docs:
```
Audit Phases 2-3 Docs (Steps 2.1-3.10): Apply audit verdicts and stamp with metadata
```

## Verification

1. All 20 docs have `last_audited` frontmatter field
2. All 20 docs have `audit_result` field (`clean` or `edited`)
3. No broken paths remain in audited docs (verified during audit)
4. CI passes (lint, format, type checks)

## Files to Modify

### Phase 2 (known paths relative to `docs/learned/`):
- `commands/command-rename-pattern.md`
- `desktop-dash/main-process-startup.md`
- `desktop-dash/vitest-setup.md`
- `desktop-dash/webview-api.md`
- `planning/metadata-field-workflow.md`
- `pr-operations/template-synchronization.md`
- `testing/hook-testing.md`
- `architecture/tripwires.md`
- `ci/containerless-ci.md`
- `ci/review-spec-format.md`

### Phase 3:
- 10 additional docs TBD from audit-scan output