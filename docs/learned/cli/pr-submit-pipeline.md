---
title: PR Submit Pipeline Architecture
read_when:
  - "modifying the PR submit workflow"
  - "adding new steps to the submit pipeline"
  - "debugging PR submission failures"
  - "understanding SubmitState or SubmitError"
tripwires:
  - action: "adding a new step to the submit pipeline"
    warning: "Each step must return SubmitState | SubmitError. Use dataclasses.replace() for state updates. Add the step to _submit_pipeline() list."
  - action: "mutating SubmitState fields directly"
    warning: "SubmitState is frozen. Use dataclasses.replace(state, field=value) to create new state."
---

# PR Submit Pipeline Architecture

The `erk pr submit` command uses an 8-step linear pipeline with immutable state threading. Each step transforms a frozen `SubmitState` dataclass, with early termination on error.

## Pipeline Overview

```
prepare_state → commit_wip → push_and_create_pr → extract_diff
    → fetch_plan_context → generate_description → enhance_with_graphite → finalize_pr
```

## Pipeline Steps

| Step | Function                | Lines   | Purpose                                                            |
| ---- | ----------------------- | ------- | ------------------------------------------------------------------ |
| 1    | `prepare_state`         | 91–147  | Discovery: repo_root, branch, issue_number, parent_branch          |
| 2    | `commit_wip`            | 150–156 | Commit uncommitted changes if present                              |
| 3    | `push_and_create_pr`    | 159–227 | Push branch + create/find PR (dispatches to Graphite or core flow) |
| 4    | `extract_diff`          | 418–452 | Get PR diff, filter, truncate, write to scratch file               |
| 5    | `fetch_plan_context`    | 455–474 | Load plan context from linked erk-plan issue                       |
| 6    | `generate_description`  | 477–518 | AI-generate PR title and body                                      |
| 7    | `enhance_with_graphite` | 521–583 | Add Graphite stack metadata (optional)                             |
| 8    | `finalize_pr`           | 586–675 | Update PR metadata, add labels, amend commit                       |

## Key Types

### SubmitState (lines 49–71)

```python
@dataclass(frozen=True)
class SubmitState:
    cwd: Path
    branch_name: str | None
    parent_branch: str | None
    trunk_branch: str | None
    pr_number: int | None
    pr_url: str | None
    diff_file: Path | None
    plan_context: str | None
    title: str | None
    body: str | None
    # ... additional fields
```

### SubmitError (lines 74–81)

```python
@dataclass(frozen=True)
class SubmitError:
    phase: str        # Pipeline step name (e.g., "prepare", "push")
    error_type: str   # Machine-readable error code
    message: str      # Human-readable description
    details: str | None
```

### SubmitStep (line 88)

```python
SubmitStep = Callable[[ErkContext, SubmitState], SubmitState | SubmitError]
```

## Graphite-First vs Core Flow

Step 3 (`push_and_create_pr`) dispatches to one of two flows:

- **Graphite-first flow**: When Graphite is authenticated and branch is tracked. Uses `gt submit` which handles push + PR creation atomically, avoiding tracking divergence.
- **Core submit flow**: Uses `git push` + `gh pr create`. The standard path when Graphite is unavailable.

## Discovery Consolidation

Step 1 (`prepare_state`) is the single location for all discovery operations:

- Repository root
- Current branch name
- Parent branch
- Trunk branch
- Issue number (from `.impl/issue.json`)

This prevents discovery duplication across later steps.

## Reference Implementation

`src/erk/cli/commands/pr/submit_pipeline.py` (762 lines)

## Related Documentation

- [PR Submit Workflow Phases](../pr-operations/pr-submit-phases.md) — User-facing phase descriptions
- [State Threading Pattern](../architecture/state-threading-pattern.md) — The underlying architectural pattern
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — SubmitError as discriminated union
