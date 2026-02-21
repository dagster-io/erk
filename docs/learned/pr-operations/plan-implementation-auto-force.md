---
title: Plan Implementation Auto-Force Push
read_when:
  - "debugging why erk pr submit force-pushed when --force was not specified"
  - "understanding force-push behavior for plan implementation branches"
  - "working with the submit pipeline for plan branches"
---

# Plan Implementation Auto-Force Push

`erk pr submit` automatically applies force-push when the current branch is a plan implementation branch. This is expected behavior, not a bug.

## Detection

Auto-force is triggered when `state.issue_number is not None`, which is set when `.impl/` is valid and contains issue tracking metadata.

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _run_phase1_graphite_submit -->

See `_run_phase1_graphite_submit()` in `src/erk/cli/commands/pr/submit_pipeline.py`.

## Why It's Safe

Plan implementation branches always diverge from remote because `erk implement` creates them fresh from trunk and commits `.impl/` locally. Force-push is expected and harmless — there is no remote history worth preserving on a fresh implementation branch.

## User Experience

When auto-force triggers, the CLI prints:

```
   Auto-forcing: plan implementation branch
```

This message appears only when the branch has diverged from remote AND `--force` was not already specified explicitly.

## Code Location

`src/erk/cli/commands/pr/submit_pipeline.py` — Phase 1 (Graphite Submit), lines ~204–236.

## When It Does Not Apply

Regular feature branches (no `.impl/` folder, or `.impl/` without issue tracking) are **not** auto-forced. Only branches where `state.issue_number is not None` receive this treatment.
