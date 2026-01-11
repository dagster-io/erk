---
title: Generated Tripwires
read_when:
  - "checking tripwire rules"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Tripwires

Action-triggered rules that fire when you're about to perform specific actions.

**CRITICAL: Before passing dry_run boolean flags through business logic function parameters** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use dependency injection with DryRunGit/DryRunGitHub wrappers for multi-step workflows. Simple CLI preview flags at the command level are acceptable for single-action commands.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError.

**CRITICAL: Before importing time module or calling time.sleep()** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use context.time.sleep() for testability. Direct time.sleep() makes tests slow.

**CRITICAL: Before implementing CLI flags that affect post-mutation behavior** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk pr land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target).

**CRITICAL: Before editing docs/agent/index.md or docs/agent/tripwires.md directly** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. These are generated files. Edit the source frontmatter instead, then run 'erk docs sync'.

**CRITICAL: Before comparing worktree path to repo_root to detect root worktree** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently.

**CRITICAL: Before detecting current worktree using path comparisons on cwd** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use git.get_repository_root(cwd) to get the worktree root, then match exactly against known paths. Path comparisons with .exists()/.resolve()/is_relative_to() are fragile.

**CRITICAL: Before checking isinstance(ctx.graphite, GraphiteDisabled) inline in command code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use BranchManager abstraction instead. Add a method to BranchManager ABC that handles both Graphite and Git paths. This centralizes the branching logic and enables testing with FakeBranchManager.

**CRITICAL: Before using os.environ.get("CLAUDE_CODE_SESSION_ID") in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Erk code NEVER has access to this environment variable. Session IDs must be passed via --session-id CLI flags. Hooks receive session ID via stdin JSON, not environment variables.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must add integration tests in tests/integration/test*real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

**CRITICAL: Before using subprocess.run with git command outside of a gateway** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations.

**CRITICAL: Before using gh issue create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](architecture/not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](architecture/protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](architecture/subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI).

**CRITICAL: Before using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](ci/prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.

**CRITICAL: Before using click.confirm() after user_output()** → Read [CLI Output Styling Guide](cli/output-styling.md) first. Use user_confirm() from erk_shared.output instead. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**CRITICAL: Before adding a command with --script flag** → Read [CLI Script Mode](cli/script-mode.md) first. Must register in SHELL_INTEGRATION_COMMANDS with all alias variants (e.g., br land, branch land).

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.

**CRITICAL: Before adding --force flag to a CLI command** → Read [Code Conventions](conventions.md) first. Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)

**CRITICAL: Before adding a function with 5+ parameters** → Read [Code Conventions](conventions.md) first. Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks.

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](planning/scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](sessions/parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing/testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.
