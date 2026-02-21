# Skip CI for Plan-Only and One-Shot Prompt Branches

## Context

CI runs on every push to every branch. For branches that only contain plan metadata (`.erk/impl-context/`) or one-shot prompts (`.worker-impl/`), this wastes CI minutes and clutters the checks column in `erk dash`. These branches have no code to lint, test, or type-check.

## Change

Add `paths-ignore` and `branches-ignore` to the push trigger in `.github/workflows/ci.yml`.

### File: `.github/workflows/ci.yml` (lines 3-5)

From:
```yaml
on:
  push:
    branches-ignore: []
```

To:
```yaml
on:
  push:
    branches-ignore:
      - "planned/review-*"
    paths-ignore:
      - '.erk/impl-context/**'
      - '.worker-impl/**'
```

### How it works

| Push type | Files changed | CI runs? | Why |
|---|---|---|---|
| Plan-only (`planned/` branch) | `.erk/impl-context/plan.md`, `ref.json` | No | All paths match `paths-ignore` |
| One-shot prompt | `.worker-impl/prompt.md` | No | All paths match `paths-ignore` |
| Learn branch (`learn/*`) | `.erk/impl-context/*` | No | All paths match `paths-ignore` |
| Plan-review branch | `PLAN-REVIEW-*.md` | No | Branch matches `branches-ignore` |
| Implementation push | `src/`, `tests/`, etc. | Yes | Code paths don't match ignore |
| Empty CI trigger commit | (no files) | Yes | Empty commits bypass `paths-ignore` |

The `pull_request` and `workflow_dispatch` triggers are unaffected.

### Why not `branches-ignore` for `planned/*`?

`planned/` branches are used for both plan-only AND implemented code. When implementation pushes code to a `planned/` branch, CI must run. `paths-ignore` correctly distinguishes: plan-only pushes (only `.erk/impl-context/` files) skip CI, while implementation pushes (containing source code) trigger CI.

## Verification

1. Push a plan-only branch and confirm no CI workflow is triggered
2. Push a one-shot prompt branch and confirm no CI workflow is triggered
3. Push implementation code to a `planned/` branch and confirm CI runs
4. Confirm `pull_request` events still work (draft check, label check, check-submission)
