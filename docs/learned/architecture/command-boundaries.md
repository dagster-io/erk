---
title: Agent Command vs CLI Command Boundaries
read_when:
  - Choosing between agent vs CLI command
  - Deciding when to use .claude/commands/ vs src/erk/cli/
  - Understanding when AI capabilities are needed
---

# Agent Command vs CLI Command Boundaries

## Overview

Erk has two types of commands:

1. **Agent commands** (`.claude/commands/`) - Markdown files executed by Claude Code
2. **CLI commands** (`src/erk/cli/`) - Python Click commands

This document clarifies when to use each.

## Use Agent Commands When

The operation requires:

- **Natural language analysis** - Categorizing, summarizing, understanding intent
- **Code generation** - Writing new code based on context
- **Documentation extraction** - Identifying gaps, generating suggestions
- **Multi-step reasoning** - Complex decision trees based on context
- **Codebase exploration** - Understanding patterns, finding related code

Examples:

- `/erk:create-extraction-plan` - Analyzes sessions for documentation gaps
- `/erk:plan-implement` - Executes implementation plans from `.impl/` folder

## Use CLI Commands When

The operation is:

- **Deterministic** - Same input always produces same output
- **Data transformation** - Parsing, formatting, converting
- **External tool orchestration** - Git, GitHub CLI, Graphite
- **File system operations** - Creating, moving, deleting files
- **State management** - Tracking worktrees, branches, issues

Examples:

- `erk pr land` - Merges PR, deletes worktree (deterministic git operations)
- `erk wt create` - Creates worktree (git operations)
- `erk exec create-extraction-plan` - Creates GitHub issue (API call)

## Hybrid Patterns

### CLI Spawning Agent

When a CLI command needs AI capabilities:

1. CLI handles prerequisites and validation (Python)
2. CLI spawns `claude --print /agent-command` for AI work
3. CLI handles results and cleanup (Python)

Example: `erk pr land` could spawn `/erk:land-extraction` for AI-based session analysis, then continue with deterministic cleanup.

### Agent Delegating to CLI

When an agent command needs deterministic operations or external tool orchestration:

1. Agent handles conversation-context extraction and reasoning
2. Agent calls CLI command via `erk exec <command>` or `erk <subcommand>`
3. CLI performs the deterministic work (git, GitHub API, file operations)
4. Agent interprets results and continues reasoning

This pattern is the **inverse** of CLI Spawning Agent. Use it when:

- The command starts from conversation context (needs agent understanding)
- But the actual work is deterministic (git operations, API calls)
- The agent needs to interpret results before deciding next steps

Examples:

| Agent Command            | Delegates To                 | Why                                                              |
| ------------------------ | ---------------------------- | ---------------------------------------------------------------- |
| `/erk:plan-submit`       | `erk plan submit <issue>`    | Agent finds issue in conversation, CLI handles workflow dispatch |
| `/erk:pr-address-remote` | `erk pr address-remote <pr>` | Agent finds PR in conversation, CLI triggers GitHub workflow     |
| `/erk:prepare`           | `erk prepare <issue>`        | Agent finds issue in conversation, CLI creates worktree          |

**Pattern characteristics:**

- Agent commands are thin wrappers that extract context
- Heavy lifting done by CLI (testable, deterministic)
- Results flow back to agent for user communication
- CLI errors reported by agent with context

## Decision Tree

```
Does operation require understanding/generating natural language?
├─ Yes → Agent command
│        └─ Does it need deterministic operations?
│            └─ Yes → Agent delegating to CLI
└─ No → Does it require reasoning about code semantics?
         ├─ Yes → Agent command
         └─ No → CLI command (may spawn agent if needed)
```

## Related Topics

- [Claude Code Agent Command Patterns](../claude-code/agent-commands.md) - Conversation-context extraction
- [Claude Executor Patterns](claude-executor-patterns.md) - ClaudeExecutor for CLI spawning agent
