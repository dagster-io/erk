---
title: Parallel Agent Orchestration Pattern
read_when:
  - "launching multiple agents concurrently"
  - "using Task with run_in_background"
  - "collecting results with TaskOutput"
  - "running agents in parallel"
  - "using file-polling or sentinel files for agent synchronization"
last_audited: "2026-02-05 13:18 PT"
audit_result: clean
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

### `/erk:learn` - Four-Tier Agent Orchestration

The `/erk:learn` workflow demonstrates a four-tier agent orchestration pattern with 7 agents total. All agents use file-polling synchronization (`.done` sentinels) instead of TaskOutput to minimize parent context usage.

**Tier 1: Parallel Analysis** (4 agents, launched simultaneously)

- **SessionAnalyzer**: Processes session XML to extract patterns, errors, corrections (1 agent per session, consolidating multi-part XMLs)
- **CodeDiffAnalyzer**: Analyzes PR diff for new files, functions, gateway methods
- **ExistingDocsChecker**: Scans docs/learned/ for potential conflicts/updates
- **PRCommentAnalyzer**: Extracts documentation opportunities from PR review threads

**Tier 2: Sequential Synthesis** (1 agent, launched after all Tier 1 sentinels exist)

- **DocumentationGapIdentifier**: Combines all Tier 1 outputs, cross-references against existing docs, produces prioritized gap analysis

**Tier 3: Plan Generation** (1 agent, launched after Tier 2 sentinel exists)

- **PlanSynthesizer**: Transforms gap analysis into executable learn plan with draft content starters

**Tier 4: Tripwire Extraction** (1 agent, launched after Tier 3 sentinel exists)

- **TripwireExtractor**: Extracts structured tripwire candidate data from the plan into JSON format

This pattern shows how parallel and sequential orchestration can be combined: independent analysis runs in parallel for speed, then dependent synthesis runs sequentially for correctness. All tiers use file-polling instead of TaskOutput, saving ~107K tokens of parent context.

## Comparison to Agent Delegation

| Aspect     | Agent Delegation            | Parallel Orchestration                 |
| ---------- | --------------------------- | -------------------------------------- |
| Agents     | Single                      | Multiple (2-10)                        |
| Execution  | Blocking (waits for result) | Background (continues immediately)     |
| Collection | Direct return               | File-polling (sentinels) or TaskOutput |
| Use case   | Workflow delegation         | Parallel analysis                      |

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

## File-Polling Synchronization

An alternative to `TaskOutput` for collecting agent results. Instead of pulling agent output into the parent context via `TaskOutput(task_id, block: true)`, agents write a `.done` sentinel file after completing their primary output, and the parent polls for sentinels.

### When to Use File-Polling vs TaskOutput

| Scenario                                              | Use          | Why                                                |
| ----------------------------------------------------- | ------------ | -------------------------------------------------- |
| Large agent count (5+) with file-routed outputs       | File-polling | Avoids pulling N large outputs into parent context |
| Small agent count (1-3) where parent needs the result | TaskOutput   | Simpler, direct access to result                   |
| Agents that write to files (self-write pattern)       | File-polling | Completes the context efficiency pattern           |
| Agents whose output the parent must inspect           | TaskOutput   | Parent needs content for decision-making           |

### Implementation

Each agent spec includes an Output Routing section:

1. Agent writes primary output to `output_path`
2. Agent writes `".done"` to `<output_path>.done`
3. Order is critical: primary file first, then sentinel

The parent polls for sentinels:

```bash
LEARN_AGENTS_DIR="<output-directory>"
TIMEOUT=600
INTERVAL=5
ELAPSED=0

while true; do
  FOUND=$(ls "$LEARN_AGENTS_DIR"/*.done 2>/dev/null | wc -l)
  if [ "$FOUND" -ge "$EXPECTED" ]; then break; fi
  ELAPSED=$((ELAPSED + INTERVAL))
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "TIMEOUT: Only $FOUND of $EXPECTED agents completed"
    break
  fi
  sleep $INTERVAL
done
```

### Context Savings

For the `/erk:learn` workflow with 10 parallel agents + 3 sequential agents, replacing TaskOutput with file-polling saves ~107K tokens of parent context — roughly 55% of the context window.

## Related Documentation

- [Scratch Storage](../planning/scratch-storage.md) - Session-scoped storage for agent outputs
- [Event-Based Progress Pattern](event-progress-pattern.md) - Alternative pattern for single operations
- [Context Efficiency Patterns](context-efficiency.md) - Self-write pattern that file-polling complements
