# Documentation Plan: Fix: Stream codespace run output to terminal

## Context

This plan captures documentation learnings from implementing plan #6514, which fixed a bug where running `erk codespace run objective next-plan` appeared to hang because remote output was not streaming to the terminal in real-time.

The root cause was a method selection error: the command used `run_ssh_command()` (non-interactive, returns exit code after completion) instead of `exec_ssh_interactive()` (interactive, uses `os.execvp()` for process replacement with direct terminal streaming). The fix was a single-line change that switched gateway methods, but the pattern distinction is non-obvious and affects multiple remote command implementations.

Documentation matters here because the distinction between `run_ssh_command()` and `exec_ssh_interactive()` is subtle and the consequences of choosing incorrectly are severe (output appears buffered/hung for potentially long-running interactive sessions). Future agents implementing remote commands need clear guidance on when to use each method, along with testing patterns for the NoReturn-based interactive method.

## Raw Materials

https://gist.github.com/schrockn/18e04d15aee3b044b4860a013072e481

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 5     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Process Replacement Pattern Documentation

**Location:** `docs/learned/architecture/ssh-command-execution.md`
**Action:** UPDATE
**Source:** [Impl], [PR #6515]

This documentation should enhance the existing explanation of SSH command execution with explicit guidance on choosing between `run_ssh_command()` (non-interactive, buffered) and `exec_ssh_interactive()` (interactive, process replacement). Include a decision framework showing when to use each method, with examples of both. Prominently call out that `exec_ssh_interactive()` uses `os.execvp()` - no Python code runs after the call.

#### 2. Test Pattern for Interactive Gateway Methods

**Location:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE
**Source:** [Impl], [PR #6515]

Add section documenting how to test `exec_ssh_interactive()` calls. Show the verification pattern: assert `fake_codespace.exec_called is True`, verify call details, verify `call.interactive is True`. Document the critical gotcha that no post-execution code runs; test only pre-execution state by inspecting the fake's recorded calls.

#### 3. Composable Remote Commands: Interactive Alternative

**Location:** `docs/learned/architecture/composable-remote-commands.md`
**Action:** UPDATE
**Source:** [Impl], [PR #6515]

Add subsection titled "For Interactive Commands: Using exec_ssh_interactive()" showing the simplified pattern for commands needing terminal control. Current template shows non-interactive pattern. Include comparison table distinguishing the two approaches by return type, output behavior, use cases.

### MEDIUM Priority

#### 1. Learn Pipeline Architecture

**Location:** `docs/learned/planning/learn-pipeline.md`
**Action:** CREATE
**Source:** [Impl]

Document the complete learn pipeline: session preprocessing (JSONL→XML), parallel analysis agents (session analyzer, code diff analyzer, existing docs checker), sequential synthesis agents (gap identifier, plan synthesizer), tripwire extraction. Include workflow diagram showing data flow. This enables future agents implementing similar automation.

#### 2. Skill Loading Best Practices

**Location:** `docs/learned/architecture/skill-loading.md`
**Action:** CREATE
**Source:** [Impl]

Document the pattern of pre-loading foundational skills (`fake-driven-testing`, `dignified-python`) before implementation. Explain why: early loading ensures standards apply from the start. Include: skill persistence, how to check for prior loading via command message, just-in-time context injection via hooks.

## Contradiction Resolutions

No contradictions found. The existing documentation correctly distinguishes between SSH execution methods. The bug was an implementation oversight, not a documentation gap.

## Prevention Insights

### 1. Wrong SSH Method Selection

**What happened:** The `erk codespace run objective next-plan` command used `run_ssh_command()` which buffers output, making remote Claude sessions appear to hang.

**Root cause:** The composable remote commands template shows the non-interactive pattern, and the existing implementation followed it without considering that Claude sessions need real-time terminal control.

**Prevention:** Add method selection decision framework to documentation. Make the interactive alternative pattern equally prominent.

**Recommendation:** TRIPWIRE

### 2. Test Assertion Pattern for NoReturn Methods

**What happened:** When the fix changed to `exec_ssh_interactive()`, tests needed updates to verify the correct method rather than checking exit codes (which don't exist with process replacement).

**Root cause:** Standard exit code testing doesn't apply to NoReturn methods. The test pattern differs fundamentally.

**Prevention:** Document the test verification pattern for interactive methods.

**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Missing TTY Allocation in Interactive SSH

**Score:** 5/10
**Trigger:** Before calling `run_ssh_command()` for an interactive process
**Warning:** Interactive processes require TTY allocation. Use `exec_ssh_interactive()` for commands needing real-time terminal control. The `-t` flag is only allocated by `exec_ssh_interactive()`.

### 2. Process Replacement Gotcha: No Post-Execution Code

**Score:** 4/10
**Trigger:** Before using `exec_ssh_interactive()` in a CLI command
**Warning:** Uses `os.execvp()` for process replacement. No Python code executes after this call. Do not add exit code handling or completion messages after the call.

### 3. Test Assertions for Interactive Gateway Methods

**Score:** 4/10
**Trigger:** When changing a gateway method from return-based to NoReturn-based
**Warning:** NoReturn methods require different test patterns. Verify `fake.exec_called is True` and `call.interactive is True` instead of checking exit codes.

### 4. Skill Loading Enforcement in Implementation

**Score:** 4/10
**Trigger:** Before writing implementation code without loading foundational skills
**Warning:** Load `dignified-python` and `fake-driven-testing` skills before implementation begins. Skipping leads to inconsistent code quality.
