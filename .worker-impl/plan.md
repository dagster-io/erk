# Learn Plan: Remote Objective Next-Plan Execution via GitHub Codespaces

**Source Issue:** #6396 - `[erk-plan] erk codespace run objective next-plan ISSUE_REF`

**PR:** #6408 - Add `erk codespace run objective next-plan` for remote execution

**Status:** Approved for documentation

**Raw Materials:** https://gist.github.com/schrockn/11705e7c0dfc4c4d6aa58d407c817ca0

---

## Context

Plan #6396 implemented a new command for running objective next-plan workflows remotely on GitHub Codespaces. This enables users to dispatch long-running plan creation workflows to a codespace environment, which continues executing asynchronously while the user retains control of their local environment.

**What was built:**
- New `erk codespace run objective next-plan ISSUE_REF` command with `--codespace` option
- Fire-and-forget execution model using `nohup` background dispatch
- Auto-starting stopped codespaces before SSH connection
- Shared codespace resolution helper for code reuse
- Comprehensive test coverage (13 new unit tests)
- Clean integration with existing codespace and objective workflows

**Why it matters:**
Remote execution enables longer-running objective workflows (which can take 10+ minutes) without blocking the user's CLI. Users can dispatch a plan creation and immediately return to local work while the codespace handles the heavy lifting.

---

## Documentation Plan

### Summary Statistics

| Metric | Count |
|--------|-------|
| **NEW documentation items** | 4 |
| **EXISTING documentation to UPDATE** | 2 |
| **Documentation gaps identified** | 3 |
| **Contradictions found** | 0 |
| **Tripwire-worthy patterns** | 2 |

---

## NEW Documentation Items

### 1. Codespace Remote Execution Pattern

**Type:** ARCHITECTURE

**Title:** `docs/learned/erk/codespace-remote-execution.md`

**Priority:** HIGH

**Scope:** Document the fire-and-forget remote execution pattern established in PR #6408

**Content Outline:**

- **Overview**
  - Fire-and-forget semantics: command returns immediately, execution continues on codespace
  - Use cases: long-running objective workflows, parallel processing, batch operations
  - Tradeoff: asynchronous execution vs output feedback

- **Architecture**
  - `build_codespace_run_command()` builder function
  - Shell wrapper template: `bash -l -c '...'`
  - Environment setup: git pull, uv sync, venv activation
  - Output logging: `/tmp/erk-run.log` on codespace

- **Implementation Pattern**
  - How new remote commands reuse `build_codespace_run_command()`
  - Composability: single function for all future remote erk commands
  - No duplication of environment setup

- **Examples**
  - Existing: `erk codespace run objective next-plan 42`
  - Future extension: `erk codespace run objective replan 42`
  - Pattern: call `build_codespace_run_command(cli_string)` → invoke via SSH

- **Debugging**
  - Output available in `/tmp/erk-run.log` on codespace after execution
  - SSH connection failures reported immediately
  - Codespace start failures cause non-zero exit code

- **Future Extensions**
  - How to add new remote commands (copy template, change CLI string)
  - Reusable for any erk CLI command needing remote execution

**Source Attribution:** [Plan #6396], [PR #6408], [Session Analysis]

**Why needed:** Future agents adding remote commands need this pattern template. Without documentation, they may duplicate the environment setup logic.

---

### 2. Codespace Gateway start_codespace() Method

**Type:** GATEWAY REFERENCE / TRIPWIRE

**Title:** `docs/learned/gateway/codespace-gateway.md` (NEW section or extension)

**Priority:** HIGH

**Scope:** Document the new `start_codespace()` method and its 3-place gateway pattern

**Content Outline:**

- **Gateway Overview**
  - `Codespace` ABC in `packages/erk-shared/src/erk_shared/gateway/codespace/abc.py`
  - Three implementations: abc, real, fake
  - Reason for 3-place (not 5-place): process replacement (os.execvp) doesn't benefit from dry-run/printing

- **start_codespace() Method**
  - Purpose: Ensure codespace is running before SSH operations
  - Why needed: Stopped codespaces cause SSH connection failures
  - Behavior: No-op if already running
  - Implementation: `gh codespace start -c {gh_name}` via subprocess

- **Implementation Pattern (Tripwire)**
  - **ABC:** Abstract method with docstring specifying contract
  - **Real:** `RealCodespace.start_codespace()` - subprocess call to `gh codespace start`
  - **Fake:** `FakeCodespace.start_codespace()` - tracks calls in `_started_codespaces` for test assertions

- **Integration Points**
  - Used by `erk codespace run objective next-plan` before SSH connection
  - Used before any SSH-based command that assumes running codespace

- **Testing**
  - `FakeCodespace.started_codespaces` property for test assertions
  - Enables verification: "Was this codespace started?"
  - Defensive copying to prevent external mutation of tracking list

**Source Attribution:** [Plan #6396], [PR #6408], [Session Analysis]

**Related:** See `docs/learned/architecture/gateway-abc-implementation.md` for 5-place vs 3-place pattern decision

**Why needed:** TRIPWIRE - When future agents extend the Codespace gateway with new methods, they must follow the 3-place pattern (abc, real, fake). This documents the pattern and rationale.

---

### 3. Composable Remote Commands Architecture

**Type:** ARCHITECTURE PATTERN

**Title:** `docs/learned/architecture/composable-remote-commands.md`

**Priority:** MEDIUM

**Scope:** Document how to add new remote commands that reuse the codespace execution framework

**Content Outline:**

- **Problem Solved**
  - Without pattern: every new remote command duplicates environment setup (git pull, uv sync, venv activation)
  - With pattern: single `build_codespace_run_command()` function handles all setup

- **Template for New Remote Commands**

  ```python
  # In new command file:
  from erk.core.codespace_run import build_codespace_run_command

  # Resolve codespace
  codespace = resolve_codespace(ctx.codespace_registry, name)

  # Start it
  ctx.codespace.start_codespace(codespace.gh_name)

  # Build remote command
  remote_cmd = build_codespace_run_command(f"erk objective replan {issue_ref}")

  # Execute
  exit_code = ctx.codespace.run_ssh_command(codespace.gh_name, remote_cmd)
  ```

- **Existing Example**
  - `erk codespace run objective next-plan` (PR #6408)
  - Shows full implementation pattern
  - Tests for gateway calls, SSH invocation, error handling

- **Extension Points**
  - Add new commands under `erk codespace run` group
  - Create new click command file (e.g., `replan_cmd.py`)
  - Call `build_codespace_run_command()` with your erk CLI string
  - Reuse codespace resolution and startup logic

- **Composability Benefits**
  - No duplication of setup logic
  - Consistent environment across all remote commands
  - Single source of truth for environment bootstrap

- **Future Commands**
  - `erk codespace run objective replan ISSUE_REF`
  - `erk codespace run plan next ISSUE_REF`
  - Any future remote erk operation fits this pattern

**Source Attribution:** [Plan #6396], [PR #6408], [Session Analysis]

**Why needed:** Future agents adding remote commands should reuse the architecture, not reinvent it. This documents the pattern so they know what to reuse.

---

### 4. Codespace Resolution Helper Pattern

**Type:** CODE PATTERN

**Title:** Section in `docs/learned/cli/codespace-patterns.md` (NEW)

**Priority:** MEDIUM

**Scope:** Document the `resolve_codespace()` helper and when to use it

**Content Outline:**

- **Problem Solved**
  - Duplicate logic: Looking up codespace by name or default with error messages
  - Before pattern: 15 lines of duplication in each command
  - After pattern: 1-line function call

- **The Helper**

  ```python
  def resolve_codespace(registry: CodespaceRegistry, name: str | None) -> RegisteredCodespace:
      """Resolve a codespace by name or fall back to the default."""
      # Returns RegisteredCodespace or raises SystemExit with error message
  ```

- **When to Use**
  - Any codespace command needing to accept optional `-c/--codespace` flag
  - Default to user's configured default codespace
  - Provide clear error messages when not found

- **Existing Usage**
  - `erk codespace connect` (refactored to use helper)
  - `erk codespace run objective next-plan` (uses helper)

- **Error Handling**
  - By-name not found: "Error: No codespace named '{name}' found"
  - Default not set: "Error: No default codespace set"
  - Default set but not found: "Error: Default codespace '{name}' not found"
  - Includes helpful hint: "Use 'erk codespace setup' to create one"

- **For New Commands**
  - Import `resolve_codespace`
  - Call once with registry and name from options
  - Get back `RegisteredCodespace` ready for use

**Source Attribution:** [Plan #6396], [PR #6408], [Session Analysis]

**Why needed:** Future codespace commands should reuse this helper rather than duplicating resolution logic. Documents the pattern and availability.

---

## EXISTING Documentation Updates

### 1. Update: `docs/learned/cli/objective-commands.md`

**Change:** Add new section on remote objective next-plan execution

**Section Title:** Remote Objective Execution via Codespaces

**Content:**
- Link to new `erk codespace run objective next-plan` command
- Comparison: local vs remote execution
- When to use remote: long-running workflows, parallel execution
- Command signature and options
- Output handling: fire-and-forget with logging to `/tmp/erk-run.log`
- Example: `erk codespace run objective next-plan 42`
- Debugging: how to check codespace logs

**Rationale:** Objective commands documentation should mention both local and remote variants. Currently only documents `erk objective next-plan` (local).

**Effort:** Low (2-3 paragraphs + examples)

---

### 2. Update: `docs/learned/cli/command-group-structure.md`

**Change:** Add example of extending existing command group

**Section Title:** Extending an Existing Command Group

**Content:**
- Pattern: Adding subcommands to established groups
- Existing group example: `erk run` (workflow runs)
- New subcommand: `erk run codespace` added in PR #6408
- How to extend: import parent group, use `add_command()`
- File structure: new subcommand files in `src/erk/cli/commands/run/`

**Rationale:** Documentation covers creating new groups but not extending existing ones. PR #6408 extends `erk run` group with `codespace` subcommand, establishing this pattern.

**Effort:** Low (1-2 paragraphs + code example)

---

## Documentation Gaps (NOT to be filled)

These gaps were identified but determined to be outside scope for this learn plan:

1. **Detailed Local/Remote Command Group Pattern**
   - Status: Already documented in `docs/learned/cli/local-remote-command-groups.md`
   - Gap: Plan follows pattern but doesn't extend existing local-remote groups
   - Action: None required (existing doc sufficient)

2. **SSH Command Execution Deep Dive**
   - Status: Already documented in `docs/learned/architecture/ssh-command-execution.md`
   - Gap: Plan reuses SSH patterns but doesn't add new patterns
   - Action: None required (existing doc sufficient)

3. **CodespaceRegistry Full Reference**
   - Status: Already documented in `docs/learned/gateway/codespace-registry.md`
   - Gap: Plan uses registry but doesn't extend API
   - Action: None required (existing doc sufficient)

---

## Tripwire Candidates

### Tripwire 1: Gateway ABC Extension - 3-Place Pattern

**Trigger:** When extending `Codespace` gateway with new methods

**Action:** Check `docs/learned/architecture/gateway-abc-implementation.md` for 3-place pattern checklist:
- [ ] Add abstract method to ABC with docstring
- [ ] Implement in `RealCodespace`
- [ ] Implement in `FakeCodespace` with test tracking
- [ ] Tests for new method

**Rationale:** Process-replacement gateways use 3-place pattern (not 5-place). `start_codespace()` correctly follows this.

**Severity:** HIGH

---

### Tripwire 2: New Remote Commands

**Trigger:** When adding new `erk codespace run` commands

**Action:** Check `docs/learned/erk/codespace-remote-execution.md` for pattern:
- [ ] Use `build_codespace_run_command()` for environment setup
- [ ] Call `resolve_codespace()` for name/default lookup
- [ ] Call `start_codespace()` before SSH operations
- [ ] Implement tests following `test_next_plan_cmd.py` pattern

**Rationale:** Pattern prevents duplication of environment setup across multiple remote commands.

**Severity:** MEDIUM

---

## Contradictions

**Result: NO CONTRADICTIONS FOUND**

All existing documentation is compatible with PR #6408:
- Local/Remote pattern exists and is followed
- SSH patterns exist and are reused
- Objective workflow documentation is extended, not contradicted
- Gateway patterns are correctly applied

---

## Related Existing Documentation

These documents provide context and should be cross-referenced in new documentation:

1. `docs/learned/cli/local-remote-command-groups.md` - Pattern being followed
2. `docs/learned/architecture/ssh-command-execution.md` - SSH patterns reused
3. `docs/learned/gateway/codespace-registry.md` - Registry lookup patterns
4. `docs/learned/architecture/gateway-abc-implementation.md` - 3-place pattern for new method
5. `docs/learned/cli/objective-commands.md` - To be updated with remote variant
6. `docs/learned/cli/command-group-structure.md` - To be updated with group extension example

---

## Summary

**Documentation deliverables from PR #6396/#6408:**

✅ **4 NEW documents** capturing patterns and architecture for future remote commands
✅ **2 UPDATES** to existing docs for completeness
✅ **2 TRIPWIRES** to guide future gateway extensions and remote commands
✅ **0 CONTRADICTIONS** found with existing documentation

**Impact:** Future agents adding remote commands or extending the Codespace gateway will have clear patterns and examples to follow, reducing duplication and maintaining consistency.

**Confidence:** HIGH - Documentation is grounded in working implementation with comprehensive tests

---

## Gist URL

Raw materials (preprocessed sessions, PR comments, code inventory):
https://gist.github.com/schrockn/11705e7c0dfc4c4d6aa58d407c817ca0