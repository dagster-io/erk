<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Commands Documentation

- **[audit-doc.md](audit-doc.md)** — understanding why audit-doc works the way it does, modifying the /local:audit-doc command, understanding collateral finding tiers, debugging unexpected audit verdicts
- **[command-rename-pattern.md](command-rename-pattern.md)** — renaming a slash command or skill, migrating command invocations across the codebase, performing a terminology shift that affects command names
- **[dynamic-trunk-detection.md](dynamic-trunk-detection.md)** — writing git commands in slash commands or skills, referencing master or main branch in .claude/ files, creating new commands that compare against trunk
- **[optimization-patterns.md](optimization-patterns.md)** — reducing command file size, using @ reference in commands, modularizing command content
- **[preview-command-pattern.md](preview-command-pattern.md)** — pairing destructive commands with preview commands, implementing dry-run for slash commands, adding preview functionality to existing commands
- **[session-id-substitution.md](session-id-substitution.md)** — writing slash commands or skills that need session context, developing hooks that interact with Claude sessions, debugging session ID unavailable or empty string errors, deciding where to place session-dependent logic (root agent vs sub-agent)
- **[skill-patterns.md](skill-patterns.md)** — creating slash commands that involve user decisions, using AskUserQuestion in commands or skills, naming prompt executor functions
- **[step-renumbering-checklist.md](step-renumbering-checklist.md)** — merging, removing, or reordering steps in slash commands, refactoring command workflows that use numbered steps, encountering broken step references after editing a command
- **[tool-restriction-safety.md](tool-restriction-safety.md)** — adding allowed-tools to a command or agent frontmatter, designing a read-only slash command, creating commands intended for use within plan mode, deciding which tools a restricted command needs
