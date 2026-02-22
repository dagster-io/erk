---
title: Cli Tripwires
read_when:
  - "working on cli code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from cli/*.md frontmatter -->

# Cli Tripwires

Rules triggered by matching actions in code.

**Design batch commands that process items despite validation failures** → Read [Batch Exec Commands](batch-exec-commands.md) first. Validate ALL items upfront before processing ANY items. Stop on first validation error.

**Return non-zero exit codes for batch command failures** → Read [Batch Exec Commands](batch-exec-commands.md) first. Always exit 0, encode errors in JSON output with per-item success fields.

**Use OR semantics for batch success (success=true if any item succeeds)** → Read [Batch Exec Commands](batch-exec-commands.md) first. Use AND semantics: top-level success=true only if ALL items succeed.

**Using RuntimeError for expected CLI failures** → Read [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md) first. RuntimeError signals a programmer error (bug in the code), NOT expected user-facing failures. Use UserFacingCliError for expected conditions (missing files, invalid input, precondition violations) that should exit cleanly with an actionable message.

**WORKFLOW_COMMAND_MAP maps command names to .yml filenames** → Read [Workflow Commands](workflow-commands.md) first. command names intentionally diverge from filenames (e.g., pr-fix-conflicts → pr-fix-conflicts.yml, but plan-implement → plan-implement.yml via DISPATCH_WORKFLOW_NAME constant)

**adding a new exec script that produces JSON consumed by another exec script** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Define shared TypedDict in packages/erk-shared/ for type-safe schema. Both producer and consumer import from the same schema definition.

**adding a new step to the submit pipeline** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. Each step must return SubmitState | SubmitError. Use dataclasses.replace() for state updates. Add the step to \_submit_pipeline() tuple.

**adding a parameter to erk exec without updating calling command** → Read [Parameter Addition Checklist](parameter-addition-checklist.md) first. 5-step verification required. Parameter additions must thread through skill argument-hint, command invocations, AND exec script. Miss any layer and you get silent failures or discovery problems. See parameter-addition-checklist.md.

**adding bulleted lists to CLI command help text** → Read [Click Help Text Formatting](help-text-formatting.md) first. Place  before bulleted/numbered lists to prevent Click from merging items into single line.

**adding discovery logic outside prepare_state()** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. All discovery (branch name, issue number, parent branch, etc.) must happen in prepare_state() to prevent duplication. Later steps assume these fields are populated.

**adding inline shell logic to a slash command instead of using erk exec** → Read [Slash Command to Exec Migration](slash-command-exec-migration.md) first. Extract reusable logic to an erk exec command. Slash commands should orchestrate exec calls, not contain business logic.

**adding new CLI flags without validation** → Read [CLI Options Validation](cli-options-validation.md) first. Check if validation logic is needed when adding new flags. Boolean flags rarely need validation, but flags accepting values (paths, names, numbers) should validate constraints.

**adding or modifying CLI commands without regenerating reference docs** → Read [Auto-Generated Reference Documentation](auto-generated-reference-docs.md) first. After CLI changes, run 'erk-dev gen-exec-reference-docs' to update auto-generated exec reference documentation. Stale docs confuse users and agents.

**adding sequential yes/no prompts for a single decision** → Read [Prompt Consolidation Pattern](prompt-consolidation-pattern.md) first. Consolidate into one binary choice. Multiple prompts for the same decision create unnecessary cognitive load. See the branch reuse example.

**adding session discovery code before checking for preprocessed materials** → Read [Learn Command Conditional Pipeline](learn-command-conditional-pipeline.md) first. Check gist URL first to avoid misleading output. The learn command checks \_get_learn_materials_gist_url() BEFORE session discovery. If a gist exists, all session discovery is skipped.

**adding user-interactive steps (confirmations, prompts) without CI detection** → Read [CI-Aware Commands](ci-aware-commands.md) first. Commands with user interaction must check `in_github_actions()` and skip prompts in CI. Interactive prompts hang indefinitely in GitHub Actions workflows.

**calling gh or git directly from a slash command** → Read [Slash Command to Exec Migration](slash-command-exec-migration.md) first. Use an erk exec script instead. Direct CLI calls bypass gateways, making the logic untestable and unreusable.

**calling is_learned_docs_available() in CLI code** → Read [erk docs check Command](erk-docs-check.md) first. Function signature requires repo_ops and cwd kwargs: is_learned_docs_available(repo_ops=..., cwd=...). Omitting either kwarg will cause a TypeError.

**choosing between Ensure and EnsureIdeal** → Read [EnsureIdeal Pattern for Type Narrowing](ensure-ideal-pattern.md) first. Ensure is for invariant checks (preconditions). EnsureIdeal is for type narrowing (handling operations that can return non-ideal states). If the value comes from an operation that returns T | ErrorType, use EnsureIdeal.

**committing .impl/ folder to git** → Read [Plan-Implement Workflow](plan-implement.md) first. .impl/ lives in .gitignore and should never be committed. Only .worker-impl/ (remote execution artifact) gets committed and later removed.

**creating exec scripts for operations requiring LLM reasoning between steps** → Read [Slash Command LLM Turn Optimization](slash-command-llm-turn-optimization.md) first. Keep conditional logic in slash commands. Only bundle mechanical API calls where all input params are known upfront.

**displaying user-provided text in Rich CLI tables** → Read [CLI Output Styling Guide](output-styling.md) first. Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear.

**displaying user-provided text in Rich CLI tables without escaping** → Read [Objective Commands](objective-commands.md) first. Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear.

**editing or deleting .impl/ folder during implementation** → Read [Plan-Implement Workflow](plan-implement.md) first. .impl/plan.md is immutable during implementation. Never edit it. Never delete .impl/ folder - it must be preserved for user review. Only .worker-impl/ should be auto-deleted.

**exec reference check fails in CI** → Read [Auto-Generated Reference Documentation](auto-generated-reference-docs.md) first. Run 'erk-dev gen-exec-reference-docs' via devrun agent. This is routine maintenance after exec script changes, not a bug to investigate.

**expecting status to auto-update after manual PR edits** → Read [Update Objective Node Command](commands/update-objective-node.md) first. Only the update-objective-node command writes computed status. Manual edits require explicitly setting status to '-' to enable inference on next parse.

**filtering session sources without logging which sessions were skipped and why** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Silent filtering makes debugging impossible. Log to stderr when skipping sessions, include the reason (empty/warmup/filtered).

**flagging 5+ parameter violations in code review** → Read [Code Review Filtering](code-review-filtering.md) first. Before flagging, verify NO exception applies (ABC/Protocol/Click)

**generating directory-change commands using erk br co without source** → Read [Shell Activation Pattern for Worktree Navigation](shell-activation-pattern.md) first. Subprocess directory changes do NOT persist to the parent shell. erk br co runs in a subprocess — its chdir() is invisible to the caller. Use the shell activation pattern: source "$(erk br co <branch> --script)" to actually navigate.

**implementing a command with user confirmations interleaved between mutations** → Read [Two-Phase Validation Model](two-phase-validation-model.md) first. Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Interleaving confirmations with mutations causes partial state on decline.

**implementing a new `erk pr` command** → Read [PR Rewrite Command](pr-rewrite.md) first. Compare feature parity with `submit_pipeline.py`. Check: issue discovery, closing reference preservation, learn plan labels, footer construction, and plan details section. Use shared utilities from `shared.py` (`assemble_pr_body`, `discover_issue_for_footer`).

**implementing business logic with gateways** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. Never create gateway instances in business logic — inject them as parameters

**implementing internal CLI functions** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. Separate \_\*\_impl() functions return exit codes or discriminated unions, never call sys.exit()

**importing from erk_shared.gateway.{service}.abc when creating exec commands** → Read [Exec Script Patterns](exec-script-patterns.md) first. Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`

**landing a PR without updating associated learn plan status** → Read [Learn Plan Land Flow](learn-plan-land-flow.md) first. Learn plan PRs trigger special execution pipeline steps that update parent plan metadata. Ensure check_learn_status, update_learn_plan, and close_review_pr steps execute after merge.

**making LLM fetch data sequentially when it could be bundled** → Read [Slash Command LLM Turn Optimization](slash-command-llm-turn-optimization.md) first. Extract 3+ mechanical sequential calls into an exec script. Each tool call costs a full LLM round-trip.

**making session_id a required parameter for a new command** → Read [Session ID Availability and Propagation](session-management.md) first. Check the fail-hard vs degrade decision table below. Most commands should accept session_id as optional.

**mutating SubmitState fields directly** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. SubmitState is frozen. Use dataclasses.replace(state, field=value) to create new state.

**parsing roadmap tables to update PR cells** → Read [Update Objective Node Command](commands/update-objective-node.md) first. Use the update-objective-node command instead of manual parsing. The command encodes table structure knowledge once rather than duplicating it across callers.

**plan-implement exists in WORKFLOW_COMMAND_MAP but erk launch plan-implement always raises UsageError** → Read [Workflow Commands](workflow-commands.md) first. use erk plan submit instead

**putting checkout-specific helpers in navigation_helpers.py** → Read [Checkout Helpers Module](checkout-helpers.md) first. `src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead.

**removing a workflow command or CLI entry** → Read [Incomplete Command Removal Pattern](incomplete-command-removal.md) first. Read incomplete-command-removal.md first. Search all string references before removing. String-based dispatch maps like WORKFLOW_COMMAND_MAP aren't caught by type checkers.

**renaming an exec command without updating all 9 reference locations** → Read [Command Rename Checklist](command-rename-checklist.md) first. Follow the 9-place checklist in command-rename-checklist.md to avoid stale references.

**retrieving dependencies in Click commands** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. Click commands retrieve real implementations from context via require\_\* helpers

**running any erk exec subcommand** → Read [erk exec Commands](erk-exec-commands.md) first. Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance.

**running gh pr create** → Read [PR Operations: Duplicate Prevention and Detection](pr-operations.md) first. Query for existing PRs first via `gh pr list --head <branch> --state all`. Prevents duplicate PR creation and workflow breaks.

**skipping session upload after local implementation** → Read [Plan-Implement Workflow](plan-implement.md) first. Local implementations must upload session via capture-session-info + upload-session. This enables async learn workflow. See session upload section below.

**submitting PRs** → Read [PR Submission Decision Framework](pr-submission.md) first. Before creating PRs, understand the workflow tradeoffs

**testing prompts without matching confirm_responses array length** → Read [Prompt Consolidation Pattern](prompt-consolidation-pattern.md) first. confirm_responses array length must match the number of prompts. Too few causes IndexError; too many indicates a prompt was removed without updating tests.

**using EnsureIdeal for discriminated union narrowing** → Read [EnsureIdeal Pattern for Type Narrowing](ensure-ideal-pattern.md) first. Only use when the error type implements NonIdealState protocol OR provides a message field. For custom error types without standard fields, add a specific EnsureIdeal method.

**using Path.cwd() or Path.home() in exec scripts** → Read [Exec Script Patterns](exec-script-patterns.md) first. Use context injection via require_cwd(ctx) for testability

**using Python format strings with :N width specifiers for CLI output containing emoji** → Read [CLI Output Styling Guide](output-styling.md) first. Use Rich tables instead — emoji have variable terminal widths (typically 2 cells) which break fixed-width alignment. See the Rich Tables for Variable-Width Characters section below.

**using a non-None default for an optional Click option** → Read [Click Framework Conventions](click-framework-conventions.md) first. Use default=None to distinguish 'not provided' from 'explicitly set'. This enables three-state semantics (None=omitted, ''=clear, value=set) used throughout erk's CLI.

**using blocking operations (user confirmation, editor launch) in CI-executed code paths** → Read [CI-Aware Commands](ci-aware-commands.md) first. Check `in_github_actions()` before any blocking operation. CI has no terminal for user input.

**using click.confirm() after user_output()** → Read [CLI Output Styling Guide](output-styling.md) first. Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**using dict .get() to access fields from exec script JSON output without a TypedDict schema** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Silent filtering failures occur when field names are mistyped. Define TypedDict in erk_shared and use cast() in consumers.

**using erk exec commands in scripts** → Read [erk exec Commands](erk-exec-commands.md) first. Some erk exec subcommands don't support `--format json`. Always check with `erk exec <command> -h` first.

**using gh issue view on a plan without checking plan backend type** → Read [CLI Backend-Aware Display Patterns](backend-aware-display.md) first. Draft-PR plan IDs are PR numbers, not issue numbers. Using gh issue view on a draft-PR plan produces a confusing 404. Route to gh pr view based on backend type.

**using ls -t or mtime to find the current session** → Read [Session ID Availability and Propagation](session-management.md) first. Use the ClaudeInstallation gateway or the session-id-injector-hook's scratch file instead. Mtime-based discovery is racy in parallel sessions.

**using os.environ to read CLAUDE_SESSION_ID** → Read [Session ID Availability and Propagation](session-management.md) first. CLAUDE_SESSION_ID is NOT an environment variable. It's a Claude Code string substitution in commands/skills, and arrives via stdin JSON in hooks.

**using this pattern** → Read [Local/Remote Command Group Pattern (Deprecated)](local-remote-command-groups.md) first. BEFORE: Using invoke_without_command=True to unify local/remote variants → READ: Why this pattern was abandoned

**using this pattern** → Read [Workflow Commands](workflow-commands.md) first. PR workflows automatically update plan issue dispatch metadata when the branch follows the P{issue_number} naming pattern

**validating PRs in workflows** → Read [PR Submission Decision Framework](pr-submission.md) first. PR validation rules apply to both workflows

**writing Examples sections in CLI docstrings without ** → Read [Click Help Text Formatting](help-text-formatting.md) first. Place  on its own line after 'Examples:' heading. Without it, Click rewraps text and breaks formatting.

**writing PR/issue body generation in exec scripts** → Read [Exec Command Patterns](exec-command-patterns.md) first. Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability.

**writing multi-line error messages in Ensure method calls** → Read [CLI Output Styling Guide](output-styling.md) first. Use implicit string concatenation with \n at end of first string. Line 1 is the primary error, line 2+ is remediation context. Do NOT use \n\n (double newline) — Ensure handles spacing.
