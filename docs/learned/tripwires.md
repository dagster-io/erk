---
title: Generated Tripwires
read_when:
  - "checking tripwire rules"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Tripwires

Action-triggered rules. You MUST consult these BEFORE taking any matching action.

**CRITICAL: Before modifying Claude CLI error reporting or PromptResult.error format** → Read [Claude CLI Error Reporting](architecture/claude-cli-error-reporting.md) first. Error messages must maintain structured format with exit code, stderr, and context. Changes affect all callers of execute_prompt() and execute_command_streaming().

**CRITICAL: Before using `--output-format stream-json` with `--print` in Claude CLI** → Read [Claude CLI Integration from Python](architecture/claude-cli-integration.md) first. Must also include `--verbose`. Without it, the command fails with 'stream-json requires --verbose'.

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

**CRITICAL: Before calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git.

**CRITICAL: Before calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GraphiteBranchOps sub-gateway, accessible only through BranchManager. Query methods (is_branch_tracked, get_parent_branch, etc.) remain on ctx.graphite.

**CRITICAL: Before calling GraphiteBranchManager.create_branch() without explicit checkout** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. GraphiteBranchManager.create_branch() restores the original branch after tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch.

**CRITICAL: Before refactoring to remove gateway fields from ErkContext** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Verify that all factory functions update consistently: `create_branch_manager()`, `create_minimal_context()`, `context_for_test()`, and all test context constructors. Global search+replace is insufficient; manually verify each factory signature.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must add integration tests in tests/integration/test*real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

**CRITICAL: Before using subprocess.run with git command outside of a gateway** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations.

**CRITICAL: Before adding a new subgateway property to any gateway ABC** → Read [Gateway ABC Implementation Checklist](architecture/gateway-abc-implementation.md) first. Must implement in all 5 layers: abc.py (abstract property), real.py (returns real implementation), fake.py (returns linked fake for mutation tracking), dry_run.py (wraps underlying property), printing.py (wraps with printing delegation). Reference implementations: git.worktree, git.branch.

**CRITICAL: Before calling gt commands without --no-interactive flag** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely. Note: `--force` does NOT prevent prompts - you must use `--no-interactive` separately.

**CRITICAL: Before calling graphite.track_branch() with a remote ref like origin/main** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. Graphite's `gt track` only accepts local branch names, not remote refs. Use BranchManager.create_branch() which normalizes refs automatically, or strip `origin/` prefix before calling track_branch().

**CRITICAL: Before using `gt restack` to resolve branch divergence errors** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. gt restack only handles parent-child stack rebasing, NOT same-branch remote divergence. Use git rebase origin/$BRANCH first.

**CRITICAL: Before using git pull or git pull --rebase on a Graphite-managed branch** → Read [Git and Graphite Edge Cases Catalog](architecture/git-graphite-quirks.md) first. Use /erk:sync-divergence instead. git pull --rebase rewrites commit SHAs outside Graphite's tracking, causing stack divergence that requires manual cleanup with gt sync --restack and force-push.

**CRITICAL: Before using gh issue create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr create in production code** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue view in command documentation** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use `erk exec get-issue-body` instead. `gh issue view` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue edit in command documentation** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Use `erk exec update-issue-body` instead. `gh issue edit` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr view --json merged** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. The `merged` field doesn't exist. Use `mergedAt` instead. Run `gh pr view --help` or check error output for valid field names.

**CRITICAL: Before using gh api or gh api graphql to fetch or resolve PR review threads** → Read [GitHub API Rate Limits](architecture/github-api-rate-limits.md) first. Load `pr-operations` skill first. Use `erk exec get-pr-review-comments` and `erk exec resolve-review-thread` instead. Raw gh api calls miss thread resolution functionality.

**CRITICAL: Before calling execute_gh_command() instead of execute_gh_command_with_retry() for network-sensitive operations** → Read [GitHub API Retry Mechanism](architecture/github-api-retry-mechanism.md) first. Use `execute_gh_command_with_retry()` for operations that may fail due to transient network errors. Pass `time_impl` for testability.

**CRITICAL: Before checking isinstance after RetriesExhausted without type narrowing** → Read [GitHub API Retry Mechanism](architecture/github-api-retry-mechanism.md) first. After checking `isinstance(result, RetriesExhausted)`, the else branch is type-narrowed to the success type. Use `assert isinstance(result, T)` if needed for clarity.

**CRITICAL: Before using gh gist create with --filename flag** → Read [GitHub CLI Quirks and Edge Cases](architecture/github-cli-quirks.md) first. --filename only works with stdin input (-), not file paths.

**CRITICAL: Before constructing gist raw URLs with hardcoded filenames** → Read [GitHub Gist URL Patterns](architecture/github-gist-api.md) first. Use /raw/ without filename - GitHub redirects to first file.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](architecture/github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before implementing mtime-based cache invalidation** → Read [Graphite Cache Invalidation](architecture/graphite-cache-invalidation.md) first. Use triple-check guard pattern: (cache exists) AND (mtime exists) AND (mtime matches). Partial checks cause stale data bugs.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](architecture/not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before using PlanContextProvider** → Read [Plan Context Integration](architecture/plan-context-integration.md) first. Read this doc first. PlanContextProvider returns None on any failure (graceful degradation). Always handle the None case.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](architecture/protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](architecture/subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations.

**CRITICAL: Before using fnmatch for gitignore-style glob patterns** → Read [Convention-Based Code Reviews](ci/convention-based-reviews.md) first. Use pathspec library instead. fnmatch doesn't support \*\* recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)

**CRITICAL: Before implementing change detection without baseline capture** → Read [erk-impl Change Detection](ci/erk-impl-change-detection.md) first. Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER.

**CRITICAL: Before using generic variable names in change detection logic** → Read [erk-impl Change Detection](ci/erk-impl-change-detection.md) first. Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES).

**CRITICAL: Before running prettier on Python files** → Read [Formatter Tools](ci/formatter-tools.md) first. Prettier cannot format Python. Use `ruff format` or `make format` for Python. Prettier only handles Markdown in this project.

**CRITICAL: Before running prettier programmatically on content containing underscore emphasis** → Read [Formatter Tools](ci/formatter-tools.md) first. Prettier converts `__text__` to `**text**` on first pass, then escapes asterisks on second pass. If programmatically applying prettier, run twice to reach stable output.

**CRITICAL: Before interpolating ${{ }} expressions directly into shell command arguments** → Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first. Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first.

**CRITICAL: Before using heredoc (<<) syntax in GitHub Actions YAML** → Read [CI Prompt Patterns](ci/prompt-patterns.md) first. Use `erk exec get-embedded-prompt` instead. Heredocs in YAML `run:` blocks have fragile indentation that causes silent failures.

**CRITICAL: Before creating Claude Code agent commands in .claude/commands/** → Read [Claude Code Agent Command Patterns](claude-code/agent-commands.md) first. Filenames MUST match the command name for discoverability.

**CRITICAL: Before putting checkout-specific helpers in navigation_helpers.py** → Read [Checkout Helpers Module](cli/checkout-helpers.md) first. `src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead.

**CRITICAL: Before adding user-interactive steps (confirmations, prompts) without CI detection** → Read [CI-Aware Commands](cli/ci-aware-commands.md) first. Commands with user interaction must check `in_github_actions()` and skip prompts in CI. Interactive prompts hang indefinitely in GitHub Actions workflows.

**CRITICAL: Before using blocking operations (user confirmation, editor launch) in CI-executed code paths** → Read [CI-Aware Commands](cli/ci-aware-commands.md) first. Check `in_github_actions()` before any blocking operation. CI has no terminal for user input.

**CRITICAL: Before running any erk exec subcommand** → Read [erk exec Commands](cli/erk-exec-commands.md) first. Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance.

**CRITICAL: Before writing PR/issue body generation in exec scripts** → Read [Exec Command Patterns](cli/exec-command-patterns.md) first. Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability.

**CRITICAL: Before using click.confirm() after user_output()** → Read [CLI Output Styling Guide](cli/output-styling.md) first. Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**CRITICAL: Before displaying user-provided text in Rich CLI tables** → Read [CLI Output Styling Guide](cli/output-styling.md) first. Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear.

**CRITICAL: Before writing `__all__` to a Python file** → Read [Code Conventions](conventions.md) first. Re-export modules are forbidden. Import directly from where code is defined.

**CRITICAL: Before adding --force flag to a CLI command** → Read [Code Conventions](conventions.md) first. Always include -f as the short form. Pattern: @click.option("-f", "--force", ...)

**CRITICAL: Before adding a function with 5+ parameters** → Read [Code Conventions](conventions.md) first. Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures and Click command callbacks.

**CRITICAL: Before parsing objective roadmap PR column status** → Read [Erk Glossary](glossary.md) first. PR column format is non-standard: empty=pending, #XXXX=done (merged PR), `plan #XXXX`=plan in progress. This is erk-specific, not GitHub convention.

**CRITICAL: Before reading learn_plan_issue or learn_status** → Read [Learn Plan Metadata Preservation](planning/learn-plan-metadata-fields.md) first. Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

**CRITICAL: Before modifying learn command to add/remove/reorder agents** → Read [Learn Workflow](planning/learn-workflow.md) first. Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output.

**CRITICAL: Before adding new agents to learn workflow** → Read [Learn Workflow](planning/learn-workflow.md) first. Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition.

**CRITICAL: Before manually creating an erk-plan issue with gh issue create** → Read [Plan Lifecycle](planning/lifecycle.md) first. Use `erk exec plan-save-to-issue --plan-file <path>` instead. Manual creation requires complex metadata block format (see Metadata Block Reference section).

**CRITICAL: Before saving a plan with --objective-issue flag** → Read [Plan Lifecycle](planning/lifecycle.md) first. Always verify the link was saved correctly with `erk exec get-plan-metadata <issue> objective_issue`. Silent failures can leave plans unlinked from their objectives.

**CRITICAL: Before implementing custom PR/plan relevance assessment logic** → Read [Plan Lifecycle](planning/lifecycle.md) first. Reference `/local:check-relevance` verdict classification system first. Use SUPERSEDED (80%+ overlap), PARTIALLY_IMPLEMENTED (30-80% overlap), DIFFERENT_APPROACH, STILL_RELEVANT, NEEDS_REVIEW categories for consistency.

**CRITICAL: Before writing to /tmp/** → Read [Scratch Storage](planning/scratch-storage.md) first. AI workflow files belong in .erk/scratch/<session-id>/, NOT /tmp/.

**CRITICAL: Before creating temp files for AI workflows** → Read [Scratch Storage](planning/scratch-storage.md) first. Use worktree-scoped scratch storage for session-specific data.

**CRITICAL: Before analyzing sessions larger than 100k characters** → Read [Scratch Storage](planning/scratch-storage.md) first. Use `erk exec preprocess-session` first. Achieves ~99% token reduction (e.g., 6.2M -> 67k chars). Critical for fitting large sessions in agent context windows.

**CRITICAL: Before checking entry['type'] == 'tool_result' in Claude session JSONL** → Read [Claude Code JSONL Schema Reference](sessions/jsonl-schema-reference.md) first. tool_results are content blocks INSIDE user entries, NOT top-level entry types. Check message.content[].type == 'tool_result' within user entries instead. Load session-inspector skill for correct schema.

**CRITICAL: Before working with session-specific data** → Read [Parallel Session Awareness](sessions/parallel-session-awareness.md) first. Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](testing/exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing/testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**CRITICAL: Before implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing/testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples.

**CRITICAL: Before adding cell values to Textual DataTable** → Read [DataTable Rich Markup Escaping](textual/datatable-markup-escaping.md) first. Always wrap in `Text(value)` if strings contain user data with brackets. Otherwise `[anything]` will be interpreted as Rich markup.

**CRITICAL: Before generating TUI commands that depend on optional PlanRowData fields** → Read [Adding Commands to TUI](tui/adding-commands.md) first. Implement three-layer validation: registry predicate → handler guard → app-level helper. Never rely on registry predicate alone.

**CRITICAL: Before using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](tui/command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.

**CRITICAL: Before modifying how plan titles are displayed in TUI** → Read [TUI Plan Title Rendering Pipeline](tui/plan-title-rendering-pipeline.md) first. Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages.

**CRITICAL: Before using title-stripping functions** → Read [TUI Plan Title Rendering Pipeline](tui/plan-title-rendering-pipeline.md) first. Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling).
