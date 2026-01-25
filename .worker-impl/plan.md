# Plan: Phase 1 - Roadmap Parser

Part of Objective #5934, Phase 1 (Steps 1.1-1.4)

## Goal

Create a reusable module that parses objective roadmap tables and determines step readiness. This is the foundation for the reconciliation loop.

## Implementation

### 1. Create Package Structure

**New package:** `packages/erk-shared/src/erk_shared/objectives/`

```
objectives/
├── __init__.py           # Package exports
├── roadmap_parser.py     # Parsing logic
└── (future: reconciler.py, plan_generation.py)
```

### 2. Define Frozen Dataclasses

**File:** `packages/erk-shared/src/erk_shared/objectives/roadmap_parser.py`

```python
from dataclasses import dataclass
from typing import Literal

StepStatus = Literal["pending", "done", "blocked", "skipped", "plan-in-progress"]

@dataclass(frozen=True)
class RoadmapStep:
    """A single step from an objective roadmap table."""
    step_id: str           # "1.1", "1A.2", "2.1"
    description: str
    status: StepStatus
    pr_number: int | None      # Set when done (merged PR)
    plan_number: int | None    # Set when plan-in-progress

@dataclass(frozen=True)
class RoadmapParseResult:
    """Result of parsing roadmap tables from an objective body."""
    steps: tuple[RoadmapStep, ...]  # Immutable tuple, not list
    errors: tuple[str, ...]         # Parse warnings/errors
```

### 3. Implement `parse_roadmap_tables()`

**Parse markdown tables with pattern:**
```
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing    | pending | |
| 1.2  | Do other    | done    | #123 |
```

**PR column parsing rules:**
- Empty/whitespace → `pending`, pr_number=None, plan_number=None
- `#123` or `#123` → `done`, pr_number=123, plan_number=None
- `plan #456` → `plan-in-progress`, pr_number=None, plan_number=456

**Status column override:** If Status column contains "blocked" or "skipped", use that regardless of PR column.

**Implementation approach:**
1. Find all markdown tables (look for `| Step |` header pattern)
2. Parse each row, extract Step, Description, Status, PR columns
3. Determine effective status from PR column first, then Status column override
4. Collect parse errors for malformed rows (don't fail, just warn)

### 4. Implement `get_next_actionable_step()`

```python
def get_next_actionable_step(
    steps: tuple[RoadmapStep, ...],
) -> RoadmapStep | None:
    """Find the first step ready for planning.

    Returns the first step where:
    - Previous step (if any) is done
    - This step is pending (not done, not blocked, not plan-in-progress)

    Returns None if no actionable step found.
    """
```

**Logic:**
1. If first step is pending → return it (no previous step required)
2. Iterate through steps in order
3. Track if previous step was "done"
4. Return first pending step whose previous step was done

### 5. Unit Tests

**File:** `packages/erk-shared/tests/unit/objectives/test_roadmap_parser.py`

**Test cases:**

1. **Basic parsing:**
   - Parse simple table with pending steps
   - Parse table with mixed statuses (pending, done, blocked)
   - Parse table with PR numbers

2. **PR column formats:**
   - Empty → pending
   - `#123` → done with pr_number=123
   - `plan #456` → plan-in-progress with plan_number=456
   - Malformed → pending with warning

3. **Status column override:**
   - `blocked` in Status column overrides PR column inference
   - `skipped` in Status column overrides PR column inference

4. **Multiple tables:**
   - Parse objective with multiple phase tables
   - Steps returned in document order

5. **Edge cases:**
   - Empty body → empty steps, no error
   - No tables → empty steps, no error
   - Malformed table → partial parse with errors

6. **`get_next_actionable_step()` logic:**
   - First step pending → returns first step
   - First step done, second pending → returns second step
   - First step plan-in-progress → returns None (wait for plan)
   - All done → returns None
   - Blocked step skipped

## Files to Create/Modify

| Action | File |
|--------|------|
| Create | `packages/erk-shared/src/erk_shared/objectives/__init__.py` |
| Create | `packages/erk-shared/src/erk_shared/objectives/roadmap_parser.py` |
| Create | `packages/erk-shared/tests/unit/objectives/__init__.py` |
| Create | `packages/erk-shared/tests/unit/objectives/test_roadmap_parser.py` |

## Verification

1. **Unit tests pass:**
   ```bash
   pytest packages/erk-shared/tests/unit/objectives/test_roadmap_parser.py -v
   ```

2. **Type check passes:**
   ```bash
   ty check packages/erk-shared/src/erk_shared/objectives/
   ```

3. **Manual validation:** Parse the actual objective #5934 body and verify steps extracted correctly.

## Related Documentation

- Skills: `dignified-python`, `fake-driven-testing`
- Pattern reference: `packages/erk-shared/src/erk_shared/github/metadata_blocks.py` (regex parsing)
- Pattern reference: `packages/erk-shared/src/erk_shared/plan_store/types.py` (frozen dataclasses)