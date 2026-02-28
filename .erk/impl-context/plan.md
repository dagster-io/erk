# Plan: Add visible AI-generated summary to plan PRs

## Context

When plan PRs are created via `/erk:plan-save`, the entire plan content is hidden inside a `<details><summary>original-plan</summary>` tag. This means you see nothing about the plan without clicking to expand it. We want a visible AI-generated summary above the collapsed plan so you can understand the plan at a glance.

## Target PR body (Stage 1)

```
This plan adds session preprocessing stats to the `erk land` output,
showing user turns, duration, and JSONL-to-XML compression ratios
alongside each discovered session.

<details>
<summary>original-plan</summary>

[full plan content]

</details>

[metadata block]
---
[checkout footer]
```

## Approach

Generate the summary at the **skill level** — Claude already has the plan in context during `/erk:plan-save`, so no extra API call is needed. Pass it as a `--summary` CLI option to `erk exec plan-save`, which threads it through to the PR body construction.

## Changes

### 1. Update `build_plan_stage_body()` to accept optional summary

**`packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py`**

Add `summary: str | None` parameter. When provided, prepend it before the `<details>` section:

```python
def build_plan_stage_body(metadata_body: str, plan_content: str, *, summary: str | None) -> str:
    plan_section = DETAILS_OPEN + plan_content + DETAILS_CLOSE
    if summary is not None:
        plan_section = summary + "\n\n" + plan_section
    return plan_section + "\n\n" + metadata_body
```

Update the module docstring's Stage 1 body format to show the summary placement.

### 2. Update `PlannedPRBackend.create_plan()` to accept and forward summary

**`packages/erk-shared/src/erk_shared/plan_store/planned_pr.py`**

Add `summary: str | None` parameter to `create_plan()`. Pass it to `build_plan_stage_body()`:

```python
pr_body = build_plan_stage_body(metadata_body, content, summary=summary)
```

### 3. Add `--summary` CLI option to `plan_save.py`

**`src/erk/cli/commands/exec/scripts/plan_save.py`**

- Add `--summary` option to the `plan_save` click command
- Thread through `_save_plan_via_planned_pr()` → `_save_as_planned_pr()` → `create_plan()`

### 4. Update `create_plan_draft_pr()` shared utility

**`packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py`**

Add optional `summary` parameter, thread to `backend.create_plan()`. Default to `None` so existing callers (CI workflows, session extraction) don't need changes.

### 5. Add summary generation step to plan-save skill

**`.claude/commands/erk/plan-save.md`**

Add **Step 1.75: Generate Plan Summary** between the branch slug step (1.5) and the save command step (2):

```
### Step 1.75: Generate Plan Summary

Write a concise 2-3 sentence summary of the plan. This summary will be visible
at the top of the PR description (above the collapsed full plan).

Guidelines:
- Focus on WHAT the plan does and WHY
- Do not repeat the title
- Plain text, no markdown headers or formatting
- Avoid special shell characters (backticks, dollar signs)
- Store as PLAN_SUMMARY
```

Update **Step 2** to include `--summary "${PLAN_SUMMARY}"` in the command.

### 6. Update tests

**`tests/unit/plan_store/test_planned_pr_lifecycle.py`**

- Update `test_build_plan_stage_body` and `test_build_plan_stage_body_structure` to pass `summary=None` (existing behavior preserved)
- Add `test_build_plan_stage_body_with_summary` — verify summary appears before details section
- Add `test_build_plan_stage_body_summary_structure` — verify ordering: summary < details < plan < close < metadata
- Update `test_build_and_extract_roundtrip` to pass `summary=None` and add a roundtrip with summary

## Files to modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/planned_pr_lifecycle.py` | Add `summary` param to `build_plan_stage_body()`, update docstring |
| `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` | Add `summary` param to `create_plan()` |
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Add `--summary` CLI option, thread through |
| `packages/erk-shared/src/erk_shared/plan_store/create_plan_draft_pr.py` | Add optional `summary` param |
| `.claude/commands/erk/plan-save.md` | Add Step 1.75, update Step 2 command |
| `tests/unit/plan_store/test_planned_pr_lifecycle.py` | Update existing tests, add summary tests |

## Key functions to reuse

- `build_plan_stage_body()` — `planned_pr_lifecycle.py:95` (modify in-place)
- `extract_plan_content()` — `planned_pr_lifecycle.py:141` (no changes needed — already looks for details tags, summary is outside them)
- `build_original_plan_section()` — `planned_pr_lifecycle.py:111` (no changes needed — Stage 2 replaces the summary with AI commit message body)

## Verification

1. Run `pytest tests/unit/plan_store/test_planned_pr_lifecycle.py` to verify lifecycle tests pass
2. Run `ruff check` and `ty check` on modified files
3. Manual: run `/erk:plan-save` on a plan and verify the PR description shows the summary above the collapsed plan
