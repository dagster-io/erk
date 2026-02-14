---
title: Agent Output Routing Patterns
read_when:
  - "adding output routing to Task prompts for self-writing agents"
  - "creating standardized instruction blocks for agent pipelines"
  - "designing commands that orchestrate multiple agents"
---

# Agent Output Routing Patterns

## The Output Routing Instruction Block

When orchestrating agents that should write their own outputs, include a standardized Output Routing section in each Task prompt. This tells the agent where to write, what format to use for confirmation, and what not to do (return full content).

<!-- Source: .claude/commands/erk/learn.md, search for "## Output Routing" -->

See the "Output Routing" sections in `.claude/commands/erk/learn.md` for the canonical template. The block includes three critical instructions: write to output_path, return only confirmation text, and do not return analysis content in the final message.

## Template Components

The Output Routing block has three required elements:

1. **Write directive** — tells agent to use Write tool to save output to the specified path
2. **Confirmation format** — specifies the exact short message to return (e.g., "Output written to <path>")
3. **Prohibition** — explicitly forbids returning full content in the final message

## When to Use

Use Output Routing blocks when:

- Agents produce large outputs (>1KB) that parent does not need to reason about
- Multiple agents run in parallel and their outputs are consumed by a later synthesis step
- Parent context budget is a concern

## Related Documentation

- [Context Efficiency](../architecture/context-efficiency.md) — Why self-write matters for token budgets
- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file approaches
