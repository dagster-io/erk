---
title: Agent Output Routing Strategies
read_when:
  - "deciding whether to embed output instructions in agent files or orchestrator Task prompts"
  - "modifying agent definitions to control where output goes"
  - "designing reusable agents that may be called from multiple contexts"
tripwires:
  - action: "adding output_path or Output Routing sections to agent definition files"
    warning: "Consider whether this agent is single-purpose or general-purpose. For general-purpose agents, embed routing instructions in the orchestrator's Task prompt to preserve reusability."
---

# Agent Output Routing Strategies

When agents need to write their own outputs, there are two strategies for controlling where and how they write. The choice depends on whether the agent is single-purpose or general-purpose.

## Strategy 1: Embedded-Prompt (Preferred for General-Purpose Agents)

The orchestrator's Task prompt includes output routing instructions. The agent definition remains clean and context-independent.

**How it works:** The orchestrator adds an "Output Routing" section to each Task prompt, telling the agent to write to a specific output_path and return only a confirmation message. The agent's own definition file does not mention output routing at all.

<!-- Source: .claude/commands/erk/learn.md, search for "## Output Routing" -->

See the Output Routing blocks in `.claude/commands/erk/learn.md` for the canonical implementation. Each Task prompt includes the routing instructions inline.

**Advantages:**

- Agent remains reusable across contexts with different output needs
- Single file to modify (orchestrator) instead of N agent files
- Output behavior is visible at the orchestration layer

**Disadvantages:**

- Requires consistent orchestrator discipline (every Task call must include routing)
- If orchestrator forgets the instructions, agent returns full content to parent

## Strategy 2: Agent-File (For Single-Purpose Agents)

The agent definition itself includes output_path in its Input section and an Output section with self-write instructions.

**How it works:** The agent file declares output_path as an input parameter and includes instructions to write output and return only a confirmation. The orchestrator only needs to pass the path.

**Advantages:**

- Guaranteed behavior — agent always self-writes regardless of orchestrator
- Less orchestrator boilerplate per Task call

**Disadvantages:**

- Reduces agent reusability (hardcoded to always self-write)
- Multiple files to modify when changing the pattern

## Decision Framework

| Agent characteristic                          | Strategy        | Rationale                           |
| --------------------------------------------- | --------------- | ----------------------------------- |
| Called from multiple orchestrators            | Embedded-prompt | Preserves flexibility               |
| Single-purpose, one orchestrator              | Either works    | Choose based on preference          |
| Output behavior must be guaranteed            | Agent-file      | No orchestrator discipline required |
| Orchestrator already has complex Task prompts | Agent-file      | Avoids prompt bloat                 |

## The Output Routing Template

When using the embedded-prompt strategy, include this block in each Task prompt:

See the "Output Routing" sections in `.claude/commands/erk/learn.md` for the standardized template that tells agents to write to output_path, return only confirmation, and not include analysis content in their final message.

## Related Documentation

- [Context Efficiency](../architecture/context-efficiency.md) — Why self-write matters
- [Agent Orchestration Safety](agent-orchestration-safety.md) — File-based handoff patterns
- [Command-Agent Delegation](agent-delegation.md) — When to delegate vs inline
