---
title: Documentation Guide
read_when:
  - "navigating erk documentation"
  - "finding where documentation lives"
  - "understanding doc organization"
---

# Documentation Guide

## Quick Navigation

The documentation is organized by audience and purpose:

### For Agents (AI Assistants)

**Python Coding Standards:**

- Load the `dignified-python` skill for all Python coding standards
- Covers: exception handling, type annotations, imports, ABC patterns, file operations, CLI development

**Erk-Specific Documentation:**

- [glossary.md](glossary.md) - Project terminology and definitions
- [testing.md](testing.md) - Testing architecture with fakes and ops patterns
- [command-agent-delegation.md](command-agent-delegation.md) - Command-agent delegation pattern for workflow orchestration
- [claude-code-session-layout.md](claude-code-session-layout.md) - Claude Code session log structure and format (`~/.claude/projects/`)

### For Humans

- [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) - Agentic programming philosophy
- [../writing/schrockn-style/](../writing/schrockn-style/) - Writing style guides
- Package READMEs (e.g., `packages/erk-dev/README.md`)

## Project Planning Files

**`.PLAN.md`** - Local implementation planning document

- Located at repository root (`.PLAN.md`)
- **In `.gitignore`** - Not tracked by git, local-only
- Used for tracking multi-phase implementation progress
- Updated as work progresses through phases
- Format: Markdown with phase/step tracking, completion status, and next steps

**Purpose**: Agents can read and update `.PLAN.md` to track implementation progress across sessions without cluttering git history with planning documents.

## Documentation Structure

```
docs/
├── agent/                      # Agent-focused reference
│   ├── glossary.md            # Erk terminology
│   ├── guide.md               # This file
│   └── testing.md             # Testing patterns
└── writing/                   # Human-readable guides
    ├── agentic-programming/
    └── schrockn-style/
```

## Task-Based Navigation

| Your Task                           | Start Here                                                                                                     |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Understanding erk terminology       | [glossary.md](glossary.md)                                                                                     |
| Understanding plan lifecycle        | [plan-lifecycle.md](plan-lifecycle.md)                                                                         |
| Understanding plan enrichment       | [plan-enrichment.md](plan-enrichment.md)                                                                       |
| Cleaning up branches/worktrees      | [erk/branch-cleanup.md](erk/branch-cleanup.md)                                                                 |
| Writing tests with fakes/ops        | [testing.md](testing.md)                                                                                       |
| Using time.sleep() or delays        | [erk-architecture.md](erk-architecture.md#time-abstraction-for-testing)                                        |
| Understanding or modifying hooks    | [hooks-erk.md](hooks-erk.md) (context-aware reminders) → General: [hooks.md](hooks.md)                         |
| Creating command-agent delegation   | [command-agent-delegation.md](command-agent-delegation.md)                                                     |
| Implementing script mode            | [cli-script-mode.md](cli-script-mode.md)                                                                       |
| Styling CLI output                  | [cli-output-styling.md](cli-output-styling.md)                                                                 |
| Working with session logs           | [claude-code-session-layout.md](claude-code-session-layout.md)                                                 |
| Writing temp files for AI workflows | [scratch-storage.md](scratch-storage.md)                                                                       |
| Organizing CLI commands             | [cli-command-organization.md](cli-command-organization.md)                                                     |
| Python coding standards             | Load `dignified-python` skill                                                                                  |
| Understanding agentic programming   | [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) |
