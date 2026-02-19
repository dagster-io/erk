---
title: CommandExecutor Gateway
read_when:
  - "working with CommandExecutor gateway"
  - "implementing command execution in TUI"
  - "adding plan-related commands"
tripwires:
  - action: "adding a new method to CommandExecutor ABC"
    warning: "Must implement in all places: abc.py, fake.py, real.py. Accept plan_id and plan_url parameters (not issue_number/issue_url). The underlying implementation may translate to GitHub API calls using issue numbers, but the interface remains backend-agnostic."
---

# CommandExecutor Gateway

The `CommandExecutor` gateway provides methods for executing plan-related operations from the TUI.

## Method Signatures

The following methods use backend-agnostic plan terminology:

- `close_plan(*, plan_id: int, plan_url: str) -> CloseResult`
- `submit_to_queue(*, plan_id: int, plan_url: str) -> SubmitResult`

See `CommandExecutor` ABC in `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py` for full interface.

## Implementation Pattern

When implementing CommandExecutor methods:

1. Accept `plan_id` and `plan_url` parameters (not `issue_number`/`issue_url`)
2. The underlying implementation may translate to GitHub API calls using issue numbers, but the interface remains backend-agnostic
3. Update all places for each gateway: ABC, fake, real

See `docs/learned/architecture/gateway-abc-implementation.md` for the 5-place update pattern.
