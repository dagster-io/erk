<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!--
  Regenerate: erk-dev gen-exec-reference-docs
  CI check:   erk-dev gen-exec-reference-docs --check (included in make fast-ci)

  Source of truth: Live Click command tree in src/erk/cli/commands/exec/group.py
  Generator code: packages/erk-dev/src/erk_dev/exec_reference/generate.py
  Generator docs: docs/learned/cli/auto-generated-reference-docs.md

  Regenerate after: adding/modifying/removing exec commands or changing help text
-->

# erk exec Commands Reference

Quick reference for all `erk exec` subcommands.

## Summary

| Command                           | Description                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------- |
| `add-objective-node`              | Add a new node to an objective's roadmap.                                         |
| `add-plan-label`                  | Add a label to a plan via the appropriate backend.                                |
| `add-plan-labels`                 | Batch add labels to multiple plans from JSON stdin.                               |
| `add-pr-labels`                   | Add labels to a PR with automatic retry on transient failures.                    |
| `add-remote-execution-note`       | Add remote execution tracking note to PR body.                                    |
| `capture-session-info`            | Capture Claude Code session info for CI workflows.                                |
| `ci-fetch-summaries`              | Fetch CI failure summaries for a PR.                                              |
| `ci-generate-summaries`           | Generate CI failure summaries using Haiku.                                        |
| `ci-update-pr-body`               | Update PR body with AI-generated summary and footer.                              |
| `ci-verify-autofix`               | Run full CI verification after autofix push.                                      |
| `cleanup-impl-context`            | Clean up .erk/impl-context/ staging directory.                                    |
| `close-pr`                        | Close a plan with a comment.                                                      |
| `close-prs`                       | Batch close multiple plan PRs with comments from JSON stdin.                      |
| `cmux-open-pr`                    | Create a cmux workspace to open a PR.                                             |
| `create-impl-context-from-plan`   | Create .erk/impl-context/ folder from plan content.                               |
| `create-pr-from-session`          | Extract plan from Claude session and create GitHub draft PR.                      |
| `dash-data`                       | Serialize plan dashboard data to JSON.                                            |
| `detect-plan-from-branch`         | Detect PR number from the current git branch.                                     |
| `detect-trunk-branch`             | Detect whether repo uses main or master as trunk branch.                          |
| `discover-reviews`                | Discover code reviews matching PR changed files.                                  |
| `download-remote-session`         | Download a session from a git branch.                                             |
| `exit-plan-mode-hook`             | Prompt user about plan saving when ExitPlanMode is called.                        |
| `extract-latest-plan`             | Extract the latest plan from Claude session files.                                |
| `fetch-sessions`                  | Fetch preprocessed sessions from a planned-pr-context branch.                     |
| `generate-pr-address-summary`     | Generate enhanced PR comment for pr-address workflow.                             |
| `get-embedded-prompt`             | Get embedded prompt content from bundled prompts.                                 |
| `get-issue-body`                  | Fetch an issue's body using REST API (avoids GraphQL rate limits).                |
| `get-learn-sessions`              | Get session information for a plan.                                               |
| `get-plan-info`                   | Retrieve plan info from the appropriate backend.                                  |
| `get-plan-metadata`               | Extract a metadata field from a plan's plan-header block.                         |
| `get-plans-for-objective`         | Fetch erk-plans linked to an objective.                                           |
| `get-pr-body-footer`              | Generate PR body footer with teleport command.                                    |
| `get-pr-commits`                  | Fetch PR commits using REST API (avoids GraphQL rate limits).                     |
| `get-pr-context`                  | Output JSON with branch, PR, diff, commits, and plan context.                     |
| `get-pr-discussion-comments`      | Fetch PR discussion comments for agent context injection.                         |
| `get-pr-feedback`                 | Fetch all PR feedback in a single command.                                        |
| `get-pr-for-plan`                 | Get PR details for a plan.                                                        |
| `get-pr-review-comments`          | Fetch PR review comments for agent context injection.                             |
| `get-pr-view`                     | Fetch PR details using REST API (avoids GraphQL rate limits).                     |
| `get-review-activity-log`         | Fetch the activity log from an existing review summary comment.                   |
| `handle-no-changes`               | Handle no-changes scenario gracefully.                                            |
| `impl-init`                       | Initialize implementation by validating .erk/impl-context/ folder.                |
| `impl-signal`                     | Signal implementation events to GitHub.                                           |
| `impl-verify`                     | Verify .erk/impl-context/ folder still exists after implementation.               |
| `incremental-dispatch`            | Dispatch a local plan against an existing PR for remote implementation.           |
| `land-execute`                    | Execute deferred land operations.                                                 |
| `list-sessions`                   | List Claude Code sessions with metadata for the current project.                  |
| `marker create`                   | Create a marker file.                                                             |
| `marker delete`                   | Delete a marker file.                                                             |
| `marker exists`                   | Check if a marker file exists.                                                    |
| `marker read`                     | Read content from a marker file.                                                  |
| `migrate-objective-schema`        | Migrate an objective's roadmap YAML to the latest schema (v4).                    |
| `normalize-tripwire-candidates`   | Normalize agent-produced tripwire candidate JSON in-place.                        |
| `objective-apply-landed-update`   | Apply mechanical updates to an objective after landing a PR.                      |
| `objective-fetch-context`         | Fetch all context for objective update in a single call.                          |
| `objective-link-pr`               | Link PR number to objective roadmap nodes from .erk/impl-context/ metadata.       |
| `objective-plan-setup`            | Fetch, validate, and set up context for objective planning.                       |
| `objective-post-action-comment`   | Post a formatted action comment to an objective issue.                            |
| `objective-render-roadmap`        | Render a complete roadmap section from JSON input on stdin.                       |
| `objective-save-to-issue`         | Save plan as objective GitHub issue.                                              |
| `objective-update-after-land`     | Update objective after landing a PR.                                              |
| `plan-save`                       | Save plan as a draft PR.                                                          |
| `plan-update`                     | Update an existing plan's content.                                                |
| `post-or-update-pr-summary`       | Post or update a PR summary comment.                                              |
| `post-pr-inline-comment`          | Post an inline review comment on a PR.                                            |
| `post-workflow-started-comment`   | Post a workflow started comment to a GitHub issue.                                |
| `pr-sync-commit`                  | Sync PR title and body from the latest git commit.                                |
| `pre-tool-use-hook`               | PreToolUse hook for dignified-python reminders on .py file edits.                 |
| `preprocess-session`              | Preprocess session log JSONL to compressed XML format.                            |
| `push-and-create-pr`              | Push branch and create/find PR, outputting JSON.                                  |
| `push-session`                    | Preprocess and push a session to the planned-pr-context branch with accumulation. |
| `quick-submit`                    | Quick commit all changes and submit.                                              |
| `rebase-with-conflict-resolution` | Rebase onto target branch and resolve conflicts with Claude.                      |
| `register-one-shot-plan`          | Register a one-shot plan with issue metadata and comment.                         |
| `reply-to-discussion-comment`     | Reply to a PR discussion comment with quote and action summary.                   |
| `resolve-objective-ref`           | Resolve an objective reference to an objective number.                            |
| `resolve-review-thread`           | Resolve a PR review thread.                                                       |
| `resolve-review-threads`          | Resolve multiple PR review threads from JSON stdin.                               |
| `run-review`                      | Run a code review using Claude.                                                   |
| `session-id-injector-hook`        | Inject session ID into conversation context when relevant.                        |
| `set-local-review-marker`         | Set local review marker on PR to skip CI reviews.                                 |
| `set-pr-description`              | Update PR title and body with agent-provided values.                              |
| `setup-impl`                      | Consolidated implementation setup.                                                |
| `setup-impl-from-pr`              | Set up .erk/impl-context/ folder from GitHub PR in current worktree.              |
| `store-tripwire-candidates`       | Store tripwire candidates as a metadata comment on a plan.                        |
| `summarize-impl-failure`          | Summarize an implementation failure using Haiku.                                  |
| `track-learn-evaluation`          | Track learn evaluation completion on a plan.                                      |
| `track-learn-result`              | Track learn workflow result on a plan.                                            |
| `update-issue-body`               | Update an issue's body using REST API (avoids GraphQL rate limits).               |
| `update-objective-node`           | Update node fields in an objective's roadmap table.                               |
| `update-plan-header`              | Update plan-header metadata fields on a PR.                                       |
| `update-pr-description`           | Update PR title and body with AI-generated description.                           |
| `upload-impl-session`             | Upload current implementation session for async learn.                            |
| `user-prompt-hook`                | UserPromptSubmit hook for session persistence and coding reminders.               |
| `validate-claude-credentials`     | Validate Claude credentials for CI workflows.                                     |
| `validate-plan-content`           | Validate plan content from file or stdin.                                         |

## Commands

### add-objective-node

Add a new node to an objective's roadmap.

**Usage:** `erk exec add-objective-node` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag            | Type    | Required | Default        | Description                                       |
| --------------- | ------- | -------- | -------------- | ------------------------------------------------- |
| `--phase`       | INTEGER | Yes      | Sentinel.UNSET | Phase number to add to                            |
| `--description` | TEXT    | Yes      | Sentinel.UNSET | Node description                                  |
| `--slug`        | TEXT    | No       | -              | Kebab-case identifier (auto-generated if omitted) |
| `--status`      | CHOICE  | No       | 'pending'      | Initial status (default: pending)                 |
| `--depends-on`  | TEXT    | No       | Sentinel.UNSET | Dependency node IDs                               |
| `--comment`     | TEXT    | No       | -              | Comment for adding this node                      |

### add-plan-label

Add a label to a plan via the appropriate backend.

**Usage:** `erk exec add-plan-label` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

**Options:**

| Flag      | Type | Required | Default        | Description            |
| --------- | ---- | -------- | -------------- | ---------------------- |
| `--label` | TEXT | Yes      | Sentinel.UNSET | Label to add to the PR |

### add-plan-labels

Batch add labels to multiple plans from JSON stdin.

**Usage:** `erk exec add-plan-labels`

### add-pr-labels

Add labels to a PR with automatic retry on transient failures.

**Usage:** `erk exec add-pr-labels` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

**Options:**

| Flag       | Type | Required | Default        | Description                     |
| ---------- | ---- | -------- | -------------- | ------------------------------- |
| `--labels` | TEXT | Yes      | Sentinel.UNSET | Labels to add (can be repeated) |

### add-remote-execution-note

Add remote execution tracking note to PR body.

**Usage:** `erk exec add-remote-execution-note`

**Options:**

| Flag          | Type    | Required | Default        | Description              |
| ------------- | ------- | -------- | -------------- | ------------------------ |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to update      |
| `--run-id`    | TEXT    | Yes      | Sentinel.UNSET | Workflow run ID          |
| `--run-url`   | TEXT    | Yes      | Sentinel.UNSET | Full URL to workflow run |

### capture-session-info

Capture Claude Code session info for CI workflows.

**Usage:** `erk exec capture-session-info`

**Options:**

| Flag     | Type | Required | Default        | Description                                              |
| -------- | ---- | -------- | -------------- | -------------------------------------------------------- |
| `--path` | PATH | No       | Sentinel.UNSET | Path to find session for (defaults to current directory) |

### ci-fetch-summaries

Fetch CI failure summaries for a PR.

**Usage:** `erk exec ci-fetch-summaries`

**Options:**

| Flag          | Type    | Required | Default        | Description                      |
| ------------- | ------- | -------- | -------------- | -------------------------------- |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to fetch summaries for |

### ci-generate-summaries

Generate CI failure summaries using Haiku.

**Usage:** `erk exec ci-generate-summaries`

**Options:**

| Flag          | Type    | Required | Default        | Description                  |
| ------------- | ------- | -------- | -------------- | ---------------------------- |
| `--run-id`    | TEXT    | Yes      | Sentinel.UNSET | GitHub Actions run ID        |
| `--pr-number` | INTEGER | No       | -              | PR number to post comment on |

### ci-update-pr-body

Update PR body with AI-generated summary and footer.

**Usage:** `erk exec ci-update-pr-body`

**Options:**

| Flag           | Type    | Required | Default        | Description                 |
| -------------- | ------- | -------- | -------------- | --------------------------- |
| `--pr-number`  | INTEGER | Yes      | Sentinel.UNSET | PR identifier (for context) |
| `--run-id`     | TEXT    | No       | -              | Optional workflow run ID    |
| `--run-url`    | TEXT    | No       | -              | Optional workflow run URL   |
| `--planned-pr` | FLAG    | No       | -              | Planned-PR PR               |

### ci-verify-autofix

Run full CI verification after autofix push.

**Usage:** `erk exec ci-verify-autofix`

**Options:**

| Flag             | Type | Required | Default        | Description                    |
| ---------------- | ---- | -------- | -------------- | ------------------------------ |
| `--original-sha` | TEXT | Yes      | Sentinel.UNSET | SHA before autofix ran         |
| `--repo`         | TEXT | Yes      | Sentinel.UNSET | GitHub repository (owner/repo) |

### cleanup-impl-context

Clean up .erk/impl-context/ staging directory.

**Usage:** `erk exec cleanup-impl-context`

### close-pr

Close a plan with a comment.

**Usage:** `erk exec close-pr` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

**Options:**

| Flag        | Type | Required | Default        | Description                        |
| ----------- | ---- | -------- | -------------- | ---------------------------------- |
| `--comment` | TEXT | Yes      | Sentinel.UNSET | Comment body to add before closing |

### close-prs

Batch close multiple plan PRs with comments from JSON stdin.

**Usage:** `erk exec close-prs`

### cmux-open-pr

Create a cmux workspace to open a PR.

**Usage:** `erk exec cmux-open-pr`

**Options:**

| Flag       | Type    | Required | Default        | Description                                                |
| ---------- | ------- | -------- | -------------- | ---------------------------------------------------------- |
| `--pr`     | INTEGER | Yes      | Sentinel.UNSET | PR number to open                                          |
| `--branch` | TEXT    | No       | -              | PR head branch name (auto-detected via gh if omitted)      |
| `--mode`   | CHOICE  | No       | 'checkout'     | checkout (lightweight) or teleport (heavyweight with sync) |

### create-impl-context-from-plan

Create .erk/impl-context/ folder from plan content.

**Usage:** `erk exec create-impl-context-from-plan` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

### create-pr-from-session

Extract plan from Claude session and create GitHub draft PR.

**Usage:** `erk exec create-pr-from-session`

**Options:**

| Flag            | Type | Required | Default        | Description                                                                   |
| --------------- | ---- | -------- | -------------- | ----------------------------------------------------------------------------- |
| `--session-id`  | TEXT | No       | Sentinel.UNSET | Session ID to search within (optional, searches all sessions if not provided) |
| `--summary`     | TEXT | No       | Sentinel.UNSET | AI-generated summary to display above the collapsed PR in the PR body         |
| `--branch-slug` | TEXT | No       | -              | Pre-generated branch slug (required). Generate in the calling skill layer.    |

### dash-data

Serialize plan dashboard data to JSON.

**Usage:** `erk exec dash-data`

**Options:**

| Flag          | Type    | Required | Default     | Description |
| ------------- | ------- | -------- | ----------- | ----------- |
| `--state`     | CHOICE  | No       | -           | -           |
| `--label`     | TEXT    | No       | ('erk-pr',) | -           |
| `--limit`     | INTEGER | No       | -           | -           |
| `--show-prs`  | FLAG    | No       | -           | -           |
| `--show-runs` | FLAG    | No       | -           | -           |
| `--run-state` | TEXT    | No       | -           | -           |
| `--creator`   | TEXT    | No       | -           | -           |

### detect-plan-from-branch

Detect PR number from the current git branch.

**Usage:** `erk exec detect-plan-from-branch`

### detect-trunk-branch

Detect whether repo uses main or master as trunk branch.

**Usage:** `erk exec detect-trunk-branch`

### discover-reviews

Discover code reviews matching PR changed files.

**Usage:** `erk exec discover-reviews`

**Options:**

| Flag            | Type    | Required | Default        | Description                                                     |
| --------------- | ------- | -------- | -------------- | --------------------------------------------------------------- |
| `--pr-number`   | INTEGER | Yes      | Sentinel.UNSET | PR number to analyze                                            |
| `--reviews-dir` | TEXT    | No       | '.erk/reviews' | Directory containing review definitions (default: .erk/reviews) |

### download-remote-session

Download a session from a git branch.

**Usage:** `erk exec download-remote-session`

**Options:**

| Flag               | Type | Required | Default        | Description                                                      |
| ------------------ | ---- | -------- | -------------- | ---------------------------------------------------------------- |
| `--session-branch` | TEXT | Yes      | Sentinel.UNSET | Git branch containing the session (e.g., planned-pr-context/123) |
| `--session-id`     | TEXT | Yes      | Sentinel.UNSET | Claude session ID (used to locate file on the branch)            |

### exit-plan-mode-hook

Prompt user about plan saving when ExitPlanMode is called.

**Usage:** `erk exec exit-plan-mode-hook`

### extract-latest-plan

Extract the latest plan from Claude session files.

**Usage:** `erk exec extract-latest-plan`

**Options:**

| Flag           | Type | Required | Default        | Description                                                                   |
| -------------- | ---- | -------- | -------------- | ----------------------------------------------------------------------------- |
| `--session-id` | TEXT | No       | Sentinel.UNSET | Session ID to search within (optional, searches all sessions if not provided) |

### fetch-sessions

Fetch preprocessed sessions from a planned-pr-context branch.

**Usage:** `erk exec fetch-sessions`

**Options:**

| Flag           | Type    | Required | Default        | Description                          |
| -------------- | ------- | -------- | -------------- | ------------------------------------ |
| `--pr-number`  | INTEGER | Yes      | Sentinel.UNSET | PR identifier to fetch sessions for  |
| `--output-dir` | PATH    | Yes      | Sentinel.UNSET | Directory to write fetched XML files |

### generate-pr-address-summary

Generate enhanced PR comment for pr-address workflow.

**Usage:** `erk exec generate-pr-address-summary`

**Options:**

| Flag           | Type    | Required | Default             | Description                     |
| -------------- | ------- | -------- | ------------------- | ------------------------------- |
| `--pr-number`  | INTEGER | Yes      | Sentinel.UNSET      | PR number being addressed       |
| `--pre-head`   | TEXT    | Yes      | Sentinel.UNSET      | Commit SHA before Claude ran    |
| `--model-name` | TEXT    | No       | 'claude-sonnet-4-5' | Claude model name used          |
| `--run-url`    | TEXT    | Yes      | Sentinel.UNSET      | URL to the workflow run         |
| `--job-status` | CHOICE  | Yes      | Sentinel.UNSET      | Job status (success or failure) |

### get-embedded-prompt

Get embedded prompt content from bundled prompts.

**Usage:** `erk exec get-embedded-prompt` <prompt_name>

**Arguments:**

| Name          | Required | Description |
| ------------- | -------- | ----------- |
| `PROMPT_NAME` | Yes      | -           |

**Options:**

| Flag         | Type | Required | Default        | Description                                          |
| ------------ | ---- | -------- | -------------- | ---------------------------------------------------- |
| `--var`      | TEXT | No       | Sentinel.UNSET | Variable substitution as KEY=VALUE (can be repeated) |
| `--var-file` | TEXT | No       | Sentinel.UNSET | Variable from file as KEY=PATH (can be repeated)     |

### get-issue-body

Fetch an issue's body using REST API (avoids GraphQL rate limits).

**Usage:** `erk exec get-issue-body` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

### get-learn-sessions

Get session information for a plan.

**Usage:** `erk exec get-learn-sessions` [issue]

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `ISSUE` | No       | -           |

### get-plan-info

Retrieve plan info from the appropriate backend.

**Usage:** `erk exec get-plan-info` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

**Options:**

| Flag             | Type | Required | Default | Description                                 |
| ---------------- | ---- | -------- | ------- | ------------------------------------------- |
| `--include-body` | FLAG | No       | -       | Include the PR body content in the response |

### get-plan-metadata

Extract a metadata field from a plan's plan-header block.

**Usage:** `erk exec get-plan-metadata` <pr_number> <field_name>

**Arguments:**

| Name         | Required | Description |
| ------------ | -------- | ----------- |
| `PR_NUMBER`  | Yes      | -           |
| `FIELD_NAME` | Yes      | -           |

### get-plans-for-objective

Fetch erk-plans linked to an objective.

**Usage:** `erk exec get-plans-for-objective` <objective_number>

**Arguments:**

| Name               | Required | Description |
| ------------------ | -------- | ----------- |
| `OBJECTIVE_NUMBER` | Yes      | -           |

### get-pr-body-footer

Generate PR body footer with teleport command.

**Usage:** `erk exec get-pr-body-footer`

**Options:**

| Flag          | Type    | Required | Default        | Description                    |
| ------------- | ------- | -------- | -------------- | ------------------------------ |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number for checkout command |

### get-pr-commits

Fetch PR commits using REST API (avoids GraphQL rate limits).

**Usage:** `erk exec get-pr-commits` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

### get-pr-context

Output JSON with branch, PR, diff, commits, and plan context.

**Usage:** `erk exec get-pr-context`

**Options:**

| Flag      | Type | Required | Default | Description            |
| --------- | ---- | -------- | ------- | ---------------------- |
| `--debug` | FLAG | No       | -       | Show diagnostic output |

### get-pr-discussion-comments

Fetch PR discussion comments for agent context injection.

**Usage:** `erk exec get-pr-discussion-comments`

**Options:**

| Flag   | Type    | Required | Default | Description                                 |
| ------ | ------- | -------- | ------- | ------------------------------------------- |
| `--pr` | INTEGER | No       | -       | PR number (defaults to current branch's PR) |

### get-pr-feedback

Fetch all PR feedback in a single command.

**Usage:** `erk exec get-pr-feedback`

**Options:**

| Flag                 | Type    | Required | Default | Description                                 |
| -------------------- | ------- | -------- | ------- | ------------------------------------------- |
| `--pr`               | INTEGER | No       | -       | PR number (defaults to current branch's PR) |
| `--include-resolved` | FLAG    | No       | -       | Include resolved review threads             |

### get-pr-for-plan

Get PR details for a plan.

**Usage:** `erk exec get-pr-for-plan` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

### get-pr-review-comments

Fetch PR review comments for agent context injection.

**Usage:** `erk exec get-pr-review-comments`

**Options:**

| Flag                 | Type    | Required | Default | Description                                 |
| -------------------- | ------- | -------- | ------- | ------------------------------------------- |
| `--pr`               | INTEGER | No       | -       | PR number (defaults to current branch's PR) |
| `--include-resolved` | FLAG    | No       | -       | Include resolved threads                    |

### get-pr-view

Fetch PR details using REST API (avoids GraphQL rate limits).

**Usage:** `erk exec get-pr-view` [pr_number]

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | No       | -           |

**Options:**

| Flag       | Type | Required | Default | Description                   |
| ---------- | ---- | -------- | ------- | ----------------------------- |
| `--branch` | TEXT | No       | -       | Branch name to look up PR for |

### get-review-activity-log

Fetch the activity log from an existing review summary comment.

**Usage:** `erk exec get-review-activity-log`

**Options:**

| Flag          | Type    | Required | Default        | Description                                |
| ------------- | ------- | -------- | -------------- | ------------------------------------------ |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to search                        |
| `--marker`    | TEXT    | Yes      | Sentinel.UNSET | HTML marker identifying the review comment |

### handle-no-changes

Handle no-changes scenario gracefully.

**Usage:** `erk exec handle-no-changes`

**Options:**

| Flag               | Type    | Required | Default        | Description                                       |
| ------------------ | ------- | -------- | -------------- | ------------------------------------------------- |
| `--pr-number`      | INTEGER | Yes      | Sentinel.UNSET | PR number to update                               |
| `--behind-count`   | INTEGER | Yes      | Sentinel.UNSET | How many commits behind base branch               |
| `--base-branch`    | TEXT    | Yes      | Sentinel.UNSET | Base branch name                                  |
| `--original-title` | TEXT    | Yes      | Sentinel.UNSET | Original PR title                                 |
| `--recent-commits` | TEXT    | No       | -              | Recent commits on base branch (newline-separated) |
| `--run-url`        | TEXT    | No       | -              | Optional workflow run URL                         |

### impl-init

Initialize implementation by validating .erk/impl-context/ folder.

**Usage:** `erk exec impl-init`

**Options:**

| Flag     | Type | Required | Default | Description           |
| -------- | ---- | -------- | ------- | --------------------- |
| `--json` | FLAG | No       | -       | Output JSON (default) |

### impl-signal

Signal implementation events to GitHub.

**Usage:** `erk exec impl-signal` <event>

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `EVENT` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                                        |
| -------------- | ---- | -------- | ------- | -------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for PR file deletion on 'started' event |

### impl-verify

Verify .erk/impl-context/ folder still exists after implementation.

**Usage:** `erk exec impl-verify`

### incremental-dispatch

Dispatch a local plan against an existing PR for remote implementation.

**Usage:** `erk exec incremental-dispatch`

**Options:**

| Flag            | Type    | Required | Default        | Description                               |
| --------------- | ------- | -------- | -------------- | ----------------------------------------- |
| `--plan-file`   | PATH    | Yes      | Sentinel.UNSET | Path to PR markdown file                  |
| `--pr`          | INTEGER | Yes      | Sentinel.UNSET | PR number to dispatch against             |
| `--ref`         | TEXT    | No       | -              | Branch to dispatch workflow from          |
| `--ref-current` | FLAG    | No       | -              | Dispatch workflow from the current branch |
| `--format`      | CHOICE  | No       | 'json'         | Output format                             |

### land-execute

Execute deferred land operations.

**Usage:** `erk exec land-execute`

**Options:**

| Flag                  | Type    | Required | Default        | Description                                                                              |
| --------------------- | ------- | -------- | -------------- | ---------------------------------------------------------------------------------------- |
| `--pr-number`         | INTEGER | Yes      | Sentinel.UNSET | PR number to merge                                                                       |
| `--branch`            | TEXT    | Yes      | Sentinel.UNSET | Branch name being landed                                                                 |
| `--worktree-path`     | PATH    | No       | Sentinel.UNSET | Path to worktree being cleaned up                                                        |
| `--is-current-branch` | FLAG    | No       | -              | Whether landing from the branch's own worktree                                           |
| `--target-child`      | TEXT    | No       | Sentinel.UNSET | Target child branch for --up navigation                                                  |
| `--objective-number`  | INTEGER | No       | Sentinel.UNSET | Linked objective issue number                                                            |
| `--linked-pr-number`  | INTEGER | No       | Sentinel.UNSET | Linked PR number                                                                         |
| `--use-graphite`      | FLAG    | No       | -              | Use Graphite for merge                                                                   |
| `--pull`              | FLAG    | No       | -              | Pull latest changes after landing (default: --pull)                                      |
| `--no-delete`         | FLAG    | No       | -              | Preserve the local branch and its slot assignment after landing                          |
| `--no-cleanup`        | FLAG    | No       | -              | User declined cleanup during validation phase                                            |
| `--skip-learn`        | FLAG    | No       | -              | Skip creating a learn PR                                                                 |
| `--script`            | FLAG    | No       | -              | Output activation script path (for shell integration)                                    |
| `--up`                | FLAG    | No       | -              | Navigate upstack to child branch after landing (resolves child at execution time)        |
| `-f`, `--force`       | FLAG    | No       | -              | Accept flag for compatibility (execute mode always skips confirmations)                  |
| `--down`              | FLAG    | No       | -              | Accept flag for compatibility (navigate-to-trunk is the default when --up is not passed) |

### list-sessions

List Claude Code sessions with metadata for the current project.

**Usage:** `erk exec list-sessions`

**Options:**

| Flag           | Type    | Required | Default | Description                                               |
| -------------- | ------- | -------- | ------- | --------------------------------------------------------- |
| `--limit`      | INTEGER | No       | 10      | Maximum number of sessions to list                        |
| `--min-size`   | INTEGER | No       | 0       | Minimum session size in bytes (filters out tiny sessions) |
| `--session-id` | TEXT    | No       | -       | Current session ID (for marking the current session)      |

### marker

Manage marker files for inter-process communication.

**Usage:** `erk exec marker`

#### create

Create a marker file.

**Usage:** `erk exec marker create` <name>

**Arguments:**

| Name   | Required | Description |
| ------ | -------- | ----------- |
| `NAME` | Yes      | -           |

**Options:**

| Flag                     | Type    | Required | Default | Description                                                             |
| ------------------------ | ------- | -------- | ------- | ----------------------------------------------------------------------- |
| `--session-id`           | TEXT    | No       | -       | Session ID for marker storage (required)                                |
| `--associated-objective` | INTEGER | No       | -       | Associated objective issue number (stored in marker file)               |
| `--content`              | TEXT    | No       | -       | Content to store in marker file (alternative to --associated-objective) |

#### delete

Delete a marker file.

**Usage:** `erk exec marker delete` <name>

**Arguments:**

| Name   | Required | Description |
| ------ | -------- | ----------- |
| `NAME` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                              |
| -------------- | ---- | -------- | ------- | ---------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for marker storage (required) |

#### exists

Check if a marker file exists.

**Usage:** `erk exec marker exists` <name>

**Arguments:**

| Name   | Required | Description |
| ------ | -------- | ----------- |
| `NAME` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                              |
| -------------- | ---- | -------- | ------- | ---------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for marker storage (required) |

#### read

Read content from a marker file.

**Usage:** `erk exec marker read` <name>

**Arguments:**

| Name   | Required | Description |
| ------ | -------- | ----------- |
| `NAME` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                              |
| -------------- | ---- | -------- | ------- | ---------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for marker storage (required) |

### migrate-objective-schema

Migrate an objective's roadmap YAML to the latest schema (v4).

**Usage:** `erk exec migrate-objective-schema` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag        | Type | Required | Default | Description              |
| ----------- | ---- | -------- | ------- | ------------------------ |
| `--dry-run` | FLAG | No       | -       | Preview without updating |

### normalize-tripwire-candidates

Normalize agent-produced tripwire candidate JSON in-place.

**Usage:** `erk exec normalize-tripwire-candidates`

**Options:**

| Flag                | Type | Required | Default        | Description                      |
| ------------------- | ---- | -------- | -------------- | -------------------------------- |
| `--candidates-file` | TEXT | Yes      | Sentinel.UNSET | Path to tripwire-candidates.json |

### objective-apply-landed-update

Apply mechanical updates to an objective after landing a PR.

**Usage:** `erk exec objective-apply-landed-update`

**Options:**

| Flag           | Type    | Required | Default        | Description                                                 |
| -------------- | ------- | -------- | -------------- | ----------------------------------------------------------- |
| `--pr`         | INTEGER | No       | -              | PR number (auto-discovered if omitted)                      |
| `--objective`  | INTEGER | No       | -              | Objective issue (auto-discovered if omitted)                |
| `--branch`     | TEXT    | No       | -              | Branch name (auto-discovered if omitted)                    |
| `--node`       | TEXT    | No       | Sentinel.UNSET | Node ID(s) to mark as done (e.g., --node 1.1 --node 1.2)    |
| `--auto-close` | FLAG    | No       | -              | Automatically close the objective if all nodes are complete |

### objective-fetch-context

Fetch all context for objective update in a single call.

**Usage:** `erk exec objective-fetch-context`

**Options:**

| Flag          | Type    | Required | Default | Description                                             |
| ------------- | ------- | -------- | ------- | ------------------------------------------------------- |
| `--pr`        | INTEGER | No       | -       | PR number (auto-discovered if omitted)                  |
| `--objective` | INTEGER | No       | -       | Objective issue (auto-discovered if omitted)            |
| `--branch`    | TEXT    | No       | -       | Branch name (auto-discovered if omitted)                |
| `--plan`      | INTEGER | No       | -       | PR number (direct lookup, skips branch-based discovery) |

### objective-link-pr

Link PR number to objective roadmap nodes from .erk/impl-context/ metadata.

**Usage:** `erk exec objective-link-pr`

**Options:**

| Flag          | Type    | Required | Default        | Description                          |
| ------------- | ------- | -------- | -------------- | ------------------------------------ |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to link to objective nodes |

### objective-plan-setup

Fetch, validate, and set up context for objective planning.

**Usage:** `erk exec objective-plan-setup` <objective_number>

**Arguments:**

| Name               | Required | Description |
| ------------------ | -------- | ----------- |
| `OBJECTIVE_NUMBER` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default        | Description                          |
| -------------- | ---- | -------- | -------------- | ------------------------------------ |
| `--session-id` | TEXT | Yes      | Sentinel.UNSET | Claude session ID for marker storage |

### objective-post-action-comment

Post a formatted action comment to an objective issue.

**Usage:** `erk exec objective-post-action-comment`

### objective-render-roadmap

Render a complete roadmap section from JSON input on stdin.

**Usage:** `erk exec objective-render-roadmap`

### objective-save-to-issue

Save plan as objective GitHub issue.

**Usage:** `erk exec objective-save-to-issue`

**Options:**

| Flag           | Type   | Required | Default | Description                                                               |
| -------------- | ------ | -------- | ------- | ------------------------------------------------------------------------- |
| `--format`     | CHOICE | No       | 'json'  | Output format: json (default) or display (formatted text)                 |
| `--session-id` | TEXT   | No       | -       | Session ID for scoped PR lookup                                           |
| `--slug`       | TEXT   | No       | -       | Short kebab-case identifier for the objective (e.g., 'build-auth-system') |
| `--validate`   | FLAG   | No       | -       | Run objective validation after creation and include results in output     |

### objective-update-after-land

Update objective after landing a PR.

**Usage:** `erk exec objective-update-after-land`

**Options:**

| Flag          | Type    | Required | Default        | Description                    |
| ------------- | ------- | -------- | -------------- | ------------------------------ |
| `--objective` | INTEGER | Yes      | Sentinel.UNSET | Linked objective issue number  |
| `--pr`        | INTEGER | Yes      | Sentinel.UNSET | PR number that was just landed |
| `--branch`    | TEXT    | Yes      | Sentinel.UNSET | Branch name that was landed    |

### plan-save

Save plan as a draft PR.

**Usage:** `erk exec plan-save`

**Options:**

| Flag                              | Type      | Required | Default | Description                                                            |
| --------------------------------- | --------- | -------- | ------- | ---------------------------------------------------------------------- |
| `--format`                        | CHOICE    | No       | 'json'  | Output format: json (default) or display (formatted text)              |
| `--plan-file`                     | PATH      | No       | -       | Path to specific PR file (highest priority)                            |
| `--session-id`                    | TEXT      | No       | -       | Session ID for scoped PR lookup                                        |
| `--plan-type`                     | CHOICE    | No       | -       | PR type: standard (default) or learn                                   |
| `--learned-from-issue`            | INTEGER   | No       | -       | Parent PR number (for learn plans)                                     |
| `--created-from-workflow-run-url` | TEXT      | No       | -       | GitHub Actions workflow run URL                                        |
| `--branch-slug`                   | TEXT      | No       | -       | Pre-generated branch slug (skips LLM call when provided)               |
| `--objective`                     | INTEGER   | No       | -       | Objective issue number (overrides session marker)                      |
| `--summary`                       | TEXT      | No       | -       | AI-generated PR summary for PR description                             |
| `--session-xml-dir`               | DIRECTORY | No       | -       | Directory containing session XML files to embed in the PR diff         |
| `--current-branch`                | FLAG      | No       | -       | Use the current branch directly instead of creating a new plnd/ branch |

### plan-update

Update an existing plan's content.

**Usage:** `erk exec plan-update`

**Options:**

| Flag           | Type    | Required | Default        | Description                                                           |
| -------------- | ------- | -------- | -------------- | --------------------------------------------------------------------- |
| `--pr-number`  | INTEGER | Yes      | Sentinel.UNSET | PR number to update                                                   |
| `--format`     | CHOICE  | No       | 'json'         | Output format: json (default) or display (formatted text)             |
| `--plan-path`  | PATH    | No       | Sentinel.UNSET | Direct path to PR file (overrides session lookup)                     |
| `--session-id` | TEXT    | No       | Sentinel.UNSET | Session ID to find PR file in scratch storage                         |
| `--summary`    | TEXT    | No       | Sentinel.UNSET | AI-generated summary to display above the collapsed PR in the PR body |

### post-or-update-pr-summary

Post or update a PR summary comment.

**Usage:** `erk exec post-or-update-pr-summary`

**Options:**

| Flag          | Type    | Required | Default        | Description                             |
| ------------- | ------- | -------- | -------------- | --------------------------------------- |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to comment on                 |
| `--marker`    | TEXT    | Yes      | Sentinel.UNSET | HTML marker to identify the comment     |
| `--body`      | TEXT    | Yes      | Sentinel.UNSET | Comment body text (must include marker) |

### post-pr-inline-comment

Post an inline review comment on a PR.

**Usage:** `erk exec post-pr-inline-comment`

**Options:**

| Flag          | Type    | Required | Default        | Description                     |
| ------------- | ------- | -------- | -------------- | ------------------------------- |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to comment on         |
| `--path`      | TEXT    | Yes      | Sentinel.UNSET | File path relative to repo root |
| `--line`      | INTEGER | Yes      | Sentinel.UNSET | Line number in the diff         |
| `--body`      | TEXT    | Yes      | Sentinel.UNSET | Comment body text               |

### post-workflow-started-comment

Post a workflow started comment to a GitHub issue.

**Usage:** `erk exec post-workflow-started-comment`

**Options:**

| Flag               | Type    | Required | Default        | Description                     |
| ------------------ | ------- | -------- | -------------- | ------------------------------- |
| `--pr-number`      | INTEGER | Yes      | Sentinel.UNSET | PR identifier                   |
| `--branch-name`    | TEXT    | Yes      | Sentinel.UNSET | Git branch name                 |
| `--impl-pr-number` | INTEGER | Yes      | Sentinel.UNSET | Pull request number             |
| `--run-id`         | TEXT    | Yes      | Sentinel.UNSET | GitHub Actions workflow run ID  |
| `--run-url`        | TEXT    | Yes      | Sentinel.UNSET | Full URL to workflow run        |
| `--repository`     | TEXT    | Yes      | Sentinel.UNSET | Repository in owner/repo format |

### pr-sync-commit

Sync PR title and body from the latest git commit.

**Usage:** `erk exec pr-sync-commit`

**Options:**

| Flag     | Type | Required | Default | Description    |
| -------- | ---- | -------- | ------- | -------------- |
| `--json` | FLAG | No       | -       | Output as JSON |

### pre-tool-use-hook

PreToolUse hook for dignified-python reminders on .py file edits.

**Usage:** `erk exec pre-tool-use-hook`

### preprocess-session

Preprocess session log JSONL to compressed XML format.

**Usage:** `erk exec preprocess-session` <log_path>

**Arguments:**

| Name       | Required | Description |
| ---------- | -------- | ----------- |
| `LOG_PATH` | Yes      | -           |

**Options:**

| Flag               | Type    | Required | Default | Description                                             |
| ------------------ | ------- | -------- | ------- | ------------------------------------------------------- |
| `--session-id`     | TEXT    | No       | -       | Filter JSONL entries by session ID before preprocessing |
| `--include-agents` | FLAG    | No       | -       | Include agent logs from same directory (default: True)  |
| `--no-filtering`   | FLAG    | No       | -       | Disable all filtering optimizations (raw output)        |
| `--stdout`         | FLAG    | No       | -       | Output XML to stdout instead of temp file               |
| `--max-tokens`     | INTEGER | No       | -       | Split output into multiple files of ~max-tokens each    |
| `--output-dir`     | PATH    | No       | -       | Directory to write output files (requires --prefix)     |
| `--prefix`         | TEXT    | No       | -       | Prefix for output filenames (requires --output-dir)     |

### push-and-create-pr

Push branch and create/find PR, outputting JSON.

**Usage:** `erk exec push-and-create-pr`

**Options:**

| Flag            | Type | Required | Default | Description                       |
| --------------- | ---- | -------- | ------- | --------------------------------- |
| `-f`, `--force` | FLAG | No       | -       | Force push                        |
| `--no-graphite` | FLAG | No       | -       | Skip Graphite (use git + gh only) |
| `--session-id`  | TEXT | No       | -       | Claude session ID for tracing     |

### push-session

Preprocess and push a session to the planned-pr-context branch with accumulation.

**Usage:** `erk exec push-session`

**Options:**

| Flag             | Type    | Required | Default        | Description                                             |
| ---------------- | ------- | -------- | -------------- | ------------------------------------------------------- |
| `--session-file` | PATH    | Yes      | Sentinel.UNSET | Path to the session JSONL file to preprocess and upload |
| `--session-id`   | TEXT    | Yes      | Sentinel.UNSET | Claude Code session ID                                  |
| `--stage`        | CHOICE  | Yes      | Sentinel.UNSET | Lifecycle stage: planning, impl, or address             |
| `--source`       | CHOICE  | Yes      | Sentinel.UNSET | Session source: 'local' or 'remote'                     |
| `--pr-number`    | INTEGER | Yes      | Sentinel.UNSET | PR identifier for the planned-pr-context branch         |

### quick-submit

Quick commit all changes and submit.

**Usage:** `erk exec quick-submit`

### rebase-with-conflict-resolution

Rebase onto target branch and resolve conflicts with Claude.

**Usage:** `erk exec rebase-with-conflict-resolution`

**Options:**

| Flag              | Type    | Required | Default             | Description                                                        |
| ----------------- | ------- | -------- | ------------------- | ------------------------------------------------------------------ |
| `--target-branch` | TEXT    | Yes      | Sentinel.UNSET      | Branch to rebase onto (trunk or parent branch for stacked PRs)     |
| `--branch-name`   | TEXT    | Yes      | Sentinel.UNSET      | Current branch name for force push                                 |
| `--model`         | TEXT    | No       | 'claude-sonnet-4-5' | Claude model to use for conflict resolution and summary generation |
| `--max-attempts`  | INTEGER | No       | 5                   | Maximum number of conflict resolution attempts                     |

### register-one-shot-plan

Register a one-shot plan with issue metadata and comment.

**Usage:** `erk exec register-one-shot-plan`

**Options:**

| Flag               | Type    | Required | Default        | Description |
| ------------------ | ------- | -------- | -------------- | ----------- |
| `--pr-number`      | INTEGER | Yes      | Sentinel.UNSET | -           |
| `--run-id`         | TEXT    | Yes      | Sentinel.UNSET | -           |
| `--impl-pr-number` | INTEGER | Yes      | Sentinel.UNSET | -           |
| `--submitted-by`   | TEXT    | Yes      | Sentinel.UNSET | -           |
| `--run-url`        | TEXT    | Yes      | Sentinel.UNSET | -           |

### reply-to-discussion-comment

Reply to a PR discussion comment with quote and action summary.

**Usage:** `erk exec reply-to-discussion-comment`

**Options:**

| Flag           | Type    | Required | Default        | Description                                 |
| -------------- | ------- | -------- | -------------- | ------------------------------------------- |
| `--comment-id` | INTEGER | Yes      | Sentinel.UNSET | Numeric comment ID to reply to              |
| `--pr`         | INTEGER | No       | -              | PR number (defaults to current branch's PR) |
| `--reply`      | TEXT    | Yes      | Sentinel.UNSET | Action summary text (what was done)         |

### resolve-objective-ref

Resolve an objective reference to an objective number.

**Usage:** `erk exec resolve-objective-ref` [ref]

**Arguments:**

| Name  | Required | Description |
| ----- | -------- | ----------- |
| `REF` | No       | -           |

### resolve-review-thread

Resolve a PR review thread.

**Usage:** `erk exec resolve-review-thread`

**Options:**

| Flag          | Type | Required | Default        | Description                              |
| ------------- | ---- | -------- | -------------- | ---------------------------------------- |
| `--thread-id` | TEXT | Yes      | Sentinel.UNSET | GraphQL node ID of the thread to resolve |
| `--comment`   | TEXT | No       | -              | Optional comment to add before resolving |

### resolve-review-threads

Resolve multiple PR review threads from JSON stdin.

**Usage:** `erk exec resolve-review-threads`

### run-review

Run a code review using Claude.

**Usage:** `erk exec run-review`

**Options:**

| Flag            | Type    | Required | Default        | Description                                                     |
| --------------- | ------- | -------- | -------------- | --------------------------------------------------------------- |
| `--name`        | TEXT    | Yes      | Sentinel.UNSET | Review filename (without .md)                                   |
| `--pr-number`   | INTEGER | No       | Sentinel.UNSET | PR number to review (PR mode)                                   |
| `--local`       | FLAG    | No       | -              | Review local changes (local mode)                               |
| `--base`        | TEXT    | No       | Sentinel.UNSET | Base branch for local mode (default: auto-detect)               |
| `--reviews-dir` | TEXT    | No       | '.erk/reviews' | Directory containing review definitions (default: .erk/reviews) |
| `--dry-run`     | FLAG    | No       | -              | Print assembled prompt without running Claude                   |

### session-id-injector-hook

Inject session ID into conversation context when relevant.

**Usage:** `erk exec session-id-injector-hook`

### set-local-review-marker

Set local review marker on PR to skip CI reviews.

**Usage:** `erk exec set-local-review-marker`

### set-pr-description

Update PR title and body with agent-provided values.

**Usage:** `erk exec set-pr-description`

**Options:**

| Flag          | Type | Required | Default        | Description       |
| ------------- | ---- | -------- | -------------- | ----------------- |
| `--title`     | TEXT | Yes      | Sentinel.UNSET | PR title          |
| `--body`      | TEXT | No       | -              | PR body text      |
| `--body-file` | PATH | No       | -              | File with PR body |

### setup-impl

Consolidated implementation setup.

**Usage:** `erk exec setup-impl`

**Options:**

| Flag      | Type    | Required | Default | Description                  |
| --------- | ------- | -------- | ------- | ---------------------------- |
| `--issue` | INTEGER | No       | -       | PR number to set up from     |
| `--file`  | PATH    | No       | -       | Markdown file to set up from |

### setup-impl-from-pr

Set up .erk/impl-context/ folder from GitHub PR in current worktree.

**Usage:** `erk exec setup-impl-from-pr` <pr_number>

**Arguments:**

| Name        | Required | Description |
| ----------- | -------- | ----------- |
| `PR_NUMBER` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                                                                         |
| -------------- | ---- | -------- | ------- | ----------------------------------------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Claude session ID for marker creation                                               |
| `--no-impl`    | FLAG | No       | -       | Skip .erk/impl-context/ folder creation (for local execution without file overhead) |

### store-tripwire-candidates

Store tripwire candidates as a metadata comment on a plan.

**Usage:** `erk exec store-tripwire-candidates`

**Options:**

| Flag                | Type    | Required | Default        | Description                      |
| ------------------- | ------- | -------- | -------------- | -------------------------------- |
| `--pr-number`       | INTEGER | Yes      | Sentinel.UNSET | PR number                        |
| `--candidates-file` | TEXT    | Yes      | Sentinel.UNSET | Path to tripwire-candidates.json |

### summarize-impl-failure

Summarize an implementation failure using Haiku.

**Usage:** `erk exec summarize-impl-failure`

**Options:**

| Flag             | Type    | Required | Default        | Description                |
| ---------------- | ------- | -------- | -------------- | -------------------------- |
| `--session-file` | PATH    | Yes      | Sentinel.UNSET | Path to session JSONL file |
| `--pr-number`    | INTEGER | Yes      | Sentinel.UNSET | PR number                  |
| `--exit-code`    | INTEGER | No       | Sentinel.UNSET | Exit code                  |

### track-learn-evaluation

Track learn evaluation completion on a plan.

**Usage:** `erk exec track-learn-evaluation` [issue]

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `ISSUE` | No       | -           |

**Options:**

| Flag           | Type | Required | Default | Description                                                  |
| -------------- | ---- | -------- | ------- | ------------------------------------------------------------ |
| `--session-id` | TEXT | No       | -       | Session ID for tracking (passed from Claude session context) |

### track-learn-result

Track learn workflow result on a plan.

**Usage:** `erk exec track-learn-result`

**Options:**

| Flag           | Type    | Required | Default        | Description                                                          |
| -------------- | ------- | -------- | -------------- | -------------------------------------------------------------------- |
| `--pr-id`      | TEXT    | Yes      | Sentinel.UNSET | PR identifier (e.g., issue number)                                   |
| `--status`     | CHOICE  | Yes      | Sentinel.UNSET | Learn workflow result status                                         |
| `--learn-plan` | INTEGER | No       | Sentinel.UNSET | Learn PR number (required if status is completed_with_plan)          |
| `--plan-pr`    | INTEGER | No       | Sentinel.UNSET | Learn documentation PR number (required if status is pending_review) |

### update-issue-body

Update an issue's body using REST API (avoids GraphQL rate limits).

**Usage:** `erk exec update-issue-body` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag          | Type | Required | Default        | Description         |
| ------------- | ---- | -------- | -------------- | ------------------- |
| `--body`      | TEXT | No       | Sentinel.UNSET | New body content    |
| `--body-file` | PATH | No       | Sentinel.UNSET | Read body from file |

### update-objective-node

Update node fields in an objective's roadmap table.

**Usage:** `erk exec update-objective-node` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag             | Type   | Required | Default        | Description                                                             |
| ---------------- | ------ | -------- | -------------- | ----------------------------------------------------------------------- |
| `--node`         | TEXT   | Yes      | Sentinel.UNSET | Node ID(s) to update (e.g., '1.3')                                      |
| `--pr`           | TEXT   | No       | -              | PR reference (e.g., '#456', or '' to clear). Omit to preserve existing. |
| `--status`       | CHOICE | No       | -              | Explicit status to set (default: infer from PR value)                   |
| `--description`  | TEXT   | No       | -              | New description for the node. Omit to preserve existing.                |
| `--slug`         | TEXT   | No       | -              | New slug for the node. Omit to preserve existing.                       |
| `--comment`      | TEXT   | No       | -              | Comment text (e.g., why a node was skipped). Omit to preserve existing. |
| `--include-body` | FLAG   | No       | -              | Include the fully-mutated issue body in JSON output as 'updated_body'   |

### update-plan-header

Update plan-header metadata fields on a PR.

**Usage:** `erk exec update-plan-header` <pr_id> [fields]

**Arguments:**

| Name     | Required | Description |
| -------- | -------- | ----------- |
| `PR_ID`  | Yes      | -           |
| `FIELDS` | No       | -           |

### update-pr-description

Update PR title and body with AI-generated description.

**Usage:** `erk exec update-pr-description`

**Options:**

| Flag           | Type | Required | Default | Description                           |
| -------------- | ---- | -------- | ------- | ------------------------------------- |
| `--debug`      | FLAG | No       | -       | Show diagnostic output                |
| `--session-id` | TEXT | No       | -       | Session ID for scratch file isolation |

### upload-impl-session

Upload current implementation session for async learn.

**Usage:** `erk exec upload-impl-session`

**Options:**

| Flag           | Type | Required | Default        | Description                 |
| -------------- | ---- | -------- | -------------- | --------------------------- |
| `--session-id` | TEXT | Yes      | Sentinel.UNSET | Claude session ID to upload |

### user-prompt-hook

UserPromptSubmit hook for session persistence and coding reminders.

**Usage:** `erk exec user-prompt-hook`

### validate-claude-credentials

Validate Claude credentials for CI workflows.

**Usage:** `erk exec validate-claude-credentials`

### validate-plan-content

Validate plan content from file or stdin.

**Usage:** `erk exec validate-plan-content`

**Options:**

| Flag          | Type | Required | Default        | Description                                         |
| ------------- | ---- | -------- | -------------- | --------------------------------------------------- |
| `--plan-file` | PATH | No       | Sentinel.UNSET | Path to PR file. If not provided, reads from stdin. |
