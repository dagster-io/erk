---
title: Tripwire Worthiness Criteria
read_when:
  - "evaluating whether an insight deserves tripwire status"
  - "reviewing [TRIPWIRE-CANDIDATE] items from learn workflow"
  - "understanding what makes something tripwire-worthy"
---

# Tripwire Worthiness Criteria

This document defines the heuristics for identifying insights that deserve tripwire status. Tripwires are action-triggered warnings that fire when an agent is about to perform a specific action.

## What Makes Something Tripwire-Worthy?

Tripwires are most valuable for **non-obvious, cross-cutting concerns with high impact**. A good tripwire prevents repeated mistakes by surfacing context at the moment it's needed.

## Scoring Criteria

The learn workflow uses these criteria to score tripwire-worthiness:

| Criterion             | Score | Description                                                    |
| --------------------- | ----- | -------------------------------------------------------------- |
| Non-obvious           | +2    | Error requires context to understand (not deducible from code) |
| Cross-cutting         | +2    | Applies to 2+ commands or multiple areas of the codebase       |
| Destructive potential | +2    | Could cause data loss, invalid state, or significant rework    |
| Silent failure        | +2    | No exception thrown; wrong result produced silently            |
| Repeated pattern      | +1    | Same mistake appears 2+ times in sessions                      |
| External tool quirk   | +1    | Involves gh, gt, GitHub API, or other external tool            |

**Maximum possible score: 10**

## Scoring Thresholds

| Score | Classification         | Action                                       |
| ----- | ---------------------- | -------------------------------------------- |
| >= 4  | `[TRIPWIRE-CANDIDATE]` | Strongly recommended for tripwire promotion  |
| 2-3   | Potential tripwire     | May warrant tripwire with additional context |
| < 2   | Regular documentation  | Document normally, not as tripwire           |

## Criteria Details

### Non-obvious (+2)

The error or behavior is not apparent from reading the code or standard documentation. It requires contextual knowledge that an agent wouldn't reasonably discover through exploration.

**Examples:**

- `--no-interactive` flag required for gt commands in automated contexts
- `gh pr view --json merged` fails because the field is `mergedAt`
- `gt track` only accepts local branch names, not remote refs like `origin/main`

### Cross-cutting (+2)

The concern applies broadly across multiple commands, modules, or use cases. Single-function bugs don't qualify.

**Examples:**

- Path handling that affects all worktree operations
- API rate limit patterns affecting all GitHub operations
- Context regeneration after `os.chdir()` in any command

### Destructive Potential (+2)

Getting this wrong could cause:

- Data loss (deleted files, lost commits)
- Invalid state (broken worktrees, corrupted metadata)
- Significant rework (PR needs to be redone, plan re-implemented)

**Examples:**

- Validate `--up` flag preconditions BEFORE merging PR
- Use `is_root` instead of path comparison (breaks in non-root worktrees)
- Branch mutation through BranchManager, not direct gateway calls

### Silent Failure (+2)

The operation completes without error but produces incorrect results. No exception is raised to alert the agent.

**Examples:**

- `fnmatch` doesn't support `**` recursive globs (use `pathspec` instead)
- Missing `--verbose` with `--output-format stream-json` fails silently
- Rich markup `[text]` disappearing in CLI tables (interpreted as style tags)

### Repeated Pattern (+1)

The same mistake has been made multiple times across different sessions or by different agents. Repetition indicates the pattern is genuinely non-obvious.

**How to identify:** Look for similar errors in multiple session analyses or PR review comments.

### External Tool Quirk (+1)

The issue involves behavior of external tools (gh, gt, GitHub API) that isn't well-documented or behaves unexpectedly.

**Examples:**

- GraphQL vs REST rate limits (separate quotas)
- `gh gist create --filename` only works with stdin
- `gt restack` doesn't handle same-branch divergence

## Examples from Existing Tripwires

### High Score (6): `--no-interactive` Flag

**Criteria met:**

- Non-obvious (+2): Not documented in gt help
- Cross-cutting (+2): Affects gt sync, gt submit, gt restack, etc.
- Silent failure (+2): Hangs indefinitely instead of erroring

**Total: 6/10** - Clear tripwire candidate

### Medium Score (4): `os.chdir()` Context Regeneration

**Criteria met:**

- Non-obvious (+2): Context caching behavior not obvious
- Destructive potential (+2): Causes FileNotFoundError on subsequent operations

**Total: 4/10** - Meets threshold

### Low Score (2): Single Function Type Error

**Criteria met:**

- Repeated pattern (+1): Seen twice
- External tool quirk (+1): Involves specific API behavior

**Total: 2/10** - Below threshold, document normally

## Review Process

When reviewing `[TRIPWIRE-CANDIDATE]` items from the learn workflow:

1. **Verify score accuracy**: Check that criteria were correctly applied
2. **Consider context**: Does the codebase have patterns that make this more/less relevant?
3. **Check for existing coverage**: Is there already a tripwire covering this case?
4. **Evaluate trigger specificity**: Is the trigger action specific enough to fire at the right time?

## Adding New Tripwires

Once a candidate is approved:

1. Identify the target document (the doc most relevant to the trigger action)
2. Add to the document's frontmatter:

```yaml
tripwires:
  - action: "specific trigger action"
    warning: "Concise warning with the correct approach"
```

3. Run `erk docs sync` to regenerate `tripwires.md`
4. Verify the tripwire appears in `docs/learned/tripwires.md`
