---
title: One-Shot Workflow
last_audited: "2026-02-24 00:00 PT"
audit_result: clean
read_when:
  - "working with erk one-shot dispatch"
  - "understanding how plans are autonomously created and implemented"
  - "debugging one-shot workflow failures"
  - "integrating objectives with one-shot dispatch"
tripwires:
  - action: "adding dry-run support to one-shot commands"
    warning: "One-shot dry-run mode must NOT create skeleton issues"
  - action: "modifying register-one-shot-plan exit behavior"
    warning: "register-one-shot-plan uses best-effort: exit 0 if any operation succeeds"
  - action: "adding post-dispatch operations without matching dispatch_cmd.py pattern"
    warning: "dispatch_one_shot() and _dispatch_planned_pr_plan() in dispatch_cmd.py must stay synchronized. Both use write_dispatch_metadata() + create_submission_queued_block(). Changes to one must be mirrored in the other."
  - action: "writing post-dispatch operations without try/except guards"
    warning: "Post-dispatch operations (metadata write, queued comment) are best-effort. Wrap in try/except with user-visible warnings. See write_dispatch_metadata() and create_submission_queued_block() in one_shot_dispatch.py."
  - action: "editing plan body content in plan creation, replan, or one-shot dispatch"
    warning: "One-shot metadata block preservation: the metadata block in the plan body (HTML comment with erk:metadata-block markers) must survive all edits. Never strip or overwrite HTML comment blocks that contain erk:metadata-block markers."
    score: 9
---

# One-Shot Workflow

The one-shot workflow enables fully autonomous planning and implementation from a single CLI command. It dispatches a GitHub Actions workflow that creates a plan and implements it without human intervention.

## End-to-End Pipeline

```
CLI dispatch → branch + draft PR → workflow trigger
  → Claude planning → plan saved to PR → implementation → PR ready
```

### Entry Points

Two CLI commands trigger the pipeline:

- `erk one-shot <prompt>` -- direct dispatch (model shortcuts: `haiku`/`h`, `sonnet`/`s`, `opus`/`o`)
- `erk objective plan <issue> --one-shot [--node <id>]` -- objective-driven dispatch

Both converge on `dispatch_one_shot()` in `src/erk/cli/commands/one_shot_dispatch.py`.

**Key constraint:** Planning and implementation run in separate Claude sessions. No context carries over. The plan must be self-contained and explicit.

## Backend-Conditional Dispatch

The dispatch behavior depends on the active plan backend:

### PlannedPRBackend (default)

The draft PR **is** the plan entity. No skeleton issue is created:

1. `generate_planned_pr_branch_name()` creates a `plnd/` branch name
2. Branch is created, pushed, and draft PR opened with `plan-header` metadata
3. `plan_issue_number` is set to the PR number (the PR is the plan)
4. Workflow fills in the actual plan content later

**Branch naming:** `plnd/{slug}-{MM-DD-HHMM}` (e.g., `plnd/my-task-01-15-1430`)

The slug is truncated to stay under git's 31-character worktree limit.

## Objective Integration

When dispatched via `erk objective plan --one-shot`, the objective plan command:

1. Validates the objective exists
2. Builds a prompt string including step ID and phase name for context
3. Passes `objective_issue` and `node_id` as `extra_workflow_inputs` in `OneShotDispatchParams`
4. These become `OBJECTIVE_ISSUE` and `NODE_ID` environment variables in the workflow

## GitHub Actions Workflow

The `.github/workflows/one-shot.yml` workflow has two jobs:

### Plan Job

1. Validates secrets (ERK_QUEUE_GH_PAT)
2. Checks out the branch and sets up tools
3. Writes prompt to `.erk/impl-context/prompt.md`
4. Runs `/erk:one-shot-plan` Claude command with environment variables:
   - `WORKFLOW_RUN_URL` -- current workflow run URL
   - `OBJECTIVE_ISSUE` -- objective issue number (if from roadmap)
   - `NODE_ID` -- specific roadmap node ID
   - `PLAN_ISSUE_NUMBER` -- plan entity number (PR number for planned-PR backend)
5. Validates Claude produced `.erk/impl-context/plan.md` and `.erk/impl-context/plan-result.json`
6. Runs `erk exec register-one-shot-plan` for metadata registration
7. Optionally updates objective roadmap step

### Implement Job

Reuses `.github/workflows/plan-implement.yml` -- the same workflow used for manual plan submissions. Triggered only if the plan job produced an issue number.

**Concurrency control:**

```yaml
concurrency:
  group: one-shot-${{ inputs.branch_name }}
  cancel-in-progress: true
```

## Registration Step (Best-Effort Composition)

`src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` performs four independent operations that `erk pr submit` normally handles at submit time. Each operation is best-effort -- failures are logged but don't block others:

1. **Dispatch metadata** -- the primary metadata source is the CLI dispatch (`write_dispatch_metadata()` in `src/erk/cli/commands/pr/metadata_helpers.py`), with CI registration as a fallback. Writes `run_id`, `node_id`, `dispatched_at` to the plan entity's `plan-header` metadata block.
2. **Queued comment** -- adds a "Queued for Implementation" emoji comment to the plan with PR link and workflow run URL
3. **PR closing reference** -- updates the PR body with `Closes #N` to enable auto-close on merge (handled by PlanBackend)
4. **Lifecycle stage** -- updates the plan entity's lifecycle stage to "planned"

The command outputs JSON results for each operation with success/error details.

### PR Closing Reference (Timing Constraint)

The `Closes #N` reference must be in the initial PR body at creation time, not added via a post-creation update. GitHub's `willCloseTarget` behavior is evaluated at PR creation — adding it later does not enable auto-close. The one-shot dispatch handles this by including the closing reference in the initial `create_pr()` call.

### Dispatch Metadata Two-Phase Write

Dispatch metadata is written in two phases:

1. **At dispatch time** (CLI): `write_dispatch_metadata()` writes `dispatched_at`, `run_id`, `node_id` immediately after workflow trigger
2. **At registration time** (CI): `register_one_shot_plan.py` writes any remaining fields that weren't available at dispatch time

The CLI write is the primary source; CI registration fills gaps when the CLI couldn't complete (e.g., network failure during dispatch).

### Divergence Risk: One-Shot vs PR Dispatch

One-shot dispatch and `erk pr submit` both push branches and create PRs, but one-shot uses force-push (squash) while plan-submit may use regular push. After a one-shot dispatch, the local branch may diverge from remote. Always `git pull --rebase` before making local changes to a one-shot branch.

## Claude Planning Command

`.claude/commands/erk/one-shot-plan.md` defines what Claude does during the plan job:

1. Reads prompt from `.erk/impl-context/prompt.md`
2. Fetches objective context if `$OBJECTIVE_ISSUE` is set
3. Explores codebase following documentation-first discovery
4. Writes a comprehensive, self-contained plan to `.erk/impl-context/plan.md`
5. Saves plan to GitHub issue:
   - If `$PLAN_ISSUE_NUMBER` is set: updates the pre-created entity
   - Otherwise: creates a new issue (backward compatible)
6. Writes `plan-result.json` with `issue_number` and `title`

## Dry-Run Mode

`dispatch_one_shot()` supports `--dry-run` which shows what would happen without side effects. Dry-run mode must NOT create skeleton issues or branches.

## Branch Safety

The dispatch function commits directly to the target branch using git plumbing (`commit_files_to_branch`) without checking out any branch. The user's working tree and HEAD remain untouched throughout the dispatch.

## Slug Generation

<!-- Source: src/erk/cli/commands/one_shot_dispatch.py:207-222, src/erk/cli/commands/objective/plan_cmd.py:47-66 -->

Branch slugs for one-shot branches are generated by calling `ctx.llm_caller.call()` directly with `BRANCH_SLUG_SYSTEM_PROMPT` (defined in `src/erk/core/branch_slug_generator.py`). The prompt instructs the LLM to produce 2-4 hyphenated lowercase words (max 30 characters) that capture the essence of the task.

### Generation Flow

1. The dispatch function calls `ctx.llm_caller.call()` directly with `BRANCH_SLUG_SYSTEM_PROMPT`
2. The raw response is postprocessed: whitespace, quotes, and backticks are stripped, then the slug passes through `sanitize_worktree_name()` for character validation
3. The validated slug is used to construct the branch name

### Fallback Behavior

When the API key is missing or the LLM call fails, the dispatch code falls back to `sanitize_worktree_name()` applied to the raw prompt text. This produces a functional but less descriptive slug.

### Call Sites

- `src/erk/cli/commands/one_shot_dispatch.py:207-222` — one-shot dispatch
- `src/erk/cli/commands/objective/plan_cmd.py:47-66` — objective plan dispatch

## Source Code References

| File                                                          | Key Components                                                                                    |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `src/erk/cli/commands/one_shot_dispatch.py`                   | `dispatch_one_shot()`, `generate_branch_name()`, `OneShotDispatchParams`, `OneShotDispatchResult` |
| `src/erk/cli/commands/objective/plan_cmd.py`                  | `_handle_one_shot()`, `_find_node_in_phases()`                                                    |
| `src/erk/cli/commands/exec/scripts/register_one_shot_plan.py` | Best-effort registration of metadata, comment, closing ref                                        |
| `src/erk/cli/commands/pr/metadata_helpers.py`                 | `write_dispatch_metadata()`, `maybe_update_plan_dispatch_metadata()`                              |
| `.github/workflows/one-shot.yml`                              | Two-job pipeline (plan + implement)                                                               |
| `.claude/commands/erk/one-shot-plan.md`                       | Claude planning command with skeleton update logic                                                |

## Related Topics

- [Plan Lifecycle](lifecycle.md) -- plan states and transitions
- [Plan Schema](plan-schema.md) -- plan format specification
- [PR Submission Patterns](pr-submission-patterns.md) -- how plans become PRs
