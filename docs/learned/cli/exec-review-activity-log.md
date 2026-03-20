---
title: Exec get-review-activity-log
read_when:
  - "working with review activity logs on PRs"
  - "fetching existing review summary comments"
  - "building workflows that read PR comment sections"
tripwires:
  - action: "expecting get-review-activity-log to fail on missing marker"
    warning: "The command always exits 0, even when the marker is not found. Check the 'found' field in the JSON response to determine whether the comment was located."
---

# Exec get-review-activity-log

`erk exec get-review-activity-log` fetches the `### Activity Log` section from an existing PR review summary comment identified by an HTML marker.

## Source

`src/erk/cli/commands/exec/scripts/get_review_activity_log.py`

## Purpose

Review summary commands (e.g., `audit-pr-docs`) post structured PR comments containing an HTML marker and an `### Activity Log` section. This exec script reads that activity log back, enabling workflows to carry forward state across multiple review runs.

## Usage

```bash
erk exec get-review-activity-log \
    --pr-number 123 \
    --marker "<!-- audit-pr-docs -->"
```

## Options

| Option        | Required | Description                                       |
| ------------- | -------- | ------------------------------------------------- |
| `--pr-number` | Yes      | PR number to search for comments                  |
| `--marker`    | Yes      | HTML marker string identifying the review comment |

## Output

Always emits JSON to stdout (pretty-printed with `indent=2`):

**When found:**

```json
{
  "success": true,
  "found": true,
  "activity_log": "- [2024-01-01] Review passed\n- [2024-01-02] ..."
}
```

**When not found:**

```json
{
  "success": true,
  "found": false,
  "activity_log": ""
}
```

## Exit Codes

Always exits 0 — designed to support the `|| true` pattern in shell scripts and CI workflows.

## Extraction Logic

The `_extract_activity_log()` helper searches for the literal string `### Activity Log` in the comment body. Everything after that heading (stripped of leading whitespace) is returned as the activity log. If the heading is absent, an empty string is returned.

## Integration Pattern

This command is used in review workflows that need to preserve history between runs:

```bash
# Fetch existing activity log before generating new review
LOG=$(erk exec get-review-activity-log \
    --pr-number "$PR_NUMBER" \
    --marker "<!-- audit-pr-docs -->")

FOUND=$(echo "$LOG" | python3 -c "import json,sys; print(json.load(sys.stdin)['found'])")
EXISTING_LOG=$(echo "$LOG" | python3 -c "import json,sys; print(json.load(sys.stdin)['activity_log'])")
```

## Related Documentation

- [Exec Script Testing Patterns](../testing/exec-script-testing.md) — Testing exec scripts
- [JSON/Dataclass Utilities](../architecture/json-dataclass-utilities.md) — JSON output conventions
