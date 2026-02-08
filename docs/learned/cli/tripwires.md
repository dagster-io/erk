---
title: Cli Tripwires
read_when:
  - "working on cli code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from cli/*.md frontmatter -->

# Cli Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before Design batch commands that process items despite validation failures** → Read [Batch Exec Commands](batch-exec-commands.md) first. Validate ALL items upfront before processing ANY items. Stop on first validation error.

**CRITICAL: Before Never create gateway instances in business logic** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. inject them as parameters

**CRITICAL: Before Return non-zero exit codes for batch command failures** → Read [Batch Exec Commands](batch-exec-commands.md) first. Always exit 0, encode errors in JSON output with per-item success fields.

**CRITICAL: Before Use OR semantics for batch success (success=true if any item succeeds)** → Read [Batch Exec Commands](batch-exec-commands.md) first. Use AND semantics: top-level success=true only if ALL items succeed.

**CRITICAL: Before Using RuntimeError for expected CLI failures** → Read [CLI Error Handling Anti-Patterns](error-handling-antipatterns.md) first. RuntimeError signals a programmer error (bug in the code), NOT expected user-facing failures. Use UserFacingCliError for expected conditions (missing files, invalid input, precondition violations) that should exit cleanly with an actionable message.

**CRITICAL: Before WORKFLOW_COMMAND_MAP maps command names to .yml filenames** → Read [Workflow Commands](workflow-commands.md) first. command names intentionally diverge from filenames (e.g., pr-fix-conflicts → pr-fix-conflicts.yml, but plan-implement → plan-implement.yml via DISPATCH_WORKFLOW_NAME constant)

**CRITICAL: Before adding a new exec script that produces JSON consumed by another exec script** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Define shared TypedDict in packages/erk-shared/ for type-safe schema. Both producer and consumer import from the same schema definition.

**CRITICAL: Before adding a new step to the submit pipeline** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. Each step must return SubmitState | SubmitError. Use dataclasses.replace() for state updates. Add the step to \_submit_pipeline() tuple.

**CRITICAL: Before adding a parameter to erk exec without updating calling command** → Read [Parameter Addition Checklist](parameter-addition-checklist.md) first. 5-step verification required. Parameter additions must thread through skill argument-hint, command invocations, AND exec script. Miss any layer and you get silent failures or discovery problems. See parameter-addition-checklist.md.

**CRITICAL: Before adding bulleted lists to CLI command help text** → Read [Click Help Text Formatting](help-text-formatting.md) first. Place  before bulleted/numbered lists to prevent Click from merging items into single line.

**CRITICAL: Before adding discovery logic outside prepare_state()** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. All discovery (branch name, issue number, parent branch, etc.) must happen in prepare_state() to prevent duplication. Later steps assume these fields are populated.

**CRITICAL: Before adding inline shell logic to a slash command instead of using erk exec** → Read [Slash Command to Exec Migration](slash-command-exec-migration.md) first. Extract reusable logic to an erk exec command. Slash commands should orchestrate exec calls, not contain business logic.

**CRITICAL: Before adding new CLI flags without validation** → Read [CLI Options Validation](cli-options-validation.md) first. Check if validation logic is needed when adding new flags. Boolean flags rarely need validation, but flags accepting values (paths, names, numbers) should validate constraints.

**CRITICAL: Before adding or modifying CLI commands without regenerating reference docs** → Read [Auto-Generated Reference Documentation](auto-generated-reference-docs.md) first. After CLI changes, run 'erk-dev gen-exec-reference-docs' to update auto-generated exec reference documentation. Stale docs confuse users and agents.

**CRITICAL: Before adding user-interactive steps (confirmations, prompts) without CI detection** → Read [CI-Aware Commands](ci-aware-commands.md) first. Commands with user interaction must check `in_github_actions()` and skip prompts in CI. Interactive prompts hang indefinitely in GitHub Actions workflows.

**CRITICAL: Before calling gh or git directly from a slash command** → Read [Slash Command to Exec Migration](slash-command-exec-migration.md) first. Use an erk exec script instead. Direct CLI calls bypass gateways, making the logic untestable and unreusable.

**CRITICAL: Before choosing between Ensure and EnsureIdeal** → Read [EnsureIdeal Pattern for Type Narrowing](ensure-ideal-pattern.md) first. Ensure is for invariant checks (preconditions). EnsureIdeal is for type narrowing (handling operations that can return non-ideal states). If the value comes from an operation that returns T | ErrorType, use EnsureIdeal.

**CRITICAL: Before committing .impl/ folder to git** → Read [Plan-Implement Workflow](plan-implement.md) first. .impl/ lives in .gitignore and should never be committed. Only .worker-impl/ (remote execution artifact) gets committed and later removed.

**CRITICAL: Before creating exec scripts for operations requiring LLM reasoning between steps** → Read [Slash Command LLM Turn Optimization](slash-command-llm-turn-optimization.md) first. Keep conditional logic in slash commands. Only bundle mechanical API calls where all input params are known upfront.

**CRITICAL: Before displaying user-provided text in Rich CLI tables** → Read [CLI Output Styling Guide](output-styling.md) first. Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear.

**CRITICAL: Before displaying user-provided text in Rich CLI tables without escaping** → Read [Objective Commands](objective-commands.md) first. Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear.

**CRITICAL: Before editing or deleting .impl/ folder during implementation** → Read [Plan-Implement Workflow](plan-implement.md) first. .impl/plan.md is immutable during implementation. Never edit it. Never delete .impl/ folder - it must be preserved for user review. Only .worker-impl/ should be auto-deleted.

**CRITICAL: Before expecting status to auto-update after manual PR edits** → Read [Update Roadmap Step Command](commands/update-roadmap-step.md) first. Only the update-roadmap-step command writes computed status. Manual edits require explicitly setting status to '-' to enable inference on next parse.

**CRITICAL: Before filtering session sources without logging which sessions were skipped and why** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Silent filtering makes debugging impossible. Log to stderr when skipping sessions, include the reason (empty/warmup/filtered).

**CRITICAL: Before implementing a command with user confirmations interleaved between mutations** → Read [Two-Phase Validation Model](two-phase-validation-model.md) first. Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Interleaving confirmations with mutations causes partial state on decline.

**CRITICAL: Before importing from erk_shared.gateway.{service}.abc when creating exec commands** → Read [Exec Script Patterns](exec-script-patterns.md) first. Gateway ABCs use submodule paths: `erk_shared.gateway.{service}.{resource}.abc`

**CRITICAL: Before landing a PR without updating associated learn plan status** → Read [Learn Plan Land Flow](learn-plan-land-flow.md) first. Learn plan PRs trigger special execution pipeline steps that update parent plan metadata and promote tripwires. Ensure check_learn_status, update_learn_plan, promote_tripwires, and close_review_pr steps execute after merge.

**CRITICAL: Before making LLM fetch data sequentially when it could be bundled** → Read [Slash Command LLM Turn Optimization](slash-command-llm-turn-optimization.md) first. Extract 3+ mechanical sequential calls into an exec script. Each tool call costs a full LLM round-trip.

**CRITICAL: Before making session_id a required parameter for a new command** → Read [Session ID Availability and Propagation](session-management.md) first. Check the fail-hard vs degrade decision table below. Most commands should accept session_id as optional.

**CRITICAL: Before mutating SubmitState fields directly** → Read [PR Submit Pipeline Architecture](pr-submit-pipeline.md) first. SubmitState is frozen. Use dataclasses.replace(state, field=value) to create new state.

**CRITICAL: Before parsing roadmap tables to update PR cells** → Read [Update Roadmap Step Command](commands/update-roadmap-step.md) first. Use the update-roadmap-step command instead of manual parsing. The command encodes table structure knowledge once rather than duplicating it across callers.

**CRITICAL: Before plan-implement exists in WORKFLOW_COMMAND_MAP but erk launch plan-implement always raises UsageError** → Read [Workflow Commands](workflow-commands.md) first. use erk plan submit instead

**CRITICAL: Before putting checkout-specific helpers in navigation_helpers.py** → Read [Checkout Helpers Module](checkout-helpers.md) first. `src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead.

**CRITICAL: Before running any erk exec subcommand** → Read [erk exec Commands](erk-exec-commands.md) first. Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance.

**CRITICAL: Before running gh pr create** → Read [PR Operations: Duplicate Prevention and Detection](pr-operations.md) first. Query for existing PRs first via `gh pr list --head <branch> --state all`. Prevents duplicate PR creation and workflow breaks.

**CRITICAL: Before skipping session upload after local implementation** → Read [Plan-Implement Workflow](plan-implement.md) first. Local implementations must upload session via capture-session-info + upload-session. This enables async learn workflow. See session upload section below.

**CRITICAL: Before using EnsureIdeal for discriminated union narrowing** → Read [EnsureIdeal Pattern for Type Narrowing](ensure-ideal-pattern.md) first. Only use when the error type implements NonIdealState protocol OR provides a message field. For custom error types without standard fields, add a specific EnsureIdeal method.

**CRITICAL: Before using Path.cwd() or Path.home() in exec scripts** → Read [Exec Script Patterns](exec-script-patterns.md) first. Use context injection via require_cwd(ctx) for testability

**CRITICAL: Before using blocking operations (user confirmation, editor launch) in CI-executed code paths** → Read [CI-Aware Commands](ci-aware-commands.md) first. Check `in_github_actions()` before any blocking operation. CI has no terminal for user input.

**CRITICAL: Before using click.confirm() after user_output()** → Read [CLI Output Styling Guide](output-styling.md) first. Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**CRITICAL: Before using dict .get() to access fields from exec script JSON output without a TypedDict schema** → Read [Exec Script Schema Patterns](exec-script-schema-patterns.md) first. Silent filtering failures occur when field names are mistyped. Define TypedDict in erk_shared and use cast() in consumers.

**CRITICAL: Before using erk exec commands in scripts** → Read [erk exec Commands](erk-exec-commands.md) first. Some erk exec subcommands don't support `--format json`. Always check with `erk exec <command> -h` first.

**CRITICAL: Before using ls -t or mtime to find the current session** → Read [Session ID Availability and Propagation](session-management.md) first. Use the ClaudeInstallation gateway or the session-id-injector-hook's scratch file instead. Mtime-based discovery is racy in parallel sessions.

**CRITICAL: Before using os.environ to read CLAUDE_SESSION_ID** → Read [Session ID Availability and Propagation](session-management.md) first. CLAUDE_SESSION_ID is NOT an environment variable. It's a Claude Code string substitution in commands/skills, and arrives via stdin JSON in hooks.

**CRITICAL: Before using this pattern** → Read [Code Review Filtering](code-review-filtering.md) first. Before flagging 5+ parameter violations, verify NO exception applies (ABC/Protocol/Click)

**CRITICAL: Before using this pattern** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. Separate \_\*\_impl() functions return exit codes or discriminated unions, never call sys.exit()

**CRITICAL: Before using this pattern** → Read [Dependency Injection in Exec Scripts](dependency-injection-patterns.md) first. Click commands retrieve real implementations from context via require\_\* helpers

**CRITICAL: Before using this pattern** → Read [Local/Remote Command Group Pattern (Deprecated)](local-remote-command-groups.md) first. BEFORE: Using invoke_without_command=True to unify local/remote variants → READ: Why this pattern was abandoned

**CRITICAL: Before using this pattern** → Read [PR Submission Decision Framework](pr-submission.md) first. Before creating PRs, understand the workflow tradeoffs

**CRITICAL: Before using this pattern** → Read [PR Submission Decision Framework](pr-submission.md) first. PR validation rules apply to both workflows

**CRITICAL: Before using this pattern** → Read [Workflow Commands](workflow-commands.md) first. PR workflows automatically update plan issue dispatch metadata when the branch follows the P{issue_number} naming pattern

**CRITICAL: Before writing Examples sections in CLI docstrings without ** → Read [Click Help Text Formatting](help-text-formatting.md) first. Place  on its own line after 'Examples:' heading. Without it, Click rewraps text and breaks formatting.

**CRITICAL: Before writing PR/issue body generation in exec scripts** → Read [Exec Command Patterns](exec-command-patterns.md) first. Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability.
