# Plan: Update CLAUDE.md and AGENTS.md Plan Terminology

Part of Objective #8381, Nodes 1.1-1.4

## Context

Plans migrated from GitHub issues to draft PRs (PR #7971, objective #7911). CLAUDE.md and AGENTS.md still describe plans as GitHub issues. Every agent session reads these files, making them the highest-leverage fixes.

## Changes

### CLAUDE.md (Node 1.1)

**Line 31** — Change:
```
2. **Save**: Claude runs `/erk:plan-save` to create a GitHub issue
```
To:
```
2. **Save**: Claude runs `/erk:plan-save` to save the plan as a draft PR
```

### AGENTS.md (Nodes 1.2, 1.3, 1.4)

**Line 90** (Node 1.2) — Change:
```
- `/erk:plan-save` — save plan to GitHub issue
```
To:
```
- `/erk:plan-save` — save plan as draft PR
```

**Lines 98-102** (Node 1.3) — Replace Codex Users protocol:
```
1. **Assess complexity**: For complex tasks (3+ files, unclear scope), create a plan first
2. **Write the plan**: Create a markdown file with implementation steps
3. **Save to GitHub**: Run `erk pr create --file <path-to-plan.md>` to create a tracked issue
4. **Implement**: Run `erk implement <issue-number>` to set up a worktree and execute
5. **Submit**: Run `erk pr submit` after implementation to create the PR
```
With:
```
1. **Assess complexity**: For complex tasks (3+ files, unclear scope), create a plan first
2. **Write the plan**: Create a markdown file with implementation steps
3. **Save to GitHub**: Run `erk pr create --file <path-to-plan.md>` to create a tracked draft PR
4. **Implement**: Run `erk implement <plan-number>` to set up a worktree and execute
5. **Submit**: Run `erk pr submit` after implementation to push the code
```

**Lines 114-116** (Node 1.4) — Change:
```
- `erk implement <issue>` — implement a plan in a worktree
- `erk pr dispatch <issue>` — dispatch for remote implementation
```
To:
```
- `erk implement <plan>` — implement a plan in a worktree
- `erk pr dispatch <plan>` — dispatch for remote implementation
```

## Files Modified

- `/workspaces/erk/CLAUDE.md` (1 line)
- `/workspaces/erk/AGENTS.md` (6 lines)

## Verification

```bash
grep -n "plan issue\|GitHub issue\|erk pr create --file\|<issue>" CLAUDE.md AGENTS.md
```

Should return zero hits (except any legitimate "GitHub issue" references to objectives, which don't exist in these files).
