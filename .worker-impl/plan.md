# Change branch prefix from `plan/` to `planned/`

## Context

Erk uses a `plan/` prefix for draft-PR-backed plan branches (e.g., `plan/fix-auth-bug-01-15-1430`). This prefix is also used for plan review branches (`plan/review-1234-01-15-1430`). Separately, a `planned/` prefix already exists for **PR titles** (via `PLANNED_PR_TITLE_PREFIX`).

This change aligns the branch prefix with the PR title prefix, changing all `plan/` branch prefixes to `planned/`.

**Note:** The `P{issue}-` prefix for issue-based branches is NOT changing — only the `plan/` prefix used by draft-PR branches and review branches.

## Changes

### 1. Core naming function — `packages/erk-shared/src/erk_shared/naming.py`

**`generate_draft_pr_branch_name()` (line 639):**
- Change `prefix = "plan/"` to `prefix = "planned/"`
- Update docstring (lines 613-637): Change all `plan/` references to `planned/` in format descriptions and examples

**`extract_objective_number()` (lines 396-427):**
- Line 402: Update docstring `plan/O{objective}` → `planned/O{objective}`
- Line 417: Update docstring example `plan/O456-fix-auth-01-15-1430` → `planned/O456-fix-auth-01-15-1430`
- Line 424: Update regex from `r"^(?:[Pp]?\d+-|plan/)[Oo](\d+)-"` to `r"^(?:[Pp]?\d+-|planned/)[Oo](\d+)-"`

**`extract_plan_review_issue_number()` (lines 430-455):**
- Line 433: Update docstring `plan/review-{issue_number}` → `planned/review-{issue_number}`
- Line 434: Update example `plan/review-6214-01-15-1430` → `planned/review-6214-01-15-1430`
- Line 440: Update return description `plan/review-{number}-` → `planned/review-{number}-`
- Lines 443, 445: Update docstring examples
- Line 452: Update regex from `r"^plan/review-(\d+)-"` to `r"^planned/review-(\d+)-"`

### 2. Review branch creation — `src/erk/cli/commands/exec/scripts/plan_create_review_branch.py`

- Line 161: Update comment `plan/review-{issue}-{MM-DD-HHMM}` → `planned/review-{issue}-{MM-DD-HHMM}`
- Line 163: Change `f"plan/review-{issue_number}{timestamp_suffix}"` to `f"planned/review-{issue_number}{timestamp_suffix}"`
- Line 207: Update docstring `plan/review-{issue}-{timestamp}` → `planned/review-{issue}-{timestamp}`

### 3. One-shot dispatch comments — `src/erk/cli/commands/one_shot_dispatch.py`

- Line 168: Update comment `use plan/ branch naming` → `use planned/ branch naming`
- Line 193: Update comment `plan/ prefix` → `planned/ prefix`

### 4. Tests — `tests/core/utils/test_naming.py`

Update all test data and assertions that reference `plan/`:

- Lines 476-477: `extract_objective_number` test data — change `"plan/O456-..."` to `"planned/O456-..."` and `"plan/O1-..."` to `"planned/O1-..."`
- Line 481: Change `"plan/fix-auth-bug-01-15-1430"` to `"planned/fix-auth-bug-01-15-1430"`
- Lines 504-505: Change `"plan/fix-auth-bug-..."` and `"plan/O456-..."` to `"planned/..."`
- Lines 522-525: Change all `"plan/review-..."` to `"planned/review-..."`
- Lines 531-533: Change negative test cases `"plan/review"` → `"planned/review"`, `"plan/review-"` → `"planned/review-"`, `"plan/review-abc-..."` → `"planned/review-abc-..."`
- Lines 549, 556, 563: `generate_draft_pr_branch_name` expected values — change `"plan/..."` to `"planned/..."`
- Lines 570, 577: Expected values with objectives — change `"plan/O456-..."` and `"plan/O1-..."` to `"planned/..."`
- Line 598: Change `assert result.startswith("plan/")` to `assert result.startswith("planned/")`
- Line 623: Change `assert result.startswith("plan/O456-")` to `assert result.startswith("planned/O456-")`

### 5. Tests — `tests/unit/cli/commands/exec/scripts/test_plan_save.py`

- Line 66: Change `startswith("plan/")` to `startswith("planned/")`
- Line 80: Change `"Branch: plan/"` to `"Branch: planned/"`
- Line 82: Change `"plan/" in result.output` to `"planned/" in result.output`
- Lines 232, 234: Change `startswith("plan/")` to `startswith("planned/")`

### 6. Tests — `tests/unit/cli/commands/exec/scripts/test_plan_migrate_to_draft_pr.py`

- Line 100: Change `startswith("plan/")` to `startswith("planned/")`
- Line 237: Change `"plan/" in output["branch_name"]` to `"planned/" in output["branch_name"]`

### 7. Tests — `tests/unit/cli/commands/exec/scripts/test_plan_create_review_branch.py`

- Line 136: Change `f"plan/review-{issue_number}-01-15-1430"` to `f"planned/review-{issue_number}-01-15-1430"`
- Line 366: Change `f"plan/review-{issue_number}-01-15-1430"` to `f"planned/review-{issue_number}-01-15-1430"`

### 8. Tests — `tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py`

Update all test setup branch names (8 occurrences):
- Line 86: `"plan/review-1234-01-15-1430"` → `"planned/review-1234-01-15-1430"`
- Line 147: `"plan/review-5678-01-15-1430"` → `"planned/review-5678-01-15-1430"`
- Line 180: `"plan/review-5679-01-15-1430"` → `"planned/review-5679-01-15-1430"`
- Line 213: `"plan/review-9999-01-15-1430"` → `"planned/review-9999-01-15-1430"`
- Line 255: `"plan/review-2222-01-15-1430"` → `"planned/review-2222-01-15-1430"`
- Line 288: `"plan/review-3333-01-15-1430"` → `"planned/review-3333-01-15-1430"`
- Line 324: `"plan/review-7777-01-15-1430"` → `"planned/review-7777-01-15-1430"`
- Line 393: `"plan/review-4444-01-15-1430"` → `"planned/review-4444-01-15-1430"`

### 9. Tests — `tests/commands/one_shot/test_one_shot_dispatch.py`

- Lines 326, 330: Update docstring references from `plan/` to `planned/`
- Line 370: Update comment `plan/ prefix` → `planned/ prefix`
- Line 371: Change `startswith("plan/")` to `startswith("planned/")`

### 10. Documentation — `docs/learned/erk/branch-naming.md`

- Line 50: Change `plan/{slug}-{MM-DD-HHMM}` to `planned/{slug}-{MM-DD-HHMM}`
- Line 56: Change `plan/O{objective}-{slug}-{MM-DD-HHMM}` to `planned/O{objective}-{slug}-{MM-DD-HHMM}`
- Lines 61-62: Update examples to `planned/fix-auth-bug-...` and `planned/O456-fix-auth-bug-...`
- Line 68: Update constraint description to mention `planned/`
- Line 89: Update `plan/O{obj}-` to `planned/O{obj}-`
- Lines 92, 94: Update extraction examples
- Line 109: Update `plan/...` to `planned/...`

### 11. Documentation — `docs/learned/planning/branch-name-inference.md`

This doc already has stale references (says `plan-` with hyphen instead of `plan/` with slash from a prior prefix change). Update lines 61-70 to use `planned/`:

- Line 6 tripwire: Update `plan-` reference to `planned/`
- Line 61: Change `### Draft-PR Branches: \`plan-\`` to `### Draft-PR Branches: \`planned/\``
- Line 63: Change `plan-{slug}-{timestamp}` to `planned/{slug}-{timestamp}` with `O{objective_id}` segment
- Line 67: Change `plan-{slug}-{timestamp}` to `planned/{slug}-{timestamp}`
- Line 68: Update `plan-` references to `planned/`
- Line 70: Update `plan-` and `plan-O{obj}-` to `planned/` and `planned/O{obj}-`

## Files NOT Changing

- **`src/erk/cli/constants.py`** — `PLANNED_PR_TITLE_PREFIX = "planned/"` is for PR titles, not branch names. Already uses `planned/`. No change needed.
- **`src/erk/cli/commands/submit.py`** and **`src/erk/cli/commands/pr/submit_pipeline.py`** — These use `PLANNED_PR_TITLE_PREFIX` for PR title prefixing, not branch naming. No change.
- **Issue-based branch naming** (`generate_issue_branch_name()`, `P{issue}-` prefix) — Not affected by this change.
- **`.github/workflows/`** — No CI files reference the `plan/` branch prefix.
- **Other `docs/learned/` files** — References like `plan/checkout_cmd.py` or `plan/list_cmd.py` are directory paths, not branch prefixes. No change.

## Implementation Details

- This is a straightforward string replacement: `"plan/"` → `"planned/"` in branch-prefix contexts only
- Be careful not to change directory path references (e.g., `src/erk/cli/commands/plan/` or `.erk/plan/PLAN.md`)
- The regex patterns in extraction functions must be updated to match the new prefix
- The 31-character limit on `prefix + sanitized_title` still applies — the `planned/` prefix is 8 chars (vs 5 for `plan/`), leaving 3 fewer chars for the title slug. This is an acceptable tradeoff.

## Verification

1. Run `ty` for type checking
2. Run `ruff check` and `ruff format --check` for linting
3. Run the specific test files:
   - `pytest tests/core/utils/test_naming.py -v`
   - `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py -v`
   - `pytest tests/unit/cli/commands/exec/scripts/test_plan_migrate_to_draft_pr.py -v`
   - `pytest tests/unit/cli/commands/exec/scripts/test_plan_create_review_branch.py -v`
   - `pytest tests/unit/cli/commands/exec/scripts/test_plan_create_review_pr.py -v`
   - `pytest tests/commands/one_shot/test_one_shot_dispatch.py -v`
4. Run the full test suite to catch any integration issues