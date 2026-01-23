# Plan: Add documentation to PR #5616 for get-pr-commits and close-issue-with-comment

> **Replans:** #5623

## Context

PR #5616 adds two exec commands (`get-pr-commits`, `close-issue-with-comment`) but is missing the documentation that was planned in issue #5623. This plan merges the documentation items into PR #5616 so documentation ships with the code.

## What Changed Since Original Plan

- PR #5616 is still OPEN - commands exist but aren't in master
- Documentation items are still relevant and should be added to PR #5616
- `exec-script-patterns.md` was never created
- erk-exec skill reference is auto-generated (not manually updated)

## Implementation Steps

### 1. Checkout PR #5616 branch

```bash
gh pr checkout 5616
```

### 2. Create `docs/learned/cli/exec-script-patterns.md`

New file documenting exec script implementation patterns:
- When to create exec commands (reusability, complexity, rate limits)
- Two implementation approaches (gateway methods vs direct `gh api`)
- JSON output format conventions
- Exit code standards
- Error handling for multi-step operations
- Registration checklist (group.py, skill docs, learned docs)

### 3. Update `docs/learned/architecture/github-api-rate-limits.md`

Add to the "Rate-Limit-Safe Commands" table:
- `erk exec get-pr-commits` (replaces `gh pr view --json commits`)
- `erk exec close-issue-with-comment` (replaces `gh issue close` + comment)

### 4. Update `docs/learned/tripwires.md`

Add tripwire:
```
**CRITICAL: Before adding a new exec command to src/erk/cli/commands/exec/scripts/** → Read [Exec Script Implementation Patterns](cli/exec-script-patterns.md) first. Must register in group.py. Missing registration causes command to be unavailable.
```

### 5. Update `docs/learned/architecture/github-interface-patterns.md`

Add "Atomic Multi-Step Operations" section documenting:
- When to combine operations (semantic atomicity, ordering dependency, reusability)
- Implementation pattern with partial success handling
- Trade-offs between combined vs separate commands

### 6. Regenerate exec reference docs

```bash
erk-dev gen-exec-reference-docs
```

### 7. Commit and push

Commit the documentation changes to PR #5616.

### 8. Close issue #5623

```bash
gh issue close 5623 --comment "Documentation merged into PR #5616"
```

## Files to Create/Modify

| File | Action |
|------|--------|
| `docs/learned/cli/exec-script-patterns.md` | CREATE |
| `docs/learned/architecture/github-api-rate-limits.md` | UPDATE |
| `docs/learned/tripwires.md` | UPDATE |
| `docs/learned/architecture/github-interface-patterns.md` | UPDATE |
| `.claude/skills/erk-exec/reference.md` | REGENERATE |

## Verification

1. Run `make format` to ensure formatting
2. Run `erk-dev gen-exec-reference-docs` to regenerate skill reference
3. Verify new commands appear in regenerated reference
4. Run `make fast-ci` to verify no regressions
5. Push changes to PR #5616