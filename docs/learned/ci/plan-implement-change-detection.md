---
title: erk-impl Change Detection
read_when:
  - "maintaining erk-impl workflow"
  - "debugging change detection issues"
  - "understanding why no-changes was triggered"
tripwires:
  - action: "implementing change detection without baseline capture"
    warning: "Read this doc first. Always capture baseline state BEFORE mutation, then compare AFTER."
  - action: "using generic variable names in change detection logic"
    warning: "Use explicit names (UNCOMMITTED, NEW_COMMITS) not generic ones (CHANGES)."
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

| Variable        | Meaning                               |
| --------------- | ------------------------------------- |
| `UNCOMMITTED`   | Staged/unstaged file changes          |
| `NEW_COMMITS`   | Whether HEAD has advanced             |
| `PRE_IMPL_HEAD` | Baseline commit before implementation |

Avoid generic names like `CHANGES` which conflate different change types.

## Edge Cases

| Scenario             | UNCOMMITTED | NEW_COMMITS | Result      |
| -------------------- | ----------- | ----------- | ----------- |
| Clean commits        | empty       | true        | Has changes |
| Uncommitted only     | non-empty   | false       | Has changes |
| Mixed                | non-empty   | true        | Has changes |
| Empty implementation | empty       | false       | No changes  |

## Related Documentation

- [No Code Changes Handling](../planning/no-changes-handling.md) - What happens when no changes detected
- [erk-impl Customization](erk-impl-customization.md) - Workflow gating patterns
