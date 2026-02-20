# Plan: Add impl-context documentation with PR-leak tripwire

## Context

`.erk/impl-context/` is a temporary staging directory used during draft-PR plan saving. It contains `plan.md` and `ref.json`, committed to the plan branch before the draft PR is created. It should be cleaned up before implementation begins, but if the cleanup fails, it can leak into the final PR. There's no documentation about this directory or a tripwire to catch PR leaks. The user wants a doc explaining impl-context and a tripwire that flags it as a tooling error if it appears in a PR.

## Changes

### 1. Create `docs/learned/planning/impl-context.md`

New doc with:

- **Frontmatter**: title, read_when conditions, tripwire for PR leak
- **What it is**: Temporary staging dir (`.erk/impl-context/`) for draft-PR plan backend
- **Contents**: `plan.md` (plan content) and `ref.json` (plan reference metadata)
- **Creation**: Created in `plan_save.py` during draft-PR plan saving
- **Cleanup**: Removed by `setup_impl_from_issue.py` (reads then `shutil.rmtree`), `plan-implement.md` step 2d, and `plan-implement.yml` CI workflow
- **Tripwire**: If `.erk/impl-context/` appears in a PR diff, leave a review comment telling the user to remove it — this is an erk tooling error (cleanup should have happened automatically)

Key tripwire in frontmatter:

```yaml
tripwires:
  - action: "reviewing a PR that contains .erk/impl-context/ files"
    warning: "Leave a PR comment telling the author to remove .erk/impl-context/. This is an erk tooling error — the directory should have been cleaned up before implementation. Run: git rm -rf .erk/impl-context/ && git commit -m 'Remove leaked impl-context'"
```

### 2. Run `erk docs sync` to regenerate tripwire index

This will pick up the new tripwire from the frontmatter and add it to `docs/learned/planning/tripwires.md`.

## Files to modify

- **Create**: `docs/learned/planning/impl-context.md`
- **Auto-generated** (via `erk docs sync`): `docs/learned/planning/tripwires.md`, `docs/learned/index.md`

## Key source files referenced

- `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py:86` — `IMPL_CONTEXT_DIR` constant
- `src/erk/cli/commands/exec/scripts/plan_save.py:163-176` — creation logic
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py:162-180` — read + cleanup
- `.claude/commands/erk/plan-implement.md:177-182` — manual cleanup step
- `.github/workflows/plan-implement.yml:203-204,400-401` — CI cleanup

## Verification

1. Confirm `docs/learned/planning/impl-context.md` has correct frontmatter structure
2. Run `erk docs sync` and verify the new tripwire appears in `docs/learned/planning/tripwires.md`
3. Grep for the new tripwire text in the regenerated tripwires file
