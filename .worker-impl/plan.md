# Phase 2: Reconciler Core

**Part of Objective #5934, Steps 2.1-2.3**

## Goal

Create the core reconciliation logic that determines what action to take for an objective with `auto-advance` label. This builds on the Phase 1 LLM-based inference by adding the decision layer that converts inference results into actionable reconciliation actions.

## Overview

The reconciler receives an objective body and determines whether any action should be taken:
- If `infer_next_step()` returns a step, action is "create_plan"
- If no step available (all done, blocked, or in progress), action is "none"
- If inference fails, action is "error"

## Implementation

### Step 2.1: Create `ReconcileAction` type

**File:** `packages/erk-shared/src/erk_shared/objectives/types.py`

Add frozen dataclass:

```python
@dataclass(frozen=True)
class ReconcileAction:
    """Action determined by the reconciler for an objective.

    Attributes:
        action_type: One of "create_plan", "none", "error"
        step_id: Step ID if action_type is "create_plan", None otherwise
        step_description: Step description if action_type is "create_plan"
        phase_name: Phase name if action_type is "create_plan"
        reason: Human-readable explanation of why this action was chosen
    """
    action_type: str  # "create_plan" | "none" | "error"
    step_id: str | None
    step_description: str | None
    phase_name: str | None
    reason: str
```

### Step 2.2: Implement `determine_action()`

**File:** `packages/erk-shared/src/erk_shared/objectives/reconciler.py` (new file)

```python
def determine_action(
    executor: PromptExecutor,
    objective_body: str,
) -> ReconcileAction:
    """Determine what reconciliation action to take for an objective.

    Calls infer_next_step() and converts the result to a ReconcileAction.

    Args:
        executor: PromptExecutor for LLM inference
        objective_body: The full markdown body of the objective issue

    Returns:
        ReconcileAction indicating what should be done
    """
```

Logic:
1. Call `infer_next_step(executor, objective_body)`
2. If result is `InferenceError`: return action_type="error"
3. If result is `NextStepResult` with `has_next_step=True`: return action_type="create_plan" with step details
4. If result is `NextStepResult` with `has_next_step=False`: return action_type="none"

### Step 2.3: Unit tests

**File:** `packages/erk-shared/tests/unit/objectives/test_reconciler.py` (new file)

Test cases:
1. `test_returns_create_plan_when_next_step_available` - FakePromptExecutor returns step, expect "create_plan"
2. `test_returns_none_when_all_steps_complete` - FakePromptExecutor returns no step (all done), expect "none"
3. `test_returns_none_when_all_steps_have_plans` - FakePromptExecutor returns no step (plans in progress), expect "none"
4. `test_returns_error_on_inference_failure` - FakePromptExecutor fails, expect "error"
5. `test_passes_objective_body_to_inference` - Verify objective body is passed through

## Files to Modify/Create

| Action | File |
|--------|------|
| Modify | `packages/erk-shared/src/erk_shared/objectives/types.py` |
| Create | `packages/erk-shared/src/erk_shared/objectives/reconciler.py` |
| Modify | `packages/erk-shared/src/erk_shared/objectives/__init__.py` |
| Create | `packages/erk-shared/tests/unit/objectives/test_reconciler.py` |

## Verification

1. Run unit tests: `pytest packages/erk-shared/tests/unit/objectives/test_reconciler.py -v`
2. Run all objectives tests: `pytest packages/erk-shared/tests/unit/objectives/ -v`
3. Run type checker: `ty packages/erk-shared/`
4. Run linter: `ruff check packages/erk-shared/`

## Related Documentation

- Skills to load: `dignified-python`, `fake-driven-testing`
- Existing pattern: `packages/erk-shared/src/erk_shared/objectives/next_step_inference.py`
- Test pattern: `packages/erk-shared/tests/unit/objectives/test_next_step_inference.py`