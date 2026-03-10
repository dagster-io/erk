# Plan: Update Help Strings and Error Messages (Objective #9109, Node 2.4)

Part of Objective #9109, Node 2.4: Update ~44 help strings and error messages referencing plan as a noun.

## Context

Objective #9109 renames "plan" terminology to "pr" across all APIs. Nodes 2.1-2.3 handled JSON fields, TypedDict fields, and Click argument/option names. This node handles the remaining user-facing **strings**: help text, error messages, and output messages where "plan" refers to an erk-plan (a PR tracked by erk).

## Scope Rules

**Rename** "plan" to "PR" in:
- Click `help=` strings where "plan" means erk-plan
- Error messages shown to users (click.echo, user_output, f-strings)
- Output messages (success confirmations, status updates)
- Docstrings that appear in `--help` output

**Do NOT rename** "plan" when it refers to:
- Claude's "plan mode" feature (ExitPlanMode, "enter plan mode")
- The `erk-plan` GitHub label (fixed identifier)
- The `plan.md` filename (literal file path)
- The `plan-header` metadata block name (technical term)
- Workflow names like `plan-implement.yml` (fixed identifiers)
- Branch prefixes like `planned-pr-context/` (fixed identifiers)
- Variable names, function names, class names (other nodes)
- The `planning` lifecycle stage value (enum value)
- The word "plan" used as a verb ("planning to perform")

## Implementation Phases

### Phase 1: CLI Command Help Strings (~20 files)

Update `help=` parameters on Click decorators. Files:

**Non-exec commands:**
- `src/erk/cli/commands/one_shot.py:102` — "Create a plan remotely" → "Create a PR remotely"
- `src/erk/cli/commands/reconcile_cmd.py:26` — "Skip creating learn plans" → "Skip creating learn PRs"
- `src/erk/cli/commands/land_cmd.py:1531` — "Skip creating a learn plan" → "Skip creating a learn PR"
- `src/erk/cli/commands/admin.py:419` — "Existing plan number" → "Existing PR number"
- `src/erk/cli/commands/pr/create_cmd.py:25,27,29` — "Plan file/title/plan" → "PR file/title/PR"
- `src/erk/cli/commands/pr/duplicate_check_cmd.py:26,32` — "Plan file/ID" → "PR file/ID"
- `src/erk/cli/commands/pr/list_cmd.py:122,128` — "plans from all users" / "by plan number" → PR
- `src/erk/cli/commands/pr/view_cmd.py:286` — "full plan body" → "full PR body"
- `src/erk/cli/commands/branch/create_cmd.py:40` — "Plan number or URL" → "PR number or URL"
- `src/erk/cli/commands/branch/checkout_cmd.py:453` — "Plan number or PR" → "PR number or URL"
- `src/erk/cli/commands/branch/delete_cmd.py:348` — "close associated PR and plan" → "close associated PRs"
- `src/erk/cli/commands/wt/create_cmd.py:454` — "Copy the plan file" → "Copy the PR file"
- `src/erk/cli/commands/wt/delete_cmd.py:534` — "close associated PR and plan" → "close associated PRs"

**Exec scripts:**
- `src/erk/cli/commands/exec/scripts/plan_save.py:499,504,510,516,537` — all plan references → PR
- `src/erk/cli/commands/exec/scripts/plan_update.py:49,61,65,69` — plan references → PR
- `src/erk/cli/commands/exec/scripts/land_execute.py:60,87` — "Linked plan number" / "learn plan" → PR
- `src/erk/cli/commands/exec/scripts/track_learn_result.py:67,78` — "Plan identifier" / "Learn plan number" → PR
- `src/erk/cli/commands/exec/scripts/get_plan_info.py:32` — "plan body content" → "PR body content"
- `src/erk/cli/commands/exec/scripts/validate_plan_content.py:88` — "plan file" → "PR file"
- `src/erk/cli/commands/exec/scripts/add_plan_label.py:27` — "Label to add to the plan" → PR
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py:319,322` — "Plan identifier" / "Planned-PR plan"
- `src/erk/cli/commands/exec/scripts/impl_signal.py:432` — "plan file deletion" → "PR file deletion"
- `src/erk/cli/commands/exec/scripts/incremental_dispatch.py:46` — "plan markdown file" → "PR markdown file"
- `src/erk/cli/commands/exec/scripts/create_pr_from_session.py:45` — "collapsed plan" → "collapsed PR"
- `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py:102` — "scoped plan lookup" → "scoped PR lookup"
- `src/erk/cli/commands/exec/scripts/push_session.py:188` — "Plan identifier" → "PR identifier"
- `src/erk/cli/commands/exec/scripts/post_workflow_started_comment.py:125` — "Plan identifier" → "PR identifier"
- `src/erk/cli/commands/exec/scripts/store_tripwire_candidates.py:48` — "Plan number" → "PR number"
- `src/erk/cli/commands/exec/scripts/setup_impl.py:151` — "Plan number to set up from" → "PR number"
- `src/erk/cli/commands/exec/scripts/objective_fetch_context.py:157` — "Plan number" → "PR number"
- `src/erk/cli/commands/exec/scripts/fetch_sessions.py:67` — "Plan identifier" → "PR identifier"
- `src/erk/cli/commands/exec/scripts/download_remote_session.py:139` — help references plan branch
- `src/erk/cli/commands/exec/scripts/launch_cmd.py:342` — "Plan number" → "PR number" (if applicable)

### Phase 2: Error Messages and Output Strings (~25 files)

Update user-facing messages. Key files:

- `src/erk/cli/github_parsing.py:60` — "Invalid plan number or URL"
- `src/erk/cli/commands/pr/create_cmd.py:77,127,129` — "Plan content is empty", "Created plan #"
- `src/erk/cli/commands/pr/list_cmd.py` — "No plans found", "Found N plan(s)"
- `src/erk/cli/commands/branch/create_cmd.py:108,109,114,139,170,269,275,280` — plan references in messages
- `src/erk/cli/commands/branch/checkout_cmd.py:374,375,380,385,521,522,527,549,554,578` — plan references
- `src/erk/cli/commands/branch/delete_cmd.py:146,170,172,176,179` — plan display format functions
- `src/erk/cli/commands/admin.py:462,467,471,509,521` — test plan messages
- `src/erk/cli/commands/exec/scripts/plan_save.py` — many output messages
- `src/erk/cli/commands/exec/scripts/plan_update.py` — output messages
- `src/erk/cli/commands/exec/scripts/close_pr.py:51,65` — "Failed to add comment/close plan"
- `src/erk/cli/commands/exec/scripts/close_prs.py:179` — "Failed to close plan"
- `src/erk/cli/commands/exec/scripts/get_plan_info.py:54` — "Plan # not found"
- `src/erk/cli/commands/exec/scripts/get_plan_metadata.py:68` — "Plan # not found"
- `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py:64` — "Plan # not found"
- `src/erk/cli/commands/exec/scripts/create_impl_context_from_plan.py:64,65` — "Could not fetch plan"
- `src/erk/cli/commands/exec/scripts/setup_impl_from_pr.py:92,94,149,249,273` — plan branch messages
- `src/erk/cli/commands/exec/scripts/setup_impl.py:245,255` — "Auto-detected plan", "No plan found"
- `src/erk/cli/commands/exec/scripts/impl_init.py:73` — "No plan.md found"
- `src/erk/cli/commands/exec/scripts/impl_signal.py:191,304,383,408` — "No plan reference", "Plan # not found"
- `src/erk/cli/commands/exec/scripts/validate_plan_content.py:69,72,77` — "Plan is empty/too short/lacks structure"
- `src/erk/cli/commands/exec/scripts/extract_latest_plan.py:44` — "No plan found"
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` — many plan-related messages
- `src/erk/cli/commands/exec/scripts/handle_no_changes.py:97,256` — "Duplicate plan", "Failed to add plan comment"
- `src/erk/cli/commands/exec/scripts/objective_fetch_context.py:186,202,209` — plan not found messages
- `src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py:220,228` — plan not found
- `src/erk/cli/commands/exec/scripts/track_learn_evaluation.py:127,137,173,174,189,190` — plan references
- `src/erk/cli/commands/exec/scripts/track_learn_result.py:173,182` — plan references
- `src/erk/cli/commands/exec/scripts/update_plan_header.py:117,134,137` — plan header messages
- `src/erk/cli/commands/exec/scripts/ci_update_pr_body.py:273,274` — plan-header messages
- `src/erk/cli/commands/exec/scripts/ci_generate_summaries.py:197,303,308,314,332,337,339` — plan issue messages
- `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py:179,181,182,185` — "No plan found"
- `src/erk/cli/commands/exec/scripts/incremental_dispatch.py:116` — "Committing plan to branch"
- `src/erk/cli/commands/exec/scripts/add_plan_labels.py:32` — docstring for type def
- `src/erk/cli/commands/exec/scripts/update_pr_description.py:104` — "Fetching plan context"
- `src/erk/cli/commands/init/main.py:363,364` — "Plans repo configured", label mentions

### Phase 3: Constants and Shared Strings

- `src/erk/cli/constants.py:63` — `ERK_LEARN_LABEL_DESCRIPTION = "Documentation learning plan"` → "Documentation learning PR"
- `src/erk/cli/commands/pr/list_cmd.py:126-127` — Choice value `"plan"` → `"pr"`, default `"plan"` → `"pr"`
- `src/erk/cli/commands/reconcile_cmd.py:120` — table column header `"Plan"` → `"PR"`

### Phase 4: Implement Shared and Core

- `src/erk/cli/commands/implement_shared.py:498,502` — "Plan file not found", "Reading plan file"
- `src/erk/cli/commands/consolidate_learn_plans_dispatch.py` — various "learn plans" references in messages

## Verification

1. Run `ruff check src/erk/` to verify no syntax errors
2. Run `ty check src/erk/` for type checking
3. Run `pytest tests/` to verify no test regressions
4. Grep for remaining "plan" in help strings: `grep -r 'help=.*[Pp]lan' src/erk/cli/` — should only show legitimate uses (plan mode, erk-plan label, plan.md filename, plan-header)
