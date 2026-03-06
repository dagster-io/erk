---
title: Prettier Formatting for Claude Commands
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
tripwires:
  - action: "creating .claude/ markdown commands without formatting"
    warning: "Run 'make prettier' via devrun after editing markdown. CI will either push an auto-fix commit or fail on unformatted markdown, so don't rely on CI to clean it up."
  - action: "attempting to use prettier on Python files"
    warning: "Prettier only formats markdown in erk. Python uses ruff format. See formatter-tools.md for the complete matrix."
  - action: "investigating a bot complaint about formatting"
    warning: "Prettier is the formatting authority for markdown/YAML/JSON files. If prettier --check passes locally, dismiss the bot complaint. See docs/learned/pr-operations/automated-review-handling.md."
read_when:
  - "Creating slash commands in .claude/commands/"
  - "Modifying existing .claude/ markdown files"
  - "Getting Prettier formatting errors in CI"
---

# Prettier Formatting for Claude Commands

## Why Prettier Is Scoped to Markdown

Erk uses **formatter separation by file type**:

- **Markdown** → Prettier (consistent line wrapping, list formatting, heading spacing)
- **Python** → ruff format (PEP 8 compliance, import sorting)

This separation prevents formatter conflicts and ensures each tool operates on file types it understands. Prettier cannot parse Python syntax; ruff cannot parse markdown tables.

<!-- Source: Makefile, prettier and format targets -->
<!-- Source: .github/workflows/ci.yml, fix-formatting job -->

See the `prettier` and `format` targets in the Makefile for the exact command invocations.

## The .gitignore Integration Pattern

Erk's Prettier configuration uses `--ignore-path .gitignore` instead of `.prettierignore`:

```makefile
prettier --write '**/*.md' --ignore-path .gitignore
```

**Design rationale**: Files ignored by git shouldn't need formatting (they're not committed). This keeps ignore patterns DRY and prevents developers from seeing formatting errors on build artifacts or generated files.

**Consequence**: Creating `.prettierignore` has no effect. To exclude files from Prettier, add patterns to `.gitignore`.

See [makefile-prettier-ignore-path.md](makefile-prettier-ignore-path.md) for the complete pattern and edge cases.

## CI Architecture: Markdown Formatting in `fix-formatting`

The current CI workflow treats markdown formatting as part of the single mutating `fix-formatting` job:

<!-- Source: .github/workflows/ci.yml, fix-formatting job (lines ~53-74) and format job (lines ~35-40) -->

The `fix-formatting` job runs three mutating steps in sequence: `make docs-fix`, `uv run ruff format`, and `prettier --write '**/*.md' --ignore-path .gitignore`. If any files change, it commits and pushes. The separate `format` job runs `make format-check` as a read-only Python formatting validation.

**Why this structure**:

1. **Single mutating boundary** - docs sync, Python formatting, and Prettier fixes happen in one place
2. **Cleaner validation graph** - downstream jobs either validate the already-clean commit or skip while the new run starts
3. **Less duplicated coordination** - review workflows do not need to know about markdown-fixing internals

`format` still exists as a read-only Python formatting check. Markdown is fixed earlier by `fix-formatting`, then validated indirectly by the restarted run and downstream docs checks.

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
2. **Transient artifacts weren't cleaned up** - Check for `.erk/impl-context/*.md` files that should have been deleted
3. **Manual formatting attempt** - Let prettier handle line wrapping and list indentation, don't try to match it manually

If `fix-formatting` detects markdown changes on a same-repo PR, it pushes an auto-fix commit. On `master` pushes or fork PRs, it fails instead of mutating the branch.

## Related Documentation

- [markdown-formatting.md](markdown-formatting.md) - Standard workflow for editing and formatting markdown
- [formatter-tools.md](formatter-tools.md) - Complete formatter matrix (ruff vs prettier)
- [ci-iteration.md](ci-iteration.md) - Devrun delegation pattern for iterative CI fixes
