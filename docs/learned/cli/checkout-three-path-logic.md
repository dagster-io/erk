---
title: Checkout Three-Path Logic
category: cli
read_when:
  - "modifying erk br co"
  - "working with --for-plan flag"
  - "changing slot allocation behavior"
last_audited: "2026-03-05 00:00 PT"
audit_result: clean
---

# Checkout Three-Path Logic

`erk br co` uses a three-path decision tree when `--for-plan` is involved, implemented in `branch/checkout_cmd.py:614-717`.

## Decision Tree

### Path 1: Stack in Place (`current_assignment is not None`)

The user is in a slot-assigned worktree and the branch has a current assignment.

- Updates assignment to new tip
- Calls `_rebase_and_track_for_plan()` if setup exists
- Calls `_setup_impl_for_plan()` if setup exists
- Calls `_perform_checkout()` with `force_script_activation=True`
- Returns early

### Path 2: Checkout in Current Worktree (`setup is not None and not new_slot`)

The user passed `--for-plan` (so `setup is not None`) but did NOT pass `--new-slot`.

- Checks out in current (root) worktree
- Calls `_rebase_and_track_for_plan()` if setup exists
- Calls `_setup_impl_for_plan()` if setup exists
- Calls `_perform_checkout()` with `force_script_activation=True`
- Returns early

### Path 3: Allocate New Slot (else)

Neither condition matched — allocate a new slot for the branch.

- Calls `allocate_slot_for_branch()`
- Tracks `is_newly_created` status
- Outputs success message if newly created

## Guard Explanation

The two guards:

- `setup is not None` = user passed `--for-plan` (the plan setup configuration is populated)
- `not new_slot` = user did NOT pass `--new-slot` (prefers staying in current worktree)

## Shared Behavior

Paths 1 and 2 call `_rebase_and_track_for_plan()` and `_setup_impl_for_plan()` when `setup` is provided, and use `force_script_activation=True` to ensure the shell navigates to the target. Path 3 uses `force_script_activation=False`.

## Related Topics

- [Same-Worktree Navigation](../erk/same-worktree-navigation.md) - Activation behavior when target is current worktree
