---
title: Gateway Decomposition Phases
read_when:
  - "understanding the gateway decomposition initiative"
  - "planning new subgateway extractions"
  - "reviewing architectural history"
tripwires:
  - action: "migrating git method calls after subgateway extraction"
    warning: "The following methods have been moved from the Git ABC to subgateways: `git.fetch_branch()` → `git.remote.fetch_branch()` (Phase 3), `git.push_to_remote()` → `git.remote.push_to_remote()` (Phase 3), `git.commit()` → `git.commit.commit()` (Phase 4), `git.stage_files()` → `git.commit.stage_files()` (Phase 4), `git.has_staged_changes()` → `git.status.has_staged_changes()` (Phase 5), `git.rebase_onto()` → `git.rebase.rebase_onto()` (Phase 6), `git.tag_exists()` → `git.tag_exists()` (Phase 7), `git.create_tag()` → `git.tag.create_tag()` (Phase 7). Calling the old API will raise `AttributeError`. Always use the subgateway property."
---

# Gateway Decomposition Phases

Historical record of the Git gateway pure facade refactoring (objective #6169).

## Why This Decomposition Happened

The Git gateway started as a monolith with ~40 methods directly on the ABC. This created three problems:

1. **Unclear boundaries** — No signal about which operations were related. `commit()` next to `fetch_branch()` next to `tag_exists()` looked equally important and equally unrelated.
2. **Large fake implementations** — `FakeGit` had to implement every method directly. When tests only needed branch operations, they still pulled in the entire Git fake infrastructure.
3. **Namespace pollution** — Adding a new method meant scanning ~40 existing methods to check for naming conflicts.

The decomposition transformed Git from a monolith into a **pure facade** — an ABC containing only property accessors to focused subgateways. Each subgateway owns a cohesive set of operations (branches, commits, tags, etc.).

**Post-decomposition:** `Git` ABC contains zero operation methods, only properties. Operations moved to 7 focused subgateways with clear ownership.

## Decomposition Strategy

The objective used **linear extraction** — one complete subgateway per PR, with full 5-layer implementation (ABC, Real, Fake, DryRun, Printing) in a single changeset. Earlier attempts at parallel extraction created merge conflicts as multiple PRs touched the same callsites.

Each phase followed identical steps:

1. Create subgateway directory with 5-layer implementation
2. Add property to Git ABC (with TYPE_CHECKING import guard)
3. Instantiate in Real/Fake, wrap in DryRun/Printing
4. Migrate all callsites to property access pattern
5. Remove methods from Git ABC

**Breaking changes over shims:** All callsites migrated directly. No backwards compatibility layer. Old API paths immediately raised `AttributeError` after removal.

## Phase Timeline

| Phase | Subgateway   | Key Operations                               | PR    | Insight                                                    |
| ----- | ------------ | -------------------------------------------- | ----- | ---------------------------------------------------------- |
| 1     | Worktree     | add, remove, list, get_root                  | —     | Established 5-layer pattern and property composition       |
| 2     | GitBranchOps | create, delete, checkout, list               | —     | Proved mutation-focused subgateways with linked fake state |
| 3     | GitRemoteOps | fetch, pull, push, get_remote_url            | #6171 | Mixed mutation/query subgateway pattern                    |
| 4     | GitCommitOps | commit, stage, amend, get_commit_message     | #6180 | Largest subgateway (8 methods), no issues                  |
| 5     | GitStatusOps | has_staged, has_uncommitted, get_file_status | #6179 | First pure-query subgateway (pass-through dry-run)         |
| 6     | GitRebaseOps | rebase_onto, rebase_continue, rebase_abort   | #6182 | Validated rebase lifecycle operations                      |
| 7     | GitTagOps    | tag_exists, create_tag, push_tag             | #6186 | Completed all mutation operations                          |
| 8     | Cleanup      | (no extraction)                              | #6285 | Removed 16 dead convenience methods from Git ABC           |

## Subgateway Behavior Variants

Subgateways fall into three dry-run categories based on their operation mix:

| Variant          | Example              | DryRun Behavior                      | Why                                                                      |
| ---------------- | -------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| Mutation-focused | GitBranchOps, GitTag | Mutations no-op or log, return mocks | Tests need to see what would happen without actually modifying git state |
| Query-only       | GitStatusOps         | Pass-through delegate                | Read-only operations have no side effects to suppress                    |
| Mixed            | GitRemoteOps, Commit | Mutations log, queries delegate      | Fetch/pull must no-op, but `get_remote_url` needs real data              |

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/status_ops/dry_run.py, DryRunGitStatusOps -->

Query-only subgateways have trivial DryRun/Printing implementations — they simply delegate all calls to the wrapped implementation since queries have no side effects.

See `DryRunGitStatusOps` in `packages/erk-shared/src/erk_shared/gateway/git/status_ops/dry_run.py` for the pass-through pattern.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py, DryRunGitBranchOps -->

Mutation-focused subgateways intercept writes and return success without executing. See `DryRunGitBranchOps` in `packages/erk-shared/src/erk_shared/gateway/git/branch_ops/dry_run.py` — mutations like `create_branch` print `[DRY RUN] Would run: git branch ...` and return `BranchCreated()` without touching git.

## Phase 8: The Convenience Method Purge

Phase 8 revealed that "remaining methods" were actually dead code. The Git ABC contained:

- **2 duplicate abstract method declarations** (defined twice in the same ABC)
- **14 convenience methods** that just forwarded to subgateways (e.g., `get_current_branch()` calling `self.branch.get_current_branch()`)

PR #6285 removed all 16 without extracting a new subgateway. The "cleanup phase" became **enforcement of pure facade pattern** — Git ABC now contains **only property accessors**, never convenience methods.

**Why remove convenience methods:**

1. **Ambiguous ownership** — Is `git.get_current_branch()` a Git operation or a Branch operation? The answer matters for fake state linking.
2. **Maintenance burden** — Convenience methods duplicate the subgateway API surface. Adding a parameter to `branch.get_current_branch()` requires updating `git.get_current_branch()` in 5 layers.
3. **False simplicity** — Convenience methods look simpler (`git.commit()` vs `git.commit.commit()`) but hide the actual ownership boundary. When debugging, knowing which subgateway owns an operation is critical.

**Periodic audit pattern:** Convenience methods creep back during development. Grep the Git ABC for methods that just call `self.subgateway.method()`, then batch-remove and migrate callsites.

## API Migration Pattern

**Before (monolithic):**

```python
git.fetch_branch(repo_root, "origin", "main")
git.commit(cwd, "feat: add feature")
git.tag_exists(repo_root, "v1.0.0")
```

**After (subgateway properties):**

```python
git.remote.fetch_branch(repo_root, "origin", "main")
git.commit.commit(cwd, "feat: add feature")
git.tag.tag_exists(repo_root, "v1.0.0")
```

The double-name in `git.commit.commit()` is intentional — `commit` is both the subgateway name and the operation name. This isn't a bug; it's clear ownership. The subgateway owns the operation, and the operation name stands alone without false simplification.

## Lessons for Future Gateway Decompositions

### What Worked

1. **Linear extraction** — One complete subgateway per PR prevented merge conflicts
2. **5-layer implementation in single PR** — Implementing all layers together prevented partial migrations
3. **Breaking changes immediately** — No shims meant fast detection of missed callsites
4. **Linked fake state pattern** — Constructor injection + `link_mutation_tracking()` proved reliable across all phases

### What Didn't Work

Early experiments tried:

- **Parallel extraction** — Multiple PRs touched the same callsites, causing conflicts
- **Incremental layer implementation** — Adding ABC then implementing layers later left the codebase in broken state between PRs
- **Backwards compatibility shims** — Convenience methods that delegated to subgateways. These just delayed migration and confused ownership.

### Pattern Reusability

The decomposition pattern applies to any large gateway:

1. Identify **coherent operation groups** (branches, commits, tags)
2. Extract **one group at a time** with full 5-layer implementation
3. Use **property access** for subgateways (not direct construction)
4. **Link fake state** via constructor + `link_mutation_tracking()`
5. **Break the API** instead of adding shims

## Related

- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) — The 5-layer implementation contract for subgateway properties
- [Gateway ABC Implementation](gateway-abc-implementation.md) — Complete checklist for implementing gateway methods across all layers
