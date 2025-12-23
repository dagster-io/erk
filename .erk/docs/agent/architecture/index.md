<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Architecture Documentation

- **[abc-convenience-methods.md](abc-convenience-methods.md)** — adding non-abstract methods to gateway ABCs, composing primitive gateway operations into higher-level methods, handling exception type differences between real and fake implementations
- **[at-reference-resolution.md](at-reference-resolution.md)** — Modifying @ reference validation, Debugging broken @ references in symlinked files, Understanding why validation passes but Claude Code fails
- **[claude-cli-integration.md](claude-cli-integration.md)** — Invoking Claude from Python, Spawning Claude CLI from Python code, Understanding non-interactive vs interactive modes
- **[claude-cli-progress.md](claude-cli-progress.md)** — adding progress output to Claude operations, wrapping Claude CLI with user feedback, using ProgressEvent or CompletionEvent, converting blocking operations to streaming progress
- **[claude-executor-patterns.md](claude-executor-patterns.md)** — launching Claude from CLI commands, deciding which ClaudeExecutor method to use, testing code that executes Claude CLI
- **[cli-binary-ops-pattern.md](cli-binary-ops-pattern.md)** — wrapping external CLI binary, testing subprocess calls, creating fake for external tool
- **[command-boundaries.md](command-boundaries.md)** — Choosing between agent vs CLI command, Deciding when to use .claude/commands/ vs src/erk/cli/, Understanding when AI capabilities are needed
- **[commandresult-extension-pattern.md](commandresult-extension-pattern.md)** — adding new field to CommandResult, extending CommandResult dataclass, adding metadata extraction, implementing new CommandResult field
- **[erk-architecture.md](erk-architecture.md)** — understanding erk architecture, implementing dry-run patterns, regenerating context after os.chdir, detecting root worktree
- **[erk-shared-package.md](erk-shared-package.md)** — sharing code between erk and erk-kits, deciding where to put new utilities, moving code between packages
- **[event-progress-pattern.md](event-progress-pattern.md)** — implementing operations that need progress reporting, separating business logic from UI output, building testable CLI operations, using ProgressEvent or CompletionEvent
- **[extraction-origin-tracking.md](extraction-origin-tracking.md)** — understanding how extraction PRs are identified, modifying erk pr land behavior, working with erk-skip-extraction label
- **[gateway-abc-implementation.md](gateway-abc-implementation.md)** — adding or modifying methods in any gateway ABC interface (Git, GitHub, Graphite), implementing new gateway operations
- **[gateway-inventory.md](gateway-inventory.md)** — understanding available gateways, adding a new gateway, creating test doubles for external services
- **[generated-files.md](generated-files.md)** — understanding how agent docs sync works, debugging generated file issues, adding new generated file types
- **[git-graphite-quirks.md](git-graphite-quirks.md)** — debugging unexpected git/gt behavior, handling rebase/restack edge cases, writing conflict detection logic, troubleshooting detached HEAD states
- **[github-graphql.md](github-graphql.md)** — using gh api graphql, writing GraphQL queries for GitHub, passing variables to GraphQL queries, fetching data not available in REST API
- **[github-interface-patterns.md](github-interface-patterns.md)** — calling GitHub API from erk, working with gh api command, fetching PR or issue data efficiently, understanding PRDetails type
- **[github-parsing.md](github-parsing.md)** — parsing GitHub URLs, extracting PR or issue numbers from URLs, understanding github parsing layers
- **[github-pr-linkage-api.md](github-pr-linkage-api.md)** — querying PRs linked to an issue, understanding how GitHub tracks issue-PR relationships, debugging why a PR doesn't show as linked to an issue, working with CrossReferencedEvent or closingIssuesReferences
- **[impl-folder-lifecycle.md](impl-folder-lifecycle.md)** — working with .impl/ or .worker-impl/ folders, understanding remote implementation workflow, debugging plan visibility in PRs
- **[issue-reference-flow.md](issue-reference-flow.md)** — issue references not appearing in PRs, debugging 'Closes #N' in PR body, working with issue.json
- **[markers.md](markers.md)** — creating worktree state tracking, adding friction before destructive operations, implementing pending extraction workflow
- **[not-found-sentinel.md](not-found-sentinel.md)** — designing return types for lookup operations, handling missing resource cases without exceptions, checking if get_pr_for_branch() returned a PR, working with GitHub PR lookup results
- **[pathlib-symlinks.md](pathlib-symlinks.md)** — Writing file validation code, Debugging unexpected path resolution behavior, Working with symlinked configuration files
- **[pr-finalization-paths.md](pr-finalization-paths.md)** — debugging PR body content or issue closing, understanding local vs remote PR submission, working with 'Closes #N' in PRs
- **[pre-destruction-capture.md](pre-destruction-capture.md)** — implementing operations that destroy or transform data, designing pipelines with data capture requirements, working with git squash, rebase, or other destructive operations
- **[protocol-vs-abc.md](protocol-vs-abc.md)** — choosing between Protocol and ABC for interface design, designing interfaces with structural vs nominal typing, working with frozen dataclasses and Protocol @property patterns
- **[restack-operations.md](restack-operations.md)** — implementing or modifying restack operations, understanding preflight/continue/finalize pattern, working with RestackPreflightSuccess/Error types, adding new three-phase operations
- **[sentinel-path-compatibility.md](sentinel-path-compatibility.md)** — writing functions that check path existence, seeing 'Called .exists() on sentinel path' errors, making functions testable with FakeGit
- **[shell-integration-constraint.md](shell-integration-constraint.md)** — implementing commands that delete the current worktree, debugging directory change issues after worktree operations, understanding why safe_chdir doesn't work for some commands
- **[shell-integration-patterns.md](shell-integration-patterns.md)** — implementing commands with shell integration, fixing shell integration handler issues, understanding script-first output ordering, debugging partial success in destructive commands
- **[subprocess-wrappers.md](subprocess-wrappers.md)** — using subprocess wrappers, executing shell commands, understanding subprocess patterns
- **[symlink-validation-pattern.md](symlink-validation-pattern.md)** — Validating @ references in markdown files, Validating import paths in configuration, Any path validation where source files may be symlinks
- **[uvx-hooks.md](uvx-hooks.md)** — implementing plugin hooks with uvx, understanding erk hook script architecture, debugging hook version issues
- **[worktree-metadata.md](worktree-metadata.md)** — storing per-worktree data, working with worktrees.toml, associating metadata with worktrees, implementing subdirectory navigation, preserving relative path on worktree switch
