---
title: Decision Menu Patterns
read_when:
  - "implementing interactive decision menus"
  - "using AskUserQuestion for multi-choice prompts"
  - "understanding hook-based decision flow"
  - "designing agent-driven workflow decision points"
---

# Decision Menu Patterns

Patterns for implementing interactive decision menus in agent-driven workflows, using hooks and the AskUserQuestion tool.

## Overview

Decision menus allow agents to present choices to users at workflow decision points. The pattern uses:

1. **Hooks** - Intercept tool calls to inject decision prompts
2. **Marker files** - Track user decisions across hook invocations
3. **AskUserQuestion** - Present structured choices to users

## Hook-Based Decision Flow

### Flow Diagram

```
Agent attempts action
       ↓
Hook intercepts (PreToolUse)
       ↓
Hook checks marker files
       ↓
┌──────┴──────┐
│  Decision   │
│  needed?    │
└──────┬──────┘
    yes │ no
        ↓  ↓
Block + prompt  Allow action
        ↓
User responds (AskUserQuestion)
        ↓
Agent creates marker file
        ↓
Agent retries action
        ↓
Hook allows (marker exists)
```

### Implementation

#### 1. Hook Input/Output (Pure Functions)

Use frozen dataclasses for testable hook logic:

```python
@dataclass(frozen=True)
class HookInput:
    session_id: str | None
    implement_now_marker_exists: bool
    plan_saved_marker_exists: bool
    plan_file_path: Path | None
    plan_title: str | None

@dataclass(frozen=True)
class HookOutput:
    action: ExitAction  # ALLOW or BLOCK
    message: str
    delete_implement_now_marker: bool
```

#### 2. Decision Logic

```python
def determine_hook_action(input: HookInput) -> HookOutput:
    """Pure function: determine action based on input state."""
    # Already decided - allow
    if input.implement_now_marker_exists:
        return HookOutput(action=ExitAction.ALLOW, message="", delete_marker=True)

    if input.plan_saved_marker_exists:
        return HookOutput(action=ExitAction.ALLOW, message="", delete_marker=False)

    # Need decision - block with prompt
    return HookOutput(
        action=ExitAction.BLOCK,
        message=_build_decision_prompt(input),
        delete_marker=False,
    )
```

#### 3. Blocking Message with AskUserQuestion

```python
def _build_decision_prompt(input: HookInput) -> str:
    return f"""Plan "{input.plan_title}" is ready.

Use the AskUserQuestion tool to ask:

"Would you like to save this plan to GitHub for later, or implement it now?"

Options:
1. Save to GitHub (creates issue, can implement later)
2. Implement now (creates branch and starts implementation)

Based on the user's response:
- If "save": Run `/erk:plan-save`
- If "implement": Create marker file then retry ExitPlanMode
"""
```

## Marker File Pattern

Marker files track decisions across hook invocations:

```
.erk/scratch/sessions/<session-id>/
├── implement-now.marker    # User chose to implement
├── plan-saved.marker       # User chose to save
└── incremental-plan.marker # Skip prompt, auto-implement
```

### Creating Markers

```python
def create_marker(session_id: str, marker_type: str) -> None:
    """Create a marker file for decision tracking."""
    marker_path = get_scratch_dir(session_id) / f"{marker_type}.marker"
    marker_path.touch()
```

### Checking Markers

```python
def marker_exists(session_id: str, marker_type: str) -> bool:
    """Check if a marker file exists."""
    marker_path = get_scratch_dir(session_id) / f"{marker_type}.marker"
    return marker_path.exists()
```

## Decision Menu Examples

### Plan Mode Exit Decision

```markdown
Use AskUserQuestion to ask:

"Plan is ready. What would you like to do?"

Options:

1. **Save to GitHub** - Create issue for later implementation
2. **Implement now** - Start implementation immediately
3. **Cancel** - Discard plan
```

### Objective Structure Selection

```markdown
Use AskUserQuestion to ask:

"What structure should this objective use?"

Options:

1. **Steelthread** - End-to-end vertical slice first
2. **Linear** - Sequential phases building on each other
3. **Single** - One focused deliverable
4. **Custom** - Define your own structure
```

### Navigation After Landing

```markdown
Use AskUserQuestion to ask:

"PR landed successfully. Where would you like to go?"

Options:

1. **Stay here** - Remain in current worktree
2. **Go to child branch** - Navigate to dependent branch
3. **Go to main** - Return to main worktree
```

## Design Guidelines

### Keep Decisions Focused

Each decision point should have:

- 2-4 clear options
- Brief description of each option
- Clear consequence of each choice

### Use Marker Files for State

Don't rely on conversation context for decision state. Marker files provide:

- Persistence across hook invocations
- Testability (check file existence)
- Recovery from interruptions

### Provide Default Actions

When appropriate, suggest a default:

```markdown
Options:

1. **Implement now** (recommended)
2. Save to GitHub
```

### Handle Edge Cases

Consider what happens when:

- User provides unexpected input
- Session is interrupted mid-decision
- Multiple decisions are needed in sequence

## Testing Decision Flows

Test the pure decision logic separately from hook mechanics:

```python
def test_hook_allows_when_marker_exists() -> None:
    """Hook should allow action when implement-now marker exists."""
    input = HookInput(
        session_id="abc123",
        implement_now_marker_exists=True,
        plan_saved_marker_exists=False,
        plan_file_path=Path("/tmp/plan.md"),
        plan_title="Test Plan",
    )

    output = determine_hook_action(input)

    assert output.action == ExitAction.ALLOW


def test_hook_blocks_when_no_decision() -> None:
    """Hook should block and prompt when no decision made."""
    input = HookInput(
        session_id="abc123",
        implement_now_marker_exists=False,
        plan_saved_marker_exists=False,
        plan_file_path=Path("/tmp/plan.md"),
        plan_title="Test Plan",
    )

    output = determine_hook_action(input)

    assert output.action == ExitAction.BLOCK
    assert "AskUserQuestion" in output.message
```

## Related Topics

- [Skill-Based CLI Pattern](../architecture/skill-based-cli.md) - CLI commands with agent orchestration
- [Scratch Storage](../planning/scratch-storage.md) - Session-scoped file storage
- [Agent Coordination via Files](../planning/agent-coordination-via-files.md) - File-based agent coordination
