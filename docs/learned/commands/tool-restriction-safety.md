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
  - action: "adding tool invocations to agent instructions without updating frontmatter"
    warning: "allowed-tools frontmatter MUST include every tool the agent's instructions reference. Missing tools cause silent runtime failures."
  - action: "creating new agent files in .claude/agents/"
    warning: "All agent files MUST have YAML frontmatter with name, description, and allowed-tools. Missing frontmatter causes silent behavioral failures."
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

## Frontmatter Must Match All Tool Invocations

When agent instructions (either in the agent file or in the orchestrator's Task prompt) tell the agent to use a specific tool, that tool MUST appear in the agent's allowed-tools frontmatter. Claude Code enforces allowed-tools at runtime — a tool call outside the allowed set fails silently or with a non-obvious error.

This is the inverse of the minimal-set principle: while you should not add tools the agent doesn't need, you must not omit tools the agent does need. In PR #6949, six agents gained Write instructions but initially lacked Write in their frontmatter, which would have caused silent failures at runtime.

**Verification pattern:** Before launching agents, audit each agent's instructions for tool invocations (Write, Bash, Grep, etc.) and cross-check against the allowed-tools frontmatter list. This applies to both agent-file instructions and embedded Task prompt instructions.

<!-- Source: .claude/agents/learn/session-analyzer.md, frontmatter -->

See the frontmatter in any `.claude/agents/learn/*.md` file for examples of allowed-tools lists that include Write for self-writing agents.

## Frontmatter Completeness Requirement

All agent files in `.claude/agents/` MUST have a YAML frontmatter block with at minimum: name, description, and allowed-tools. An agent file without frontmatter will be treated as a plain markdown prompt with no tool restrictions or metadata, which can lead to unpredictable behavior.

In PR #6949, the tripwire-extractor agent was discovered to be missing its entire frontmatter block. This was a silent failure — the agent ran but without the metadata that Claude Code uses for tool restriction and identity.

**Prevention:** When creating new agent files, always start with the frontmatter template. When reviewing PRs that add or modify agents, verify frontmatter presence.

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

## Related Documentation

- [Agent Delegation](../planning/agent-delegation.md) — delegation patterns including tool restriction inheritance
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) — gathering context before planning
