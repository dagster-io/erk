---
title: Token Optimization Patterns
last_audited: "2026-02-04 05:48 PT"
audit_result: clean
read_when:
  - "designing multi-agent workflows"
  - "handling large data payloads in agent orchestration"
  - "experiencing context bloat from fetching multiple documents"
  - "building consolidation or aggregation commands"
tripwire:
  trigger: "Before fetching N large documents into parent agent context"
  action: "Read [Token Optimization Patterns](token-optimization-patterns.md) first. Delegate content fetching to child Explore agents. Parent receives only analysis summaries, not raw content. Achieves O(1) parent context instead of O(n)."
---

# Token Optimization Patterns

When orchestrating multiple agents that each need to process large documents, naive approaches can cause O(n) token bloat in the parent context. This document describes the delegation pattern that achieves O(1) parent context usage.

## The Problem

Consider a workflow that consolidates N plan issues into a single unified plan. A naive implementation might:

1. Parent agent fetches all N plan bodies into its context
2. Parent reads and analyzes all content
3. Parent generates consolidated plan

**Token cost**: Parent context contains N \* plan_size tokens, even if each plan is 5000+ tokens.

For N=7 plans, this could add 35,000+ tokens to the parent context before any analysis begins.

## The Solution: Delegated Content Fetching

Instead of fetching content into the parent context, delegate fetching to child agents:

1. Parent validates plan metadata only (labels, state, issue numbers)
2. Parent launches N child Explore agents **in parallel**, each with:
   - Instruction to fetch its own plan content
   - Specific investigation goals
   - Plan issue number as parameter
3. Each child fetches and analyzes its plan independently
4. Parent receives only the **analysis summary** from each child, not the raw content

**Token cost**: Parent context contains N \* summary_size tokens, where summary_size << plan_size.

## Implementation Reference

This pattern is demonstrated in `.claude/commands/erk/replan.md` Steps 3-4:

### Step 3: Plan Content Fetching (Delegated)

```markdown
### Step 3: Plan Content Fetching (Delegated to Step 4)

Plan content is fetched by each Explore agent in Step 4, not in the main context.
This avoids dumping large plan bodies into the main conversation.

Skip to Step 4.
```

### Step 4: Deep Investigation

```markdown
### Step 4: Deep Investigation

Use the Explore agent (Task tool with subagent_type=Explore) to perform deep investigation of the codebase.

**If CONSOLIDATION_MODE:**

Launch parallel Explore agents (one per plan, using `run_in_background: true`), each investigating:

- Plan items and their current status
- Overlap potential with other plans being consolidated
- File mentions and their current state
```

Each Explore agent prompt includes:

```
Fetch the plan content from issue #<number> using:
erk exec get-plan-content <number>

Then investigate:
1. Which items are fully implemented
2. Which items overlap with other plans
3. Current file states
```

The parent never sees the raw plan content — only the investigation results.

## When to Apply

Use this pattern when:

1. **Multiple large documents**: Workflow processes N documents, each >1000 tokens
2. **Independent analysis**: Each document can be analyzed separately before synthesis
3. **Parallel processing**: Child agents can run concurrently (no sequential dependencies)
4. **Summary << Content**: Analysis output is much smaller than raw input

**Examples**:

- Consolidating multiple plan issues into one plan
- Analyzing multiple PRs for release notes
- Comparing implementations across multiple repos
- Aggregating session logs from multiple worktrees

## Anti-Patterns

**Don't use this pattern when**:

1. Documents are small (<500 tokens each) — overhead not worth it
2. Parent needs full content for synthesis (not just analysis results)
3. Sequential processing required — can't parallelize child agents
4. Child agents would need to communicate with each other

## Results from /erk:replan

Before optimization (Step 3 in parent context):

- **Token usage**: ~45,000 tokens for 7-plan consolidation
- **Context pressure**: Risk of summarization during synthesis

After optimization (Step 3 delegated to Step 4 children):

- **Token usage**: ~8,000 tokens for 7-plan consolidation
- **Context pressure**: Parent retains full conversation history

**Reduction**: 82% fewer tokens in parent context

## Related Patterns

- **Background agents**: Use `run_in_background: true` to launch child agents in parallel
- **TaskOutput tool**: Retrieve results from background agents when ready
- **Summary contracts**: Define clear output formats for child agents (JSON, bullet lists, etc.)

## Worked Example: objective-next-plan Command

The `objective-next-plan` command demonstrates Task agent delegation for data fetching and formatting.

### Problem

Creating an implementation plan from an objective step requires:

1. Fetching objective metadata (title, description, issue number)
2. Fetching roadmap table with status column
3. Parsing and mapping status values (ACTIVE → in_progress, etc.)
4. Extracting pending steps
5. Generating next-step recommendation

**Naive approach**: LLM makes 3+ sequential fetches (objective body, roadmap, status parsing), consuming ~4500 tokens.

### Solution

Delegate entire data fetching and formatting to a Task agent:

```python
# Prompt structure for Task agent
prompt = f"""
Fetch objective context for issue #{objective_issue} and format as JSON with:

1. OBJECTIVE - title, issue_number, description
2. STATUS - ACTIVE, PLANNING, or COMPLETED
3. ROADMAP - table with step, status, pr, notes columns
4. PENDING_STEPS - array of incomplete steps
5. RECOMMENDED - next_step and reason

Map status values:
- ACTIVE → in_progress
- PLANNING → pending
- COMPLETED → done

Output structured JSON only.
"""

# Launch Task agent with haiku model
task_agent = Task(
    subagent_type='general-purpose',
    model='haiku',  # Mechanical work, use cheap model
    prompt=prompt
)
```

### Token Savings

| Approach                      | Tokens  | Turns   |
| ----------------------------- | ------- | ------- |
| Sequential LLM fetches        | ~4500   | 3-4     |
| Task agent delegation (haiku) | ~2000   | 1       |
| **Reduction**                 | **55%** | **66%** |

### Model Selection

- **Task agent**: haiku (mechanical data fetching and formatting)
- **Parent agent**: sonnet (plan synthesis and reasoning)

**Rationale**: Delegate mechanical work to cheap models, reserve expensive models for creative work.

### Output Format

Task agent returns structured JSON matching the schema in [Objective Summary Format](../reference/objective-summary-format.md).

Parent agent consumes JSON directly without additional parsing turns.

## Related Documentation

- [Objective Summary Format](../reference/objective-summary-format.md) - Structured output specification
- [Replan Command](.claude/commands/erk/replan.md) - Full implementation
- [Explore Agent](../agents/explore.md) - Investigation capabilities
