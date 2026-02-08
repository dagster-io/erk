---
title: Markdown Formatting in CI Workflows
read_when:
  - "editing markdown files"
  - "handling Prettier CI failures"
  - "implementing documentation changes"
tripwires:
  - action: "editing markdown files in docs/"
    warning: "Run `make prettier` via devrun after markdown edits. Multi-line edits trigger Prettier failures. Never manually format - use the command."
last_audited: "2026-02-08"
audit_result: clean
---

# Markdown Formatting in CI Workflows

## Why Format Before CI

Prettier enforces deterministic markdown formatting that humans cannot replicate manually. Line wrapping rules, list spacing, heading consistency, and code fence normalization all follow complex algorithms that depend on context across the entire document.

**The workflow is always: Edit → Format → CI.** Skipping the format step guarantees a CI failure on the prettier check job.

## The Core Constraint

<!-- Source: Makefile, prettier and prettier-check targets -->
<!-- Source: .github/workflows/ci.yml, prettier job -->

CI runs `prettier --check '**/*.md'` which fails if any markdown file differs from Prettier's canonical format. See the `prettier` job in `.github/workflows/ci.yml` and the `prettier-check` target in `Makefile`.

This constraint is **deliberate**: all committed markdown must be formatted consistently. There is no escape hatch for "committed but unformatted" files.

## Standard Workflow

| Phase     | Action                           | Tool         | Why                                        |
| --------- | -------------------------------- | ------------ | ------------------------------------------ |
| 1. Edit   | Modify markdown content          | Write/Edit   | Create or update documentation             |
| 2. Format | Run `make prettier` and report   | devrun agent | Apply Prettier's formatting rules          |
| 3. CI     | Run `make fast-ci` and report    | devrun agent | Verify all checks pass                     |
| 4. Fix    | Address test/lint failures       | Parent agent | Analyze devrun output, modify files        |
| 5. Commit | Commit all changes               | Bash/git     | Push formatted, passing code               |

**Critical**: Phase 2 (Format) must happen before Phase 3 (CI). Running CI without formatting first wastes a CI cycle and forces a second iteration.

## Why Agents Cannot Format Manually

Prettier's line wrapping algorithm considers:

- Prose flow and sentence boundaries
- Link length and inline code spans
- List nesting depth and indentation
- Table column alignment
- Heading hierarchy

Attempting to replicate these rules with Edit tool calls creates subtle formatting differences that Prettier detects. The agent would need hundreds of edits to match Prettier's output—or could just run `make prettier` once.

## The devrun Delegation Pattern

<!-- Source: docs/learned/ci/ci-iteration.md, The Core Cycle section -->

The parent agent must delegate `make prettier` to devrun following the Run-Report-Fix-Verify cycle:

1. **Run** (devrun): Execute `make prettier`, which calls `prettier --write`
2. **Report** (devrun): Confirm formatting completed, note modified files
3. **Fix** (parent): Not needed—Prettier auto-formats in-place
4. **Verify** (devrun): Run `make fast-ci` to confirm prettier-check passes

Note the special case: devrun executes `prettier --write` (which modifies files), but devrun itself doesn't use Edit/Write tools. The command modifies files, not the agent. See [CI Iteration Pattern](ci-iteration.md) for why this distinction matters.

## Anti-Patterns

### ❌ Manual Line Wrapping

Counting characters and inserting line breaks manually. Prettier's wrapping considers semantic boundaries, not just character count.

### ❌ Skipping Format Step

Running `make fast-ci` immediately after editing markdown. The prettier-check will fail, forcing a second iteration.

### ❌ Using Edit to Fix Formatting

After a prettier-check failure, using Edit tool to adjust line breaks or spacing. Run `make prettier` instead—it applies all rules consistently across the file.

### ❌ Asking devrun to "Fix Formatting"

Prompting devrun with "fix any formatting errors." This violates devrun's read-only constraint. The correct prompt is "run `make prettier` and report results."

## Decision Table: Format or Manual Edit?

| Change Type                | Tool Flow                     | Rationale                                      |
| -------------------------- | ----------------------------- | ---------------------------------------------- |
| Adding paragraphs          | Edit → devrun(make prettier)  | Prose changes affect line wrapping             |
| Fixing typos (single line) | Edit → devrun(make prettier)  | Even single-line edits can shift wrapping      |
| Adding code blocks         | Edit → devrun(make prettier)  | Code fence formatting has strict rules         |
| Updating tables            | Edit → devrun(make prettier)  | Column alignment must match across all rows    |
| Reordering list items      | Edit → devrun(make prettier)  | List spacing rules depend on nesting depth     |

**Takeaway**: Always format after markdown edits, regardless of change size. The cost of running `make prettier` (seconds) is far lower than the cost of a CI cycle (minutes).

## Configuration Architecture

<!-- Source: Makefile, prettier targets with --ignore-path .gitignore -->
<!-- Source: .prettierignore, .worker-impl/ exclusion -->

Erk's Prettier configuration has two layers:

1. **Makefile delegation**: Both `prettier` and `prettier-check` targets pass `--ignore-path .gitignore`
2. **Explicit .prettierignore**: Exists but is **unused** by Makefile targets (see [Makefile Prettier Ignore Path](makefile-prettier-ignore-path.md))

The `--ignore-path .gitignore` flag means: gitignored files are automatically excluded from Prettier. This keeps ignore patterns DRY and prevents "committed but unformatted" files.

When `.worker-impl/` or other transient artifacts appear in `.prettierignore`, they're redundant—those paths are already in `.gitignore`.

## Related Documentation

- [CI Iteration Pattern](ci-iteration.md) — devrun delegation and Run-Report-Fix-Verify cycle
- [Makefile Prettier Ignore Path](makefile-prettier-ignore-path.md) — why .prettierignore is bypassed
- [Formatter Tools](formatter-tools.md) — prettier vs ruff: which formats what
