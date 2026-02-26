# Plan: Improve success output for erk CLI commands

## Context

`erk pr submit -f` completed but produced insufficient output — just clickable URLs with no summary of what happened. An audit of all 61 user-facing CLI commands found that 59 have good output. Two need improvement:

1. **`pr/submit_cmd.py`** — Has output (URLs) but lacks a meaningful summary
2. **`pr/replan_cmd.py`** — No pre-launch message before exec'ing into Claude

Exec scripts and hooks are out of scope (agent-facing JSON APIs and system-reminder channels respectively).

## Changes

### 1. `src/erk/cli/commands/pr/submit_cmd.py` (lines 159-169)

Replace the minimal URL-only success output with a structured summary. All data is already available on the `SubmitState` result object.

**Current output:**
```
✅ <clickable PR URL>
📊 <clickable Graphite URL>
```

**New output:**
```
✅ PR submitted

  Action:     Created PR #123          (or "Updated PR #123")
  Branch:     my-feature → main
  Title:      Fix the login bug
  PR:         https://github.com/...
  Graphite:   https://app.graphite.dev/...   (if available)
  Plan:       #456                            (if linked)
```

Implementation:
- Add a `_print_summary(result: SubmitState)` helper in `submit_cmd.py`
- Use `click.echo` + `click.style(..., dim=True)` for field labels (matches `pr/view_cmd.py` pattern)
- Preserve clickable hyperlink escape sequences for PR and Graphite URLs
- Conditionally show fields: Title (only if `result.title`), Graphite (only if `result.graphite_url`), Plan (only if `result.plan_id`)
- Use `result.was_created` → "Created" vs "Updated"
- Use `result.branch_name` and `result.base_branch` (fall back to `result.parent_branch`) for branch display

### 2. `src/erk/cli/commands/pr/replan_cmd.py` (line 41)

Add a pre-launch message before `launch_interactive` replaces the process:

```python
click.echo(f"Launching Claude to replan: {', '.join(issue_refs)}")
```

## Verification

1. Run `erk pr submit` on a test branch — verify summary appears with all fields
2. Run `erk pr submit --skip-description` — verify Title line is omitted
3. Run `erk pr replan 123` — verify pre-launch message appears before Claude takes over
4. Run existing tests to confirm no regressions
