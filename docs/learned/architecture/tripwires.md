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

**CRITICAL: Before Call plan-update-issue after editing local plan files** → Read [Plan File Sync Pattern](plan-file-sync-pattern.md) first. Sync is NOT automatic — GitHub issue will show stale content without explicit sync

**CRITICAL: Before Detect mode in Phase 0 before any other phases execute** → Read [Phase 0 Detection Pattern](phase-zero-detection-pattern.md) first. Late detection wastes work and creates scattered conditionals across all phases

**CRITICAL: Before Parsing CalledProcessError messages for git operations** → Read [Git Operation Patterns](git-operation-patterns.md) first. Avoid parsing git error messages to determine failure modes. Use LBYL with git show-ref --verify to check existence before operations, or design discriminated unions that handle all returncode cases explicitly.

**CRITICAL: Before Prefer the Write tool over bash heredocs for large agent outputs** → Read [Heredoc Quoting and Escaping in Agent-Generated Bash](bash-python-integration.md) first. heredocs fail silently with special characters

**CRITICAL: Before RealLiveDisplay writes to stderr by default (matches erk's user_output convention)** → Read [LiveDisplay Gateway](live-display-gateway.md) first. stdout is reserved for structured data

**CRITICAL: Before Rely solely on agent-level enforcement for critical rules** → Read [Defense-in-Depth Enforcement](defense-in-depth-enforcement.md) first. Add skill-level and PR-level enforcement layers. Only workflow/CI enforcement is truly reliable.

**CRITICAL: Before Return pre-rendered display strings from backend APIs** → Read [State Derivation Pattern](state-derivation-pattern.md) first. Return raw state fields instead. Derive display state in frontend pure functions for testability and reusability.

**CRITICAL: Before accessing properties on a discriminated union result without isinstance() check** → Read [Discriminated Union Error Handling](discriminated-union-error-handling.md) first. Always check isinstance(result, ErrorType) before accessing success-variant properties. Without type narrowing, you may access .message on a success type or .data on an error type.

**CRITICAL: Before adding HTML, badges, or GitHub-specific markup to commit messages** → Read [PR Body Formatting Pattern](pr-body-formatting.md) first. Use the two-target pattern: plain text pr_body for commits, enhanced pr_body_for_github for the PR. Never put GitHub-specific HTML into git commit messages.

**CRITICAL: Before adding a new method to Git ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to GitHub ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a new method to Graphite ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py.

**CRITICAL: Before adding a parameter to an erk exec script without updating the calling slash command** → Read [Parameter Threading Pattern](parameter-threading-pattern.md) first. 3-layer parameter threading: When adding a parameter, update all three layers: skill SKILL.md argument-hint, slash command .md, and erk exec script. Verify all invocations thread the parameter through.

**CRITICAL: Before adding a subgateway property to a gateway ABC** → Read [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) first. Must implement property in 5 places: ABC with TYPE_CHECKING import guard, Real with concrete instance, Fake with linked state, DryRun wrapping inner subgateway, Printing wrapping with script_mode/dry_run.

**CRITICAL: Before adding file I/O, network calls, or subprocess invocations to a class **init\***\* → Read [Erk Architecture Patterns](erk-architecture.md) first. Load `dignified-python` skill first. Class **init\*\* should be lightweight (just data assignment). Heavy operations belong in static factory methods like `from_config_path()` or `load()`. This enables direct instantiation in tests without I/O setup.

**CRITICAL: Before adding optional fields to pipeline state without defaults** → Read [State Threading Pattern](state-threading-pattern.md) first. New pipeline state fields must have defaults (usually None) to avoid breaking make_initial_state() factories. See optional-field-propagation.md for the pattern.

**CRITICAL: Before adding re-exports to gateway implementation modules** → Read [Re-Export Pattern](re-export-pattern.md) first. Only re-export types that genuinely improve public API. Add # noqa: F401 - re-exported for <reason> comment.

**CRITICAL: Before adding subprocess.run or run_subprocess_with_context calls to a gateway real.py file** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must add integration tests in tests/integration/test*real*\*.py. Real gateway methods with subprocess calls need tests that verify the actual subprocess behavior.

**CRITICAL: Before amending a commit when Graphite is enabled** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. After amending commits or running gt restack, Graphite's cache may not update, leaving branches diverged. Call retrack_branch() to fix tracking. The auto-fix is already implemented in sync_cmd and branch_manager.

**CRITICAL: Before assuming GitHub API failures are transient without repository-specific testing** → Read [GitHub API Diagnostics](github-api-diagnostics.md) first. Test with a control repository first. Some GitHub bugs affect specific repos but not others. Follow the 3-step diagnostic methodology.

**CRITICAL: Before assuming cursor position will persist across DataTable.clear() calls** → Read [Selection Preservation by Value](selection-preservation-by-value.md) first. Save cursor position by row key before clear(), restore after repopulating. See textual/quirks.md for pattern.

**CRITICAL: Before build_codespace_ssh_command() bootstraps the environment** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. don't duplicate setup

**CRITICAL: Before calling GraphiteBranchManager.create_branch() without explicit checkout** → Read [Erk Architecture Patterns](erk-architecture.md) first. GraphiteBranchManager.create_branch() restores the original branch after tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch.

**CRITICAL: Before calling checkout_branch() in a multi-worktree repository** → Read [Multi-Worktree State Handling](multi-worktree-state.md) first. Verify the target branch is not already checked out in another worktree using `git.worktree.find_worktree_for_branch()`. Git enforces a single-checkout constraint - attempting to checkout a branch held elsewhere causes silent state corruption or unexpected failures.

**CRITICAL: Before calling create_branch() and assuming you're on the new branch** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. GraphiteBranchManager.create_branch() restores the original branch after Graphite tracking. Always call branch_manager.checkout_branch() afterward if you need to be on the new branch.

**CRITICAL: Before calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager. Query methods (get_current_branch, list_local_branches, etc.) remain on ctx.git.

**CRITICAL: Before calling ctx.git.branch mutation methods directly (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. Use ctx.branch_manager instead for all user-facing branches. Only use ctx.git.branch directly for ephemeral/placeholder branches that should never be Graphite-tracked. See branch-manager-decision-tree.md.

**CRITICAL: Before calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use ctx.branch_manager instead. Branch mutation methods are in GraphiteBranchOps sub-gateway, accessible only through BranchManager. Query methods (is_branch_tracked, get_parent_branch, etc.) remain on ctx.graphite.

**CRITICAL: Before calling ctx.graphite_branch_ops mutation methods directly (track_branch, delete_branch, submit_branch)** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. Use ctx.branch_manager instead. GraphiteBranchOps is a sub-gateway that BranchManager delegates to internally. Direct calls bypass the dual-mode abstraction.

**CRITICAL: Before calling delete_branch() without passing the force parameter through** → Read [BranchManager Abstraction](branch-manager-abstraction.md) first. The force flag controls -D (force) vs -d (safe) git delete. Dropping it silently changes behavior. Always flow force=force through all layers.

**CRITICAL: Before calling execute_gh_command() instead of execute_gh_command_with_retry() for network-sensitive operations** → Read [GitHub API Retry Mechanism](github-api-retry-mechanism.md) first. Use `execute_gh_command_with_retry()` for operations that may fail due to transient network errors. Pass `time_impl` for testability.

**CRITICAL: Before calling get_X() and handling IssueNotFound sentinel inline** → Read [LBYL Gateway Pattern](lbyl-gateway-pattern.md) first. Check with X_exists() first for cleaner error messages and LBYL compliance.

**CRITICAL: Before calling graphite.track_branch() with a remote ref like origin/main** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Graphite's `gt track` only accepts local branch names, not remote refs. Use BranchManager.create_branch() which normalizes refs automatically, or strip `origin/` prefix before calling track_branch().

**CRITICAL: Before calling gt commands without --no-interactive flag** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Always use `--no-interactive` with gt commands (gt sync, gt submit, gt restack, etc.). Without this flag, gt may prompt for user input and hang indefinitely. Note: `--force` does NOT prevent prompts - you must use `--no-interactive` separately.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](erk-architecture.md) first. After os.chdir(), regenerate context using regenerate_context(ctx). Stale ctx.cwd causes FileNotFoundError.

**CRITICAL: Before changing a gateway method signature** → Read [Gateway Signature Migration](gateway-signature-migration.md) first. Search for ALL callers with grep before changing. PR #6329 migrated 8 call sites across 7 files. Missing a call site causes runtime errors.

**CRITICAL: Before changing config section names ([interactive-claude] or [interactive-agent])** → Read [Interactive Agent Configuration](interactive-agent-config.md) first. Maintain fallback from [interactive-agent] to [interactive-claude] for backward compatibility.

**CRITICAL: Before changing gateway return type to discriminated union** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Verify all 5 implementations import the new types. Missing imports in abc.py, fake.py, dry_run.py, or printing.py break the gateway pattern.

**CRITICAL: Before changing permission_mode_to_claude() (or future permission_mode_to_codex()) implementations** → Read [PermissionMode Abstraction](permission-modes.md) first. Verify both Claude and Codex backend implementations maintain identical enum-to-mode mappings.

**CRITICAL: Before checking if get_pr_for_branch() returned a PR** → Read [Not-Found Sentinel Pattern](not-found-sentinel.md) first. Use `isinstance(pr, PRNotFound)` not `pr is not None`. PRNotFound is a sentinel object, not None.

**CRITICAL: Before checking isinstance after RetriesExhausted without type narrowing** → Read [GitHub API Retry Mechanism](github-api-retry-mechanism.md) first. After checking `isinstance(result, RetriesExhausted)`, the else branch is type-narrowed to the success type. Use `assert isinstance(result, T)` if needed for clarity.

**CRITICAL: Before checking isinstance(ctx.graphite, GraphiteDisabled) inline in command code** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use BranchManager abstraction instead. Add a method to BranchManager ABC that handles both Graphite and Git paths. This centralizes the branching logic and enables testing with FakeBranchManager.

**CRITICAL: Before choosing between exceptions and discriminated unions for operation failures** → Read [Discriminated Union Error Handling](discriminated-union-error-handling.md) first. If callers branch on the error and continue the operation, use discriminated unions. If all callers just terminate and surface the message, use exceptions. Read the 'When to Use' section.

**CRITICAL: Before choosing between execute_prompt() modes** → Read [Prompt Executor Gateway](prompt-executor-gateway.md) first. execute_prompt() supports both single-shot and streaming modes - choose based on whether you need real-time updates

**CRITICAL: Before choosing output stream for LiveDisplay** → Read [LiveDisplay Gateway](live-display-gateway.md) first. RealLiveDisplay writes to stderr by default (matches erk's user_output convention) — stdout is reserved for structured data

**CRITICAL: Before comparing git SHA to Graphite's tracked SHA for divergence detection** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Ensure both `commit_sha` and `graphite_tracked_sha` are non-None before comparison. Returning False when either is None avoids false negatives on new branches.

**CRITICAL: Before comparing worktree path to repo_root to detect root worktree** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use WorktreeInfo.is_root instead of path comparison. Path comparison fails when running from within a non-root worktree because ctx.cwd resolves differently.

**CRITICAL: Before constructing gist raw URLs with hardcoded filenames** → Read [GitHub Gist URL Patterns](github-gist-api.md) first. Use /raw/ without filename - GitHub redirects to first file.

**CRITICAL: Before creating Protocol with bare attributes for frozen dataclasses** → Read [Protocol vs ABC Interface Design Guide](protocol-vs-abc.md) first. Use @property decorators in Protocol for frozen dataclass compatibility. Bare attributes cause type errors.

**CRITICAL: Before creating a new complex command with multiple validation steps** → Read [Linear Pipeline Architecture](linear-pipelines.md) first. Consider two-pipeline pattern: validation pipeline (check preconditions) + execution pipeline (perform operations). Use discriminated unions (State | Error) for pipeline steps. Reference land_pipeline.py as exemplar.

**CRITICAL: Before creating branches in erk code** → Read [Branch Manager Decision Tree](branch-manager-decision-tree.md) first. Use the decision tree to determine whether to use ctx.branch_manager (with Graphite tracking) or ctx.git.branch (low-level git). Placeholder/ephemeral branches bypass branch_manager.

**CRITICAL: Before creating fake subgateway without shared state** → Read [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) first. Fake subgateways must share state containers with parent via constructor parameters and call link_mutation_tracking(). Without this, mutations through subgateway won't be visible to parent queries.

**CRITICAL: Before deleting a gateway after consolidating into another** → Read [Gateway Removal Pattern](gateway-removal-pattern.md) first. Follow complete removal checklist: verify no references, delete all 5 layers, clean up compositions, update docs, run full test suite.

**CRITICAL: Before designing a new hook or reminder system** → Read [Context Injection Architecture](context-injection-tiers.md) first. Consider the three-tier context architecture and consolidation patterns. Read docs/learned/architecture/context-injection-tiers.md first.

**CRITICAL: Before designing error handling for a new gateway method** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Ask: does the caller continue after the failure? If yes, use discriminated union. If all callers terminate, use exceptions. See 'Non-Ideal State Decision Checklist' section.

**CRITICAL: Before detecting current worktree using path comparisons on cwd** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use git.get_repository_root(cwd) to get the worktree root, then match exactly against known paths. Path comparisons with .exists()/.resolve()/is_relative_to() are fragile.

**CRITICAL: Before duplicating environment setup in remote commands** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. build_codespace_ssh_command() bootstraps the environment - don't duplicate setup

**CRITICAL: Before executing remote commands on codespaces** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. always start_codespace() before executing commands to ensure the environment is ready
**CRITICAL: Before executing remote commands without proper startup** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. Always start_codespace() before executing remote commands
**CRITICAL: Before executing remote commands without starting codespace** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. Always start_codespace() before executing remote commands
**CRITICAL: Before expecting execute_interactive() to return** → Read [Prompt Executor Gateway](prompt-executor-gateway.md) first. execute_interactive() never returns in production - it replaces the process via os.execvp
**CRITICAL: Before expecting status to auto-update after manual PR edits** → Read [Roadmap Mutation Semantics](roadmap-mutation-semantics.md) first. Only the update-roadmap-step command writes computed status. Manual GitHub edits or direct body mutations leave status at its current value — you must explicitly set status to '-' to enable inference on next parse.

**CRITICAL: Before generating large agent outputs via bash heredocs** → Read [Heredoc Quoting and Escaping in Agent-Generated Bash](bash-python-integration.md) first. Prefer the Write tool over bash heredocs for large agent outputs — heredocs fail silently with special characters

**CRITICAL: Before hand-constructing frozen dataclass instances with selective field copying** → Read [Optional Field Propagation](optional-field-propagation.md) first. Always use dataclasses.replace() to preserve all fields. Hand-construction with partial field copying silently drops optional fields (learn_status, learn_plan_issue, objective_issue, etc.).

**CRITICAL: Before implementing CLI flags that affect post-mutation behavior** → Read [Erk Architecture Patterns](erk-architecture.md) first. Validate flag preconditions BEFORE any mutations. Example: `--up` in `erk land` checks for child branches before merging PR. This prevents partial state (PR merged, worktree deleted, but no valid navigation target).

**CRITICAL: Before implementing a cleanup operation that modifies metadata based on external API success** → Read [Fail-Open Pattern](fail-open-patterns.md) first. Use fail-open pattern. If critical step fails, do NOT execute dependent steps that modify persistent state.

**CRITICAL: Before implementing custom environment setup for remote commands** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. build_codespace_ssh_command() already bootstraps the environment - don't duplicate setup
**CRITICAL: Before implementing idempotent operations that fail on missing resources** → Read [LBYL Gateway Pattern](lbyl-gateway-pattern.md) first. Use LBYL existence check to return early, making the operation truly idempotent.
**CRITICAL: Before implementing interactive commands for remote execution** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. Interactive commands need exec_ssh_interactive(), not run_ssh_command()
**CRITICAL: Before implementing interactive remote commands** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. use exec_ssh_interactive(), not run_ssh_command() which cannot handle user input

**CRITICAL: Before implementing mtime-based cache invalidation** → Read [Graphite Cache Invalidation](graphite-cache-invalidation.md) first. Use triple-check guard pattern: (cache exists) AND (mtime exists) AND (mtime matches). Partial checks cause stale data bugs.

**CRITICAL: Before importing time module or calling time.sleep() or datetime.now()** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use context.time.sleep() and context.time.now() for testability. Direct time.sleep() makes tests slow and datetime.now() makes tests non-deterministic.

**CRITICAL: Before injecting Time dependency into gateway real.py for lock-waiting or retry logic** → Read [Erk Architecture Patterns](erk-architecture.md) first. Accept optional Time in **init** with default to RealTime(). Use injected dependency in methods. This enables testing with FakeTime without blocking. See packages/erk-shared/src/erk_shared/gateway/git/lock.py for pattern.

**CRITICAL: Before migrating a gateway method to return discriminated union** → Read [Discriminated Union Error Handling](discriminated-union-error-handling.md) first. Update ALL 5 implementations (ABC, real, fake, dry_run, printing) AND all call sites AND tests. Incomplete migrations break type safety.

**CRITICAL: Before migrating git method calls after subgateway extraction** → Read [Gateway Decomposition Phases](gateway-decomposition-phases.md) first. The following methods have been moved from the Git ABC to subgateways: `git.fetch_branch()` → `git.remote.fetch_branch()` (Phase 3), `git.push_to_remote()` → `git.remote.push_to_remote()` (Phase 3), `git.commit()` → `git.commit.commit()` (Phase 4), `git.stage_files()` → `git.commit.stage_files()` (Phase 4), `git.has_staged_changes()` → `git.status.has_staged_changes()` (Phase 5), `git.rebase_onto()` → `git.rebase.rebase_onto()` (Phase 6), `git.tag_exists()` → `git.tag_exists()` (Phase 7), `git.create_tag()` → `git.tag.create_tag()` (Phase 7). Calling the old API will raise `AttributeError`. Always use the subgateway property.

**CRITICAL: Before mixing discriminated unions with exception-based cleanup in a single method** → Read [Mixed Exception/Union Pattern (Deprecated)](gateway-specific-patterns.md) first. This pattern was tried in PR #6347 and reverted in PR #6375. Message-only discriminated unions with no domain-meaningful variants add complexity without value. Use exceptions for all error cases, or use discriminated unions with meaningful variants throughout. Document why in the PR.

**CRITICAL: Before modifying Claude CLI error reporting or PromptResult.error format** → Read [Claude CLI Error Reporting](claude-cli-error-reporting.md) first. Error messages must maintain structured format with exit code, stderr, and context. Changes affect all callers of execute_prompt() and execute_command_streaming().

**CRITICAL: Before modifying InteractiveAgentConfig fields or config file format** → Read [Interactive Agent Configuration](interactive-agent-config.md) first. Update both config loading (RealErkInstallation.load_config) and usage sites. Check backward compatibility with [interactive-claude] section.

**CRITICAL: Before modifying PR footer format** → Read [PR Footer Format Validation](pr-footer-validation.md) first. Update generator, parser, AND validator in sync. Add support for new format BEFORE deprecating old format. Never break parsing of existing PRs.

**CRITICAL: Before modifying PermissionMode enum or permission mode mappings** → Read [PermissionMode Abstraction](permission-modes.md) first. permission_mode_to_claude() (and future permission_mode_to_codex()) must stay in sync. Update both when changing mappings.

**CRITICAL: Before mutating pipeline state directly instead of using dataclasses.replace()** → Read [State Threading Pattern](state-threading-pattern.md) first. Pipeline state must be frozen. Use dataclasses.replace() to create new state at each step.

**CRITICAL: Before omitting -t flag for SSH connections** → Read [SSH Command Execution Patterns](ssh-command-execution.md) first. missing -t flag prevents TTY allocation and breaks interactive programs
**CRITICAL: Before omitting -t flag for interactive programs** → Read [SSH Command Execution Patterns](ssh-command-execution.md) first. Missing -t flag prevents TTY allocation and breaks interactive programs
**CRITICAL: Before passing SSH commands to subprocess** → Read [SSH Command Execution Patterns](ssh-command-execution.md) first. SSH command must be a single string argument, not multiple shell words

**CRITICAL: Before passing array or object variables to gh api graphql with -F and json.dumps()** → Read [GitHub GraphQL API Patterns](github-graphql.md) first. Arrays and objects require special gh syntax: arrays use -f key[]=value1 -f key[]=value2, objects use -f key[subkey]=value. Using -F key=[...] or -F key={...} passes them as literal strings, not typed values.

**CRITICAL: Before passing dry_run boolean flags through business logic function parameters** → Read [Erk Architecture Patterns](erk-architecture.md) first. Use dependency injection with DryRunGit/DryRunGitHub wrappers for multi-step workflows. Simple CLI preview flags at the command level are acceptable for single-action commands.

**CRITICAL: Before passing variables to gh api graphql as JSON blob** → Read [GitHub GraphQL API Patterns](github-graphql.md) first. Variables must be passed individually with -f (strings) and -F (typed). The syntax `-f variables={...}` does NOT work.

**CRITICAL: Before reading from or writing to ~/.claude/ paths using Path.home() directly** → Read [ClaudeInstallation Gateway](claude-installation-gateway.md) first. Use ClaudeInstallation gateway instead. All ~/.claude/ filesystem operations must go through this gateway for testability and storage abstraction.

**CRITICAL: Before removing an abstract method from a gateway ABC** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Must remove from 5 places simultaneously: abc.py, real.py, fake.py, dry_run.py, printing.py. Partial removal causes type checker errors. Update all call sites to use subgateway property. Verify with grep across packages.

**CRITICAL: Before running tsc --noEmit from root in multi-config TypeScript project** → Read [TypeScript Multi-Config Project Checking](typescript-multi-config.md) first. tsc --noEmit from root breaks subdirectory configs. Use tsc -p <path> --noEmit for each tsconfig.json separately.

**CRITICAL: Before skipping fallback strategies when the selected item might disappear** → Read [Selection Preservation by Value](selection-preservation-by-value.md) first. Always provide fallback behavior when selected item not found in refreshed data (reset to 0, preserve index clamped, or clear selection).

**CRITICAL: Before suppressing F401 (unused import) warnings** → Read [Re-Export Pattern](re-export-pattern.md) first. Use # noqa: F401 comment per-import with reason, not global ruff config. Indicates intentional re-export vs actual unused import.
**CRITICAL: Before testing code that uses PromptExecutor** → Read [Prompt Executor Gateway](prompt-executor-gateway.md) first. FakePromptExecutor tracks all calls via properties - use .prompt_calls, .interactive_calls, .passthrough_calls for assertions
**CRITICAL: Before testing PromptExecutor without checking call tracking** → Read [Prompt Executor Gateway](prompt-executor-gateway.md) first. FakePromptExecutor tracks all calls via properties - use .prompt_calls, .interactive_calls, .passthrough_calls for assertions
**CRITICAL: Before threading state through pipeline steps with mutable dataclasses** → Read [Land State Threading Pattern](land-state-threading.md) first. Use frozen dataclasses (@dataclass(frozen=True)) for pipeline state. Update fields with dataclasses.replace() to create new instances. Immutability enables caching, testability, and replay.

**CRITICAL: Before tracking selection by array index when the array can be mutated** → Read [Selection Preservation by Value](selection-preservation-by-value.md) first. Track selection by unique identifier (issue_number, row key), not array position. Array indices become unstable when rows are added, removed, or reordered.

**CRITICAL: Before try/except in fake.py or dry_run.py** → Read [Gateway Error Boundaries](gateway-error-boundaries.md) first. Gateway error handling (try/except) belongs ONLY in real.py. Fake and dry-run implementations return error discriminants based on constructor params, they don't catch exceptions.

**CRITICAL: Before updating a roadmap step's PR cell** → Read [Roadmap Mutation Semantics](roadmap-mutation-semantics.md) first. The update-roadmap-step command computes display status from the PR value and writes it directly into the status cell. Status inference only happens during parsing when status is '-' or empty.

**CRITICAL: Before using LiveDisplay in watch loops or long-running operations** → Read [LiveDisplay Gateway](live-display-gateway.md) first. guard with try/finally to ensure stop() is called even on KeyboardInterrupt

**CRITICAL: Before using PlanContextProvider** → Read [Plan Context Integration](plan-context-integration.md) first. Read this doc first. PlanContextProvider returns None on any failure (graceful degradation). Always handle the None case.

**CRITICAL: Before using `--output-format stream-json` with `--print` in Claude CLI** → Read [Claude CLI Integration from Python](claude-cli-integration.md) first. Must also include `--verbose`. Without it, the command fails with 'stream-json requires --verbose'.

**CRITICAL: Before using `gt restack` to resolve branch divergence errors** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. gt restack only handles parent-child stack rebasing, NOT same-branch remote divergence. Use git rebase origin/$BRANCH first.

**CRITICAL: Before using bare subprocess.run with check=True** → Read [Subprocess Wrappers](subprocess-wrappers.md) first. Use wrapper functions: run_subprocess_with_context() (gateway) or run_with_error_reporting() (CLI). Exception: Graceful degradation pattern with explicit CalledProcessError handling is acceptable for optional operations.

**CRITICAL: Before using bash heredocs for large agent outputs** → Read [Heredoc Quoting and Escaping in Agent-Generated Bash](bash-python-integration.md) first. heredocs fail silently with special characters — prefer the Write tool
**CRITICAL: Before using execute_interactive() in production code** → Read [Prompt Executor Gateway](prompt-executor-gateway.md) first. execute_interactive() never returns in production - it replaces the process via os.execvp

**CRITICAL: Before using gh api or gh api graphql to fetch or resolve PR review threads** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Load `pr-operations` skill first. Use `erk exec get-pr-review-comments` and `erk exec resolve-review-thread` instead. Raw gh api calls miss thread resolution functionality.

**CRITICAL: Before using gh codespace start** → Read [GitHub CLI Limits](github-cli-limits.md) first. gh codespace start does not exist. Use REST API POST /user/codespaces/{name}/start via gh api instead.

**CRITICAL: Before using gh gist create with --filename flag** → Read [GitHub CLI Quirks and Edge Cases](github-cli-quirks.md) first. --filename only works with stdin input (-), not file paths.

**CRITICAL: Before using gh issue create in production code** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/issues -X POST` instead. `gh issue create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue edit in command documentation** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use `erk exec update-issue-body` instead. `gh issue edit` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh issue view in command documentation** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use `erk exec get-issue-body` instead. `gh issue view` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr create in production code** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. Use REST API via `gh api repos/{owner}/{repo}/pulls -X POST` instead. `gh pr create` uses GraphQL which has separate (often exhausted) rate limits.

**CRITICAL: Before using gh pr diff --name-only in production code** → Read [GitHub CLI Limits](github-cli-limits.md) first. For PRs with 300+ files, gh pr diff fails with HTTP 406. Use REST API with pagination instead.

**CRITICAL: Before using gh pr view --json merged** → Read [GitHub API Rate Limits](github-api-rate-limits.md) first. The `merged` field doesn't exist. Use `mergedAt` instead. Run `gh pr view --help` or check error output for valid field names.

**CRITICAL: Before using git pull or git pull --rebase on a Graphite-managed branch** → Read [Git and Graphite Edge Cases Catalog](git-graphite-quirks.md) first. Use /erk:sync-divergence instead. git pull --rebase rewrites commit SHAs outside Graphite's tracking, causing stack divergence that requires manual cleanup with gt sync --restack and force-push.

**CRITICAL: Before using os.environ.get("CLAUDE_CODE_SESSION_ID") in erk code** → Read [Erk Architecture Patterns](erk-architecture.md) first. Erk code NEVER has access to this environment variable. Session IDs must be passed via --session-id CLI flags. Hooks receive session ID via stdin JSON, not environment variables.

**CRITICAL: Before using run_ssh_command() for interactive TUI processes** → Read [SSH Command Execution Patterns](ssh-command-execution.md) first. causes apparent hangs - use exec_ssh_interactive() for processes requiring user input
**CRITICAL: Before using run_ssh_command() for interactive commands** → Read [Composable Remote Commands Pattern](composable-remote-commands.md) first. Interactive commands need exec_ssh_interactive(), not run_ssh_command()
**CRITICAL: Before using run_ssh_command() for interactive TUI processes** → Read [SSH Command Execution Patterns](ssh-command-execution.md) first. causes apparent hangs - use exec_ssh_interactive() instead
**CRITICAL: Before using subprocess.run with git command outside of a gateway** → Read [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) first. Use the Git gateway instead. Direct subprocess calls bypass testability (fakes) and dry-run support. The Git ABC (erk_shared.gateway.git.abc.Git) likely already has a method for this operation. Only use subprocess directly in real.py gateway implementations.

**CRITICAL: Before using unquoted heredoc delimiters (<<EOF) when body contains special characters** → Read [Heredoc Quoting and Escaping in Agent-Generated Bash](bash-python-integration.md) first. Never use unquoted heredoc delimiters (<<EOF) when the body contains $, \, or backticks — bash silently expands them

**CRITICAL: Before using unquoted heredoc delimiters (<<EOF) when body contains special characters** → Read [Heredoc Quoting and Escaping in Agent-Generated Bash](bash-python-integration.md) first. Never use unquoted heredoc delimiters (<<EOF) when the body contains $, \, or backticks — bash silently expands them

**CRITICAL: Before writing complex business logic directly in Click command functions** → Read [CLI-to-Pipeline Boundary Pattern](cli-to-pipeline-boundary.md) first. Extract to pipeline layer when command has >3 distinct steps or complex state management. CLI layer should handle: Click decorators, parameter parsing, output formatting. Pipeline layer should handle: business logic, state management, error types.
