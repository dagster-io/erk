# Plan: Add Reference vs. Conceptual Documentation Guidance to learn.md

## Problem

The `/erk:learn` process dismissed documentation needs by saying "Auto-documented by generator" for new CLI options. This confused:
- **Reference documentation** (WHAT exists) - flags, types, signatures
- **Conceptual documentation** (WHY/WHEN) - context, relationships, best practices

The auto-generated `erk-exec-reference/SKILL.md` shows option names and types, but not:
- Why the feature exists (problem it solves)
- When to use it (context, workflows)
- Best practices (e.g., "use 20000 tokens to stay under 25000 limit")

## Solution

Update `.claude/commands/erk/learn.md` to explicitly reject "reference exists" as a reason to skip documentation.

## Changes

### File: `.claude/commands/erk/learn.md`

#### Change 1: Add to Invalid reasons list (around line 253-258)

Add two new invalid reasons:
```markdown
Invalid reasons (REJECT these):

- "Code is self-documenting"
- "Patterns are discoverable in the code"
- "Well-tested so documentation unnecessary"
- "Simple/straightforward implementation"
- "Auto-documented by generator" ← NEW
- "Reference docs exist" ← NEW
```

#### Change 2: Add Reference vs. Conceptual explanation (before Invalid reasons)

Insert a new callout section after the enumerated table requirements (around line 245):

```markdown
**⚠️ Reference vs. Conceptual Documentation**

Auto-generated reference docs (like `erk-exec-reference/SKILL.md`) show WHAT exists:
- Option names and types
- Required vs optional flags
- Basic descriptions

But reference docs do NOT cover:
- **Why** the feature exists (the problem it solves)
- **When** to use it (context, workflows, use cases)
- **How** it fits with other features (relationships)
- **Best practices** (recommended values, common patterns)

**Example:** A new `--max-tokens` option might be reference-documented as "INTEGER - Split output into multiple files." But future agents need to know:
- "Use 20000 to stay safely under Claude's 25000 token read limit"
- "Combine with --output-dir/--prefix for named files"

If a feature changes how a workflow operates, it needs conceptual documentation even when reference docs exist.
```

## Critical Files

- `.claude/commands/erk/learn.md` (lines 241-259)

## Verification

1. Read the updated learn.md and verify the new guidance is clear
2. Run `make fast-ci` to ensure markdown formatting passes