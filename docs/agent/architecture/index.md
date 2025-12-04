# Architecture Documentation

- **[commandresult-extension-pattern.md](commandresult-extension-pattern.md)** — adding new field to CommandResult, extending CommandResult dataclass, adding metadata extraction, implementing new CommandResult field
- **[erk-architecture.md](erk-architecture.md)** — understanding erk architecture, implementing dry-run patterns, regenerating context after os.chdir
- **[github-parsing.md](github-parsing.md)** — parsing GitHub URLs, extracting PR or issue numbers from URLs, understanding github parsing layers
- **[protocol-vs-abc.md](protocol-vs-abc.md)** — choosing between Protocol and ABC for interface design, designing interfaces with structural vs nominal typing, working with frozen dataclasses and Protocol @property patterns
- **[sentinel-path-compatibility.md](sentinel-path-compatibility.md)** — writing functions that check path existence, seeing 'Called .exists() on sentinel path' errors, making functions testable with FakeGit
- **[subprocess-wrappers.md](subprocess-wrappers.md)** — using subprocess wrappers, executing shell commands, understanding subprocess patterns
- **[worktree-metadata.md](worktree-metadata.md)** — storing per-worktree data, working with worktrees.toml, associating metadata with worktrees
