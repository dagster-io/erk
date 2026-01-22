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

**CRITICAL: Before importing time module or calling time.sleep() or datetime.now()** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use context.time.sleep() and context.time.now() for testability. Direct time.sleep() makes tests slow and datetime.now() makes tests non-deterministic.

**CRITICAL: Before implementing CLI flags that affect post-mutation behavior** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk pr land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target).

**CRITICAL: Before comparing worktree path to repo_root to detect root worktree** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently.

**CRITICAL: Before detecting current worktree using path comparisons on cwd** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use git.get_repository_root(cwd) to get the worktree root, then match exactly against known paths. Path comparisons with .exists()/.resolve()/is_relative_to() are fragile.

**CRITICAL: Before checking isinstance(ctx.graphite, GraphiteDisabled) inline in command code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use BranchManager abstraction instead. Add a method to BranchManager ABC that handles both Graphite and Git paths. This centralizes the branching logic and enables testing with FakeBranchManager.

**CRITICAL: Before using os.environ.get("CLAUDE_CODE_SESSION_ID") in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Erk code NEVER has access to this environment variable. Session IDs must be passed via --session-id CLI flags. Hooks receive session ID via stdin JSON, not environment variables.

**CRITICAL: Before injecting Time dependency into gateway real.py for lock-waiting or retry logic** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Accept optional Time in **init** with default to RealTime(). Use injected dependency in methods. This enables testing with FakeTime without blocking. See packages/erk-shared/src/erk_shared/git/lock.py for pattern.

**CRITICAL: Before adding file I/O, network calls, or subprocess invocations to a class **init\***\* → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Load `dignified-python` skill first. Class **init\*\* should be lightweight (just data assignment). Heavy operations belong in static factory methods like `from_config_path()` or `load()`. This enables direct instantiation in tests without I/O setup.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must add integration tests in tests/integration/test*real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

**CRITICAL: Before using subprocess.run with git command outside of a gateway** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations.

**CRITICAL: Before calling gt commands without --no-interactive flag** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely. Note: `--force` does NOT prevent prompts - you must use `--no-interactive` separately.

**CRITICAL: Before calling graphite.track_branch() with a remote ref like origin/main** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. Graphite's `gt track` only accepts local branch names, not remote refs. Use BranchManager.create_branch() which normalizes refs automatically, or strip `origin/` prefix before calling track_branch().

**CRITICAL: Before using gh issue create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue view in command documentation** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use `erk exec get-issue-body` instead. `gh issue view` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue edit in command documentation** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use `erk exec update-issue-body` instead. `gh issue edit` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](architecture/not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](architecture/protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](architecture/subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations.

**CRITICAL: Before using fnmatch for gitignore-style glob patterns** → Read [Convention-Based Code Reviews](ci/convention-based-reviews.md) first. Use pathspec library instead. fnmatch doesn't support \*\* recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)

**CRITICAL: Before running prettier on Python files** → Read [Formatter Tools](ci/formatter-tools.md) first. Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project.

**CRITICAL: Before running prettier programmatically on content containing underscore emphasis** → Read [Formatter Tools](ci/formatter-tools.md) first. Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output.

**CRITICAL: Before interpolating ${{ }} expressions directly into shell command arguments** → Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first. Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first.

**CRITICAL: Before using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](ci/prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.

**CRITICAL: Before putting checkout-specific helpers in navigation_helpers.py** → Read [Checkout Helpers Module](cli/checkout-helpers.md) first. `src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead.

**CRITICAL: Before using click.confirm() after user_output()** → Read [CLI Output Styling Guide](cli/output-styling.md) first. Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.

**CRITICAL: Before adding --force flag to a CLI command** → Read [Code Conventions](conventions.md) first. Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)

**CRITICAL: Before adding a function with 5+ parameters** → Read [Code Conventions](conventions.md) first. Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks.

**CRITICAL: Before manually creating an erk-plan issue with gh issue create** → Read [Plan Lifecycle](planning/lifecycle.md) first. Use `erk exec plan-save-to-issue --plan-file <path>` instead. Manual creation requires complex metadata block format (see Metadata Block Reference section).

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](planning/scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before checking entry['type'] == 'tool_result' in Claude session JSONL** → Read [Claude Code JSONL Schema Reference](sessions/jsonl-schema-reference.md) first. tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](sessions/parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing/testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**CRITICAL: Before using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](tui/command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.
