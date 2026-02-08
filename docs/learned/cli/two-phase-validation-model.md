---
title: Two-Phase Validation Model for Complex Commands
read_when:
  - "implementing commands with multiple confirmations"
  - "designing commands that perform destructive mutations"
  - "working on erk land or similar multi-step commands"
tripwires:
  - action: "implementing a command with multiple user confirmations"
    warning: "Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Inline confirmations cause partial state on decline."
last_audited: "2026-02-07 18:25 PT"
audit_result: edited
---

# Two-Phase Validation Model

Complex CLI commands that perform multiple mutations should use a two-phase model.

## Phase 1: Validation

- Gather ALL user confirmations upfront
- Perform all precondition checks
- **Type narrowing**: Use `EnsureIdeal` to narrow discriminated unions (e.g., `PRDetails | PRNotFound` → `PRDetails`)
- NO mutations occur in this phase
- Collect all decisions into confirmation objects

## Phase 2: Execution

- Perform mutations in sequence
- Use pre-gathered confirmations
- No user interaction in this phase

## Why This Matters

Partial mutations are dangerous. If a command:

1. Merges a PR
2. Asks for confirmation to delete worktree
3. User says no

The PR is already merged but the worktree remains - an inconsistent state.

## Implementation Pattern

Create frozen dataclasses to capture confirmation results:

```python
@dataclass(frozen=True)
class CleanupConfirmation:
    """Pre-gathered cleanup confirmation result.

    Captures user's response to cleanup prompt during validation phase,
    allowing all confirmations to be batched upfront before any mutations.
    """

    proceed: bool  # True = proceed with cleanup, False = preserve
```

Gather confirmations during validation, then thread them through to execution:

1. Validation phase calls `_gather_cleanup_confirmation()` - prompts user
2. Result stored in context object (`cleanup_confirmed` field)
3. Execution phase uses stored result - no additional prompts

## Reference Implementation

See `CleanupConfirmation` and `_gather_cleanup_confirmation()` in `src/erk/cli/commands/land_cmd.py`.

Key functions:

- `_gather_cleanup_confirmation()`: Prompts during validation
- `_cleanup_and_navigate()`: Uses pre-gathered confirmation during execution

## EnsureIdeal as Type Narrowing

The validation phase often includes type narrowing from discriminated unions. `EnsureIdeal` provides a concrete implementation of type narrowing for CLI commands:

```python
# Phase 1: Validation - narrow types from unions
pr_details = EnsureIdeal.unwrap_pr(
    ctx.github.get_pr_for_branch(repo_root, branch),
    f"No pull request found for branch '{branch}'."
)
# Type narrowed: PRDetails | PRNotFound → PRDetails

# Phase 2: Execution - use narrowed type
ctx.github.merge_pr(repo_root, pr_details.number)
```

See [EnsureIdeal Pattern](ensure-ideal-pattern.md) for complete documentation.

## Extended Example: Land Command Pipeline

The land command implements an extended two-phase model with separate validation and execution pipelines. This demonstrates how the two-phase pattern scales to complex workflows with multiple steps.

### Validation Pipeline (5 Steps)

**Purpose**: Check preconditions, resolve values, no mutations

Steps (see `_validation_pipeline()` in `land_pipeline.py`):

1. `resolve_target` -- resolve PR number, fetch details, type-narrow via `EnsureIdeal.unwrap_pr()`
2. `validate_pr` -- check PR state is OPEN, base is trunk, unresolved comments
3. `check_learn_status` -- check learn plan status and prompt if needed
4. `gather_confirmations` -- batch all cleanup confirmations upfront via `_gather_cleanup_confirmation()`
5. `resolve_objective` -- look up linked objective for the branch

Each step has signature `(ErkContext, LandState) -> LandState | LandError`. The runner short-circuits on the first `LandError`.

**Key characteristics**:

- Read-only operations (no mutations)
- Type narrowing (PR number resolution, branch detection)
- Fails fast on first error
- Returns enriched state with validated values

### Execution Pipeline (6 Steps)

**Purpose**: Perform mutations with validated state

Steps (see `_execution_pipeline()` in `land_pipeline.py`):

1. `merge_pr` -- merge PR via Graphite or GitHub API
2. `update_objective` -- update linked objective if present
3. `update_learn_plan` -- update parent plan's learn_status if this is a learn plan
4. `promote_tripwires` -- extract and promote tripwire candidates from learn plans
5. `close_review_pr` -- close review PR if plan has one
6. `cleanup_and_navigate` -- dispatch cleanup by type, navigate to trunk or child branch

Same step signature and short-circuit behavior as the validation pipeline.

**Key characteristics**:

- Mutating operations (modifies repository state)
- Assumes validation passed (no type narrowing needed)
- Steps may have dependencies on previous step results
- No user interaction (all confirmations pre-gathered)

### Benefits of Pipeline Separation

1. **Clear boundaries**: Validation pipeline is read-only, execution pipeline mutates
2. **Independent testability**: Can test validation without side effects
3. **Resumability**: Execution pipeline can be serialized to shell script and re-executed
4. **Composability**: Each pipeline is a sequence of steps with same signature

### State Threading

State objects (`LandState`) thread through both pipelines:

- **Validation pipeline**: Enriches state with resolved values (PR number, target branch)
- **Execution pipeline**: Uses validated state, adds execution results

See [Land State Threading](../architecture/land-state-threading.md) for immutable state management patterns.

### Reference Implementation

**File**: `src/erk/cli/commands/land_pipeline.py` (706 lines, 20 functions)

**Cross-references**:

- [Linear Pipelines](../architecture/linear-pipelines.md) - Two-pipeline pattern architecture
- [CLI-to-Pipeline Boundary](../architecture/cli-to-pipeline-boundary.md) - Separating CLI from business logic
- [Learn Plan Land Flow](learn-plan-land-flow.md) - Learn-plan-specific execution steps

## Related Topics

- [EnsureIdeal Pattern](ensure-ideal-pattern.md) - Type narrowing from discriminated unions
- [CI-Aware Commands](ci-aware-commands.md) - Commands must skip prompts in CI
- [Output Styling Guide](output-styling.md) - Using `ctx.console.confirm()` for testability
