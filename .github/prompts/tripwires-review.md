REPO: {{ github.repository }}
PR NUMBER: {{ github.event.pull_request.number }}

## Task

Review code changes for violations of erk tripwire patterns.

## Step 1: Load the Tripwires Documentation

Read `docs/learned/tripwires.md` for the complete tripwire list.

## Step 2: Get Existing Review Comment

Fetch the existing review comment to preserve the activity log:

```
gh pr view {{ github.event.pull_request.number }} --json comments --jq '.comments[] | select(.body | contains("<!-- tripwires-review -->")) | .body'
```

If a comment exists, extract the Activity Log section (everything after `### Activity Log`). You will append to this log.

## Step 3: Get the Diff

```
gh pr diff {{ github.event.pull_request.number }} --name-only
gh pr diff {{ github.event.pull_request.number }}
```

## Step 4: Analyze Code for Tripwire Violations

### High-Confidence Patterns (flag directly)

These patterns are almost always violations:

| Pattern                           | Violation                      | Fix                                                                 |
| --------------------------------- | ------------------------------ | ------------------------------------------------------------------- |
| `import time` or `time.sleep(`    | Direct time module usage       | Use `context.time.sleep()`                                          |
| `subprocess.run` without wrapper  | Bare subprocess                | Use `run_subprocess_with_context()` or `run_with_error_reporting()` |
| `__all__ =`                       | Re-export module               | Import directly from source                                         |
| `/tmp/` in paths for AI workflows | Wrong scratch location         | Use `.erk/scratch/<session-id>/`                                    |
| `gt sync` or `gt repo sync`       | Auto-running dangerous command | Never auto-run; require explicit user action                        |

### Context-Required Patterns (read surrounding code)

These need surrounding code context to determine if they're violations:

| Pattern                             | Check                               | Violation Criteria                                                     |
| ----------------------------------- | ----------------------------------- | ---------------------------------------------------------------------- |
| `dry_run: bool` parameter           | Is this at CLI boundary?            | Violation if in business logic; OK at CLI entry point                  |
| `os.chdir(`                         | Does `regenerate_context()` follow? | Violation if no context regeneration after chdir                       |
| New method in gateway `abc.py`      | Are all 5 implementations present?  | Violation if missing from real.py, fake.py, dry_run.py, or printing.py |
| `get_pr_for_branch` + `is not None` | How is return value checked?        | Should use `isinstance(pr, PRNotFound)`                                |
| Protocol with bare attributes       | Used with frozen dataclasses?       | Should use `@property` decorators                                      |
| `path == repo_root` for worktree    | Detecting root worktree?            | Use `WorktreeInfo.is_root` instead                                     |

## Step 5: Post Inline Comments

**IMPORTANT: Post an inline comment for EACH violation found.**

```
erk exec post-pr-inline-comment \
  --pr-number {{ github.event.pull_request.number }} \
  --path "path/to/file" \
  --line LINE_NUMBER \
  --body "**Tripwire**: [pattern detected] - [why it's a problem] - [fix suggestion]"
```

## Step 6: Post Summary Comment

**IMPORTANT: All timestamps MUST be in Pacific Time (PT), NOT UTC.**

Get the current Pacific time timestamp:

```
TZ='America/Los_Angeles' date '+%Y-%m-%d %H:%M:%S'
```

Post/update the summary comment:

```
erk exec post-or-update-pr-summary \
  --pr-number {{ github.event.pull_request.number }} \
  --marker "<!-- tripwires-review -->" \
  --body "SUMMARY_TEXT"
```

Summary format (preserve existing Activity Log entries and prepend new entry):

```
<!-- tripwires-review -->

## ✅ Tripwires Review   (use ✅ if 0 violations, ❌ if 1+ violations)

**Last updated:** YYYY-MM-DD HH:MM:SS PT

Found X violations across Y files. Inline comments posted for each.

### Patterns Checked
✅ import time / time.sleep() - None found
✅ Bare subprocess.run - None found
❌ __all__ exports - Found in src/foo.py:12
✅ /tmp/ for AI workflows - None found

(Use ✅ when pattern NOT found, ❌ when pattern found. Only list patterns relevant to the diff.)

### Violations Summary
- `file.py:123`: [brief description]

### Files Reviewed
- `file.py`: N violations
- `file.sh`: N violations

---

### Activity Log
- **YYYY-MM-DD HH:MM:SS PT**: [Brief description of this review's findings]
- [Previous log entries preserved here...]
```

Activity log entry examples:

- "Found 2 violations (bare subprocess.run in x.py, /tmp/ usage in y.py)"
- "All violations resolved"
- "No tripwire violations detected"

Keep the last 10 log entries maximum.
