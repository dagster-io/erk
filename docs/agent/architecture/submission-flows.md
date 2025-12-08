---
title: Git vs Graphite Submission Flows
read_when:
  - "choosing between /git:pr-push and /gt:pr-submit"
  - "understanding PR submission workflows"
  - "implementing new submission commands"
---

# Git vs Graphite Submission Flows

Erk supports two PR submission workflows: **Git** (simple push + PR) and **Graphite** (squash + rebase + submit). Choose based on whether you need stacked PR management.

## Quick Comparison

| Feature                  | Git (`/git:pr-push`)       | Graphite (`/gt:pr-submit`)      |
| ------------------------ | -------------------------- | ------------------------------- |
| **Commit History**       | Preserved                  | Squashed to single commit       |
| **Stack Awareness**      | No                         | Yes (rebases entire stack)      |
| **Authentication**       | GitHub only                | GitHub + Graphite               |
| **Push Command**         | `git push -u origin HEAD`  | `gt submit --publish`           |
| **PR Creation**          | `gh pr create`             | Built into `gt submit`          |
| **Use Case**             | Single-branch development  | Stacked PR workflows            |
| **Complexity**           | Low                        | Medium                          |

## Git Flow (`/git:pr-push`)

**Command**: `erk pr push` → `git push + gh pr create`

### Process

```
Local Branch (multiple commits)
    ↓
git push -u origin HEAD
    ↓
gh pr create --fill
    ↓
PR Created (preserves all commits)
```

### Characteristics

- **Preserves commit history**: All commits appear in PR as-is
- **Simple push**: Standard git push to remote
- **No squashing**: Commit history untouched
- **No stack awareness**: Each branch independent
- **Fast**: No rebase or stack operations

### When to Use

- Working on a single branch (no dependencies)
- Want to preserve detailed commit history
- Not using Graphite stacks
- Quick fixes or documentation changes

### Implementation

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/git/agents/git/git-branch-submitter.md`

**Phases**:
1. **Validate**: Check for uncommitted changes, ensure on branch
2. **Push**: `git push -u origin HEAD`
3. **Create PR**: `gh pr create --fill` (or edit if exists)
4. **AI Generation**: Generate PR title/body from diff
5. **Update PR**: Apply AI-generated metadata

**Key Difference**: No squashing or restacking. Just push + PR creation.

## Graphite Flow (`/gt:pr-submit`)

**Command**: `erk pr submit` → `gt submit --publish --restack`

### Process

```
Local Branch (multiple commits)
    ↓
Squash to single commit
    ↓
Rebase entire stack
    ↓
gt submit --publish (push + create PR)
    ↓
PR Created (single commit)
```

### Characteristics

- **Squashes commits**: Multiple commits → single commit
- **Stack-aware**: Rebases all upstack branches
- **Graphite integration**: Uses `gt submit` for push + PR
- **Single commit per PR**: Clean history for reviewers
- **Slower**: Rebase + submit takes longer than simple push

### When to Use

- Using Graphite stacked PRs
- Want clean single-commit PRs
- Need to rebase stack automatically
- Building features across multiple PRs

### Implementation

**File**: `src/erk/cli/commands/pr/submit_cmd.py`

**Phases** (see [Two-Phase Operations](two-phase-operations.md)):
1. **Preflight**: Auth checks, squash, submit, extract diff
2. **AI Generation**: Generate commit message from diff
3. **Finalize**: Update PR metadata, clean up temp files

**Key Difference**: Squashing + restacking before submission.

## Detailed Flow Comparison

### Git Flow Steps

```bash
# 1. Validate state
git status  # Check for uncommitted changes
git rev-parse --abbrev-ref HEAD  # Ensure on branch (not detached)

# 2. Push branch
git push -u origin HEAD

# 3. Create or update PR
gh pr create --fill || gh pr edit --add-label "ai-generated"

# 4. Generate PR content (AI)
# (Extract diff, call Claude CLI)

# 5. Update PR metadata
gh pr edit <number> --title "..." --body "..."
```

**Total Operations**: ~5 steps, no squashing or rebasing

### Graphite Flow Steps

```bash
# 1. Preflight: Auth checks
gh auth status
gt auth status

# 2. Preflight: Squash commits (if multiple)
git rebase -i HEAD~N  # Squash to single commit

# 3. Preflight: Submit with restack
gt submit --publish --restack
# This internally does:
#   - Rebase stack
#   - Push to remote
#   - Create PR

# 4. Preflight: Extract diff
git diff <parent> HEAD

# 5. AI: Generate commit message
# (Call Claude CLI with diff)

# 6. Finalize: Update PR metadata
gh pr edit <number> --title "..." --body "..."

# 7. Finalize: Clean up temp files
rm -f /tmp/diff-*.txt
```

**Total Operations**: ~7 steps, includes squashing and restacking

## Migration Path

### From Git to Graphite

If you start with Git flow and want to adopt Graphite:

1. Install Graphite CLI (`gt`)
2. Initialize Graphite in repo: `gt repo init`
3. Authenticate: `gt auth --token <github_token>`
4. Start using `/gt:pr-submit` for new PRs

**Compatibility**: Existing PRs created with Git flow continue to work. Graphite only manages PRs created with `gt submit`.

### From Graphite to Git

If you want to simplify and drop Graphite:

1. Continue using `/git:pr-push` for new PRs
2. Existing Graphite stacks remain managed by Graphite
3. No migration needed - both workflows coexist

## Architecture Principles

### Consolidation (Both Flows)

Both workflows follow the **Preflight → AI → Finalize** pattern:

- **Preflight**: Validate and execute git operations
- **AI**: Generate PR content from diff
- **Finalize**: Apply AI-generated metadata to PR

See [Two-Phase Operations](two-phase-operations.md) for details.

### Python Orchestration (Both Flows)

Both workflows are **Python-first**:

- CLI commands in `src/erk/cli/commands/pr/`
- Slash commands delegate to CLI (don't orchestrate git directly)
- Agent code focuses on user interaction, not git operations

**Why Python?**
- Testable with Fake implementations
- Lower token cost than bash orchestration
- Structured error handling (Result types)
- Type-safe interfaces (Git ABC, GitHub ABC)

## Common Pitfalls

### Using Wrong Flow

❌ **Wrong**: Using Graphite flow for simple fixes
```bash
/gt:pr-submit "Fix typo"  # Overkill for documentation fix
```

✅ **Right**: Use Git flow for simple changes
```bash
/git:pr-push "Fix typo"  # Fast and preserves commits
```

❌ **Wrong**: Using Git flow for stacked PRs
```bash
/git:pr-push "Add feature X (depends on PR #123)"
# No stack awareness - rebasing manually is error-prone
```

✅ **Right**: Use Graphite flow for stacks
```bash
/gt:pr-submit "Add feature X"  # Auto-rebases stack
```

### Mixing Workflows in Same Stack

❌ **Wrong**: Mix Git and Graphite in same stack
```bash
# PR #1 created with gt submit
/gt:pr-submit "Add auth"

# PR #2 depends on #1, but uses git push
/git:pr-push "Add login UI"  # Stack relationship broken
```

✅ **Right**: Consistent workflow per stack
```bash
# Both PRs use Graphite
/gt:pr-submit "Add auth"
/gt:pr-submit "Add login UI"  # Stack maintained
```

## Performance Considerations

### Git Flow Performance

- **Fast**: ~2-5 seconds (push + PR create)
- **Predictable**: No rebase conflicts
- **Scalable**: Works with any branch structure

### Graphite Flow Performance

- **Slower**: ~10-30 seconds (squash + rebase + submit)
- **Variable**: Rebase conflicts add time
- **Stack Size**: Performance degrades with large stacks (10+ PRs)

**Optimization**: Use `gt submit --no-verify` to skip hooks (if safe).

## Related Documentation

- [Two-Phase Operations](two-phase-operations.md) - Preflight → AI → Finalize pattern
- [Erk Architecture Patterns](erk-architecture.md) - Dependency injection, dry-run
- [Result Pattern](result-pattern.md) - Structured result types
- [Subprocess Wrappers](subprocess-wrappers.md) - Safe subprocess execution
