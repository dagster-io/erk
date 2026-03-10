---
title: Review Activity Log Fetch (Exec Script)
read_when:
  - "fetching review activity logs"
  - "working with erk exec get-review-activity-log"
  - "push down review activity log fetch"
tripwires: []
---

# Review Activity Log Fetch (Exec Script)

## Command

```bash
erk exec get-review-activity-log --pr-number <N> --marker <marker>
```

## Purpose

Fetches the activity log section from an existing review summary comment on a PR. This is a "push down" pattern — moving computation from LLM prompts into a tested CLI command.

## Options

- `--pr-number` (required): PR number to search
- `--marker` (required): HTML marker identifying the review comment (e.g., `<!-- audit-pr-docs -->`)

## Output

JSON with:

- `success`: boolean (always true)
- `found`: boolean (whether activity log section was found)
- `activity_log`: string (the activity log text, or empty)

## Examples

```bash
$ erk exec get-review-activity-log --pr-number 123 --marker "<!-- audit-pr-docs -->"
{"success": true, "found": true, "activity_log": "- [2024-01-01] ..."}

$ erk exec get-review-activity-log --pr-number 123 --marker "<!-- no-such-marker -->"
{"success": true, "found": false, "activity_log": ""}
```

## Implementation

- Location: `src/erk/cli/commands/exec/scripts/get_review_activity_log.py`
- Exit code always 0 (supports `|| true` pattern)
- Searches PR comments for the marker, then extracts text after `### Activity Log` heading
