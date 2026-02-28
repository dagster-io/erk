# Print learn plan link after `erk land`

## Context

When `erk land` successfully creates a learn plan, the success message only shows the plan number:

```
✓ Created learn plan #8465 for plan #8463
```

The user requested that a clickable link to the learn plan PR be printed so they can easily navigate to it. The `CreatePlanDraftPRResult` already has a `plan_url` field that is populated on success, but it's not used in the output message.

## Changes

### 1. Modify success message in `src/erk/cli/commands/land_learn.py`

**Lines 321-325** — Update the success branch of `_create_learn_pr_impl` to include the URL.

Current code:
```python
if result.success:
    user_output(
        click.style("✓", fg="green")
        + f" Created learn plan #{result.plan_number} for plan #{plan_id}"
    )
```

New code:
```python
if result.success:
    user_output(
        click.style("✓", fg="green")
        + f" Created learn plan #{result.plan_number} for plan #{plan_id}"
    )
    if result.plan_url:
        user_output(f"  {result.plan_url}")
```

This prints the URL on a separate, indented line below the success message, matching the indented style used elsewhere in the land pipeline output. The URL is printed with 2-space indent for visual hierarchy under the `✓` line.

**Expected output:**
```
✓ Created learn plan #8465 for plan #8463
  https://github.com/dagster-io/erk/pull/8465
```

### 2. Update test in `tests/unit/cli/commands/land/test_land_learn.py`

**`test_creates_pr_and_shows_success`** (lines 249-287) — Add an assertion that the URL appears in the output.

Add after the existing assertions (after line 287):
```python
assert "https://github.com/" in captured.err
```

This verifies the URL is printed. The FakeGitHub generates URLs in the format `https://github.com/{owner}/{repo}/pull/{number}`, so this assertion is reliable.

## Files NOT Changing

- `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` — `plan_url` already populated correctly
- `packages/erk-shared/src/erk_shared/gateway/github/fake.py` — FakeGitHub already generates proper PR URLs
- No new files needed

## Implementation Details

- The `result.plan_url` field is a `str | None`. It is `None` only on failure, and we're inside the `result.success` branch, so the `if result.plan_url:` guard is defensive but consistent with the type.
- The 2-space indent for the URL line matches the indentation style used by session discovery lines in the same output (e.g., `  📋 Discovered 1 session(s)...`).
- The URL is printed as plain text — terminals with URL detection will make it clickable automatically.

## Verification

1. Run tests: `pytest tests/unit/cli/commands/land/test_land_learn.py -x`
2. Run type checker: `ty check src/erk/cli/commands/land_learn.py`
3. Run linter: `ruff check src/erk/cli/commands/land_learn.py`