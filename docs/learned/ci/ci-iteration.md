---
title: CI Iteration Pattern with devrun Agent
read_when:
  - "running CI commands in workflows"
  - "delegating pytest, ty, ruff commands"
  - "understanding devrun agent restrictions"
tripwires:
  - action: "asking devrun agent to fix errors"
    warning: "devrun is READ-ONLY. Never prompt with 'fix errors' or 'make tests pass'. Use pattern: 'Run command and report results', then parent agent fixes based on output."
last_audited: "2026-02-08 15:45 PT"
audit_result: clean
---

# CI Iteration Pattern with devrun Agent

## Why devrun Exists

The devrun agent enforces a critical architectural separation: **command execution is read-only, file modification is deliberate**. This prevents agents from "fixing" code without understanding failures, which leads to copy-paste solutions and masks root causes.

Without this separation, agents fall into the auto-fix trap:
1. Run tests, see failures
2. Apply superficial fix (suppress warning, catch exception broadly)
3. Tests pass, but the underlying issue remains

devrun forces the Run-Report-Fix-Verify cycle where the parent agent must understand failures before fixing them.

## The Core Cycle: Run-Report-Fix-Verify

<!-- Source: .claude/agents/devrun.md, workflow section -->

All CI iteration follows this four-phase pattern:

1. **Run** (devrun): Execute command, no file access
2. **Report** (devrun): Parse output, return structured results
3. **Fix** (parent): Analyze failures, modify code
4. **Verify** (devrun): Re-run command, confirm resolution

The cycle repeats until all checks pass or the parent agent determines manual intervention is needed.

### Why This Matters

The parent agent **must analyze** before fixing. This prevents:

- Suppressing warnings instead of addressing causes
- Adding broad exception handlers instead of fixing bugs
- Formatting code without understanding why formatting failed
- Re-running commands hoping for different results

## devrun's Hard Constraints

<!-- Source: .claude/agents/devrun.md, tools section and FORBIDDEN patterns -->

devrun has **no Edit or Write tools** in its tool set. This is enforced by the SDK, not by prompt engineering.

### Allowed Operations

- Execute commands via Bash: `pytest`, `ty`, `ruff`, `prettier`, `make`, `gt`
- Read files to understand failures (Read, Grep, Glob)
- Write to `/tmp/*` and `.erk/scratch/*` only

### Forbidden Bash Patterns

Even though devrun has Bash access, it cannot circumvent the read-only constraint:

```bash
# All forbidden in devrun Bash calls
sed -i file.py           # in-place editing
awk -i inplace file.py   # in-place awk
> file.py                # output redirection
cat > file.py            # write via cat
cat << EOF > file.py     # heredoc to file
cp source.py dest.py     # copying project files
```

These patterns are blocked by the agent's instructions, not by the tool system.

## Prompt Patterns: Forbidden vs Required

### ❌ Forbidden Prompts

These prompts violate the read-only contract:

```
Use devrun agent to run pytest and fix any errors that arise.
Use devrun agent to make the tests pass.
Use devrun agent to run ruff and fix lint issues.
Use devrun agent to auto-format the code.
```

**Why forbidden**: All imply devrun should modify files ("fix", "make pass", "auto-format").

### ✅ Required Patterns

These prompts respect the read-only boundary:

```
Use devrun agent to run pytest tests/ and report results.
Use devrun agent to execute `ty check` and parse output for type errors.
Use devrun agent to run `make fast-ci` and list all failures.
After fixing errors, use devrun agent to verify with: pytest tests/
```

**Why correct**: Explicitly request execution and reporting, not modification.

## The Prettier Special Case

<!-- Source: .claude/commands/local/fast-ci.md, prettier section -->

The `make prettier` target runs `prettier --write`, which modifies files. But devrun can still execute it because devrun doesn't directly modify files—it executes commands that happen to modify files.

**Distinction:**

- **Forbidden**: devrun using Edit/Write tools (doesn't have them)
- **Allowed**: devrun executing `make prettier` which calls `prettier --write`

The parent agent remains responsible for deciding when to format. devrun just executes the command.

## Integration with Slash Commands

<!-- Source: .claude/commands/local/fast-ci.md, .claude/commands/local/py-fast-ci.md, .claude/commands/local/all-ci.md -->

Three slash commands encode different CI iteration strategies:

| Command            | Scope                  | Use When                               |
| ------------------ | ---------------------- | -------------------------------------- |
| `/local:fast-ci`   | Unit tests only        | Rapid development feedback             |
| `/local:py-fast-ci` | Python checks only     | Iterating on Python, skip markdown     |
| `/local:all-ci`    | Full suite + integration | Pre-submit validation                  |

All three commands:
1. Load the `ci-iteration` skill for iteration logic
2. Use devrun exclusively for all `pytest/ty/ruff/prettier/make/gt` commands
3. Track progress with TodoWrite
4. Report final status (SUCCESS or STUCK)

### Fail-Fast Phases

`/local:fast-ci` and `/local:py-fast-ci` use two-phase execution:

**Phase 1**: Run `make lint ty` (or `make lint format ty` for py-fast-ci). Stop immediately if either fails.

**Phase 2**: Only after phase 1 passes, run remaining checks.

**Why**: Linting and type errors are fast to detect and cheap to fix. Catch them before waiting for test execution.

## Decision Table: When to Use devrun

| Scenario                               | Use devrun? | Rationale                               |
| -------------------------------------- | ----------- | --------------------------------------- |
| Running pytest to find failures        | ✅ Yes       | Read-only command execution             |
| Fixing test failures                   | ❌ No        | Parent agent fixes with Edit/Write      |
| Executing `make fast-ci`               | ✅ Yes       | Compound command execution              |
| Analyzing type errors from ty output   | ✅ Yes       | Parse and report                        |
| Adding type annotations to fix errors  | ❌ No        | Parent agent modifies files             |
| Running `prettier --check`             | ✅ Yes       | Read-only check                         |
| Running `prettier --write` via make    | ✅ Yes       | Command invokes write, not agent        |
| Deciding which files need formatting   | ❌ No        | Parent agent analyzes devrun report     |

## Common Anti-Patterns

### Anti-Pattern: Asking devrun to Iterate

```
Use devrun agent to run tests and keep fixing until they pass.
```

**Problem**: devrun cannot "keep fixing" because it has no Edit tools.

**Correct**: Parent agent owns the iteration loop. devrun executes one command per invocation.

### Anti-Pattern: Batching Fixes

```
Use devrun to run all CI checks, then I'll fix everything at once.
```

**Problem**: Compound failures have dependencies. Fixing lint errors might resolve type errors.

**Correct**: Fix one category, verify, then proceed. The iteration cycle is the unit of work.

### Anti-Pattern: Trusting Auto-Fixes Blindly

```
Use devrun to run `ruff check --fix` and we're done.
```

**Problem**: Auto-fixes can introduce new issues or mask underlying problems.

**Correct**: Parent agent reviews ruff's changes after auto-fix, understands what changed and why.

## Why Not Just Run Commands Directly?

**Historical context**: Before devrun, agents would run `pytest` via Bash in the main conversation. This polluted the main context window with test output (thousands of tokens) and created temptation to "just fix it quickly" without analysis.

devrun provides:

1. **Context isolation**: Test output stays in the devrun context, summary returns to parent
2. **Tool restrictions**: Impossible to accidentally modify files during execution
3. **Consistent parsing**: devrun knows pytest/ty/ruff output formats, extracts structured errors
4. **Parallel safety**: Multiple devrun agents can run commands without conflicting file access

## Related Artifacts

- `.claude/agents/devrun.md` — Agent specification with tool restrictions
- `.claude/skills/ci-iteration/SKILL.md` — Iteration workflow and progress tracking
- `.claude/commands/local/fast-ci.md` — Fast CI command implementation
- `.claude/commands/local/py-fast-ci.md` — Python-only CI command
- `.claude/commands/local/all-ci.md` — Full CI suite command
- `Makefile` — CI target definitions (fast-ci, py-fast-ci, all-ci)
