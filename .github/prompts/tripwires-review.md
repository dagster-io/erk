REPO: {{ github.repository }}
PR NUMBER: {{ github.event.pull_request.number }}

## Task

Review code changes for violations of erk tripwire patterns.

## Step 1: Load Tripwire Index

Read `docs/learned/tripwires.md`. This is the **definitive source** of all tripwires.

Each tripwire follows this format:

```
**CRITICAL: Before [trigger action]** → Read [linked doc] first. [summary]
```

Parse EVERY tripwire entry to extract:

- **Trigger**: The action pattern (e.g., "calling os.chdir()", "passing dry_run boolean flags")
- **Linked doc**: The documentation file to read if triggered
- **Summary**: Brief description of what the rule enforces

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

## Step 4: Match Tripwires to Diff

For EACH tripwire parsed in Step 1, scan the diff for code matching its trigger pattern.

**Pattern Matching Guidelines:**

| Trigger Pattern                                             | What to Search For                             |
| ----------------------------------------------------------- | ---------------------------------------------- |
| "passing dry_run boolean flags"                             | `dry_run: bool` in function signatures         |
| "calling os.chdir()"                                        | `os.chdir(` in code                            |
| "importing time module or calling time.sleep()"             | `import time` or `time.sleep(`                 |
| "implementing CLI flags that affect post-mutation behavior" | New CLI flags with `--` prefix                 |
| "editing docs/agent/index.md or docs/agent/tripwires.md"    | Changes to those files                         |
| "comparing worktree path to repo_root"                      | `path == repo_root` or similar comparisons     |
| "adding a new method to Git/GitHub/Graphite ABC"            | New method definitions in gateway abc.py files |
| "passing variables to gh api graphql as JSON blob"          | `gh api graphql` with `-f variables=`          |
| "passing array or object variables to gh api graphql"       | `-F key=[` or `-F key={` patterns              |
| "checking if get_pr_for_branch() returned a PR"             | `get_pr_for_branch` + `is not None`            |
| "creating Protocol with bare attributes"                    | Protocol class with non-@property attributes   |
| "using bare subprocess.run with check=True"                 | `subprocess.run` without wrapper               |
| "adding a command with --script flag"                       | New `--script` flag definitions                |
| "writing `__all__` to a Python file"                        | `__all__ =` in Python files                    |
| "running gt sync or gt repo sync"                           | `gt sync` or `gt repo sync` commands           |
| "writing to /tmp/"                                          | `/tmp/` in path strings for AI workflows       |
| "creating temp files for AI workflows"                      | temp file creation patterns                    |
| "working with session-specific data"                        | session data access patterns                   |

This is DYNAMIC - new tripwires added to tripwires.md are automatically checked.

Track which tripwires matched the diff (triggered tripwires).

## Step 5: Load Docs for Matched Tripwires (Lazy Loading)

For EACH tripwire that matched in Step 4:

1. Read the linked documentation file
2. Extract ALL rules from that doc
3. Verify the diff follows EVERY rule in the doc

**Do NOT skip to pattern matching** - read the full doc to understand context and all requirements.

## Step 6: Post Inline Comments for Violations

**IMPORTANT: Post an inline comment for EACH violation found.**

```
erk exec post-pr-inline-comment \
  --pr-number {{ github.event.pull_request.number }} \
  --path "path/to/file" \
  --line LINE_NUMBER \
  --body "**Tripwire**: [pattern detected] - [why it's a problem] - [fix suggestion]"
```

## Step 7: Post Summary Comment

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

### Tripwires Triggered
- [tripwire name] → loaded [doc path]
- [tripwire name] → loaded [doc path]

(List only tripwires that matched the diff)

### Patterns Checked
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

(Use ✅ when compliant, ❌ when violation found. Only list patterns relevant to the diff.)

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
- "Triggered 3 tripwires, loaded docs, found 1 violation"

Keep the last 10 log entries maximum.
