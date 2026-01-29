---
title: Architecture Tripwires
read_when:
  - "working on architecture code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from architecture/*.md frontmatter -->

# Architecture Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before Archive value to 'last\_' variant BEFORE clearing** → Read [Archive-on-Clear Metadata Pattern](metadata-archival-pattern.md) first. Order matters — clear-then-archive loses the value silently

**CRITICAL: Before Call plan-update-from-feedback after editing local plan files** → Read [Plan File Sync Pattern](plan-file-sync-pattern.md) first. Sync is NOT automatic — GitHub issue will show stale content without explicit sync

**CRITICAL: Before Detect mode in Phase 0 before any other phases execute** → Read [Phase 0 Detection Pattern](phase-zero-detection-pattern.md) first. Late detection leads to starting wrong mode then discovering the error

**CRITICAL: Before GraphiteBranchManager.create_branch() without explicit checkout** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. GraphiteBranchManager.create_branch() restores the original branch after tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding file I/O, network calls, or subprocess invocations to a class **init\***\* → Read [Erk Architecture Patterns](erk-architecture.md) first. Load `dignified-python` skill first. Class **init\*\* should be lightweight (just data assignment). Heavy operations belong in static factory methods like `from_config_path()` or `load()`. This enables direct instantiation in tests without I/O setup.

**CRITICAL: Before adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must add integration tests in tests/integration/test*real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

**CRITICAL: Before calling GraphiteBranchManager.create_branch() without explicit checkout** → Read [Erk Architecture Patterns](erk-architecture.md) first. GraphiteBranchManager.create_branch() restores the original branch after tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch.

**CRITICAL: Before calling checkout_branch() in a multi-worktree repository** → Read [Multi-Worktree State Handling](multi-worktree-state.md) first. Verify the target branch is not already checked out in another worktree using `git.worktree.find_worktree_for_branch()`. Git enforces a single-checkout constraint - attempting to checkout a branch held elsewhere causes silent state corruption or unexpected failures.

**CRITICAL: Before calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git.

**CRITICAL: Before calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git.

**CRITICAL: Before calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GraphiteBranchOps sub-gateway, accessible only through BranchManager. Query methods (is_branch_tracked, get_parent_branch, etc.) remain on ctx.graphite.

**CRITICAL: Before calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GraphiteBranchOps sub-gateway, accessible only through BranchManager. Query methods (is_branch_tracked, get_parent_branch, etc.) remain on ctx.graphite.

**CRITICAL: Before calling execute_gh_command() instead of execute_gh_command_with_retry() for network-sensitive operations** → Read [GitHub API Retry Mechanism](github-api-retry-mechanism.md) first. Use `execute_gh_command_with_retry()` for operations that may fail due to transient network errors. Pass `time_impl` for testability.

**CRITICAL: Before calling graphite.track_branch() with a remote ref like origin/main** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Graphite's `gt track` only accepts local branch names, not remote refs. Use BranchManager.create_branch() which normalizes refs automatically, or strip `origin/` prefix before calling track_branch().

**CRITICAL: Before calling gt commands without --no-interactive flag** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely. Note: `--force` does NOT prevent prompts - you must use `--no-interactive` separately.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](erk-architecture.md) first. After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before checking isinstance after RetriesExhausted without type narrowing** → Read [GitHub API Retry Mechanism](github-api-retry-mechanism.md) first. After checking `isinstance(result, RetriesExhausted)`, the else branch is type-narrowed to the success type. Use `assert isinstance(result, T)` if needed for clarity.

**CRITICAL: Before checking isinstance(ctx.graphite, GraphiteDisabled) inline in command code** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use BranchManager abstraction instead. Add a method to BranchManager ABC that handles both Graphite and Git paths. This centralizes the branching logic and enables testing with FakeBranchManager.

**CRITICAL: Before comparing git SHA to Graphite's tracked SHA for divergence detection** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Ensure both `commit_sha` and `graphite_tracked_sha` are non-None before comparison. Returning False when either is None avoids false negatives on new branches.

**CRITICAL: Before comparing worktree path to repo_root to detect root worktree** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently.

**CRITICAL: Before constructing gist raw URLs with hardcoded filenames** → Read [GitHub Gist URL Patterns](github-gist-api.md) first. Use /raw/ without filename - GitHub redirects to first file.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before designing a new hook or reminder system** → Read [Three-Tier Context Injection Architecture](context-injection-tiers.md) first. Consider the three-tier context architecture. Read docs/learned/architecture/context-injection-tiers.md first.

**CRITICAL: Before detecting current worktree using path comparisons on cwd** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use git.get_repository_root(cwd) to get the worktree root, then match exactly against known paths. Path comparisons with .exists()/.resolve()/is_relative_to() are fragile.

**CRITICAL: Before hand-constructing Plan or PlanRowData with only required fields** → Read [Optional Field Propagation](optional-field-propagation.md) first. Always pass through gateway methods or use dataclasses.replace(). Hand-construction drops optional fields (learn_status, learn_plan_issue, etc.).

**CRITICAL: Before implementing CLI flags that affect post-mutation behavior** → Read [Erk Architecture Patterns](erk-architecture.md) first. Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target).

**CRITICAL: Before implementing mtime-based cache invalidation** → Read [Graphite Cache Invalidation](graphite-cache-invalidation.md) first. Use triple-check guard pattern: (cache exists) AND (mtime exists) AND (mtime matches). Partial checks cause stale data bugs.

**CRITICAL: Before importing time module or calling time.sleep() or datetime.now()** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use context.time.sleep() and context.time.now() for testability. Direct time.sleep() makes tests slow and datetime.now() makes tests non-deterministic.

**CRITICAL: Before injecting Time dependency into gateway real.py for lock-waiting or retry logic** → Read [Erk Architecture Patterns](erk-architecture.md) first. Accept optional Time in **init** with default to RealTime(). Use injected dependency in methods. This enables testing with FakeTime without blocking. See packages/erk-shared/src/erk_shared/gateway/git/lock.py for pattern.

**CRITICAL: Before migrating git method calls after subgateway extraction** → Read [Gateway Decomposition Phases](gateway-decomposition-phases.md) first. The following methods have been moved from the Git ABC to subgateways: `git.fetch_branch()` → `git.remote.fetch_branch()` (Phase 3), `git.push_to_remote()` → `git.remote.push_to_remote()` (Phase 3), `git.commit()` → `git.commit.commit()` (Phase 4), `git.stage_files()` → `git.commit.stage_files()` (Phase 4), `git.has_staged_changes()` → `git.status.has_staged_changes()` (Phase 5), `git.rebase_onto()` → `git.rebase.rebase_onto()` (Phase 6), `git.tag_exists()` → `git.tag.tag_exists()` (Phase 7), `git.create_tag()` → `git.tag.create_tag()` (Phase 7). Calling the old API will raise `AttributeError`. Always use the subgateway property.

**CRITICAL: Before modifying Claude CLI error reporting or PromptResult.error format** → Read [Claude CLI Error Reporting](claude-cli-error-reporting.md) first. Error messages must maintain structured format with exit code, stderr, and context. Changes affect all callers of execute_prompt() and execute_command_streaming().

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before passing dry_run boolean flags through business logic function parameters** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use dependency injection with DryRunGit/DryRunGitHub wrappers for multi-step workflows. Simple CLI preview flags at the command level are acceptable for single-action commands.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before raising exceptions for expected failure cases in business logic** → Read [Discriminated Union Error Handling](discriminated-union-error-handling.md) first. Use discriminated unions (T | ErrorType) instead. Exceptions are for truly exceptional conditions, not business logic failures.

**CRITICAL: Before reading from or writing to ~/.claude/ paths using Path.home() directly** → Read [ClaudeInstallation Gateway](claude-installation-gateway.md) first. Use ClaudeInstallation gateway instead. All ~/.claude/ filesystem operations should go through this gateway for testability and abstraction.

**CRITICAL: Before using PlanContextProvider** → Read [Plan Context Integration](plan-context-integration.md) first. Read this doc first. PlanContextProvider returns None on any failure (graceful degradation). Always handle the None case.

**CRITICAL: Before using `--output-format stream-json` with `--print` in Claude CLI** → Read [Claude CLI Integration from Python](claude-cli-integration.md) first. Must also include `--verbose`. Without it, the command fails with 'stream-json requires --verbose'.

**CRITICAL: Before using `gt restack` to resolve branch divergence errors** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. gt restack only handles parent-child stack rebasing, NOT same-branch remote divergence. Use git rebase origin/$BRANCH first.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations.

**CRITICAL: Before using gh api or gh api graphql to fetch or resolve PR review threads** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Load `pr-operations` skill first. Use `erk exec get-pr-review-comments` and `erk exec resolve-review-thread` instead. Raw gh api calls miss thread resolution functionality.

**CRITICAL: Before using gh gist create with --filename flag** → Read [GitHub CLI Quirks and Edge Cases](github-cli-quirks.md) first. --filename only works with stdin input (-), not file paths.

**CRITICAL: Before using gh issue create in production code** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue edit in command documentation** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use `erk exec update-issue-body` instead. `gh issue edit` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue view in command documentation** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use `erk exec get-issue-body` instead. `gh issue view` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr create in production code** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr diff --name-only in production code** → Read [GitHub CLI Limits](github-cli-limits.md) first. For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead.

**CRITICAL: Before using gh pr view --json merged** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. The `merged` field doesn't exist. Use `mergedAt` instead. Run `gh pr view --help` or check error output for valid field names.

**CRITICAL: Before using git pull or git pull --rebase on a Graphite-managed branch** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Use /erk:sync-divergence instead. git pull --rebase rewrites commit SHAs outside Graphite's tracking, causing stack divergence that requires manual cleanup with gt sync --restack and force-push.

**CRITICAL: Before using os.environ.get("CLAUDE_CODE_SESSION_ID") in erk code** → Read [Erk Architecture Patterns](erk-architecture.md) first. Erk code NEVER has access to this environment variable. Session IDs must be passed via --session-id CLI flags. Hooks receive session ID via stdin JSON, not environment variables.

**CRITICAL: Before using subprocess.run with git command outside of a gateway** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.gateway.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations.
