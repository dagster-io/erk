---
title: CI Iteration Pattern with devrun Agent
read_when:
  - "running CI commands in workflows"
  - "delegating pytest, ty, ruff commands"
  - "understanding devrun agent restrictions"
tripwires:
  - action: "asking devrun agent to fix errors"
    warning: "devrun is READ-ONLY. Never prompt with 'fix errors' or 'make tests pass'. Use pattern: 'Run command and report results', then parent agent fixes based on output."
---

# CI Iteration Pattern with devrun Agent

Proper delegation pattern for running CI commands via the devrun agent.

## Table of Contents

- [Core Pattern: Run-Report-Fix-Verify](#core-pattern-run-report-fix-verify)
- [devrun Agent Restrictions](#devrun-agent-restrictions)
- [Forbidden Prompts](#forbidden-prompts)
- [Required Prompt Pattern](#required-prompt-pattern)
- [Example: Prettier Formatting](#example-prettier-formatting)
- [Example: Test Failures](#example-test-failures)

---

## Core Pattern: Run-Report-Fix-Verify

The CI iteration pattern has four phases:

### 1. Run (via devrun)

Delegate command execution to devrun agent:

```
Use devrun agent to run: pytest tests/
```

### 2. Report (devrun returns)

devrun reports command output without modifying files:

```
Test failures:
- test_foo.py::test_bar - AssertionError: expected 5, got 3
- test_baz.py::test_qux - TypeError: missing argument 'name'
```

### 3. Fix (parent agent)

Parent agent (you) analyzes output and fixes code:

```
Fixing test_bar: Update calculation in foo.py line 45
Fixing test_qux: Add 'name' parameter to function call
```

### 4. Verify (via devrun)

Run devrun again to confirm fixes:

```
Use devrun agent to verify: pytest tests/
```

**Key principle:** devrun never modifies files. Parent agent always fixes.

---

## devrun Agent Restrictions

### What devrun Can Do

- **Run commands:** pytest, ty, ruff, prettier, make, gt
- **Parse output:** Extract errors, warnings, test failures
- **Report results:** Return structured output to parent agent

### What devrun Cannot Do

- **Modify files:** No writing, editing, or creating files
- **Fix errors:** No auto-correction of lint issues or test failures
- **Make decisions:** No choosing which fix to apply

### Why READ-ONLY?

devrun is optimized for:

- **Fast execution:** No context loading for file editing
- **Reliable reporting:** Consistent command output parsing
- **Separation of concerns:** Testing vs. fixing are separate operations

---

## Forbidden Prompts

These prompts violate devrun's READ-ONLY contract:

### ❌ "Fix any errors that arise"

```
Use devrun agent to run pytest and fix any errors that arise.
```

**Problem:** Implies devrun should modify files to fix errors.

### ❌ "Make the tests pass"

```
Use devrun agent to make the tests pass.
```

**Problem:** Requires modifying code, which devrun cannot do.

### ❌ "Fix lint issues"

```
Use devrun agent to run ruff and fix lint issues.
```

**Problem:** Fixing requires file edits.

### ❌ "Auto-format the code"

```
Use devrun agent to auto-format with prettier.
```

**Problem:** Formatting modifies files (though this is read-only operation for prettier --check).

---

## Required Prompt Pattern

Use these prompt patterns that respect devrun's READ-ONLY nature:

### ✅ "Run and report results"

```
Use devrun agent to run pytest tests/ and report results.
```

**Correct:** Just execute command, return output.

### ✅ "Execute and parse output"

```
Use devrun agent to execute `ty check` and parse output for type errors.
```

**Correct:** Run command, extract errors, report to parent.

### ✅ "Run checks and list failures"

```
Use devrun agent to run `make fast-ci` and list all failures.
```

**Correct:** Execute, collect failures, return list.

### ✅ "Verify changes"

```
After fixing errors, use devrun agent to verify with: pytest tests/
```

**Correct:** Re-run after parent agent fixes.

---

## Example: Prettier Formatting

### Scenario

Markdown files need formatting after edits.

### ❌ Wrong Approach

```
Use devrun agent to format all markdown files with prettier.
```

**Problem:** Implies devrun should run `prettier --write` (modifies files).

### ✅ Correct Approach

#### Step 1: Parent Agent Formats

```
I'll format the markdown files first.

Use devrun agent to run: make prettier
```

`make prettier` target runs `prettier --write` on markdown files.

#### Step 2: devrun Executes

devrun runs `make prettier`, files are formatted, reports success.

#### Step 3: Parent Agent Verifies

```
Use devrun agent to verify formatting: prettier --check docs/**/*.md
```

devrun runs check-only mode, reports if formatting is correct.

### Key Insight

`make prettier` is a **write operation**, but it's invoked by devrun as a command.

devrun doesn't directly modify files; it runs the `make` command which modifies files.

This is acceptable because:

- devrun is still just executing commands
- The command itself (make/prettier) does the modification
- devrun remains a command executor, not a file editor

---

## Example: Test Failures

### Scenario

Tests are failing after implementation.

### ❌ Wrong Approach

```
Use devrun agent to run pytest and fix any failures.
```

**Problem:** Asks devrun to fix (modify code).

### ✅ Correct Approach

#### Step 1: Run Tests (via devrun)

```
Use devrun agent to run: pytest tests/unit/
```

#### Step 2: devrun Reports

```
2 failed:
- test_parse_session_file_path: AssertionError (line 45)
- test_get_session_metadata: KeyError 'session_id' (line 78)
```

#### Step 3: Parent Agent Analyzes

```
Analyzing failures:
1. test_parse_session_file_path expects return type SessionFilePath,
   but function returns dict. Fix: Update return statement.
2. test_get_session_metadata expects 'session_id' key,
   but metadata uses 'id'. Fix: Change key name.
```

#### Step 4: Parent Agent Fixes

```
Fixing parse_session_file_path in src/erk/session.py:
- Line 45: return SessionFilePath(session_id=..., part_number=...)

Fixing get_session_metadata in src/erk/session.py:
- Line 67: metadata['session_id'] (was: metadata['id'])
```

#### Step 5: Verify (via devrun)

```
Use devrun agent to verify: pytest tests/unit/
```

#### Step 6: devrun Confirms

```
All tests passed.
```

---

## Reference: ci-iteration Skill

The `ci-iteration` skill encodes this pattern for reuse.

**Location:** `.claude/skills/ci-iteration/`

**When to load:** Before running CI commands in iterative workflows

**What it provides:**

- Run-Report-Fix-Verify pattern
- devrun prompt templates
- Forbidden vs. allowed patterns

---

## Integration with Slash Commands

### `/local:fast-ci`

Uses devrun agent to run unit tests iteratively:

```bash
/local:fast-ci
```

**Pattern:**

1. devrun runs `pytest tests/unit/`
2. devrun reports failures
3. Parent agent fixes failures
4. devrun re-runs tests
5. Loop until all pass

### `/local:py-fast-ci`

Python-only variant:

```bash
/local:py-fast-ci
```

**Pattern:** Same as fast-ci, plus lint/format checks with devrun.

### `/local:all-ci`

Full CI including integration tests:

```bash
/local:all-ci
```

**Pattern:** Iterates through unit, integration, lint, format, type checks via devrun.

---

## Summary: Delegation Contract

| Responsibility | devrun Agent             | Parent Agent           |
| -------------- | ------------------------ | ---------------------- |
| Run commands   | ✅ Execute pytest/ty/etc | ❌ No direct execution |
| Parse output   | ✅ Extract errors        | ✅ Analyze errors      |
| Report results | ✅ Return structured     | ❌ No reporting        |
| Modify files   | ❌ READ-ONLY             | ✅ Edit/Write files    |
| Fix errors     | ❌ No fixing             | ✅ Fix based on output |
| Verify fixes   | ✅ Re-run commands       | ❌ No verification     |

---

## Related Documentation

- [Markdown Formatting in CI](markdown-formatting.md) - Prettier workflow for markdown files
- [Plan Implement CI Customization](plan-implement-customization.md) - Post-implementation CI hooks
- [devrun Agent](../../.claude/agents/devrun.md) - Agent specification
