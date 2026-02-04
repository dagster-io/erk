---
title: Objective Summary Format
read_when:
  - working with objective-next-plan command
  - implementing Task agent delegation for objective context
  - parsing objective summary JSON output
tripwires:
  - action: "parsing objective summary output without structured format"
    warning: "Use the documented JSON format with OBJECTIVE, STATUS, ROADMAP, PENDING_STEPS, and RECOMMENDED sections. Status mapping uses pending/done/in_progress/blocked/skipped."
---

# Objective Summary Format

This document specifies the structured output format for Task agent delegation in objective context fetching, specifically used by the `objective-next-plan` command.

## Purpose

The objective summary format enables:

1. **Token optimization** - Task agents fetch and structure objective data, reducing token usage in parent context
2. **Consistent parsing** - Structured JSON output enables reliable field extraction
3. **Status translation** - Maps display statuses (ACTIVE/PLANNING/COMPLETED) to workflow statuses (pending/done/in_progress/blocked/skipped)

## Output Format

Task agents delegated for objective context must return JSON with these sections:

### Required Sections

#### 1. OBJECTIVE

```json
{
  "OBJECTIVE": {
    "title": "Implement feature X",
    "issue_number": 1234,
    "description": "Full objective description..."
  }
}
```

**Fields:**

- `title` (string) - Objective title from GitHub issue
- `issue_number` (integer) - GitHub issue number
- `description` (string) - Full objective body text

#### 2. STATUS

```json
{
  "STATUS": "ACTIVE"
}
```

**Valid values:**

- `ACTIVE` - Objective is in progress
- `PLANNING` - Objective is being planned
- `COMPLETED` - Objective is finished

**Status mapping to workflow statuses:**

| Display Status | Maps To     |
| -------------- | ----------- |
| ACTIVE         | in_progress |
| PLANNING       | pending     |
| COMPLETED      | done        |
| (none)         | pending     |
| BLOCKED        | blocked     |
| SKIPPED        | skipped     |

#### 3. ROADMAP

```json
{
  "ROADMAP": [
    {
      "step": "Design API endpoints",
      "status": "done",
      "pr": 1235,
      "notes": "Completed in PR #1235"
    },
    {
      "step": "Implement auth layer",
      "status": "in_progress",
      "pr": null,
      "notes": "Currently working on"
    }
  ]
}
```

**Table format:**

Each roadmap entry has:

- `step` (string) - Description of the roadmap step
- `status` (string) - One of: pending, done, in_progress, blocked, skipped
- `pr` (integer | null) - Associated PR number, or null if not yet created
- `notes` (string) - Additional context or notes

#### 4. PENDING_STEPS

```json
{
  "PENDING_STEPS": [
    "Implement auth layer",
    "Add integration tests",
    "Write documentation"
  ]
}
```

**Fields:**

- Array of strings representing steps not yet completed
- Derived from ROADMAP entries with status != "done"

#### 5. RECOMMENDED

```json
{
  "RECOMMENDED": {
    "next_step": "Implement auth layer",
    "reason": "Critical path dependency for remaining work"
  }
}
```

**Fields:**

- `next_step` (string) - Recommended next action
- `reason` (string) - Rationale for the recommendation

## Task Agent Prompt Structure

When delegating objective context fetching to a Task agent, use this pattern:

```markdown
Fetch objective context for issue #1234 and format as JSON with the following sections:

1. OBJECTIVE - title, issue_number, description
2. STATUS - ACTIVE, PLANNING, or COMPLETED
3. ROADMAP - table with step, status, pr, notes columns
4. PENDING_STEPS - array of incomplete steps
5. RECOMMENDED - next_step and reason

Map status values:

- ACTIVE → in_progress
- PLANNING → pending
- COMPLETED → done

Use haiku model for token efficiency.
```

## Model Selection

- **Recommended model**: `haiku`
- **Rationale**: Objective data fetching is mechanical work (fetch, parse, format). Haiku provides sufficient capability at lower token cost.

## Token Savings

Example from `objective-next-plan` refactor (#6698):

- **Before** (sequential LLM turns): ~3 turns × 1500 tokens = ~4500 tokens
- **After** (Task agent delegation): ~1200 tokens (agent execution) + 800 tokens (result consumption) = ~2000 tokens
- **Savings**: ~55% token reduction

## Related Documentation

- [Token Optimization Patterns](../planning/token-optimization-patterns.md) - Task agent delegation pattern
- [Objective Commands](../cli/objective-commands.md) - Commands that consume this format
- [Agent Orchestration Safety Patterns](../planning/agent-orchestration-safety.md) - File-based agent output pattern

## Code References

- Implementation: `src/erk/cli/commands/objective/next_plan_cmd.py`
- Task agent prompt: Search for `Task(subagent_type='general-purpose'` in next_plan_cmd.py
