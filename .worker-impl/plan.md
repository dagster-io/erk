# Plan: Address PR Review Comment - Rename `title_suffix` to `title_tag`

## PR Context

- **PR #5726**: Move [erk-learn] to Beginning of Plan Titles
- **Branch**: P5725-move-erk-learn-to-beginni-01-23-1539

## Review Feedback

**Thread ID**: `PRRT_kwDOPxC3hc5q1X5U`
**Location**: `packages/erk-shared/src/erk_shared/github/plan_issues.py:159`
**Comment**: "no longer a suffix"

### Analysis

The reviewer correctly points out that the variable `title_suffix` is now misleading:
- For **standard plans**: The tag is appended (suffix): `"My Plan [erk-plan]"`
- For **learn plans**: The tag is prepended (prefix): `"[erk-learn] My Plan"`

Since the tag can be either a prefix or suffix depending on context, `title_suffix` is no longer accurate. The fix is to rename to `title_tag` (a neutral term that doesn't imply position).

## Implementation

### Files to Modify

1. **`packages/erk-shared/src/erk_shared/github/plan_issues.py`** - Core function
   - Parameter: `title_suffix` → `title_tag` (line 73)
   - Docstring: Update description (line 94)
   - Comments: "title suffix" → "title tag" (lines 147, 154)
   - Variable usages: All occurrences (lines 148, 150, 152, 156, 158)

2. **`packages/erk-shared/tests/unit/github/test_plan_issues.py`** - Tests
   - Keyword args: `title_suffix=` → `title_tag=` (25+ occurrences)
   - Test name: `test_uses_custom_title_suffix` → `test_uses_custom_title_tag`
   - Test name: `test_objective_has_no_title_suffix` → `test_objective_has_no_title_tag`

3. **`packages/erk-shared/src/erk_shared/plan_store/github.py`** - Metadata parsing
   - Docstring: metadata key documentation (line 271)
   - Variable: `title_suffix_raw` → `title_tag_raw` (line 282)
   - Variable: `title_suffix_str` → `title_tag_str` (lines 283, 284, 285, 310)
   - Dict key: `metadata.get("title_suffix")` → `metadata.get("title_tag")`

4. **`src/erk/cli/commands/exec/scripts/create_issue_from_session.py`**
   - Keyword arg: `title_suffix=None` → `title_tag=None` (line 74)

5. **`src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`**
   - Keyword arg: `title_suffix=None` → `title_tag=None` (line 266)

6. **`src/erk/cli/commands/plan/create_cmd.py`**
   - Keyword arg: `title_suffix=None` → `title_tag=None` (line 91)

## Verification

1. Run type checker: `ty` (via devrun agent)
2. Run unit tests: `make test-unit` (via devrun agent)
3. Verify no remaining `title_suffix` references: `grep -r title_suffix`

## Thread Resolution

After implementation, resolve thread with:
```
Fixed - renamed `title_suffix` to `title_tag` since it can be either a prefix or suffix depending on plan type.
```