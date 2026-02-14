---
title: Context Efficiency in Multi-Agent Pipelines
read_when:
  - "designing multi-agent orchestration commands"
  - "parent context is being exhausted or compacted during agent pipelines"
  - "choosing how agents should return their results"
tripwires:
  - action: "reading agent output with TaskOutput then writing it to a file with Write"
    warning: "This is the content relay anti-pattern. Content appears twice in parent context (tool result + tool parameter) with no reasoning benefit. Have agents write their own outputs instead."
---

# Context Efficiency in Multi-Agent Pipelines

## The Content Relay Anti-Pattern

When a parent orchestrator calls TaskOutput(block: true) to read an agent's result, then Write(content) to persist it, the content flows through the parent's context twice: once as the TaskOutput tool result, once as the Write tool parameter. The parent never reasons about this content — it is purely mechanical relay. For N agents producing K tokens each, the parent accumulates 2NK tokens of relay overhead.

## The Self-Write Solution

Instead of relaying content, have agents write their own output files:

1. Parent creates output directory before launching agents
2. Parent passes output_path to each agent via Task prompt
3. Parent includes Output Routing instructions telling the agent to write to output_path and return only a short confirmation
4. Parent verifies files exist with a single ls -la call after all agents complete

## Token Impact

<!-- Source: .claude/commands/erk/learn.md, Output Routing sections -->

The /erk:learn command reduced parent context from ~105-262K tokens to ~35-53K tokens (3-5x reduction) by applying this pattern to 7 agents. Each agent produces 5-15K tokens of analysis, so the relay overhead was 6 agents x 2 copies x 5-15K = 60-180K tokens eliminated.

## When to Apply

Use self-write when:

- Parent orchestrates N agents producing large outputs (>1KB each)
- Parent does not need to reason about intermediate outputs
- Parent only needs final synthesis or specific outputs

Keep relay (TaskOutput) when:

- Parent needs to make decisions based on agent output content
- Output is small (<1KB) and the relay overhead is negligible
- Agent output determines which subsequent agents to launch

## Related Documentation

- [Agent Orchestration Safety](../planning/agent-orchestration-safety.md) — File-based handoff patterns
- [Multi-Tier Agent Orchestration](../planning/agent-orchestration.md) — Pipeline design
- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file tradeoff
