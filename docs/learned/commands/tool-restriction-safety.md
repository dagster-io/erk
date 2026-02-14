---
read_when:
  - adding allowed-tools to a command or agent frontmatter
  - designing a read-only slash command
  - creating commands intended for use within plan mode
  - deciding which tools a restricted command needs
title: Tool Restriction Safety Pattern
tripwires:
  - action: "adding allowed-tools to a command or agent frontmatter"
    warning: "ALWAYS apply the minimal-set principle — only allow tools the command actually needs"
  - action: "creating commands that delegate to subagents"
    warning: "NEVER omit Task from allowed-tools if the command delegates to subagents"
  - action: "writing allowed-tools frontmatter"
    warning: "Commands and agents use DIFFERENT allowed-tools syntax — check the format section"
---

# Tool Restriction Safety Pattern

The `allowed-tools` frontmatter field enforces a tool allowlist on commands and agents, ensuring they cannot perform operations outside their intended scope. This is Claude Code's mechanism for creating safe, read-only commands that work within plan mode.

## Why This Exists

Some commands should be safe to run at any time — during planning, before implementation, or in contexts where code modification would be harmful. Without `allowed-tools`, a command could accidentally write files, execute destructive shell commands, or delegate to agents that do so.

The `allowed-tools` field makes safety **structural** rather than relying on prompt instructions like "don't write files." The Claude Code runtime enforces the restriction — any tool call outside the allowed set fails with an error identifying the blocked tool.

## Syntax Differs Between Commands and Agents

Commands and agents use different YAML formats for the same feature:

- **Commands** (`.claude/commands/`): comma-separated string — `allowed-tools: Read, Glob, Grep`
- **Agents** (`.claude/agents/`): YAML list with one tool per line

<!-- Source: .claude/commands/local/interview.md, frontmatter -->

See the frontmatter in `.claude/commands/local/interview.md` for the command format.

<!-- Source: .claude/agents/learn/session-analyzer.md, frontmatter -->

See the frontmatter in `.claude/agents/learn/session-analyzer.md` for the agent format.

## When to Use Tool Restrictions

| Scenario                            | Use `allowed-tools`? | Why                                       |
| ----------------------------------- | -------------------- | ----------------------------------------- |
| Information gathering before action | Yes                  | No side effects needed                    |
| Commands used within plan mode      | Yes                  | Plan mode expects read-only behavior      |
| Decision-support commands           | Yes                  | Only needs exploration + user interaction |
| Codebase exploration commands       | Yes                  | Read-only by nature                       |
| Commands that implement features    | No                   | Needs Write, Edit, Bash                   |
| Commands that create PRs or commits | No                   | Needs Bash for git/gh                     |
| Commands that run CI or tests       | No                   | Needs Bash for test runners               |

## The Minimal-Set Principle

Only allow tools the command absolutely needs. Start with zero tools and add only what's required by the command's logic. This prevents scope creep where a command gains unnecessary write capabilities.

The common read-only set is `Read`, `Glob`, `Grep`, plus `AskUserQuestion` if the command interacts with the user. Add `Task` only if the command delegates to subagents. Add `Bash` only if the command needs specific shell commands (e.g., `git log` for read-only git queries).

## Inheritance: Commands Restrict Their Subagents

When a command with `allowed-tools` delegates to a subagent via `Task`, the subagent inherits the command's tool restrictions — even if the agent's own frontmatter lists additional tools. This means:

- A command restricted to `Read, Glob, Grep, Task` can launch agents, but those agents can only use `Read, Glob, Grep`
- The agent's own `allowed-tools` in its frontmatter is further intersected with the command's restrictions
- This makes tool restrictions transitive — safety guarantees cascade through the delegation chain

## Plan Mode Integration

Tool-restricted commands are the primary mechanism for doing useful work within plan mode. Because plan mode blocks Write/Edit/Bash by default, only commands that declare a compatible `allowed-tools` set can run without disrupting the planning context.

This enables the "interview then plan" workflow: run a read-only command to gather requirements and explore the codebase, then use the gathered context to inform the plan — all without leaving plan mode.

<!-- Source: .claude/commands/local/interview.md -->

See `/local:interview` for the canonical example of this pattern.

## Completeness Requirement

All agent files in `.claude/agents/` MUST include `allowed-tools` in their frontmatter. This applies to every agent definition — not just read-only ones. The frontmatter block must be complete with `name`, `description`, and `allowed-tools`.

When reviewing agent files, verify:

1. Every agent has `allowed-tools` in frontmatter
2. The listed tools match what the agent's instructions reference (e.g., if instructions say "use Read to examine files", `Read` must be in `allowed-tools`)
3. No tools are listed that the agent doesn't need (minimal-set principle)

## Related Documentation

- [Agent Delegation](../planning/agent-delegation.md) — delegation patterns including tool restriction inheritance
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) — gathering context before planning
