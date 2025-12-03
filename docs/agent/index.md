# Agent Documentation

## Categories

| Category                      | Description                                      |
| ----------------------------- | ------------------------------------------------ |
| [Architecture](architecture/) | Core patterns, interfaces, subprocess wrappers   |
| [CLI Development](cli/)       | Command organization, output styling, formatting |
| [Planning](planning/)         | Plan lifecycle, enrichment, agent delegation     |
| [Testing](testing/)           | Test architecture, fakes, rebase conflicts       |
| [Sessions](sessions/)         | Session logs, context analysis, tools            |
| [Hooks](hooks/)               | Hook system, erk-specific hooks                  |
| [Kits](kits/)                 | Kit CLI commands, kit architecture               |
| [Commands](commands/)         | Slash command optimization                       |
| [Reference](reference/)       | GitHub integration, external references          |
| [Erk](erk/)                   | Erk-specific workflows                           |
| [TUI](tui/)                   | Textual TUI development, quirks and workarounds  |

## Root Documents

| Document                         | Read when...                                                |
| -------------------------------- | ----------------------------------------------------------- |
| [glossary.md](glossary.md)       | Understanding project terminology                           |
| [conventions.md](conventions.md) | Naming functions, variables, CLI commands, Claude artifacts |
| [guide.md](guide.md)             | Navigating documentation, finding docs                      |

## Category Contents

### [Architecture](architecture/)

| Document                                                      | Read when...                                         |
| ------------------------------------------------------------- | ---------------------------------------------------- |
| [erk-architecture.md](architecture/erk-architecture.md)       | Understanding dry-run patterns, context regeneration |
| [protocol-vs-abc.md](architecture/protocol-vs-abc.md)         | Choosing between Protocol and ABC for interfaces     |
| [subprocess-wrappers.md](architecture/subprocess-wrappers.md) | Executing shell commands, using subprocess wrappers  |
| [github-parsing.md](architecture/github-parsing.md)           | Parsing GitHub URLs, extracting PR/issue numbers     |

### [CLI Development](cli/)

| Document                                               | Read when...                                           |
| ------------------------------------------------------ | ------------------------------------------------------ |
| [command-organization.md](cli/command-organization.md) | Organizing CLI commands, designing command hierarchies |
| [output-styling.md](cli/output-styling.md)             | Styling CLI output, using colors                       |
| [list-formatting.md](cli/list-formatting.md)           | Formatting list output, designing list commands        |
| [script-mode.md](cli/script-mode.md)                   | Implementing script mode, shell integration            |

### [Planning](planning/)

| Document                                            | Read when...                                         |
| --------------------------------------------------- | ---------------------------------------------------- |
| [lifecycle.md](planning/lifecycle.md)               | Creating or closing plans, understanding plan states |
| [enrichment.md](planning/enrichment.md)             | Adding metadata to plans, enrichment workflow        |
| [workflow.md](planning/workflow.md)                 | Using .impl/ folders, implementing plans             |
| [agent-delegation.md](planning/agent-delegation.md) | Delegating to agents from commands                   |
| [scratch-storage.md](planning/scratch-storage.md)   | Writing temp files for AI workflows                  |

### [Testing](testing/)

| Document                                                               | Read when...                                      |
| ---------------------------------------------------------------------- | ------------------------------------------------- |
| [testing.md](testing/testing.md)                                       | Using erk fakes (FakeGit, etc.), running tests    |
| [rebase-conflicts.md](testing/rebase-conflicts.md)                     | ErkContext API changes, env_helpers during rebase |
| [import-conflict-resolution.md](testing/import-conflict-resolution.md) | Resolving import conflicts during rebase          |

### [Sessions](sessions/)

| Document                                            | Read when...                                     |
| --------------------------------------------------- | ------------------------------------------------ |
| [layout.md](sessions/layout.md)                     | Understanding ~/.claude/projects/ structure      |
| [tools.md](sessions/tools.md)                       | Finding session logs, inspecting agent execution |
| [context-analysis.md](sessions/context-analysis.md) | Debugging context window issues                  |

### [Hooks](hooks/)

| Document                   | Read when...                                             |
| -------------------------- | -------------------------------------------------------- |
| [hooks.md](hooks/hooks.md) | Creating hooks, understanding hook lifecycle             |
| [erk.md](hooks/erk.md)     | Working with erk-specific hooks, context-aware reminders |

### [Kits](kits/)

| Document                                          | Read when...                                      |
| ------------------------------------------------- | ------------------------------------------------- |
| [cli-commands.md](kits/cli-commands.md)           | Creating kit CLI commands, understanding patterns |
| [code-architecture.md](kits/code-architecture.md) | Understanding kit code structure                  |

### [Commands](commands/)

| Document                                                      | Read when...                              |
| ------------------------------------------------------------- | ----------------------------------------- |
| [optimization-patterns.md](commands/optimization-patterns.md) | Reducing command size, using @ references |

### [Reference](reference/)

| Document                                                       | Read when...                                       |
| -------------------------------------------------------------- | -------------------------------------------------- |
| [github-branch-linking.md](reference/github-branch-linking.md) | Linking branches to issues, using gh issue develop |

### [Erk](erk/)

| Document                                                 | Read when...                                  |
| -------------------------------------------------------- | --------------------------------------------- |
| [branch-cleanup.md](erk/branch-cleanup.md)               | Cleaning up branches and worktrees            |
| [graphite-branch-setup.md](erk/graphite-branch-setup.md) | Submitting PRs with Graphite, no_parent error |

### [TUI](tui/)

| Document                                   | Read when...                                           |
| ------------------------------------------ | ------------------------------------------------------ |
| [textual-quirks.md](tui/textual-quirks.md) | Working with Textual TUI, avoiding common API pitfalls |
