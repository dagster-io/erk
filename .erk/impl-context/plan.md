# Documentation Plan: Fix stale `erk plan check` reference in one-shot workflow

## Context

This plan addresses a maintenance fix for PR #8148, which corrected a broken one-shot workflow after a CLI command rename. PR #8110 consolidated `erk plan` commands under the `erk pr` group, renaming `erk plan check` to `erk pr check`. However, two stale references were missed: the workflow file (fixed by this PR) and a documentation file that still needs updating.

The learning value here is not in the fix itself (a trivial one-line change) but in preventing similar oversights during future command renames. The existing command-rename-checklist.md already documents the 9-place checklist, but this incident demonstrates that workflow files remain a blind spot. The checklist was not consulted during PR #8110, allowing the stale reference to reach production.

Future agents benefit from understanding that workflow failures of this type are "rename without grep" failures - silent during development, discovered only in CI, and trivial to prevent with systematic verification. The tripwire addition will surface this warning proactively when agents work on command renames.

## Raw Materials

Materials extracted from plan #8148 implementation sessions.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 1     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Update plan-schema.md stale command reference

**Location:** `docs/learned/planning/plan-schema.md`
**Action:** UPDATE_REFERENCES
**Source:** [Impl]

**Draft Content:**

Line 29 currently reads:
```
- **Validation:** Run `erk plan check <issue-number>` (see `src/erk/cli/commands/plan/check_cmd.py`)
```

Update to:
```
- **Validation:** Run `erk pr check <issue-number>` (see `src/erk/cli/commands/pr/check_cmd.py`)
```

The command was renamed from `erk plan check` to `erk pr check` in PR #8110, and the implementation file moved from `src/erk/cli/commands/plan/check_cmd.py` to `src/erk/cli/commands/pr/check_cmd.py`.

---

## Contradiction Resolutions

### 1. Plan schema validation command reference

**Existing doc:** `docs/learned/planning/plan-schema.md:29`
**Conflict:** Documentation references `erk plan check` command and file path `src/erk/cli/commands/plan/check_cmd.py`, but both were renamed in PR #8110. The command is now `erk pr check` and the file is at `src/erk/cli/commands/pr/check_cmd.py`.
**Resolution:** Update both the command name and the file path reference on line 29.

## Stale Documentation Cleanup

Existing docs with phantom references requiring action:

### 1. Plan schema validation command reference

**Location:** `docs/learned/planning/plan-schema.md:29`
**Action:** UPDATE_REFERENCES
**Phantom References:** `erk plan check` (renamed to `erk pr check`), `src/erk/cli/commands/plan/check_cmd.py` (moved to `src/erk/cli/commands/pr/check_cmd.py`)
**Cleanup Instructions:** Replace line 29 with the updated command name and file path. No other content changes needed - the surrounding documentation about plan schema structure remains valid.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Workflow command reference drift

**What happened:** PR #8110 renamed `erk plan check` to `erk pr check` and moved the implementation file, updating most references. However, `.github/workflows/one-shot.yml:190` was missed, causing the one-shot workflow to fail with `Error: No such command 'check'` when agents attempted to dispatch plans.

**Root cause:** The PR author did not grep `.github/workflows/` for the old command name before merging. Tests passed locally because workflow files are not covered by unit tests.

**Prevention:** Before merging any CLI command rename PR, run:
```bash
grep -r "erk <old-group> <cmd>" .github/workflows/
```
This should be part of the existing 9-place command-rename-checklist.md verification step.

**Recommendation:** TRIPWIRE - Add explicit warning about workflow files to cli/tripwires.md

### 2. Documentation reference drift

**What happened:** After fixing the workflow, `docs/learned/planning/plan-schema.md:29` was discovered to still reference the old command. This was also missed during PR #8110.

**Root cause:** Same as above - systematic grep was not performed against docs/learned/ for the old command name.

**Prevention:** The command-rename-checklist.md step 6 already covers this, but it was not followed.

**Recommendation:** ADD_TO_DOC - The checklist already exists; the issue is checklist adherence, not missing documentation.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Missing workflow updates when renaming CLI commands

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before merging CLI command rename PRs, or when consolidating CLI command groups
**Warning:** Must grep `.github/workflows/` for all references to old command name. Workflow failures block production automation and are only discovered in CI.
**Target doc:** `docs/learned/cli/tripwires.md`

This tripwire addresses a gap in the existing command-rename-checklist.md tripwire. While the checklist mentions workflow files as step 9, the error in this incident shows that mentioning it in a checklist is insufficient - the checklist was not consulted. A direct tripwire warning when working on CLI command renames will surface the workflow verification requirement proactively.

The harm without this tripwire: workflow failures are silent during local development (tests pass), discovered only when the workflow runs in CI, and block critical automation like the one-shot agent dispatch pipeline. The fix is trivial (one-line change) but diagnosis requires correlating CI failures with git history to understand when the command was renamed.

**Suggested tripwire text:**
- **action:** "merging CLI command rename PRs without grepping workflows"
- **warning:** "Before merging, run `grep -r 'erk <old-command>' .github/workflows/` to find stale references. Workflow failures are discovered only in CI and block production automation."

## Potential Tripwires

No items with score 2-3. The single tripwire candidate identified exceeds the threshold with a score of 6.

## Verification Commands

After implementing the documentation update, verify no stale references remain:

```bash
# Should find only CHANGELOG.md (historical reference - OK)
grep -r "erk plan check" --include="*.yml" --include="*.md" . | grep -v CHANGELOG

# Should find 17+ current uses in docs/learned/
grep -r "erk pr check" docs/learned/ | wc -l
```
