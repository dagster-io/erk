---
name: erk-exec-reference
description: >
  Reference for all `erk exec` subcommands with flags and usage.
  Use when looking up erk exec command syntax, flags, or options.
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk-dev gen-exec-reference-docs' to regenerate. -->

# erk exec Commands Reference

Quick reference for all `erk exec` subcommands.

## Summary

| Command                           | Description                                                               |
| --------------------------------- | ------------------------------------------------------------------------- |
| `add-reaction-to-comment`         | Add a reaction to a PR/issue comment.                                     |
| `add-remote-execution-note`       | Add remote execution tracking note to PR body.                            |
| `capture-session-info`            | Capture Claude Code session info for CI workflows.                        |
| `check-impl`                      | Check .impl/ folder structure and validate prerequisites.                 |
| `ci-update-pr-body`               | Update PR body with AI-generated summary and footer.                      |
| `create-issue-from-session`       | Extract plan from Claude session and create GitHub issue.                 |
| `create-learn-branch`             | Create and push a branch for learn documentation.                         |
| `create-plan-from-context`        | Create GitHub issue from plan content with erk-plan label.                |
| `create-worker-impl-from-issue`   | Create .worker-impl/ folder from GitHub issue with plan content.          |
| `detect-trunk-branch`             | Detect whether repo uses main or master as trunk branch.                  |
| `discover-reviews`                | Discover code reviews matching PR changed files.                          |
| `download-remote-session`         | Download a session artifact from a GitHub Actions workflow run.           |
| `exit-plan-mode-hook`             | Prompt user about plan saving when ExitPlanMode is called.                |
| `extract-latest-plan`             | Extract the latest plan from Claude session files.                        |
| `find-project-dir`                | Find Claude Code project directory for a filesystem path.                 |
| `generate-pr-summary`             | Generate PR summary from PR diff using Claude.                            |
| `get-closing-text`                | Get closing text for PR body based on .impl/issue.json or branch name.    |
| `get-embedded-prompt`             | Get embedded prompt content from bundled prompts.                         |
| `get-issue-body`                  | Fetch an issue's body using REST API (avoids GraphQL rate limits).        |
| `get-issue-timeline-prs`          | Fetch PRs referencing an issue via REST API timeline.                     |
| `get-learn-sessions`              | Get session information for a plan issue.                                 |
| `get-plan-metadata`               | Extract a metadata field from a plan issue's plan-header block.           |
| `get-plans-for-objective`         | Fetch erk-plan issues linked to an objective.                             |
| `get-pr-body-footer`              | Generate PR body footer with checkout command.                            |
| `get-pr-discussion-comments`      | Fetch PR discussion comments for agent context injection.                 |
| `get-pr-for-plan`                 | Get PR details for a plan issue.                                          |
| `get-pr-review-comments`          | Fetch PR review comments for agent context injection.                     |
| `impl-init`                       | Initialize implementation by validating .impl/ folder.                    |
| `impl-signal`                     | Signal implementation events to GitHub.                                   |
| `impl-verify`                     | Verify .impl/ folder still exists after implementation.                   |
| `issue-title-to-filename`         | Convert plan title to filename.                                           |
| `land-execute`                    | Execute deferred land operations.                                         |
| `list-sessions`                   | List Claude Code sessions with metadata for the current project.          |
| `mark-impl-ended`                 | Update implementation ended event in GitHub issue and local state file.   |
| `mark-impl-started`               | Update implementation started event in GitHub issue and local state file. |
| `marker create`                   | Create a marker file.                                                     |
| `marker delete`                   | Delete a marker file.                                                     |
| `marker exists`                   | Check if a marker file exists.                                            |
| `marker read`                     | Read content from a marker file.                                          |
| `objective-save-to-issue`         | Save plan as objective GitHub issue.                                      |
| `plan-save-to-issue`              | Extract plan from ~/.claude/plans/ and create GitHub issue.               |
| `plan-update-issue`               | Update an existing GitHub issue's plan comment with new content.          |
| `post-or-update-pr-summary`       | Post or update a PR summary comment.                                      |
| `post-pr-inline-comment`          | Post an inline review comment on a PR.                                    |
| `post-workflow-started-comment`   | Post a workflow started comment to a GitHub issue.                        |
| `preprocess-session`              | Preprocess session log JSONL to compressed XML format.                    |
| `quick-submit`                    | Quick commit all changes and submit.                                      |
| `rebase-with-conflict-resolution` | Rebase onto target branch and resolve conflicts with Claude.              |
| `reply-to-discussion-comment`     | Reply to a PR discussion comment with quote and action summary.           |
| `resolve-review-thread`           | Resolve a PR review thread.                                               |
| `run-review`                      | Run a code review using Claude.                                           |
| `session-id-injector-hook`        | Inject session ID into conversation context when relevant.                |
| `setup-impl-from-issue`           | Set up .impl/ folder from GitHub issue in current worktree.               |
| `slot-objective`                  | Get the last objective issue for the current slot.                        |
| `track-learn-evaluation`          | Track learn evaluation completion on a plan issue.                        |
| `tripwires-reminder-hook`         | Output tripwires reminder for UserPromptSubmit hook.                      |
| `update-dispatch-info`            | Update dispatch info in GitHub issue plan-header metadata.                |
| `update-issue-body`               | Update an issue's body using REST API (avoids GraphQL rate limits).       |
| `user-prompt-hook`                | UserPromptSubmit hook for session persistence and coding reminders.       |
| `validate-claude-credentials`     | Validate Claude credentials for CI workflows.                             |
| `validate-plan-content`           | Validate plan content from stdin.                                         |
| `wrap-plan-in-metadata-block`     | Return plan content for issue body.                                       |

## Commands

### add-reaction-to-comment

Add a reaction to a PR/issue comment.

**Usage:** `erk exec add-reaction-to-comment`

**Options:**

| Flag           | Type    | Required | Default        | Description                                                         |
| -------------- | ------- | -------- | -------------- | ------------------------------------------------------------------- |
| `--comment-id` | INTEGER | Yes      | Sentinel.UNSET | Numeric comment ID                                                  |
| `--reaction`   | TEXT    | No       | '+1'           | Reaction type: +1, -1, laugh, confused, heart, hooray, rocket, eyes |

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

### check-impl

Check .impl/ folder structure and validate prerequisites.

**Usage:** `erk exec check-impl`

**Options:**

| Flag        | Type | Required | Default | Description              |
| ----------- | ---- | -------- | ------- | ------------------------ |
| `--dry-run` | FLAG | No       | -       | Validate and output JSON |

### ci-update-pr-body

Update PR body with AI-generated summary and footer.

**Usage:** `erk exec ci-update-pr-body`

**Options:**

| Flag             | Type    | Required | Default        | Description                    |
| ---------------- | ------- | -------- | -------------- | ------------------------------ |
| `--issue-number` | INTEGER | Yes      | Sentinel.UNSET | Issue number to close on merge |
| `--run-id`       | TEXT    | No       | -              | Optional workflow run ID       |
| `--run-url`      | TEXT    | No       | -              | Optional workflow run URL      |

### create-issue-from-session

Extract plan from Claude session and create GitHub issue.

**Usage:** `erk exec create-issue-from-session`

**Options:**

| Flag           | Type | Required | Default        | Description                                                                   |
| -------------- | ---- | -------- | -------------- | ----------------------------------------------------------------------------- |
| `--session-id` | TEXT | No       | Sentinel.UNSET | Session ID to search within (optional, searches all sessions if not provided) |

### create-learn-branch

Create and push a branch for learn documentation.

**Usage:** `erk exec create-learn-branch`

**Options:**

| Flag             | Type    | Required | Default        | Description                        |
| ---------------- | ------- | -------- | -------------- | ---------------------------------- |
| `--issue-number` | INTEGER | Yes      | Sentinel.UNSET | GitHub issue number                |
| `--trunk-branch` | TEXT    | Yes      | Sentinel.UNSET | Name of trunk branch (main/master) |

### create-plan-from-context

Create GitHub issue from plan content with erk-plan label.

**Usage:** `erk exec create-plan-from-context`

### create-worker-impl-from-issue

Create .worker-impl/ folder from GitHub issue with plan content.

**Usage:** `erk exec create-worker-impl-from-issue` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag          | Type      | Required | Default | Description                                               |
| ------------- | --------- | -------- | ------- | --------------------------------------------------------- |
| `--repo-root` | DIRECTORY | No       | -       | Repository root directory (defaults to current directory) |

### detect-trunk-branch

Detect whether repo uses main or master as trunk branch.

**Usage:** `erk exec detect-trunk-branch`

### discover-reviews

Discover code reviews matching PR changed files.

**Usage:** `erk exec discover-reviews`

**Options:**

| Flag            | Type    | Required | Default           | Description                                                        |
| --------------- | ------- | -------- | ----------------- | ------------------------------------------------------------------ |
| `--pr-number`   | INTEGER | Yes      | Sentinel.UNSET    | PR number to analyze                                               |
| `--reviews-dir` | TEXT    | No       | '.claude/reviews' | Directory containing review definitions (default: .claude/reviews) |

### download-remote-session

Download a session artifact from a GitHub Actions workflow run.

**Usage:** `erk exec download-remote-session`

**Options:**

| Flag           | Type | Required | Default        | Description                                 |
| -------------- | ---- | -------- | -------------- | ------------------------------------------- |
| `--run-id`     | TEXT | Yes      | Sentinel.UNSET | GitHub Actions workflow run ID              |
| `--session-id` | TEXT | Yes      | Sentinel.UNSET | Claude session ID (used to locate artifact) |

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

### find-project-dir

Find Claude Code project directory for a filesystem path.

**Usage:** `erk exec find-project-dir`

**Options:**

| Flag     | Type | Required | Default        | Description                                              |
| -------- | ---- | -------- | -------------- | -------------------------------------------------------- |
| `--path` | PATH | No       | Sentinel.UNSET | Path to find project for (defaults to current directory) |
| `--json` | FLAG | No       | -              | Output in JSON format                                    |

### generate-pr-summary

Generate PR summary from PR diff using Claude.

**Usage:** `erk exec generate-pr-summary`

**Options:**

| Flag          | Type    | Required | Default        | Description            |
| ------------- | ------- | -------- | -------------- | ---------------------- |
| `--pr-number` | INTEGER | Yes      | Sentinel.UNSET | PR number to summarize |

### get-closing-text

Get closing text for PR body based on .impl/issue.json or branch name.

**Usage:** `erk exec get-closing-text`

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

### get-issue-timeline-prs

Fetch PRs referencing an issue via REST API timeline.

**Usage:** `erk exec get-issue-timeline-prs` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

### get-learn-sessions

Get session information for a plan issue.

**Usage:** `erk exec get-learn-sessions` [issue]

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `ISSUE` | No       | -           |

### get-plan-metadata

Extract a metadata field from a plan issue's plan-header block.

**Usage:** `erk exec get-plan-metadata` <issue_number> <field_name>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |
| `FIELD_NAME`   | Yes      | -           |

### get-plans-for-objective

Fetch erk-plan issues linked to an objective.

**Usage:** `erk exec get-plans-for-objective` <objective_number>

**Arguments:**

| Name               | Required | Description |
| ------------------ | -------- | ----------- |
| `OBJECTIVE_NUMBER` | Yes      | -           |

### get-pr-body-footer

Generate PR body footer with checkout command.

**Usage:** `erk exec get-pr-body-footer`

**Options:**

| Flag             | Type    | Required | Default        | Description                                   |
| ---------------- | ------- | -------- | -------------- | --------------------------------------------- |
| `--pr-number`    | INTEGER | Yes      | Sentinel.UNSET | PR number for checkout command                |
| `--issue-number` | INTEGER | No       | Sentinel.UNSET | Issue number to close                         |
| `--plans-repo`   | TEXT    | No       | Sentinel.UNSET | Target repo in owner/repo format (cross-repo) |

### get-pr-discussion-comments

Fetch PR discussion comments for agent context injection.

**Usage:** `erk exec get-pr-discussion-comments`

**Options:**

| Flag   | Type    | Required | Default | Description                                 |
| ------ | ------- | -------- | ------- | ------------------------------------------- |
| `--pr` | INTEGER | No       | -       | PR number (defaults to current branch's PR) |

### get-pr-for-plan

Get PR details for a plan issue.

**Usage:** `erk exec get-pr-for-plan` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

### get-pr-review-comments

Fetch PR review comments for agent context injection.

**Usage:** `erk exec get-pr-review-comments`

**Options:**

| Flag                 | Type    | Required | Default | Description                                 |
| -------------------- | ------- | -------- | ------- | ------------------------------------------- |
| `--pr`               | INTEGER | No       | -       | PR number (defaults to current branch's PR) |
| `--include-resolved` | FLAG    | No       | -       | Include resolved threads                    |

### impl-init

Initialize implementation by validating .impl/ folder.

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

| Flag           | Type | Required | Default | Description                                          |
| -------------- | ---- | -------- | ------- | ---------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for plan file deletion on 'started' event |

### impl-verify

Verify .impl/ folder still exists after implementation.

**Usage:** `erk exec impl-verify`

### issue-title-to-filename

Convert plan title to filename.

**Usage:** `erk exec issue-title-to-filename` <title>

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `TITLE` | Yes      | -           |

### land-execute

Execute deferred land operations.

**Usage:** `erk exec land-execute`

**Options:**

| Flag                  | Type    | Required | Default        | Description                                                                       |
| --------------------- | ------- | -------- | -------------- | --------------------------------------------------------------------------------- |
| `--pr-number`         | INTEGER | Yes      | Sentinel.UNSET | PR number to merge                                                                |
| `--branch`            | TEXT    | Yes      | Sentinel.UNSET | Branch name being landed                                                          |
| `--worktree-path`     | PATH    | No       | Sentinel.UNSET | Path to worktree being cleaned up                                                 |
| `--is-current-branch` | FLAG    | No       | -              | Whether landing from the branch's own worktree                                    |
| `--target-child`      | TEXT    | No       | Sentinel.UNSET | Target child branch for --up navigation                                           |
| `--objective-number`  | INTEGER | No       | Sentinel.UNSET | Linked objective issue number                                                     |
| `--use-graphite`      | FLAG    | No       | -              | Use Graphite for merge                                                            |
| `--pull`              | FLAG    | No       | -              | Pull latest changes after landing (default: --pull)                               |
| `--no-delete`         | FLAG    | No       | -              | Preserve the local branch and its slot assignment after landing                   |
| `--script`            | FLAG    | No       | -              | Output activation script path (for shell integration)                             |
| `--up`                | FLAG    | No       | -              | Navigate upstack to child branch after landing (resolves child at execution time) |
| `-f`, `--force`       | FLAG    | No       | -              | Accept flag for compatibility (execute mode always skips confirmations)           |

### list-sessions

List Claude Code sessions with metadata for the current project.

**Usage:** `erk exec list-sessions`

**Options:**

| Flag           | Type    | Required | Default | Description                                               |
| -------------- | ------- | -------- | ------- | --------------------------------------------------------- |
| `--limit`      | INTEGER | No       | 10      | Maximum number of sessions to list                        |
| `--min-size`   | INTEGER | No       | 0       | Minimum session size in bytes (filters out tiny sessions) |
| `--session-id` | TEXT    | No       | -       | Current session ID (for marking the current session)      |

### mark-impl-ended

Update implementation ended event in GitHub issue and local state file.

**Usage:** `erk exec mark-impl-ended`

**Options:**

| Flag           | Type | Required | Default | Description                                          |
| -------------- | ---- | -------- | ------- | ---------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for tracking (passed from hooks/commands) |

### mark-impl-started

Update implementation started event in GitHub issue and local state file.

**Usage:** `erk exec mark-impl-started`

**Options:**

| Flag           | Type | Required | Default | Description                                          |
| -------------- | ---- | -------- | ------- | ---------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Session ID for tracking (passed from hooks/commands) |

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

### objective-save-to-issue

Save plan as objective GitHub issue.

**Usage:** `erk exec objective-save-to-issue`

**Options:**

| Flag           | Type   | Required | Default | Description                                               |
| -------------- | ------ | -------- | ------- | --------------------------------------------------------- |
| `--format`     | CHOICE | No       | 'json'  | Output format: json (default) or display (formatted text) |
| `--session-id` | TEXT   | No       | -       | Session ID for scoped plan lookup                         |

### plan-save-to-issue

Extract plan from ~/.claude/plans/ and create GitHub issue.

**Usage:** `erk exec plan-save-to-issue`

**Options:**

| Flag                | Type    | Required | Default | Description                                                               |
| ------------------- | ------- | -------- | ------- | ------------------------------------------------------------------------- |
| `--format`          | CHOICE  | No       | 'json'  | Output format: json (default) or display (formatted text)                 |
| `--plan-file`       | PATH    | No       | -       | Path to specific plan file (highest priority)                             |
| `--session-id`      | TEXT    | No       | -       | Session ID for scoped plan lookup (uses slug from session logs)           |
| `--objective-issue` | INTEGER | No       | -       | Link plan to parent objective issue number                                |
| `--plan-type`       | CHOICE  | No       | -       | Plan type: standard (default) or learn (for documentation learning plans) |

### plan-update-issue

Update an existing GitHub issue's plan comment with new content.

**Usage:** `erk exec plan-update-issue`

**Options:**

| Flag             | Type    | Required | Default        | Description                                               |
| ---------------- | ------- | -------- | -------------- | --------------------------------------------------------- |
| `--issue-number` | INTEGER | Yes      | Sentinel.UNSET | GitHub issue number to update                             |
| `--format`       | CHOICE  | No       | 'json'         | Output format: json (default) or display (formatted text) |
| `--plan-path`    | PATH    | No       | Sentinel.UNSET | Direct path to plan file (overrides session lookup)       |
| `--session-id`   | TEXT    | No       | Sentinel.UNSET | Session ID to find plan file in scratch storage           |

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

| Flag             | Type    | Required | Default        | Description                     |
| ---------------- | ------- | -------- | -------------- | ------------------------------- |
| `--issue-number` | INTEGER | Yes      | Sentinel.UNSET | GitHub issue number             |
| `--branch-name`  | TEXT    | Yes      | Sentinel.UNSET | Git branch name                 |
| `--pr-number`    | INTEGER | Yes      | Sentinel.UNSET | Pull request number             |
| `--run-id`       | TEXT    | Yes      | Sentinel.UNSET | GitHub Actions workflow run ID  |
| `--run-url`      | TEXT    | Yes      | Sentinel.UNSET | Full URL to workflow run        |
| `--repository`   | TEXT    | Yes      | Sentinel.UNSET | Repository in owner/repo format |

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

### quick-submit

Quick commit all changes and submit.

**Usage:** `erk exec quick-submit`

### rebase-with-conflict-resolution

Rebase onto target branch and resolve conflicts with Claude.

**Usage:** `erk exec rebase-with-conflict-resolution`

**Options:**

| Flag              | Type    | Required | Default             | Description                                                    |
| ----------------- | ------- | -------- | ------------------- | -------------------------------------------------------------- |
| `--target-branch` | TEXT    | Yes      | Sentinel.UNSET      | Branch to rebase onto (trunk or parent branch for stacked PRs) |
| `--branch-name`   | TEXT    | Yes      | Sentinel.UNSET      | Current branch name for force push                             |
| `--model`         | TEXT    | No       | 'claude-sonnet-4-5' | Claude model to use for conflict resolution                    |
| `--max-attempts`  | INTEGER | No       | 5                   | Maximum number of conflict resolution attempts                 |

### reply-to-discussion-comment

Reply to a PR discussion comment with quote and action summary.

**Usage:** `erk exec reply-to-discussion-comment`

**Options:**

| Flag           | Type    | Required | Default        | Description                                 |
| -------------- | ------- | -------- | -------------- | ------------------------------------------- |
| `--comment-id` | INTEGER | Yes      | Sentinel.UNSET | Numeric comment ID to reply to              |
| `--pr`         | INTEGER | No       | -              | PR number (defaults to current branch's PR) |
| `--reply`      | TEXT    | Yes      | Sentinel.UNSET | Action summary text (what was done)         |

### resolve-review-thread

Resolve a PR review thread.

**Usage:** `erk exec resolve-review-thread`

**Options:**

| Flag          | Type | Required | Default        | Description                              |
| ------------- | ---- | -------- | -------------- | ---------------------------------------- |
| `--thread-id` | TEXT | Yes      | Sentinel.UNSET | GraphQL node ID of the thread to resolve |
| `--comment`   | TEXT | No       | -              | Optional comment to add before resolving |

### run-review

Run a code review using Claude.

**Usage:** `erk exec run-review`

**Options:**

| Flag            | Type    | Required | Default           | Description                                                        |
| --------------- | ------- | -------- | ----------------- | ------------------------------------------------------------------ |
| `--name`        | TEXT    | Yes      | Sentinel.UNSET    | Review filename (without .md)                                      |
| `--pr-number`   | INTEGER | No       | Sentinel.UNSET    | PR number to review (PR mode)                                      |
| `--local`       | FLAG    | No       | -                 | Review local changes (local mode)                                  |
| `--base`        | TEXT    | No       | Sentinel.UNSET    | Base branch for local mode (default: auto-detect)                  |
| `--reviews-dir` | TEXT    | No       | '.claude/reviews' | Directory containing review definitions (default: .claude/reviews) |
| `--dry-run`     | FLAG    | No       | -                 | Print assembled prompt without running Claude                      |

### session-id-injector-hook

Inject session ID into conversation context when relevant.

**Usage:** `erk exec session-id-injector-hook`

### setup-impl-from-issue

Set up .impl/ folder from GitHub issue in current worktree.

**Usage:** `erk exec setup-impl-from-issue` <issue_number>

**Arguments:**

| Name           | Required | Description |
| -------------- | -------- | ----------- |
| `ISSUE_NUMBER` | Yes      | -           |

**Options:**

| Flag           | Type | Required | Default | Description                                                             |
| -------------- | ---- | -------- | ------- | ----------------------------------------------------------------------- |
| `--session-id` | TEXT | No       | -       | Claude session ID for marker creation                                   |
| `--no-impl`    | FLAG | No       | -       | Skip .impl/ folder creation (for local execution without file overhead) |

### slot-objective

Get the last objective issue for the current slot.

**Usage:** `erk exec slot-objective`

### track-learn-evaluation

Track learn evaluation completion on a plan issue.

**Usage:** `erk exec track-learn-evaluation` [issue]

**Arguments:**

| Name    | Required | Description |
| ------- | -------- | ----------- |
| `ISSUE` | No       | -           |

**Options:**

| Flag           | Type | Required | Default | Description                                                  |
| -------------- | ---- | -------- | ------- | ------------------------------------------------------------ |
| `--session-id` | TEXT | No       | -       | Session ID for tracking (passed from Claude session context) |

### tripwires-reminder-hook

Output tripwires reminder for UserPromptSubmit hook.

**Usage:** `erk exec tripwires-reminder-hook`

### update-dispatch-info

Update dispatch info in GitHub issue plan-header metadata.

**Usage:** `erk exec update-dispatch-info` <issue_number> <run_id> <node_id> <dispatched_at>

**Arguments:**

| Name            | Required | Description |
| --------------- | -------- | ----------- |
| `ISSUE_NUMBER`  | Yes      | -           |
| `RUN_ID`        | Yes      | -           |
| `NODE_ID`       | Yes      | -           |
| `DISPATCHED_AT` | Yes      | -           |

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

### user-prompt-hook

UserPromptSubmit hook for session persistence and coding reminders.

**Usage:** `erk exec user-prompt-hook`

### validate-claude-credentials

Validate Claude credentials for CI workflows.

**Usage:** `erk exec validate-claude-credentials`

### validate-plan-content

Validate plan content from stdin.

**Usage:** `erk exec validate-plan-content`

### wrap-plan-in-metadata-block

Return plan content for issue body.

**Usage:** `erk exec wrap-plan-in-metadata-block`
