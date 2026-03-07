---
title: Dynamic Trunk Detection
read_when:
  - writing git commands in slash commands or skills
  - referencing master or main branch in .claude/ files
  - creating new commands that compare against trunk
tripwires:
  - action: "hardcoding 'master' or 'main' as branch name in a command or skill"
    warning: "Use dynamic trunk detection: `TRUNK=$(erk exec detect-trunk-branch | jq -r '.trunk_branch')`. Hardcoded branch names break portability across repos."
  - action: "writing git diff/merge-base/reset against a literal branch name in .claude/ files"
    warning: "Use dynamic trunk detection: `TRUNK=$(erk exec detect-trunk-branch | jq -r '.trunk_branch')`. Hardcoded branch names break portability across repos."
---

# Dynamic Trunk Detection

## Why Dynamic Detection

Repositories use different trunk branch names — `master`, `main`, or occasionally `develop`. Hardcoding any one of these in `.claude/` commands, skills, or agents breaks portability when the same tooling is used across repos with different conventions.

The `erk exec detect-trunk-branch` command queries the origin remote and returns the detected trunk branch as JSON, checking `main` first then `master`.

## The Pattern

```bash
TRUNK=$(erk exec detect-trunk-branch | jq -r '.trunk_branch')
git diff "$TRUNK"...HEAD
git merge-base "$TRUNK" HEAD
git log "$TRUNK"..HEAD
```

Always capture the result into a variable, then use `"$TRUNK"` in subsequent git commands.

## Anti-Patterns

### Hardcoded branch names

```bash
# WRONG: breaks in repos that use 'main'
git diff master...HEAD

# WRONG: breaks in repos that use 'master'
git log main..HEAD
```

### Inline detection without variable

```bash
# WRONG: runs detection multiple times, fragile quoting
git diff "$(erk exec detect-trunk-branch | jq -r '.trunk_branch')"...HEAD
```

Capture once into `TRUNK` and reuse the variable.

## Where It Applies

- `.claude/commands/` — slash commands with git operations
- `.claude/skills/` — skill definitions that reference trunk
- `.claude/agents/` — agent configurations comparing against trunk
- CI workflows — GitHub Actions that need to diff against trunk

## Implementation

The detection logic lives in `src/erk/cli/commands/exec/scripts/detect_trunk_branch.py`. It checks the origin remote for `main` first (modern convention), then `master` (legacy convention), returning a JSON result with `success` and `trunk_branch` fields.
