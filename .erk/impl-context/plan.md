# Plan: Fix cli/ and erk/ docs terminology (Objective #8381, Node 6.4)

## Context

Part of Objective #8381 (Standardize Plan-as-PR Terminology). Nodes 6.1-6.3 already updated planning/ and cross-cutting docs. This node updates the remaining cli/ and erk/ documentation files to replace stale "issue" terminology with "plan"/"plan PR" language.

## Files to Modify (7 files)

### cli/ docs (4 files)

1. **`docs/learned/cli/plan-implement.md`** (~18 replacements)
   - "GitHub issues" → "GitHub" (plans aren't stored as issues anymore)
   - "Issue number" → "Plan number"
   - "issue tracking" → "plan tracking"
   - "plan issue" → "plan"
   - "linked to issue" → "linked to plan"
   - "issue metadata" → "plan metadata"
   - `has_issue_tracking` → `has_plan_tracking` (already renamed in code)
   - "auto-close an issue" → "auto-close a plan"
   - Remove stale `issue.json` reference (already gone from code)

2. **`docs/learned/cli/command-organization.md`** (~6 replacements)
   - "plan issue" → "plan" in all command descriptions and tables

3. **`docs/learned/cli/erk-exec-commands.md`** (~10 replacements)
   - "plan issue metadata" → "plan metadata"
   - "plan issue" → "plan" in descriptions
   - `--issue` flag references → `--plan` (flag rename is Phase 7 code work, but docs should reflect target state)
   - "issue number" → "plan number"
   - "issue-based plans" → "plan-based implementations"

4. **`docs/learned/cli/pr-submit-pipeline.md`** (~3 replacements)
   - "issue number" → "plan number"
   - "issue linkage" → "plan linkage"
   - Remove stale `issue.json` reference

### erk/ docs (3 files)

5. **`docs/learned/erk/issue-pr-linkage-storage.md`** (~20 replacements)
   - Title: "Issue-PR Linkage" → "Plan-PR Linkage"
   - Heading: same rename
   - "GitHub issues (plans)" → "plan PRs"
   - "issue" → "plan" throughout when referring to plans
   - "issue number" → "plan number"
   - `get_prs_linked_to_issues()` → `get_prs_linked_to_plans()` (verify actual function name in code first)
   - read_when entries updated

6. **`docs/learned/erk/pr-address-workflows.md`** (~8 replacements)
   - `{issue}` placeholder → `{plan_number}`
   - "plan issue" → "plan"
   - "GitHub issue" → "Plan"

7. **`docs/learned/erk/remote-workflow-template.md`** (~2 replacements)
   - "plan issue number" → "plan number"
   - "on the issue" → "on the plan"

## Implementation Steps

1. **Verify function names** - Check if `get_prs_linked_to_issues()` has been renamed yet (affects issue-pr-linkage-storage.md)
2. **Update all 7 files** - Apply terminology replacements as listed above
3. **Verify no broken cross-references** - The issue-pr-linkage-storage.md references `../architecture/github-pr-linkage-api.md`; update link text but keep path unchanged

## Key Considerations

- **`--issue` flag in docs**: The actual CLI flag is still `--issue` (code rename is Phase 7, node 7.4). In erk-exec-commands.md, update the surrounding language but note the actual current flag name. Or update to target state since Phase 7 will follow.
- **`issue.json` already gone**: Code removed this; docs should not reference it.
- **`has_issue_tracking` already gone**: Renamed in code; docs should use current name.
- **File rename for issue-pr-linkage-storage.md**: The filename itself contains "issue". Renaming the file is out of scope for this node (would be node 6.5 or 6.6's territory for index files). Only update content.

## Verification

1. Run `ruff check` (no Python changes, but sanity check)
2. Grep all 7 files for remaining "issue" references to ensure none were missed
3. Grep for broken markdown links in the modified files
4. Visual review of each file for coherent language after changes
