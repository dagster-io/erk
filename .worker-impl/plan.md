# Plan: Complete howto/pr-checkout-sync.md

> **Replans:** #5285
> **Objective:** #4284

## What Changed Since Original Plan

- Shell integration has been removed from codebase (Jan 2026)
- Commands are fully implemented with sophisticated Graphite integration
- PR #5286 was closed without merging - documentation still missing

## Investigation Findings

### Corrections to Original Plan

1. **Remove shell-integration references** - No longer exists
2. **Add Graphite mode details** - Commands have --dangerous flag for Graphite tracking
3. **Add `/erk:pr-address` command reference** - For addressing review comments

### Current State

- File `docs/howto/pr-checkout-sync.md` is a skeleton with 9 TODO sections
- All CLI commands exist and are fully implemented
- No documentation content has been written

## Remaining Gaps

- [ ] Write comprehensive how-to content
- [ ] Document both git-only and Graphite modes
- [ ] Add common scenarios table

## Implementation Steps

### Step 1: Write Overview Section

Explain when/why to checkout existing PRs:
- Reviewing teammate's PR
- Debugging remote execution results
- Taking over abandoned PRs
- Continuing work from different machine

### Step 2: Document `erk pr co`

```bash
erk pr co 123
erk pr co https://github.com/owner/repo/pull/123
erk pr co 123 --no-slot  # Don't assign to a slot
erk pr co 123 -f         # Force even if branch exists
```

### Step 3: Document `erk pr sync`

Two modes:

**Git-only (default):**
```bash
erk pr sync
# Fetches base → rebases → force pushes
```

**Graphite mode:**
```bash
erk pr sync --dangerous
# Registers with Graphite → enables stack commands
```

### Step 4: Document Making Changes

- Edit files normally
- Use Claude Code: `claude`
- Address review comments: `/erk:pr-address`

### Step 5: Document `erk pr submit`

```bash
erk pr submit
erk pr submit -f  # Force if branch diverged
```

### Step 6: Document `erk land`

```bash
erk land          # Land current PR
erk land --up     # Navigate to child after landing
```

### Step 7: Add Common Scenarios Table

| Scenario | Commands |
|----------|----------|
| Review teammate's PR | `erk pr co <num>` → review → comment |
| Debug remote execution | `erk pr co <num>` → `erk pr sync` → fix → `erk pr submit` |
| Take over PR | `erk pr co <num>` → `erk pr sync --dangerous` → continue |

## File to Modify

`docs/howto/pr-checkout-sync.md`

## Verification

1. `make docs-build` - Verify no broken links
2. Review rendered output for readability
3. Verify all commands mentioned actually exist