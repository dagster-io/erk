---
title: Gateway Decomposition Phases
read_when:
  - "understanding the gateway decomposition initiative"
  - "planning new subgateway extractions"
  - "reviewing architectural history"
tripwires:
  - action: "migrating git method calls after subgateway extraction"
    warning: "The following methods have been moved from the Git ABC to subgateways: `git.fetch_branch()` → `git.remote.fetch_branch()` (Phase 3), `git.push_to_remote()` → `git.remote.push_to_remote()` (Phase 3), `git.commit()` → `git.commit.commit()` (Phase 4), `git.stage_files()` → `git.commit.stage_files()` (Phase 4), `git.has_staged_changes()` → `git.status.has_staged_changes()` (Phase 5), `git.rebase_onto()` → `git.rebase.rebase_onto()` (Phase 6), `git.tag_exists()` → `git.tag.tag_exists()` (Phase 7), `git.create_tag()` → `git.tag.create_tag()` (Phase 7). Calling the old API will raise `AttributeError`. Always use the subgateway property."
---

# Gateway Decomposition Phases

Timeline of the systematic Git gateway decomposition (#6169).

## Overview

The monolithic Git gateway originally contained all git operations. This initiative decomposed it into focused subgateways, each responsible for a cohesive set of operations.

## Phase Timeline

| Phase   | Subgateway   | Operations Extracted                                                                                      | PR        | Status   |
| ------- | ------------ | --------------------------------------------------------------------------------------------------------- | --------- | -------- |
| Phase 2 | GitBranchOps | create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch                  | (earlier) | Complete |
| Phase 3 | GitRemoteOps | fetch_branch, pull_branch, fetch_pr_ref, push_to_remote, pull_rebase, get_remote_url                      | #6171     | Complete |
| Phase 4 | GitCommitOps | stage_files, commit, add_all, amend_commit, get_commit_message, get_recent_commits, etc.                  | #6180     | Complete |
| Phase 5 | GitStatusOps | has_staged_changes, has_uncommitted_changes, get_file_status, check_merge_conflicts, get_conflicted_files | #6179     | Complete |
| Phase 6 | GitRebaseOps | rebase_onto, rebase_continue, rebase_abort, is_rebase_in_progress                                         | #6182     | Complete |
| Phase 7 | GitTagOps    | tag_exists, create_tag, push_tag                                                                          | #6186     | Complete |

## Pattern

Each phase follows the same extraction pattern:

1. Create subgateway directory with 5-layer structure (abc, real, fake, dry_run, printing)
2. Move method implementations to new files
3. Add property to parent gateway (all 5 layers)
4. Migrate callsites to new property path (e.g., `git.method()` → `git.subgateway.method()`)
5. Remove methods from parent gateway
6. Document in gateway inventory

## Subgateway Variants

| Variant          | Example                    | DryRun Behavior                   | Printing Behavior               |
| ---------------- | -------------------------- | --------------------------------- | ------------------------------- |
| Mutation-focused | GitBranchOps, GitTagOps    | No-op, return success             | Log then delegate               |
| Query-only       | GitStatusOps               | Pass-through delegate             | Pass-through delegate           |
| Mixed            | GitRemoteOps, GitCommitOps | Mutations no-op, queries delegate | Mutations log, queries delegate |

## Related

- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md)
- [Gateway Inventory](gateway-inventory.md)
- [Gateway ABC Implementation](gateway-abc-implementation.md)
