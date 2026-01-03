REPO: {{ github.repository }}
PR NUMBER: {{ github.event.pull_request.number }}

## Task

Review Python code changes for adherence to dignified-python standards.

## Step 1: Load the Dignified Python Standards

Read these skill files from the repository:

1. .claude/skills/dignified-python/SKILL.md (routing and version detection)
2. .claude/skills/dignified-python/dignified-python-core.md (LBYL, exceptions, paths, imports, DI, performance)
3. .claude/skills/dignified-python/cli-patterns.md (Click best practices)
4. .claude/skills/dignified-python/subprocess.md (subprocess handling)

## Step 2: Get Existing Review Comment

Fetch the existing review comment to preserve the activity log:

```
gh pr view {{ github.event.pull_request.number }} --json comments --jq '.comments[] | select(.body | contains("<!-- dignified-python-review -->")) | .body'
```

If a comment exists, extract the Activity Log section (everything after `### Activity Log`). You will append to this log.

## Step 3: Get the Python Diff

```
gh pr diff {{ github.event.pull_request.number }} --name-only | grep '\.py$'
gh pr diff {{ github.event.pull_request.number }}
```

## Step 3b: Identify Changed Lines

For each Python file, determine which lines were actually modified (not just context):

- Lines starting with `+` in the diff are additions/modifications
- Lines starting with ` ` (space) are unchanged context

For the `__all__` / re-export rule specifically:

- If `__all__` appears on a `+` line → Flag as violation (actively being modified)
- If `__all__` only appears in context lines → Skip (pre-existing, not being modified)

This allows file moves/refactors to pass while catching active modifications.

## Step 4: Analyze Code

Check each Python file against dignified-python rules:

- LBYL over EAFP (no try/except for control flow)
- Exception handling (no silent swallowing, log at boundaries)
- Path operations (exists before resolve)
- Import organization (module-level, absolute, no re-exports)
- No default parameter values
- Dependency injection with ABC
- Frozen dataclasses

**For `__all__` / re-exports:**

- Only flag if `__all__` appears in the **changed lines** (Step 3b analysis)
- Skip if `__all__` is pre-existing and unchanged in this PR

## Step 5: Post Inline Comments

**IMPORTANT: You MUST post an inline comment for EACH violation found.**

```
erk exec post-pr-inline-comment \
  --pr-number {{ github.event.pull_request.number }} \
  --path "path/to/file.py" \
  --line LINE_NUMBER \
  --body "**Dignified Python**: [rule violated] - [fix suggestion]"
```

## Step 6: Post Summary Comment

**IMPORTANT: All timestamps MUST be in Pacific Time (PT), NOT UTC.**

Get the current Pacific time timestamp by running this command:

```
TZ='America/Los_Angeles' date '+%Y-%m-%d %H:%M:%S'
```

Use this timestamp (with " PT" suffix) for both "Last updated" and Activity Log entries.

Post/update the summary comment:

```
erk exec post-or-update-pr-summary \
  --pr-number {{ github.event.pull_request.number }} \
  --marker "<!-- dignified-python-review -->" \
  --body "SUMMARY_TEXT"
```

Summary format (preserve existing Activity Log entries and prepend new entry):

```
<!-- dignified-python-review -->

## ✅ Dignified Python Review   (use ✅ if 0 issues, ❌ if 1+ issues)

**Last updated:** YYYY-MM-DD HH:MM:SS PT

Found X issues across Y files. Inline comments posted for each.

### Files Reviewed
- `file.py`: N issues

---

### Activity Log
- **YYYY-MM-DD HH:MM:SS PT**: [Brief description of this review's findings]
- [Previous log entries preserved here...]
```

Activity log entry examples:

- "Found 2 issues (LBYL violation in x.py, inline import in y.py)"
- "All issues resolved"
- "False positive dismissed: CLI error boundary pattern"

Keep the last 10 log entries maximum.
