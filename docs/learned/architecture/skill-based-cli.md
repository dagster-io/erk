---
title: Skill-Based CLI Pattern
read_when:
  - "implementing CLI commands that delegate to Claude skills"
  - "understanding learn command's skill invocation"
  - "designing commands with agent orchestration"
  - "connecting CLI to slash commands"
---

# Skill-Based CLI Pattern

Pattern where a CLI command serves as a lightweight entry point that delegates orchestration to a Claude skill (slash command).

## Overview

The skill-based CLI pattern separates concerns:

- **CLI (Python)**: User interface, argument parsing, data discovery, validation
- **Skill (Markdown)**: Complex orchestration, multi-step workflows, agent coordination

This enables complex agent-driven workflows while keeping CLI code simple.

## Pattern Structure

### 1. CLI Command (Entry Point)

The CLI command handles user-facing concerns:

```python
@click.command()
@click.argument("issue_number", type=int, required=False)
def learn(issue_number: int | None) -> None:
    """Extract insights from plan implementation sessions."""
    # 1. Discover data (sessions, issues, etc.)
    sessions = _discover_sessions(ctx, issue_number)

    # 2. Validate preconditions
    if not sessions:
        raise click.ClickException("No sessions found")

    # 3. Delegate to skill for orchestration
    ctx.claude_executor.execute_interactive(
        worktree_path=repo_root,
        command=f"/erk:learn {issue_number}",
    )
```

### 2. Skill (Orchestration)

The skill handles complex agent workflows:

```markdown
# /erk:learn

## Agent Instructions

### Step 1: Parse Arguments
Extract issue number from `$ARGUMENTS`...

### Step 2: Discover Sessions
Find sessions associated with the plan...

### Step 3: Launch Parallel Agents
Task(subagent_type="session-analyzer", run_in_background=true, ...)
Task(subagent_type="code-diff-analyzer", run_in_background=true, ...)

### Step 4: Synthesize Results
Wait for agents, then synthesize into documentation plan...
```

## Benefits

1. **Separation of concerns** - CLI handles UX, skill handles orchestration
2. **Testability** - CLI logic is unit-testable Python
3. **Flexibility** - Skills can be updated without code deployment
4. **Agent-native** - Skills are natural for multi-agent coordination

## When to Use

Use skill-based CLI when:

- Command requires multi-step agent orchestration
- Workflow involves parallel agent invocation
- Logic is primarily agent-driven (analysis, synthesis)
- Command would benefit from skill's markdown format

Use traditional CLI when:

- Command is purely mechanical (no agent reasoning)
- Response time is critical (skill invocation has overhead)
- Logic is well-defined algorithm (not agent judgment)

## Implementation Details

### CLI Discovery Phase

The CLI discovers and validates data before invoking the skill:

```python
def learn(issue_number: int | None) -> None:
    # Discover associated sessions
    plan = _fetch_plan(ctx, issue_number)
    sessions = _find_sessions_for_plan(ctx, plan)

    # Validate
    if not sessions:
        user_output(ctx, "No sessions found for this plan")
        return

    # Show summary before delegation
    user_output(ctx, f"Found {len(sessions)} sessions to analyze")

    # Delegate to skill
    ctx.claude_executor.execute_interactive(
        worktree_path=repo_root,
        command=f"/erk:learn {issue_number}",
    )
```

### Skill Orchestration Phase

The skill receives control and orchestrates agents:

```markdown
### Step 3: Launch Parallel Agents

Launch analysis agents in parallel:

Task(
  subagent_type: "session-analyzer",
  run_in_background: true,
  prompt: "Analyze session at {session_path}. Write results to {output_path}."
)
```

### Result Handoff

Agents write results to scratch storage for downstream consumption:

```
.erk/scratch/sessions/<session-id>/learn/
├── session-abc123.md      # Session analyzer output
├── diff-analysis.md       # Code diff analyzer output
└── learn-plan.md          # Final synthesized plan
```

## Example: learn Command

The `erk learn` command demonstrates this pattern:

**CLI (`src/erk/cli/commands/learn/learn_cmd.py`)**:

- Parses issue number argument
- Discovers sessions associated with the plan
- Validates session existence
- Invokes `/erk:learn` skill

**Skill (`.claude/commands/erk/learn.md`)**:

- Orchestrates 5 agents across 3 tiers
- Manages file-based coordination between agents
- Synthesizes final documentation plan

## Related Topics

- [Agent Delegation](../planning/agent-delegation.md) - Command-to-agent delegation patterns
- [Agent Coordination via Files](../planning/agent-coordination-via-files.md) - File-based agent coordination
- [Menu Patterns](../tui/menu-patterns.md) - Decision menus in agent workflows
