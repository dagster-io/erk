---
description: Quick commit all changes and submit with Graphite
---

# Quick Submit

Quickly commit all changes with a generic "update" message and submit to Graphite.

## Usage

```bash
/quick-submit
```

## What This Command Does

1. Stages all uncommitted changes
2. Creates a commit with a generic "update" message (if there are changes)
3. Submits the branch via Graphite (or git push if Graphite is not configured)
4. Returns the PR URL on success

This is a shortcut for rapid iteration when you don't need a detailed commit message.

## Implementation Steps

### Step 1: Stage and Commit Changes

Run the following command from the repository root:

```bash
erk exec quick-submit
```

This command will:
- Stage all changes in the working directory
- Commit them with the message "update" if there are staged changes
- Return a JSON response with the result

### Step 2: Parse the Response

The command outputs JSON with the following structure:

```json
{
  "success": true,
  "committed": true,
  "message": "Changes submitted successfully",
  "pr_url": "https://github.com/owner/repo/pull/123"
}
```

Or on error:

```json
{
  "success": false,
  "error_type": "stage-failed|commit-failed|submit-failed",
  "message": "Error description"
}
```

**Decision logic:**
- If `success` is `true`: Report the success message and PR URL to the user
- If `success` is `false`: Display the error message and ask the user to fix the issue

### Step 3: Report Results

Display the result based on the response:

**On success:**
```
Changes submitted successfully
View PR: {pr_url}
```

**On failure:**
```
Error: {error_message}
```

If the error is `stage-failed` or `commit-failed`, suggest the user check their git state.
If the error is `submit-failed`, suggest the user try `/erk:git-pr-push` as an alternative.

## Error Handling

- **No changes**: The command will still submit if there are already committed changes on the branch. No error is raised if there are no staged changes.
- **Graphite not initialized**: Falls back to git push if the repository is not Graphite-managed.
- **Submit fails**: Display the error and suggest `/erk:git-pr-push` as an alternative.

## Notes

- This is a shortcut for rapid iteration
- Uses generic "update" commit message
- For detailed commit messages, use `/erk:pr-submit` instead
- For git-only workflows (no Graphite), use `/erk:git-pr-push`
