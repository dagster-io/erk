# Documentation Plan: Add tmux session persistence to codespace commands

## Context

This PR introduces tmux session persistence for erk's codespace commands, solving a critical reliability problem: network disconnects previously killed remote processes, forcing users to restart long-running operations from scratch. Now, commands like `erk codespace connect --tmux` and `erk codespace run objective plan` wrap remote execution in tmux sessions that survive disconnects and allow transparent reattachment.

The implementation introduces several cross-cutting patterns: TTY-based session naming for per-terminal isolation, session name sanitization for shell safety, smart bootstrap placement (outside tmux for fast reconnects), and TERM environment variable handling for terminal compatibility. These patterns affect multiple codespace commands and establish conventions for future persistent session features.

Documentation matters because the patterns here are non-obvious: setting `TERM=xterm-256color` before tmux prevents cryptic terminal errors, placing bootstrap outside tmux is a performance optimization that isn't immediately apparent, and session name sanitization prevents shell escaping issues that could manifest silently. Future developers adding codespace features need to understand these conventions, and users need to understand the new reconnection semantics.

## Raw Materials

PR #8239

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 18 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 2 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. TERM=xterm-256color for remote tmux

**Location:** `docs/learned/integrations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session 6a0f17b8 (prevention insight)

**Draft Content:**

```markdown
## TERM Environment Variable for Remote tmux

**Trigger:** When launching tmux via SSH in codespace or remote environments

**Warning:** Always set `TERM=xterm-256color` before tmux invocation to avoid "missing or unsuitable terminal" errors when the local terminal type isn't known remotely.

**Problem:** Modern terminals (ghostty, wezterm, kitty) have TERM values like `xterm-ghostty` that remote environments lack terminfo for. tmux fails with cryptic errors like `missing or unsuitable terminal: xterm-ghostty`.

**Prevention:** Prefix tmux invocation with `TERM=xterm-256color`. See `src/erk/core/codespace_run.py` and `src/erk/cli/commands/codespace/connect_cmd.py` for implementation.
```

---

#### 2. Core tmux persistence pattern

**Location:** `docs/learned/integrations/codespace-tmux-persistence.md`
**Action:** CREATE
**Source:** [Impl] Diff Analysis, Session 858755df

**Draft Content:**

```markdown
---
read-when:
  - adding tmux persistence to codespace commands
  - implementing persistent remote sessions
  - working with codespace command composition
category: integrations
---

# Codespace tmux Session Persistence

This document covers the tmux session persistence pattern used in erk's codespace commands for network-resilient remote execution.

## Overview

tmux persistence enables commands to survive network disconnects. Re-running the same command reattaches to the active session instead of starting a new one.

## Core Integration Point

The `build_codespace_tmux_command()` function in `src/erk/core/codespace_run.py` composes tmux wrapping with existing SSH commands. It handles:

- Session naming (deterministic or TTY-derived)
- Session name sanitization for shell safety
- TERM override for terminal compatibility
- Bootstrap placement (outside tmux for fast reconnects)

## Session Naming Strategies

### Deterministic Names (Plan Runs)

For commands with stable identifiers, use deterministic names like `plan-{issue}`. This enables reconnection from any terminal.

### TTY-Derived Names (Interactive)

For interactive sessions, derive names from TTY path via `_tty_session_name()` in `src/erk/cli/commands/codespace/connect_cmd.py`. This provides per-terminal isolation without bookkeeping.

## Session Name Sanitization

All session names must be sanitized before use. See `_sanitize_tmux_session_name()` in `src/erk/core/codespace_run.py`. The function converts special characters to hyphens, lowercases, and strips leading/trailing hyphens.

## Bootstrap Placement

Bootstrap operations (git pull, uv sync, venv activation) run OUTSIDE tmux sessions. This ensures reconnects are instant (no re-bootstrap). The bootstrap completes before `tmux new-session -A` invocation.

## When to Use tmux Wrapping

Use `build_codespace_tmux_command()` for:
- Commands taking >10 seconds
- User-interactive commands
- Plan execution runs

Use direct `build_codespace_ssh_command()` for:
- Quick status checks
- List operations
- Commands completing in seconds
```

---

#### 3. Modified behavior: plan runs now use tmux

**Location:** `docs/learned/planning/codespace-plan-runs.md`
**Action:** CREATE
**Source:** [Impl] Diff Analysis, Session 858755df

**Draft Content:**

```markdown
---
read-when:
  - running plans in codespaces
  - understanding codespace plan execution
  - debugging plan run disconnects
category: planning
---

# Codespace Plan Runs and tmux Persistence

Plan runs in codespaces now automatically use tmux session persistence.

## Behavior Change

All `erk codespace run objective plan` invocations wrap the remote command in a tmux session with a deterministic name: `plan-{issue_ref}`.

## Reconnection Workflow

1. First run creates session and starts planning
2. If network disconnects, SSH terminates but tmux session continues
3. Re-running the same command reattaches to active session
4. Planning continues from where it left off

## Implementation

See `src/erk/cli/commands/codespace/run/objective/plan_cmd.py` for the `build_codespace_tmux_command()` invocation with `session_name=f"plan-{issue_ref}"`.

## User Experience

Users see the session name in connection output. The `tmux new-session -A` pattern transparently creates or attaches based on session state.
```

---

#### 4. Devcontainer package installation pattern

**Location:** `docs/learned/ci/devcontainer-dependencies.md`
**Action:** CREATE
**Source:** [Impl] Session 6a0f17b8 (user correction)

**Draft Content:**

```markdown
---
read-when:
  - adding system dependencies to codespaces
  - setting up devcontainer packages
  - choosing runtime vs baked dependencies
category: ci
---

# Devcontainer Dependency Installation

When adding system dependencies to codespaces, prefer baking them into the devcontainer definition over runtime installation.

## Guidance

**Prefer `postCreateCommand`:** Add packages to `.devcontainer/devcontainer.json` `postCreateCommand` to bake them into codespace creation. This makes dependencies permanent and eliminates runtime installation latency.

**Avoid runtime installation:** Runtime bootstrap (install on connect) adds latency on every connection and introduces fragility. It's acceptable for optional tools but not required dependencies.

## Example

When tmux was needed for session persistence, it was added to `postCreateCommand`:

```json
"postCreateCommand": "sudo apt-get update && sudo apt-get install -y tmux"
```

This runs once during codespace creation, not on every connection.

## Key Learning

When working with codespaces/devcontainers, always consider baking dependencies into the container definition before suggesting runtime installation. Runtime installation adds latency and fragility; devcontainer changes are one-time and permanent.
```

---

#### 5. CLI options: --tmux and --session

**Location:** `docs/learned/cli/codespace-connect.md`
**Action:** CREATE
**Source:** [Impl] Diff Analysis, Session 858755df-part1

**Draft Content:**

```markdown
---
read-when:
  - using erk codespace connect
  - configuring tmux persistence for interactive sessions
  - understanding codespace session naming
category: cli
---

# erk codespace connect Options

The `erk codespace connect` command supports optional tmux session persistence via `--tmux` and `--session` flags.

## Options

### --tmux / -t

Enables tmux session persistence. The session name is derived from your terminal's TTY path, providing per-terminal isolation without explicit naming.

### --session NAME

Explicitly names the tmux session. Implies `--tmux`. Use this to:
- Share a session across multiple terminals
- Resume a known session by name
- Override TTY-derived naming

## TTY-Based Session Naming

When using `--tmux` without `--session`, the session name is derived from `os.ttyname(0)`. This transforms paths like `/dev/ttys003` (macOS) or `/dev/pts/3` (Linux) into session names like `claude-ttys003` or `claude-pts-3`.

This provides zero-bookkeeping per-terminal isolation: different terminal tabs get different sessions automatically.

## User Transparency

Connection output shows the session name:
```
Connecting to codespace 'mybox' (tmux session: claude-ttys003)...
```

## Interaction with --shell

The `--shell` option disables tmux wrapping regardless of `--tmux` flag. Shell mode is for debug access where tmux would interfere.

## Fallback Behavior

If not connected to a TTY (pipes, CI, background processes), `_tty_session_name()` falls back to `"claude-session"` rather than raising an error.
```

---

### MEDIUM Priority

#### 6. Sanitize tmux session names tripwire

**Location:** `docs/learned/integrations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Diff Analysis

**Draft Content:**

```markdown
## tmux Session Name Sanitization

**Trigger:** When using dynamic strings (issue numbers, branch names, URLs) as tmux session names

**Warning:** Always sanitize with the pattern from `_sanitize_tmux_session_name()` to prevent shell escaping issues. Convert special characters to hyphens, lowercase, and collapse/strip leading/trailing hyphens.

**Problem:** Unsanitized strings can contain characters that break shell quoting or tmux session name restrictions. For example, `plan/42_foo.bar` should become `plan-42-foo-bar`.

**Prevention:** Use `_sanitize_tmux_session_name()` from `src/erk/core/codespace_run.py` for all session names derived from dynamic input.
```

---

#### 7. TTY-based session naming pattern

**Location:** `docs/learned/cli/codespace-connect.md` (section)
**Action:** Already covered in item #5
**Source:** [Impl] Diff Analysis, Session 858755df-part1

---

#### 8. Bootstrap placement outside tmux

**Location:** `docs/learned/integrations/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Diff Analysis

**Draft Content:**

```markdown
## Bootstrap Placement for Persistent Sessions

**Trigger:** When adding persistent session features to codespace commands

**Warning:** Place bootstrap operations (git pull, uv sync, venv activation) OUTSIDE tmux sessions so reconnects are fast.

**Problem:** If bootstrap runs inside tmux, every reconnect re-runs the bootstrap, adding 5-30 seconds to session resumption.

**Prevention:** Structure commands so bootstrap completes before `tmux new-session -A`. See `src/erk/core/codespace_run.py` for the pattern.
```

---

#### 9. CLI flag dependencies pattern

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session 858755df-part2

**Draft Content:**

```markdown
## Cascading CLI Flag Dependencies

**Trigger:** When implementing CLI flags where one logically requires another

**Warning:** Implement the dependency implicitly rather than erroring. For example, `--session` implies `--tmux` automatically.

**Pattern:** Check if the higher-level flag is set and enable the dependency flag transparently. Test the cascading behavior explicitly.

**Example:** In `erk codespace connect`, using `--session myname` automatically enables tmux wrapping without requiring `--tmux --session myname`.
```

---

#### 10. Update composable-remote-commands

**Location:** `docs/learned/architecture/composable-remote-commands.md`
**Action:** UPDATE
**Source:** [Impl] Existing Docs Check

**Draft Content:**

Add to existing doc:

```markdown
## Step 3 Extension: tmux Wrapping

When building remote commands for long-running or interactive operations, consider wrapping with `build_codespace_tmux_command()` from `src/erk/core/codespace_run.py`.

This adds a tmux session layer that enables:
- Network disconnect resilience
- Session reattachment via `tmux new-session -A -s NAME`
- Deterministic or TTY-derived session naming

See `docs/learned/integrations/codespace-tmux-persistence.md` for the full pattern.
```

---

#### 11. Update codespace-remote-execution

**Location:** `docs/learned/erk/codespace-remote-execution.md`
**Action:** UPDATE
**Source:** [Impl] Existing Docs Check

**Draft Content:**

Add section:

```markdown
## tmux-Wrapped Bootstrap Variant

For operations requiring network resilience, the bootstrap sequence can be wrapped in tmux:

1. Bootstrap runs outside tmux (fast reconnects)
2. `tmux new-session -A -s SESSION_NAME` creates or attaches
3. Wrapped command executes inside tmux

This pattern is used by `erk codespace run objective plan` and optional via `--tmux` in `erk codespace connect`.

See `docs/learned/integrations/codespace-tmux-persistence.md` for implementation details.
```

---

### LOW Priority

#### 12. OSError fallback pattern for TTY operations

**Location:** `docs/learned/cli/codespace-connect.md` (covered in item #5)
**Action:** Already covered
**Source:** [Impl] Session 858755df-part1

---

#### 13. Opt-in feature rollout pattern

**Location:** `docs/learned/cli/codespace-patterns.md`
**Action:** CREATE
**Source:** [Impl] Session 858755df-part1

**Draft Content:**

```markdown
---
read-when:
  - adding new codespace features
  - deciding between opt-in and default-on behavior
category: cli
---

# Codespace Feature Rollout Patterns

## Opt-in Before Default

When adding significant behavior changes to codespace commands, consider making them opt-in via a flag before enabling by default. This allows:

- User testing and feedback collection
- Gradual rollout without breaking workflows
- Documentation of the feature before it becomes standard

## Example: tmux Persistence

The `--tmux` flag on `erk codespace connect` was made opt-in rather than default. Users who want session persistence enable it explicitly. This can become the default after sufficient testing.

## User Transparency

When auto-detecting behavior (like TTY-based session naming), always log what was detected:

```
Connecting to codespace 'mybox' (tmux session: claude-ttys003)...
```

This builds trust by showing users what the tool decided on their behalf.
```

---

#### 14. User transparency via logging pattern

**Location:** Covered in items #5 and #13
**Action:** Already covered
**Source:** [Impl] Session 858755df-part1

---

#### 15. Testing default behavior changes tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add tripwire)
**Source:** [Impl] Session 858755df-part2

**Draft Content:**

```markdown
## Testing Default Behavior Changes

**Trigger:** When inverting default behavior (opt-in to opt-out or vice versa)

**Warning:** Ensure test coverage includes: (1) new default behavior, (2) explicit opt-in/opt-out, (3) any cascading implications from other flags.

**Example:** When tmux was changed from default to opt-in, tests needed to verify:
- Default behavior: no tmux in remote command
- With `--tmux`: tmux wrapping present
- With `--session`: tmux wrapping present (cascading implication)
```

---

#### 16. Testing tmux presence/absence in commands

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE (add pattern)
**Source:** [Impl] Diff Analysis

**Draft Content:**

```markdown
## Testing tmux in Codespace Commands

**Pattern:** Commands that should use tmux persistence must assert `"tmux new-session -A -s"` in the remote command. Commands that shouldn't (like `--shell`) must assert `"tmux" not in remote_command`.

**Source:** See `tests/unit/cli/commands/codespace/test_connect_cmd.py` for examples of both positive and negative assertions.
```

---

#### 17. Session cleanup guidance

**Location:** `docs/learned/integrations/codespace-tmux-persistence.md` (section)
**Action:** CREATE (as section in item #2)
**Source:** [Impl] Diff Analysis

**Draft Content:**

Add section to codespace-tmux-persistence.md:

```markdown
## Session Cleanup

Long-lived codespaces accumulate tmux sessions over time.

### Listing Sessions

```bash
# Inside codespace
tmux ls
```

### Killing Sessions

```bash
# Kill specific session
tmux kill-session -t session-name

# Kill all sessions
tmux kill-server
```

### Session Lifecycle

Sessions persist until:
- Explicitly killed
- Codespace is stopped/rebuilt
- All processes in session exit
```

---

#### 18. Workflow examples

**Location:** `docs/learned/cli/codespace-connect.md` (section)
**Action:** Add to item #5
**Source:** [Impl] Diff Analysis

**Draft Content:**

Add section:

```markdown
## Workflow Examples

### Planning Workflow (Automatic tmux)

```bash
# First run: creates session, starts planning
$ erk codespace run objective plan 42

# Network drops, SSH disconnects, but tmux continues

# Reconnect: reattaches to session 'plan-42'
$ erk codespace run objective plan 42
```

### Interactive Coding (Explicit tmux)

```bash
# Enable tmux with TTY-derived session name
$ erk codespace connect --tmux

# Network drops

# Same terminal reattaches to same session
$ erk codespace connect --tmux
```

### Shared Session (Explicit Name)

```bash
# Terminal 1: Create named session
$ erk codespace connect --session shared

# Terminal 2: Attach to same session
$ erk codespace connect --session shared
```
```

---

## Contradiction Resolutions

None detected. Existing documentation is clean with no conflicts.

## Stale Documentation Cleanup

None detected. All existing referenced documentation has valid paths.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing or unsuitable terminal error

**What happened:** Running tmux via SSH produced `missing or unsuitable terminal: xterm-ghostty`

**Root cause:** Local terminal (ghostty) has a TERM value that remote codespace lacks terminfo for. tmux requires valid terminfo to function.

**Prevention:** Always set `TERM=xterm-256color` before tmux invocation when SSH-ing from local terminal to remote environment.

**Recommendation:** TRIPWIRE (already documented as item #1)

### 2. tmux command not found in codespace

**What happened:** First tmux invocation failed with `bash: line 1: tmux: command not found`

**Root cause:** tmux was not installed in the codespace image by default.

**Prevention:** Add system dependencies to `.devcontainer/devcontainer.json` `postCreateCommand` to bake them into codespace creation. Don't assume standard tools exist.

**Recommendation:** ADD_TO_DOC (documented in item #4)

### 3. Package has no installation candidate

**What happened:** Manual `apt-get install tmux` failed with no installation candidate error.

**Root cause:** apt package index was stale (no prior `apt-get update`).

**Prevention:** Always run `apt-get update` before `apt-get install`. Already handled in devcontainer fix which runs both commands.

**Recommendation:** CONTEXT_ONLY (covered by existing subprocess documentation)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. TERM=xterm-256color for remote tmux

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before launching tmux via SSH in codespace or remote environments
**Warning:** Always set `TERM=xterm-256color` before tmux invocation to avoid "missing or unsuitable terminal" errors when local terminal type isn't known remotely.
**Target doc:** `docs/learned/integrations/tripwires.md`

This tripwire is essential because the error message (`missing or unsuitable terminal: xterm-ghostty`) doesn't obviously suggest the fix (override TERM), and the issue affects any modern terminal connecting to any remote environment lacking updated terminfo. The user encountered this directly during implementation and it blocked progress until diagnosed.

### 2. Sanitize tmux session names

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** Before using dynamic strings (issue numbers, branch names, URLs) as tmux session names
**Warning:** Always sanitize with the pattern from `_sanitize_tmux_session_name()` to prevent shell escaping issues.
**Target doc:** `docs/learned/integrations/tripwires.md`

This tripwire prevents shell injection and tmux session name restriction violations that could manifest silently or with cryptic errors. Any future command using dynamic identifiers as session names needs to follow this pattern.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Bootstrap placement outside tmux

**Score:** 3/10 (Cross-cutting +2, Non-obvious +1)
**Notes:** This is an optimization pattern rather than a correctness issue. Placing bootstrap inside tmux doesn't break anything, it just makes reconnects slow. If reconnect performance becomes a user-reported issue, consider promoting to tripwire.

### 2. CLI flag dependencies (--session implies --tmux)

**Score:** 3/10 (Cross-cutting +2, Repeated pattern potential +1)
**Notes:** This is a UX design pattern rather than an error-prevention pattern. It could apply to other commands with cascading options, but the consequences of not following it are suboptimal UX rather than bugs or failures. Consider promoting if more commands adopt similar flag dependencies.
