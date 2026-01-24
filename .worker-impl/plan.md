# Plan: Dual-Check Change Detection Documentation [Updated]

> **Replans:** #5712

## What Changed Since Original Plan

The **technical implementation** from PR #5710 is fully functional in `.github/workflows/erk-impl.yml`. However, the **documentation** was never created. This replan focuses on the documentation gaps, which remain valid.

Key changes since the original plan:
- Workflow implementation is complete (lines 187-312 in erk-impl.yml)
- Partial documentation exists in `no-changes-handling.md` and `lifecycle.md`
- Existing CI docs follow a consistent pattern that new docs should match

## Investigation Findings

### What's Already Implemented (Code)
- **PRE_IMPL_HEAD capture**: Lines 187-189 - working correctly
- **Dual-check detection**: Lines 261-312 - fully functional
- **Graceful handling**: `handle_no_changes.py` - complete

### What Exists (Documentation)
- `docs/learned/planning/no-changes-handling.md` - Documents the response to no-changes
- `docs/learned/planning/lifecycle.md` - Has "No-Changes Error Scenario" section (lines 447-464)
- `docs/learned/ci/erk-impl-customization.md` - References `has_changes` gating

### What's Missing (Documentation Gaps)
1. **No explanation of HOW detection works** - The dual-check mechanism is undocumented
2. **No architectural pattern doc** - State capture pattern is not generalized
3. **No tripwires** - Common mistakes not captured

## Remaining Gaps

### HIGH Priority - Create New Documentation

1. **`docs/learned/ci/erk-impl-change-detection.md`** (NEW)
   - Explains the dual-check detection mechanism
   - Documents WHY both checks are needed (the PR #5708 bug)
   - Shows the code pattern with inline comments
   - Read when: Maintaining erk-impl workflow, debugging change detection

### MEDIUM Priority - Update Existing Documentation

2. **`docs/learned/planning/workflow.md`** (UPDATE)
   - Add "How Changes Are Detected" subsection under "Remote Implementation via GitHub Actions"
   - Brief explanation pointing to the detailed CI doc
   - Currently missing any explanation of detection mechanism

### LOW Priority - Add Tripwires

3. **`docs/learned/tripwires.md`** (UPDATE via frontmatter)
   - Add tripwire for state capture validation pattern
   - Add tripwire for semantic variable naming in change detection

---

## Implementation Steps

### Step 1: Create erk-impl-change-detection.md

Create `docs/learned/ci/erk-impl-change-detection.md` with:

```markdown
---
title: erk-impl Change Detection
read_when:
  - "maintaining erk-impl workflow"
  - "debugging change detection issues"
  - "understanding why no-changes was triggered"
tripwires:
  - trigger: "Before implementing change detection without baseline capture"
    action: "Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER."
  - trigger: "Before using generic variable names in change detection logic"
    action: "Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES)."
---

# erk-impl Change Detection

The erk-impl workflow uses a **dual-check** approach to detect whether implementation produced changes.

## Why Dual-Check?

Single-channel detection is insufficient because agent implementations can express work through two independent channels:

1. **Uncommitted changes** - Files modified but not committed (dirty working tree)
2. **New commits** - Commits created during implementation (clean working tree, new HEAD)

PR #5708 discovered this bug: when an agent committed all its work and left a clean working directory, single-channel detection (git status only) incorrectly reported "no changes."

## The Pattern

### Step 1: Capture Pre-Implementation State

Before running the agent, capture the current HEAD:

```yaml
- name: Save pre-implementation HEAD
  id: pre_impl
  run: echo "head=$(git rev-parse HEAD)" >> $GITHUB_OUTPUT
```

### Step 2: Check Both Channels

After implementation, check both independently:

```bash
# Channel 1: Uncommitted changes
UNCOMMITTED=$(git status --porcelain | grep -v ... || true)

# Channel 2: New commits since pre-implementation
CURRENT_HEAD=$(git rev-parse HEAD)
NEW_COMMITS="false"
if [ "$CURRENT_HEAD" != "$PRE_IMPL_HEAD" ]; then
  NEW_COMMITS="true"
fi
```

### Step 3: Combine Results

Changes exist if **either** channel has changes:

```bash
if [ -z "$UNCOMMITTED" ] && [ "$NEW_COMMITS" = "false" ]; then
  # No changes → graceful handling
else
  # Changes detected → proceed with submission
fi
```

## Variable Naming Convention

Use semantic names that describe what's being detected:

| Variable | Meaning |
|----------|---------|
| `UNCOMMITTED` | Staged/unstaged file changes |
| `NEW_COMMITS` | Whether HEAD has advanced |
| `PRE_IMPL_HEAD` | Baseline commit before implementation |

Avoid generic names like `CHANGES` which conflate different change types.

## Edge Cases

| Scenario | UNCOMMITTED | NEW_COMMITS | Result |
|----------|-------------|-------------|--------|
| Clean commits | empty | true | Has changes |
| Uncommitted only | non-empty | false | Has changes |
| Mixed | non-empty | true | Has changes |
| Empty implementation | empty | false | No changes |

## Related Documentation

- [No Code Changes Handling](../planning/no-changes-handling.md) - What happens when no changes detected
- [erk-impl Customization](erk-impl-customization.md) - Workflow gating patterns
```

### Step 2: Update workflow.md

Add a subsection under "Remote Implementation via GitHub Actions" (after line 268):

```markdown
### How Changes Are Detected

The workflow uses a **dual-check** approach to detect implementation changes:

1. **Pre-implementation**: Captures `git rev-parse HEAD` before the agent runs
2. **Post-implementation**: Checks both uncommitted changes AND new commits
3. **Result**: Changes exist if either channel has changes

This dual-check prevents false negatives when agents commit their work without leaving uncommitted changes. See [erk-impl Change Detection](../ci/erk-impl-change-detection.md) for details.
```

### Step 3: Add tripwires via frontmatter

The tripwires will be auto-generated from the frontmatter in `erk-impl-change-detection.md`. Run `erk docs sync` after creating the doc.

---

## Files to Modify

| File | Action | Lines |
|------|--------|-------|
| `docs/learned/ci/erk-impl-change-detection.md` | CREATE | ~80 lines |
| `docs/learned/planning/workflow.md` | UPDATE | +15 lines after line 268 |

## Verification

After implementation:

1. Run `erk docs sync` to regenerate tripwires.md and index files
2. Verify `docs/learned/ci/index.md` includes the new doc
3. Verify `docs/learned/tripwires.md` includes the new tripwires
4. Run `make format` to ensure proper formatting

## Notes

- **Reduced scope**: The original plan included `state-capture-validation.md` as a general architectural pattern. This is deferred - the specific CI doc is sufficient for now.
- **Phase 4b labeling**: The original plan wanted "Phase 4b" in lifecycle.md. The existing "No-Changes Error Scenario" section is adequate.
- **Variable naming tripwire**: Included in the new doc's frontmatter rather than as a separate doc.