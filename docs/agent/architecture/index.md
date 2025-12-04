# Architecture Documentation

- **[at-reference-resolution.md](at-reference-resolution.md)** — modifying @ reference validation, debugging broken @ references in symlinked files, understanding why validation passes but Claude Code fails
- **[commandresult-extension-pattern.md](commandresult-extension-pattern.md)** — adding new field to CommandResult, extending CommandResult dataclass, adding metadata extraction, implementing new CommandResult field
- **[erk-architecture.md](erk-architecture.md)** — understanding erk architecture, implementing dry-run patterns, regenerating context after os.chdir
- **[github-parsing.md](github-parsing.md)** — parsing GitHub URLs, extracting PR or issue numbers from URLs, understanding github parsing layers
- **[pathlib-symlinks.md](pathlib-symlinks.md)** — writing file validation code, debugging unexpected path resolution behavior, working with symlinked configuration files
- **[protocol-vs-abc.md](protocol-vs-abc.md)** — choosing between Protocol and ABC for interface design, designing interfaces with structural vs nominal typing, working with frozen dataclasses and Protocol @property patterns
- **[sentinel-path-compatibility.md](sentinel-path-compatibility.md)** — writing functions that check path existence, seeing 'Called .exists() on sentinel path' errors, making functions testable with FakeGit
- **[shell-integration-constraint.md](shell-integration-constraint.md)** — implementing commands that delete the current worktree, debugging directory change issues after worktree operations, understanding why safe_chdir doesn't work for some commands
- **[shell-integration-patterns.md](shell-integration-patterns.md)** — implementing commands with shell integration, fixing shell integration handler issues, understanding script-first output ordering, debugging partial success in destructive commands
- **[subprocess-wrappers.md](subprocess-wrappers.md)** — using subprocess wrappers, executing shell commands, understanding subprocess patterns
- **[symlink-validation-pattern.md](symlink-validation-pattern.md)** — validating @ references in markdown files, validating import paths in configuration, any path validation where source files may be symlinks
- **[worktree-metadata.md](worktree-metadata.md)** — storing per-worktree data, working with worktrees.toml, associating metadata with worktrees
