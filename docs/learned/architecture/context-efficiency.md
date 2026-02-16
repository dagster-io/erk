---
title: Context Efficiency Patterns
read_when:
  - "orchestrating multi-agent workflows"
  - "parent agent reading large agent output via TaskOutput"
  - "designing agent output routing to minimize context usage"
tripwires:
  - action: "reading agent output with TaskOutput then writing it to a file with Write"
    warning: "This is the 'content relay' anti-pattern — it causes 2x context duplication. Instead, have agents accept an output_path parameter and write directly. See /erk:learn for the canonical implementation."
last_audited: "2026-02-16 14:00 PT"
audit_result: clean
---

# Context Efficiency Patterns

When orchestrating multi-agent workflows, **avoid relaying content through the parent agent's context window**. The parent should route data between agents without loading it into its own context.

## The Content Relay Anti-Pattern

The most common context efficiency mistake is reading agent output via `TaskOutput` and then writing it to a file with `Write`:

```
Parent reads TaskOutput (content enters parent context) → Parent writes via Write (content sent again)
```

This doubles the context cost: the content occupies space in the parent's context window during the read, then again during the write. For large outputs (60-180K tokens), this can exhaust the context window.

## The Self-Write Solution

Instead, have agents accept an `output_path` parameter and write their results directly:

```
Parent launches agent with output_path → Agent writes directly → Parent continues without loading content
```

The parent agent never sees the content — it only needs to know the file path. This reduces parent context usage by 60-180K tokens per agent output.

### Implementation Pattern

In the orchestrator's Task prompt:

```
Write your analysis to {output_path}. Do not return the content in your response.
```

The parent then passes the file path to downstream agents without reading it:

```
Analyze the content at {input_path} and write results to {output_path}.
```

## When Content Relay Is Acceptable

- Small outputs (under 1K tokens) where the overhead is negligible
- When the parent needs to inspect or transform the content before routing
- Single-agent workflows with no downstream consumers

## Canonical Example

The `/erk:learn` command orchestrates 7+ analysis agents. Each agent writes to a file path, and downstream agents read from upstream paths — the parent agent never loads the analysis content into its own context.

## Related Documentation

- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Decision framework for routing approaches
