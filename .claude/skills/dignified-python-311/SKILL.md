---
name: dignified-python-311
description: This skill should be used when editing Python code in the erk codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, modern type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Also provides production-tested code smell patterns from Dagster Labs for API design, parameter complexity, and code organization. Essential for maintaining erk's dignified Python standards.
---

# Dignified Python - Python 3.11 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@.claude/docs/dignified-python/dignified-python-core.md
@.claude/docs/dignified-python/version-specific/311/type-annotations.md

## Version-Specific Checklist

@.claude/docs/dignified-python/version-specific/311/checklist.md

## Conditional Loading (Load Based on Task Patterns)

Use the routing index in @routing-patterns.md to determine which additional files to load:

- **CLI development** → @.claude/docs/dignified-python/cli-patterns.md
- **Subprocess operations** → @.claude/docs/dignified-python/subprocess.md

## Comprehensive Reference (If Needed)

If unsure which specific file to load, or need full overview:
.claude/docs/dignified-python/dignified-python-core.md

**For code reviews:** See `.claude/docs/code-review/` for code smell patterns and refactoring guidance (not auto-loaded).

## How to Use This Skill

1. **Core knowledge** is loaded automatically (LBYL, pathlib, ABC, imports, exceptions, type annotations)
2. **Additional patterns** may require extra loading (CLI patterns, subprocess)
3. **Each file is self-contained** with complete guidance for its domain

**Note:** Most common patterns are now loaded by default for convenience
