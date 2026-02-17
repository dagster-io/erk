---
title: Linear Pipeline Architecture
read_when:
  - "designing multi-step operations with validation and execution phases"
  - "refactoring complex commands into functional pipelines"
  - "working with land command or similar staged workflows"
tripwires:
  - action: "creating a new complex command with multiple validation steps"
    warning: "Consider two-pipeline pattern: validation pipeline (check preconditions) + execution pipeline (perform operations). Use discriminated unions (State | Error) for pipeline steps. Reference land_pipeline.py as exemplar."
last_audited: "2026-02-17 12:00 PT"
audit_result: clean
---

# Linear Pipeline Architecture

Complex workflows that mix read-only validation with destructive operations benefit from explicit separation. The land command demonstrates a two-pipeline architecture that divides precondition checking from mutation execution, bridging them with a shell script serialization boundary.

## Why Two Pipelines

**The core problem**: Command-line tools need to validate preconditions, gather user confirmations, and perform mutations — but mixing these concerns creates fragile error handling and makes testing difficult.

**The solution**: Split the workflow into two independent pipelines with a serialization boundary:

1. **Validation pipeline**: Read-only operations that check preconditions, resolve values, and gather confirmations. Failures are cheap — no state has been modified.
2. **Execution pipeline**: Mutating operations that assume validation passed. Failures are expensive — rollback may be required.

**Why this matters**:

- **Fail-fast validation**: All precondition checks happen before any mutations. If landing fails due to unresolved comments or missing PRs, the repository state is unchanged.
- **Independent testing**: Each pipeline can be tested in isolation. Validation tests don't need to mock destructive operations. Execution tests can assume validation passed.
- **Clear audit trail**: The serialization boundary makes it obvious where read-only analysis ends and mutations begin.

## The Shell Script Serialization Boundary

<!-- Source: src/erk/cli/commands/land_cmd.py, render_land_execution_script -->

Between validation and execution, the land command generates a shell script. The user must explicitly source this script to proceed with mutations. See `render_land_execution_script()` in `src/erk/cli/commands/land_cmd.py`.

**Why a shell script instead of direct execution?**

1. **Explicit consent**: Sourcing the script is a physical confirmation that validation results are correct. Users can inspect the script before executing.
2. **Resumability**: The script captures all validated state as CLI arguments. If execution fails midway, the user can edit the script and retry without re-running validation.
3. **Separation of privilege**: The validation phase runs with user confirmation enabled. The execution phase runs non-interactively (confirmations already gathered) and can be triggered by shell integration without blocking on stdin.

**Trade-off**: The serialization boundary requires state to be expressible as CLI flags. Complex validation state (like PRDetails objects) must be either re-fetched during execution or baked into the script as positional arguments (PR number, branch name). See the "Baked-in vs User-Controllable Flags" pattern below.

## Pipeline Step Signature

<!-- Source: src/erk/cli/commands/land_pipeline.py, LandStep type alias -->

All pipeline steps share a uniform signature:

```python
LandStep = Callable[[ErkContext, LandState], LandState | LandError]
```

**Why this signature?**

- **Functional composition**: Steps are pure functions that transform state. No hidden side effects except through ErkContext gateways.
- **Discriminated union returns**: Each step returns either success (updated state) or error. The runner short-circuits on the first error without catching exceptions or checking status codes.
- **Immutable state threading**: State is a frozen dataclass. Steps use `dataclasses.replace()` to produce new state, making data flow explicit. See [Land State Threading](land-state-threading.md) for the immutability pattern.

**Anti-pattern**: Don't use exceptions for control flow in pipeline steps. Raising exceptions makes it unclear whether validation failed (expected) or implementation crashed (bug). Return `LandError` for validation failures.

## State Factories and Recomputation

<!-- Source: src/erk/cli/commands/land_pipeline.py, make_initial_state and make_execution_state -->

Two factory functions create initial state for each pipeline. See `make_initial_state()` and `make_execution_state()` in `src/erk/cli/commands/land_pipeline.py`.

**Why separate factories?**

The validation pipeline takes CLI arguments directly. The execution pipeline reconstructs state from shell script arguments. They have different invariants:

- **Validation state**: `force=False` (user can cancel), `dry_run=True|False` (CLI flag), `repo_root` pre-discovered
- **Execution state**: `force=True` (user already confirmed by sourcing script), `dry_run=False` (always mutates), `plan_issue_number` re-derived from branch name

**Intentional recomputation**: Some fields are **not** serialized through the shell script and are recomputed fresh during execution:

- `repo_root` and `main_repo_root`: Re-discovered via `discover_repo_context(ctx.cwd)` in the execution pipeline
- `pr_details`: Re-fetched from GitHub if needed by `merge_pr()` step
- `plan_issue_number`: Re-derived from branch name via `extract_leading_issue_number()`

**Why not serialize everything?**

1. **Stale data risk**: If the user modifies the branch or edits the PR between validation and execution, using cached data would operate on stale state.
2. **Script readability**: Shell scripts with serialized JSON blobs are opaque. Baking only the minimal stable state (PR number, branch name) keeps scripts inspectable.
3. **Flexibility**: The user can manually edit the script to land a different PR or branch without re-running validation.

## Baked-in vs User-Controllable Flags

<!-- Source: src/erk/cli/commands/land_cmd.py, render_land_execution_script -->

The shell script serialization boundary distinguishes two classes of state:

**Baked-in flags** (determined at validation time, static in the script):

- `--worktree-path`: Resolved worktree location
- `--is-current-branch`: Whether landing from that worktree
- `--objective-number`: Linked objective issue number
- `--use-graphite`: Whether Graphite merge is enabled

**User-controllable flags** (passed via `"$@"`, editable at source time):

- `--up`: Navigate upstack (child branch resolved at execution time)
- `--no-pull`: Skip pull after landing
- `--no-delete`: Preserve branch/slot
- `-f`: Force flag (documented but redundant — execute mode is already non-interactive)

**Why this split?**

- Baked-in flags capture **resolved state** that depends on validation results (e.g., which worktree exists, whether an objective is linked). Users shouldn't change these without re-validating.
- User-controllable flags are **navigation preferences** that don't affect validation correctness. Users can safely toggle `--no-delete` or `--no-pull` without invalidating preconditions.

**Decision test**: If changing the flag would invalidate a precondition check (e.g., PR state, unresolved comments), bake it in. If changing the flag only affects post-merge behavior (e.g., branch cleanup, navigation), make it user-controllable.

## Pipeline Step Lists with Caching

<!-- Source: src/erk/cli/commands/land_pipeline.py, _validation_pipeline and _execution_pipeline -->

The pipeline step lists are built by `@cache`-decorated functions. See `_validation_pipeline()` and `_execution_pipeline()` in `src/erk/cli/commands/land_pipeline.py`.

**Why cache the step lists?**

- **Identity stability**: Returning the same tuple object from repeated calls ensures that pipeline composition is deterministic. Useful for debugging when comparing pipeline runs.
- **Idempotency guarantee**: The `@cache` decorator signals that the step list is static and doesn't vary based on runtime state. Attempting to conditionally include steps (e.g., `if use_graphite: include_step`) would fail with a cache hit/miss mismatch, forcing the design toward explicit step logic.

**Common mistake**: Don't cache the runner functions themselves (`run_validation_pipeline`, `run_execution_pipeline`). The runners execute side effects and must run on every call. Only the step list builders are cached.

**Caveat**: State objects must be immutable (frozen dataclasses) for the pipeline pattern to work correctly. Mutable state would allow steps to silently modify earlier results without explicit `dataclasses.replace()` calls, breaking the functional composition model.

## Validation Pipeline Structure

<!-- Source: src/erk/cli/commands/land_pipeline.py, _validation_pipeline and step implementations -->

The validation pipeline runs in `erk land` (the CLI command) and performs read-only operations. See the `_validation_pipeline()` tuple and step implementations in `src/erk/cli/commands/land_pipeline.py`.

**Why this step order?**

1. **`resolve_target`**: Resolve branch/PR/URL argument first. Later steps depend on knowing which PR is being landed.
2. **`validate_pr`**: Check PR state (OPEN, base=trunk, clean working tree). Fail fast before expensive operations like user prompts.
3. **`check_learn_status`**: Check if plan has been learned from. Prompt for async learn trigger. This is read-only but may invoke user interaction, so it runs after basic validation passes.
4. **`gather_confirmations`**: Batch all user confirmations upfront. This centralizes interactive prompts before any mutations.
5. **`resolve_objective`**: Look up linked objective. This is cheap and doesn't require user interaction, so it runs last.

**Anti-pattern**: Don't add steps that perform mutations (e.g., merging the PR, deleting branches) to the validation pipeline. Validation must remain side-effect-free so it can be re-run or aborted without cleanup.

## Execution Pipeline Structure

<!-- Source: src/erk/cli/commands/land_pipeline.py, _execution_pipeline and step implementations -->

The execution pipeline runs in `erk exec land-execute` (invoked by the shell script) and performs mutations. See the `_execution_pipeline()` tuple and step implementations in `src/erk/cli/commands/land_pipeline.py`.

**Why this step order?**

1. **`merge_pr`**: Merge the PR first. If this fails, no other mutations have happened (branch still exists, objective not updated).
2. **`update_objective`**: Update linked objective with the merged PR number. Runs before learn plan update because objective update is more critical.
3. **`update_learn_plan`**: Update parent plan's learn_status if this is a learn plan. This is advisory metadata, so it runs after objective update.
4. **`close_review_pr`**: Close review PR if the plan has one. This is cleanup and runs near the end.
5. **`cleanup_and_navigate`**: Delete branch, unassign slot, navigate to trunk/child. This is the terminal step and may call `SystemExit` to change directories.

**Why this ordering matters**: Early steps (merge, objective update) are high-value mutations that should complete before lower-priority metadata updates (tripwires, review PR). If execution fails partway through, the most important state (PR merged, objective recorded) will have succeeded.

## Relationship to Two-Phase Validation Model

The linear pipeline architecture extends the [two-phase validation model](../cli/two-phase-validation-model.md):

- **Phase 1** (CLI layer): Parse arguments, construct initial state
- **Phase 2** (Validation pipeline): Validate preconditions, resolve values, gather confirmations
- **Phase 3** (Execution pipeline): Perform mutations with validated state

The key difference: Phase 2 and Phase 3 are now explicit pipeline sequences with uniform step signatures, rather than ad-hoc validation checks scattered through a single function.

**Why the pipeline pattern is an evolution**: The two-phase model separates CLI concerns from business logic, but doesn't specify how to structure multi-step business logic. The pipeline pattern fills that gap by imposing functional composition and discriminated union error handling on the business logic layer.

## When to Use This Pattern

**Use the two-pipeline pattern when**:

- Your command has 5+ validation steps that must all pass before any mutations
- You need to gather user confirmations upfront (batch all prompts before mutations)
- Validation failures are common and should be cheap (no rollback required)
- The command modifies shared state (repository, GitHub) and failures are expensive

**Don't use the two-pipeline pattern when**:

- Your command has 1-2 validation steps (inline checks are simpler)
- Validation and execution are interleaved by design (e.g., interactive TUI with live updates)
- The command is idempotent and failures are cheap (no need for separation)

**Decision test**: If you find yourself writing rollback logic to undo partial mutations after validation failures, you need the two-pipeline pattern.

## Related Documentation

- [Land State Threading](land-state-threading.md) - Immutable state management with dataclasses.replace()
- [CLI-to-Pipeline Boundary](cli-to-pipeline-boundary.md) - Separating CLI concerns from business logic
- [Two-Phase Validation Model](../cli/two-phase-validation-model.md) - Foundation pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - State | Error return types
