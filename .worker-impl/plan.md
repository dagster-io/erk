# Plan: Complete howto/pr-checkout-sync.md

**Part of Objective #4284, Step 2C.1**

## Summary

Complete the `docs/howto/pr-checkout-sync.md` how-to guide that covers checking out existing PRs, syncing with remote, making changes, and iterating.

## Context

**Current state:** Skeleton file with TODO comments (39 lines)

**Existing coverage:**
- `docs/howto/navigate-branches-worktrees.md` covers `erk pr co` briefly (checkout only)
- `docs/howto/local-workflow.md` covers the full lifecycle but assumes you created the PR

**Gap:** No documentation for working with PRs you didn't create - reviewing teammate PRs, debugging remote execution results, taking over abandoned PRs.

## Content Outline

### 1. Overview
When you'd want to check out an existing PR:
- Reviewing a teammate's PR
- Debugging a remotely-executed implementation
- Taking over a PR from another developer
- Continuing work on your own PR from a different machine

### 2. Checking Out a PR
```bash
erk pr co 123
erk pr co https://github.com/owner/repo/pull/123
```
- Creates worktree if needed
- Fetches the branch
- Switches to it
- Options: `--no-slot`, `-f/--force`

### 3. Syncing with Remote
Two modes based on Graphite usage:

**Git-only mode (no Graphite):**
```bash
erk pr sync
```
- Fetches base branch
- Rebases onto it
- Force pushes

**Graphite mode:**
```bash
erk pr sync --dangerous
```
- Registers branch with Graphite
- Enables stack commands (gt submit, gt restack)

### 4. Making Changes
- Edit files normally
- Use Claude Code for assistance: `claude`
- Address review comments: `/erk:pr-address`

### 5. Submitting Updates
```bash
erk pr submit
erk pr submit -f  # if branch diverged
```

### 6. Landing
```bash
erk land          # land current PR
erk land --up     # navigate to child after landing
```

### 7. Common Scenarios
| Scenario | Commands |
|----------|----------|
| Review teammate's PR | `erk pr co <num>` → review → comment on GitHub |
| Debug remote execution | `erk pr co <num>` → `erk pr sync` → fix → `erk pr submit` |
| Take over PR | `erk pr co <num>` → `erk pr sync --dangerous` → continue work |

## File to Modify

`docs/howto/pr-checkout-sync.md`

## Style Guidelines

- Follow Divio how-to style (task-oriented, step-by-step)
- Match tone of `docs/howto/local-workflow.md` and `docs/howto/navigate-branches-worktrees.md`
- Include code blocks with bash highlighting
- Link to related docs in See Also section
- Remove shell-integration references (it's being removed)

## Verification

1. Run `mkdocs build` to verify no broken links
2. Review rendered output for readability
3. Verify all commands mentioned actually exist (`erk pr co`, `erk pr sync`, `erk pr submit`, `erk land`)