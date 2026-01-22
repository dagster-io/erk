---
title: Parallel Agent Orchestration Pattern
read_when:
  - "launching multiple agents concurrently"
  - "using Task with run_in_background"
  - "collecting results with TaskOutput"
  - "running agents in parallel"
---

# Parallel Agent Orchestration Pattern

Run multiple Task agents concurrently and synthesize their results. This pattern reduces total time from O(n) to ~O(1) for independent operations.

## Pattern Overview

1. **Launch agents in parallel** with `run_in_background: true`
2. **Collect results** with `TaskOutput(task_id, block: true)`
3. **Store outputs** in scratch storage (optional)
4. **Synthesize** findings into unified result

## When to Use

- **Parallel analysis**: Session analysis + diff analysis running concurrently
- **Bulk operations**: Investigating multiple issues simultaneously
- **Independent work**: Any workflow where tasks don't depend on each other

## Implementation

### Step 1: Launch Agents

Use the Task tool with `run_in_background: true`:

```
Task(
  subagent_type: "Explore",  # or "general-purpose"
  run_in_background: true,
  description: "Brief description",
  prompt: "Detailed prompt with clear output format"
)
```

Launch all agents in a single message with multiple Task tool calls.

### Step 2: Collect Results

Use TaskOutput to retrieve findings from each agent:

```
TaskOutput(task_id: <id-from-step-1>, block: true)
```

Call TaskOutput for each launched agent. Results arrive as agents complete.

### Step 3: Store and Synthesize (Optional)

For workflows that need persistent records:

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/<workflow>/
```

Save agent outputs to this directory for later reference or gist upload.

### Step 4: Combine Results

Build a unified result from individual agent findings:

- Aggregate into summary tables
- Identify patterns across results
- Present consolidated findings to user

## Examples in Codebase

### `/local:bulk-replan` - Parallel Issue Investigation

Launches up to 10 Explore agents simultaneously to investigate erk-plan issues. Each agent:

- Fetches issue details via REST API
- Searches codebase for implementation evidence
- Returns structured status (IMPLEMENTED, OBSOLETE, NEEDS_FRESH_PLAN, etc.)

Results are collected and presented in a summary table for batch approval.

### `/erk:learn` - Parallel Session Analysis

Launches two agents concurrently:

- **Session analyzer**: Processes Claude Code session logs for insights
- **Code diff analyzer**: Reviews PR changes for documentation needs

Both run in background; results are synthesized into a documentation plan.

## Comparison to Agent Delegation

| Aspect     | Agent Delegation            | Parallel Orchestration             |
| ---------- | --------------------------- | ---------------------------------- |
| Agents     | Single                      | Multiple (2-10)                    |
| Execution  | Blocking (waits for result) | Background (continues immediately) |
| Collection | Direct return               | TaskOutput                         |
| Use case   | Workflow delegation         | Parallel analysis                  |

## Best Practices

### Prompt Design

Each agent needs a clear, self-contained prompt:

- Include all necessary context (the agent has no prior context)
- Specify exact output format for easy parsing
- Define clear success/failure criteria

### Rate Limit Awareness

Limit to ~10 parallel agents to avoid rate limits. For bulk operations with more items, process in batches.

### Error Handling

- If an agent fails or times out, skip that item and note in summary
- Don't let one failure block others
- Report partial results with clear indication of what failed

### Result Format

Specify structured output in prompts for easy parsing:

```
**Output Format:**

ISSUE: #<number>
STATUS: <IMPLEMENTED|OBSOLETE|NEEDS_REPLAN>
EVIDENCE: <supporting evidence>
```

## Related Documentation

- [Scratch Storage](../planning/scratch-storage.md) - Session-scoped storage for agent outputs
- [Event-Based Progress Pattern](event-progress-pattern.md) - Alternative pattern for single operations
