---
title: Plan Mismatch Recovery
read_when:
  - "debugging stale plan content in .erk/impl-context/"
  - "plan content doesn't match what's on GitHub"
  - "re-running implementation setup for an existing plan"
tripwires:
  - action: "assuming .erk/impl-context/plan.md always matches the PR body"
    warning: "Plan content can become stale after CI updates rewrite the PR body. Re-run setup-impl-from-pr to refresh local plan content."
    score: 5
---

# Plan Mismatch Recovery

`.erk/impl-context/plan.md` can diverge from the PR body after CI updates or manual edits. This document covers detection and recovery.

## How Staleness Occurs

1. **CI body rewrites:** `ci_update_pr_body.py` regenerates the PR body with an AI-generated summary, changing the body while the local `plan.md` retains the original content.
2. **Manual PR edits:** Editing the PR body on GitHub doesn't propagate to the local `.erk/impl-context/` directory.
3. **Re-dispatch:** Running a plan implementation again after the first attempt modified the plan content.

## Recovery: Re-run setup-impl-from-pr

```bash
erk exec setup-impl-from-pr <pr_number>
```

This fetches fresh plan content from the PR:

1. Reads committed `.erk/impl-context/plan.md` and `ref.json` if they exist on the branch
2. Falls back to extracting plan content from the PR body via `extract_plan_content()`
3. Creates a new branch-scoped `.erk/impl-context/<branch>/` directory with the refreshed content

### Early Exit Safety

<!-- Source: src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py, early exit guard -->

`setup_impl_from_pr` checks for existing impl directories before switching branches. If a matching impl directory already exists (identified by comparing the PR ID), the setup skips branch switching and reuses the existing directory. This prevents abandoning an implementation branch by accidentally checking out the plan branch.

## Detection

Compare plan-ref.json metadata against the actual PR state:

```bash
# Check local plan reference
cat .erk/impl-context/*/ref.json

# Compare against PR
gh pr view <pr_number> --json title,body
```

## Prevention

- Always use `resolve_impl_dir()` discovery instead of hardcoded paths
- The discovery function handles both branch-scoped and flat formats automatically
- After CI updates, the local plan.md is still valid for implementation purposes (it contains the original plan steps)

## Related Documentation

- [Impl-Context Staging Directory](impl-context.md) — Staging directory lifecycle
- [Impl-Folder Discovery Algorithm](../architecture/impl-folder-discovery.md) — How resolve_impl_dir() works
