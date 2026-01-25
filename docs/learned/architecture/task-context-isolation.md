---
title: Task Context Isolation Pattern
read_when:
  - "fetching large JSON responses from APIs"
  - "parsing PR review comments"
  - "analyzing GitHub issues or PRs"
  - "need to reduce context window usage"
  - "returning structured data from a Task"
---

# Task Context Isolation Pattern

Use the Task tool to fetch and process large data (API responses, PR comments, issue bodies) in an isolated context, returning only a compact summary to the parent agent. This pattern provides ~65-70% context reduction while preserving actionable data.

## Problem

Large JSON responses from APIs pollute the main conversation context:

- PR review comments can be 2,500-3,000 tokens of raw JSON
- The parent agent only needs summary + thread IDs to act
- Raw JSON stays in context indefinitely, wasting tokens

## Solution: Prose + Structured JSON

The Task returns both human-readable prose AND parseable JSON in a single response:

````
## Summary
PR #5944: 1 actionable item (missing integration tests), 12 informational comments skipped.

## Actionable Items
| # | Thread ID | Path | Line | Issue |
|---|-----------|------|------|-------|
| 1 | PRRT_kwDOPxC3hc5q73Ne | abc.py | 8 | Missing integration tests |

## Structured Data
```json
{
  "pr_number": 5944,
  "pr_title": "BeadsGateway ABC with list_issues Method",
  "actionable_threads": [
    {"thread_id": "PRRT_kwDOPxC3hc5q73Ne", "path": "abc.py", "line": 8, "action": "Add integration tests"}
  ],
  "discussion_actions": [],
  "informational_count": 12
}
````

```

The parent agent:

1. Displays the prose summary to the user
2. Parses the JSON block for actionable data (thread IDs, comment IDs)
3. Acts on the data without ever seeing the raw API response

## Token Savings

| Approach | Tokens | Description |
|----------|--------|-------------|
| Direct fetch | ~2,500-3,000 | Raw JSON stays in main context |
| Task pattern | ~750-900 | Only summary + structured data returned |
| **Savings** | **65-70%** | Context reduction |

## When to Use

- **PR review comments**: Fetch, classify, and return actionable thread IDs
- **GitHub issue analysis**: Parse issue body, extract structured data
- **Large API responses**: Any API that returns verbose JSON
- **Preview commands**: When you only need a summary, not action capability

## When NOT to Use

- **Saving raw data to files**: If you need the raw JSON for a gist, fetch directly
- **Single small responses**: Overhead not worth it for <500 token responses
- **Need full context**: If parent needs to reason about raw data details

## Implementation

### Basic Pattern (Prose Only)

For preview commands that just display results:

```

Task(
subagent_type: "general-purpose",
model: "haiku", # Mechanical classification
description: "Fetch PR feedback preview",
prompt: |
Fetch PR review comments and classify them.

    ## Steps
    1. Run: `erk exec get-pr-review-comments`
    2. Classify: actionable vs informational

    ## Output Format
    ### Summary
    [Human-readable paragraph]

    ### Items Table
    | # | Location | Issue | Proposed Action |
    ...

)

```

### Advanced Pattern (Prose + JSON)

For commands that need to act on the data:

```

Task(
subagent_type: "general-purpose",
model: "sonnet", # Need reasoning for classification
description: "Fetch PR review feedback",
prompt: |
Fetch and classify PR review feedback.

    ## Steps
    1. Fetch comments with erk exec commands
    2. Classify each comment
    3. Group into batches by complexity

    ## Output Format

    ### Summary
    [Prose paragraph]

    ### Actionable Items
    [Table with thread IDs visible]

    ### Structured Data
    ```json
    {
      "actionable_threads": [
        {"thread_id": "...", "path": "...", "action": "..."}
      ],
      ...
    }
    ```

)

````

### Parent Agent Parsing

After receiving Task output, parse the JSON block:

```python
# Pseudo-code for parent agent logic
import json
import re

# Extract JSON from markdown code block
json_match = re.search(r'```json\s*(\{.*?\})\s*```', task_output, re.DOTALL)
if json_match:
    data = json.loads(json_match.group(1))
    for thread in data["actionable_threads"]:
        # Act on each thread using thread_id
        resolve_thread(thread["thread_id"])
````

## Examples in Codebase

### `/erk:pr-preview-address`

Full Task delegation for preview-only command. Returns prose summary, no JSON needed since no actions are taken.

### `/erk:pr-address`

**Phase 1**: Task returns prose + JSON with thread IDs. Parent parses JSON and uses thread IDs to resolve threads after making fixes.

**Phase 4**: Task returns verification summary only (haiku model). Just confirms all threads resolved.

### `/erk:learn`

Task analyzes PR comments for documentation opportunities. Returns insights table, not raw comment data.

## Model Selection

| Task Type                    | Model  | Rationale                       |
| ---------------------------- | ------ | ------------------------------- |
| Mechanical classification    | haiku  | Pattern matching, no creativity |
| Context-aware classification | sonnet | Needs to understand intent      |
| Complex reasoning            | opus   | Multi-factor decisions          |

Prefer haiku when the classification rules are explicit and deterministic.

## Best Practices

### Prompt Design

1. **Explicit output format**: Show exact structure expected
2. **Classification criteria**: Define actionable vs informational clearly
3. **Thread ID visibility**: Always include IDs in both table and JSON

### JSON Structure

Keep the JSON minimal - only include what the parent needs to act:

```json
{
  "actionable_threads": [
    {"thread_id": "...", "path": "...", "line": N, "action": "..."}
  ],
  "discussion_actions": [
    {"comment_id": N, "action": "..."}
  ],
  "informational_count": N
}
```

### Error Handling

Include error states in the JSON:

```json
{
  "error": "No PR found for branch",
  "actionable_threads": [],
  "discussion_actions": []
}
```

## Related Documentation

- [Parallel Agent Orchestration](parallel-agent-pattern.md) - Running multiple Tasks concurrently
- [GitHub API Rate Limits](github-api-rate-limits.md) - API considerations when fetching PR data
