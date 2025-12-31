---
title: Documentation Guide
read_when:
  - "navigating erk documentation"
  - "finding where documentation lives"
  - "understanding doc organization"
---

# Documentation Guide

## Quick Navigation

The documentation is organized by topic category:

### Documentation Categories

| Category                      | Description                                      |
| ----------------------------- | ------------------------------------------------ |
| [Architecture](architecture/) | Core patterns, interfaces, subprocess wrappers   |
| [CLI Development](cli/)       | Command organization, output styling, formatting |
| [Planning](planning/)         | Plan lifecycle, enrichment, agent delegation     |
| [Testing](testing/)           | Test architecture, fakes, rebase conflicts       |
| [Sessions](sessions/)         | Session logs, context analysis, tools            |
| [Hooks](hooks/)               | Hook system, erk-specific hooks                  |
| [Commands](commands/)         | Slash command optimization                       |
| [Reference](reference/)       | GitHub integration, external references          |
| [Erk](erk/)                   | Erk-specific workflows                           |

### Root Documents

- [glossary.md](glossary.md) - Project terminology and definitions
- [conventions.md](conventions.md) - Naming conventions
- [guide.md](guide.md) - This navigation guide

### For Agents (AI Assistants)

**Python Coding Standards:**

- Load the `dignified-python-313` skill for all Python coding standards
- Covers: exception handling, type annotations, imports, ABC patterns, file operations, CLI development

**Testing:**

- Load the `fake-driven-testing` skill for testing guidance
- See [Testing](testing/) for reference documentation

### For Humans

- [../writing/agentic-programming/agentic-programming.md](../writing/agentic-programming/agentic-programming.md) - Agentic programming philosophy
- [../writing/schrockn-style/](../writing/schrockn-style/) - Writing style guides
- Package READMEs (e.g., `packages/erk-dev/README.md`)

## Project Planning Files

**`.impl/`** - Local implementation planning folder

- Contains `plan.md` (immutable reference) and `progress.md` (mutable tracking)
- See [Planning](planning/) for workflow details

## Documentation Structure

```
docs/agent/
├── architecture/              # Core patterns and design
├── cli/                       # CLI development
├── commands/                  # Slash command patterns
├── erk/                       # Erk-specific guides
├── hooks/                     # Hook system
├── planning/                  # Plan workflows
├── reference/                 # External integrations
├── sessions/                  # Session log tools
├── testing/                   # Test architecture
├── conventions.md             # Naming conventions
├── glossary.md                # Terminology
├── guide.md                   # This file
└── index.md                   # Master index
```

## Task-Based Navigation

| Your Task                           | Start Here                                                                               |
| ----------------------------------- | ---------------------------------------------------------------------------------------- |
| Understanding erk terminology       | [glossary.md](glossary.md)                                                               |
| Understanding plan lifecycle        | [Planning](planning/)                                                                    |
| Cleaning up branches/worktrees      | [erk/branch-cleanup.md](erk/branch-cleanup.md)                                           |
| Writing tests with fakes            | [Testing](testing/) or load `fake-driven-testing` skill                                  |
| Using time.sleep() or delays        | [Architecture](architecture/) - see erk-architecture.md#time-abstraction                 |
| Understanding or modifying hooks    | [Hooks](hooks/)                                                                          |
| Creating command-agent delegation   | [Planning](planning/) - see agent-delegation.md                                          |
| Implementing script mode            | [CLI Development](cli/) - see script-mode.md                                             |
| Styling CLI output                  | [CLI Development](cli/) - see output-styling.md                                          |
| Working with session logs           | [Sessions](sessions/)                                                                    |
| Writing temp files for AI workflows | [Planning](planning/) - see scratch-storage.md                                           |
| Organizing CLI commands             | [CLI Development](cli/) - see command-organization.md                                    |
| Python coding standards             | Load `dignified-python-313` skill                                                        |
| Understanding agentic programming   | [../writing/agentic-programming/](../writing/agentic-programming/agentic-programming.md) |

## Adding Category Descriptions

Category descriptions in `docs/agent/index.md` help agents understand when to explore each category and where to add new docs.

**Location:** Descriptions are defined in `CATEGORY_DESCRIPTIONS` in `packages/erk-kits/src/erk_kits/operations/agent_docs.py`.

**Format:** Each description should answer two questions:

1. **When to explore** — What tasks or questions should lead an agent here?
2. **When to add docs** — What type of documentation belongs in this category?

**Template:**

```
"Explore when [doing X]. Add docs here for [type of content]."
```

**Example:**

```python
"cli": (
    "Explore when building CLI commands or output formatting. "
    "Add docs here for Click patterns and terminal UX."
),
```

After editing, run `erk docs sync` to regenerate `docs/agent/index.md`.
