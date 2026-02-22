# Plan: Hide Review Bot Comment Details in `<details>` Block

## Context

Review bot summary comments (posted to PRs by automated CI reviews) currently render all content inline. This makes PR comment threads noisy and hard to scan — five review bots can create substantial wall-of-text comments. Wrapping the bulk of each comment in a collapsed `<details>` HTML block keeps the key signal (pass/fail, violation count) visible while collapsing verbose details (patterns checked, violations list, files reviewed, activity log) by default.

## What Changes

One file: `src/erk/review/prompt_assembly.py`

Modify the summary format inside `REVIEW_PROMPT_TEMPLATE` (lines 103–130) so Claude is instructed to wrap the detailed sections in a `<details>` block.

## New Summary Format

The visible portion (outside `<details>`) should remain:

- The HTML marker comment
- The `## ✅/❌ {review_name}` header
- `**Last updated:**` line
- One-liner count: "Found X violations across Y files."

Everything below that goes inside `<details><summary>Details</summary>`:

- `### Patterns Checked`
- `### Violations Summary`
- `### Files Reviewed`
- `---`
- `### Activity Log`

Resulting format:

```
{marker}

## ✅ {review_name}   (use ✅ if 0 violations, ❌ if 1+ violations)

**Last updated:** YYYY-MM-DD HH:MM:SS PT

Found X violations across Y files. Inline comments posted for each.

<details>
<summary>Details</summary>

### Patterns Checked
✅ [pattern] - None found
❌ [pattern] - Found in src/foo.py:12

(Use ✅ when compliant, ❌ when violation found.)

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
