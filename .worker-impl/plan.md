# Plan: Phase 1 - LLM-Based Roadmap Inference

Part of Objective #5934, Phase 1 (revised approach)

## Goal

Use Claude Haiku to infer the next actionable step from an objective's roadmap. This replaces the regex-based parsing approach with LLM inference for flexibility and robustness.

## Design Decision

**LLM-based inference** instead of regex parsing because:
- Handles format variations naturally
- Understands context (what "done" means, what "blocked" means)
- More maintainable than brittle regex patterns
- Cost is acceptable (~$0.001 per inference, runs every 15 min per objective)

## Implementation

### 1. Create Package Structure

**New package:** `packages/erk-shared/src/erk_shared/objectives/`

```
objectives/
├── __init__.py
├── types.py              # Frozen dataclasses
└── next_step_inference.py  # LLM-based step extraction
```

### 2. Define Types

**File:** `packages/erk-shared/src/erk_shared/objectives/types.py`

```python
from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class NextStepResult:
    """Result of inferring the next actionable step from an objective."""
    has_next_step: bool
    step_id: str | None        # e.g., "1.1", "2A.1"
    step_description: str | None
    phase_name: str | None     # e.g., "Phase 1: Roadmap Parser"
    reason: str                # Why this step (or why no step)

@dataclass(frozen=True)
class InferenceError:
    """Error during LLM inference."""
    message: str
```

### 3. Implement LLM Inference

**File:** `packages/erk-shared/src/erk_shared/objectives/next_step_inference.py`

```python
from erk_shared.prompt_executor.abc import PromptExecutor, PromptResult

INFERENCE_PROMPT = '''
Analyze this objective and determine the next actionable step.

Rules for determining the next step:
1. A step is "done" if its PR column contains "#" followed by a number (e.g., "#5892")
2. A step has a "plan in progress" if its PR column contains "plan #" (e.g., "plan #5935")
3. A step is "blocked" if its Status column says "blocked"
4. A step is "pending" if its PR column is empty and Status is not blocked

Find the FIRST step where:
- The previous step (if any) is done
- This step is pending (not done, not blocked, not plan-in-progress)

Respond in this exact format:
NEXT_STEP: <yes or no>
STEP_ID: <step id like "1.1" or "2A.1", or "none">
DESCRIPTION: <step description, or "none">
PHASE: <phase name, or "none">
REASON: <brief explanation>

OBJECTIVE:
{objective_body}
'''

def infer_next_step(
    executor: PromptExecutor,
    objective_body: str,
) -> NextStepResult | InferenceError:
    """Use Haiku to infer the next actionable step."""
    prompt = INFERENCE_PROMPT.format(objective_body=objective_body)

    result = executor.execute_prompt(prompt, model="haiku")

    if not result.success:
        return InferenceError(message=result.error or "Unknown error")

    return _parse_inference_response(result.output)

def _parse_inference_response(output: str) -> NextStepResult:
    """Parse the structured text response from Haiku."""
    # Extract fields from response using simple line parsing
    # (implementation details)
```

### 4. Wire Into Reconciler

The reconciler will call:
```python
result = infer_next_step(ctx.prompt_executor, objective_body)
if isinstance(result, InferenceError):
    log_warning(f"Inference failed: {result.message}")
    return
if result.has_next_step:
    create_plan_for_step(result)
```

### 5. Unit Tests with FakePromptExecutor

**File:** `packages/erk-shared/tests/unit/objectives/test_next_step_inference.py`

Use `FakePromptExecutor` to test response parsing without actual API calls:

```python
def test_parses_next_step_response():
    fake_executor = FakePromptExecutor(responses=[
        PromptResult(success=True, output="""
NEXT_STEP: yes
STEP_ID: 2.1
DESCRIPTION: Create ReconcileAction type
PHASE: Phase 2: Reconciler Core
REASON: Phase 1 steps are done (#5936), Phase 2 is pending
""", error=None)
    ])

    result = infer_next_step(fake_executor, "...")
    assert result.has_next_step
    assert result.step_id == "2.1"

def test_handles_no_next_step():
    fake_executor = FakePromptExecutor(responses=[
        PromptResult(success=True, output="""
NEXT_STEP: no
STEP_ID: none
DESCRIPTION: none
PHASE: none
REASON: All steps have plans in progress or are complete
""", error=None)
    ])

    result = infer_next_step(fake_executor, "...")
    assert not result.has_next_step

def test_handles_inference_error():
    fake_executor = FakePromptExecutor(responses=[
        PromptResult(success=False, output="", error="Rate limited")
    ])

    result = infer_next_step(fake_executor, "...")
    assert isinstance(result, InferenceError)
```

## Files to Create/Modify

| Action | File |
|--------|------|
| Create | `packages/erk-shared/src/erk_shared/objectives/__init__.py` |
| Create | `packages/erk-shared/src/erk_shared/objectives/types.py` |
| Create | `packages/erk-shared/src/erk_shared/objectives/next_step_inference.py` |
| Create | `packages/erk-shared/tests/unit/objectives/__init__.py` |
| Create | `packages/erk-shared/tests/unit/objectives/test_next_step_inference.py` |

## Key Files to Reference

| Purpose | File |
|---------|------|
| PromptExecutor ABC | `packages/erk-shared/src/erk_shared/prompt_executor/abc.py` |
| FakePromptExecutor | `packages/erk-shared/src/erk_shared/prompt_executor/fake.py` |
| Real implementation | `packages/erk-shared/src/erk_shared/prompt_executor/real.py` |
| Similar LLM extraction | `packages/erk-shared/src/erk_shared/learn/extraction/llm_distillation.py` |

## Verification

1. **Unit tests pass:**
   ```bash
   pytest packages/erk-shared/tests/unit/objectives/ -v
   ```

2. **Type check passes:**
   ```bash
   ty check packages/erk-shared/src/erk_shared/objectives/
   ```

3. **Manual test with real objective:**
   ```python
   from erk_shared.prompt_executor.real import RealPromptExecutor
   from erk_shared.objectives.next_step_inference import infer_next_step

   executor = RealPromptExecutor()
   result = infer_next_step(executor, objective_5934_body)
   print(result)
   ```

## Note on In-Flight Plan #5935

The regex-based plan (#5935) is currently being implemented by the remote worker. Options:
1. Let it complete - we can supersede it with this approach
2. The PR can be closed without merging

This LLM-based approach is the preferred path forward.