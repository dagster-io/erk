---
description:
  Create git commit and submit current branch with Graphite (squashes commits
  and rebases stack)
argument-hint: <description>
---

# Submit PR

Automatically create a git commit with a helpful summary message and submit the current branch as a pull request.

**Note:** This command squashes commits and rebases the stack. If you prefer a simpler workflow that preserves your commit history, use `/erk:git-pr-push` instead.

## Usage

```bash
# Invoke the command (description argument is optional but recommended)
/erk:pr-submit "Add user authentication feature"

# Without argument (will analyze changes automatically)
/erk:pr-submit
```

## Implementation

This command uses a three-step flow to avoid nested Claude subprocess calls:

1. **Push + create PR** (no AI) via `erk exec push-and-create-pr`
2. **Gather context** via `erk exec get-pr-context` (returns JSON)
3. **Generate title + body** natively (you are the agent — no subprocess)
4. **Apply description** via `erk exec set-pr-description`

### Step 1: Push and Create PR

```bash
erk exec push-and-create-pr
```

This pushes the branch, creates/finds the PR via Graphite, but skips AI description generation. The PR is created with a placeholder title. Outputs JSON with `pr.number`, `pr.url`, and `pr.was_created`.

If this fails (exit code 1), display the error from the JSON output and stop.

Check `pr.was_created` in the JSON output:

- `was_created: true` → Report "Created PR #N". This is a **new submission** — use "Create" language in subsequent steps.
- `was_created: false` → Report "Pushed changes (PR #N already exists)". This is a **resubmission** — use "Update" language in subsequent steps and skip Step 5.

### Step 2: Get PR Context

```bash
erk exec get-pr-context
```

This outputs JSON to stdout with:

- `branch.current` and `branch.parent`
- `pr.number` and `pr.url`
- `diff_file` path to the diff content
- `commit_messages` array
- `plan_context` (nullable) with `plan_id`, `plan_content`, `objective_summary`

Parse the JSON output. If this fails, display the error and stop.

### Step 3: Generate Title and Body / Update Title and Body

Report step as "Generate Title and Body" for new submissions, "Update Title and Body" for resubmissions.

1. Read the diff file from the `diff_file` path in the JSON
2. Load the `erk-diff-analysis` skill for the commit message prompt format
3. Consider the `commit_messages` and `plan_context` from the JSON
4. If the user provided a `` argument, use it to guide the description
5. Generate a PR title (first line) and body following the diff analysis format

### Step 4: Apply Description / Update Description

Report step as "Apply Description" for new submissions, "Update Description" for resubmissions.

Write the generated body to a temp file, then apply:

```bash
erk exec set-pr-description --title "<generated title>" --body-file "<temp file path>"
```

If this fails, display the error and stop.

### Step 5: Link PR to Objective (if applicable)

**Skip this step entirely for resubmissions** (`was_created: false`) — the PR is already linked.

For new submissions: if `ref.json` exists in `.erk/impl-context/<branch>/` and contains `objective_id`:

```bash
erk exec objective-link-pr --pr-number <pr_number>
```

Where `<pr_number>` is the PR number from Step 1. If this fails, warn but continue -- PR creation succeeded.

### Step 6: Report Results

Report:

- PR URL (from step 2 JSON)
- For new submissions: "PR created successfully"
- For resubmissions: "PR updated successfully"

### Refresh Status Line

After reporting results, output the following to trigger a status line refresh:

```
🔄 Status line refreshed
```

## Error Handling

If any step fails, display the error and stop. Do NOT attempt to auto-resolve errors. Let the user fix issues and re-run.

Common errors:

- Authentication issues (Graphite/GitHub)
- Merge conflicts
- No commits to submit
- No PR found for branch
