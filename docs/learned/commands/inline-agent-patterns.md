---
title: Inline Agent Patterns
read_when:
  - "defining agents inline within command files instead of as separate agent files"
  - "adding output routing to agents defined directly in orchestrator commands"
---

# Inline Agent Patterns

## Inline vs File-Based Agents

Most agents in erk are defined as separate files in `.claude/agents/`. However, some agents are defined inline within command files — their instructions appear directly in the orchestrator's Task prompt rather than referencing an external agent file.

## Output Routing for Inline Agents

Inline agents need the same output routing as file-based agents, but the mechanism differs:

**File-based agents:** Routing instructions are embedded in the Task prompt by the orchestrator (embedded-prompt strategy) or in the agent file itself (agent-file strategy).

**Inline agents:** Routing instructions are part of the inline agent definition within the command file. Since there is no separate agent file, there is no frontmatter to set allowed-tools — the agent inherits tool access from how it is launched.

<!-- Source: .claude/commands/erk/learn.md, search for "PR Comment Analyzer" -->

See the PR Comment Analyzer (Agent 4) in `.claude/commands/erk/learn.md` for an example of an inline agent with output routing. It receives output_path and includes the same Output Routing instructions as file-based agents.

## When to Use Inline Agents

| Characteristic                              | File-based | Inline |
| ------------------------------------------- | ---------- | ------ |
| Reused across commands                      | Yes        | No     |
| Has complex instructions                    | Yes        | Maybe  |
| Single-use, tightly coupled to orchestrator | No         | Yes    |
| Needs its own frontmatter/metadata          | Yes        | N/A    |

## Related Documentation

- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file approaches
- [Command-Agent Delegation](../planning/agent-delegation.md) — When to delegate to agents
