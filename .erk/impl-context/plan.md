# Plan: Make `erk workflow run list` PR-centric

## Context

The current `erk workflow run list` is plan-centric: it extracts plan issue numbers from `display_title`, fetches issue titles, and derives linked PRs. This means non-plan-implement workflows (`pr-address`, `pr-rebase`, `one-shot`, etc.) can't show meaningful data — they display "X" and are hidden by default behind a `--show-legacy` flag. But these aren't "legacy" — they're current workflows that target PRs directly.

The fix: make the table PR-centric. Most workflows already accept `pr_number` as an input, so we encode it in `run-name` and parse it from `display_title`.

## Changes

### 1. Update workflow `run-name` formats to include `#pr_number`

Add `#${{ inputs.pr_number }}` to the `run-name` of workflows that have a `pr_number` input:

| File | Current run-name | New run-name |
|---|---|---|
| `.github/workflows/plan-implement.yml` | `"${{ inputs.plan_id }}:${{ inputs.distinct_id }}"` | `"${{ inputs.plan_id }}:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"` |
| `.github/workflows/pr-rebase.yml` | `"rebase:${{ inputs.branch_name }}:${{ inputs.distinct_id }}"` | `"rebase:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"` |
| `.github/workflows/pr-rewrite.yml` | `"rewrite:${{ inputs.branch_name }}:${{ inputs.distinct_id }}"` | `"rewrite:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"` |
| `.github/workflows/one-shot.yml` | `"one-shot:${{ inputs.distinct_id }}"` | `"one-shot:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"` |
| `.github/workflows/pr-address.yml` | Already has `#pr_number` | No change |
| `.github/workflows/learn.yml` | No `pr_number` input | No change |

### 2. Add `extract_pr_number()` to `src/erk/cli/commands/run/shared.py`

New function that finds `#\d+` in `display_title`:
- `"pr-address:#456:abc123"` → 456
- `"8559:#460:abc123"` → 460
- `"one-shot:#458:abc123"` → 458
- `"8559:abc123"` (old format) → None
- `"Some title [abc123]"` (legacy) → None

### 3. Rewrite `src/erk/cli/commands/run/list_cmd.py`

- **Remove `--show-legacy` flag** — always show all runs
- **Rename "plan" column to "pr"**
- **Two-pass PR number extraction:**
  1. Try `extract_pr_number(display_title)` for direct `#NNN` format (new workflows)
  2. Fall back to `extract_plan_number(display_title)` → `get_prs_linked_to_issues()` → select best PR (old plan-implement format)
- **Keep `list_issues()` call** — still needed to derive `GitHubRepoLocation` and for plan→PR linkage
- **Remove both filtering passes** (the ones that hide runs without plan data)
- **Show `-` (not "X")** for runs where no PR can be determined (e.g., learn runs, truly legacy runs)
- **Title column**: Show PR title from `PullRequestInfo` (available from plan→PR linkage). For direct PR numbers not in linkage data, show `-`.

### 4. Update tests in `tests/commands/run/test_list.py`

- Remove/rewrite `--show-legacy` tests
- Remove filtering tests (runs are no longer filtered out)
- Add test for `pr-address` format: display_title `"pr-address:#456:abc123"` → shows `#456` in pr column
- Add test for new plan-implement format: display_title `"142:#460:abc123"` → shows `#460` in pr column
- Add test for old plan-implement format: display_title `"142:abc123"` → falls back to plan→PR linkage
- Add test for learn/no-PR runs: shows `-` for pr/title/chks
- Update existing tests that reference "plan" column or "X" markers

## Verification

1. Run `uv run pytest tests/commands/run/test_list.py` — all tests pass
2. Run `uv run pytest tests/` scoped to any related test directories
3. Manual test: `erk workflow run list` should show all workflow types with PR numbers filled in where available
