---
audit_result: edited
last_audited: '2026-02-08'
read_when:
- Creating slash commands in .claude/commands/
- Modifying existing .claude/ markdown files
- Getting Prettier formatting errors in CI
title: Prettier Formatting for Claude Commands
tripwires:
- action: creating .claude/ markdown commands without formatting
  warning: Run 'make prettier' via devrun after editing markdown. CI runs prettier-check
    as a separate job and will fail on unformatted files.
- action: attempting to use prettier on Python files
  warning: Prettier only formats markdown in erk. Python uses ruff format. See formatter-tools.md
    for the complete matrix.
---

# Prettier Formatting for Claude Commands

## Why Prettier Is Scoped to Markdown

Erk uses **formatter separation by file type**:

- **Markdown** → Prettier (consistent line wrapping, list formatting, heading spacing)
- **Python** → ruff format (PEP 8 compliance, import sorting)

This separation prevents formatter conflicts and ensures each tool operates on file types it understands. Prettier cannot parse Python syntax; ruff cannot parse markdown tables.

<!-- Source: Makefile, prettier and format targets -->
<!-- Source: .github/workflows/ci.yml, prettier job -->

See the `prettier` and `format` targets in the Makefile for the exact command invocations.

## The .gitignore Integration Pattern

Erk's Prettier configuration uses `--ignore-path .gitignore` instead of `.prettierignore`:

```makefile
prettier --write '**/*.md' --ignore-path .gitignore
```

**Design rationale**: Files ignored by git shouldn't need formatting (they're not committed). This keeps ignore patterns DRY and prevents developers from seeing formatting errors on build artifacts or generated files.

**Consequence**: Creating `.prettierignore` has no effect. To exclude files from Prettier, add patterns to `.gitignore`.

See [makefile-prettier-ignore-path.md](makefile-prettier-ignore-path.md) for the complete pattern and edge cases.

## CI Architecture: Prettier as a Separate Job

The CI workflow runs Prettier as an independent job, not part of the Python format/lint sequence:

```yaml
jobs:
  prettier: # Independent job
    runs-on: ubuntu-latest
    steps:
      - uses: ./.github/actions/setup-prettier
      - run: prettier --check '**/*.md' --ignore-path .gitignore

  format: # Separate Python job
    runs-on: ubuntu-latest
    steps:
      - run: make format-check
```

**Why separate jobs**: Prettier and ruff have different dependencies (Node.js vs Python). Separating them allows:

1. **Parallel execution** - Both jobs run simultaneously
2. **Granular failure reporting** - Know immediately if the failure is markdown or Python
3. **Targeted autofix** - The autofix job can apply prettier fixes without touching Python formatting

The `autofix` job has permission to run `prettier --write **/*.md` when the prettier job fails, automatically fixing markdown formatting and pushing a commit.

See [autofix-job-needs.md](autofix-job-needs.md) for how the autofix job depends on formatter job results.

## The Devrun Delegation Pattern

When editing markdown in `.claude/commands/`, always format via the devrun agent:

**Correct pattern:**

1. Edit markdown with Write/Edit tools
2. Delegate formatting: `Task(subagent_type='devrun', prompt="Run make prettier and report results")`
3. Review devrun output
4. If prettier made changes, read the formatted file to see what changed

**Anti-pattern:**

- Running `Bash("make prettier")` directly from the main agent
- Attempting to manually fix prettier violations by re-editing with the Edit tool

The devrun agent isolates command execution from the main context. This prevents prettier output (which can be verbose for multi-file changes) from polluting the main conversation.

See [ci-iteration.md](ci-iteration.md) for the broader pattern of using devrun for all format/lint/test iterations.

## When Prettier Fails in CI

Prettier failures typically indicate:

1. **Markdown was edited but not formatted** - Run `make prettier` locally via devrun
2. **Transient artifacts weren't cleaned up** - Check for `.worker-impl/*.md` files that should have been deleted
3. **Manual formatting attempt** - Let prettier handle line wrapping and list indentation, don't try to match it manually

The CI prettier job output shows exactly which files have formatting violations. The autofix job will attempt to fix them automatically, but only if the PR is from the same repository (forks don't have write permissions).

## Related Documentation

- [markdown-formatting.md](markdown-formatting.md) - Standard workflow for editing and formatting markdown
- [formatter-tools.md](formatter-tools.md) - Complete formatter matrix (ruff vs prettier)
- [ci-iteration.md](ci-iteration.md) - Devrun delegation pattern for iterative CI fixes
