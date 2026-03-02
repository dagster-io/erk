Usage: erk impl [OPTIONS] TARGET

  Create worktree from GitHub issue or plan file and execute implementation.

  By default, runs in interactive mode where you can interact with Claude
  during implementation. Use --no-interactive for automated execution.

  TARGET can be: - GitHub issue number (e.g., #123 or 123) - GitHub issue URL
  (e.g., https://github.com/user/repo/issues/123) - Path to plan file (e.g.,
  ./my-feature-plan.md)

  Note: Plain numbers (e.g., 809) are always interpreted as GitHub issues.
  For files with numeric names, use ./ prefix (e.g., ./809).

  For GitHub issues, the issue must have the 'erk-plan' label.

  Examples:

    # Interactive mode (default)
    erk implement 123

    # Interactive mode, skip permissions
    erk implement 123 --dangerous

    # Non-interactive mode (automated execution)
    erk implement 123 --no-interactive

    # Full CI/PR workflow (requires --no-interactive)
    erk implement 123 --no-interactive --submit

    # YOLO mode - full automation (dangerous + submit + no-interactive)
    erk implement 123 --yolo

    # Shell integration
    source <(erk implement 123 --script)

    # From plan file
    erk implement ./my-feature-plan.md

Options:
  --dry-run         Print what would be executed without doing it
  --submit          Automatically run CI validation and submit PR after
                    implementation
  --dangerous       Skip permission prompts by passing --dangerously-skip-
                    permissions to Claude
  --no-interactive  Execute commands via subprocess without user interaction
  --yolo            Equivalent to --dangerous --submit --no-interactive (full
                    automation)
  --verbose         Show full Claude Code output (default: filtered)
  -m, --model TEXT  Model to use for Claude (haiku/h, sonnet/s, opus/o)
  -f, --force       Auto-unassign oldest slot if pool is full (no interactive
                    prompt).
  -h, --help        Show this message and exit.

Hidden Options:


-------------------------

add -d shortcut/alias for --dangerous
