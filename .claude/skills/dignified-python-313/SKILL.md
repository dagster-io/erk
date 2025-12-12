---
name: dignified-python-313
description: This skill should be used when editing Python code in the erk codebase. Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception handling patterns, modern type syntax (list[str], str | None), pathlib operations, ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level. Also provides production-tested code smell patterns from Dagster Labs for API design, parameter complexity, and code organization. Essential for maintaining erk's dignified Python standards.
---

# Dignified Python - Python 3.13 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@.claude/docs/dignified-python/dignified-python-core.md
@.claude/docs/dignified-python/type-annotations-common.md
@.claude/docs/dignified-python/version-specific/313/type-annotations-delta.md

## Version-Specific Checklist

@.claude/docs/dignified-python/version-specific/313/checklist.md

## Conditional Loading (Load Based on Task Patterns)

Core files above cover 80%+ of Python code patterns. Only load these additional files when you detect specific patterns:

Pattern detection examples:

- If task mentions "click" or "CLI" → Load `cli-patterns.md`
- If task mentions "subprocess" → Load `subprocess.md`

## How to Use This Skill

1. **Core knowledge** is loaded automatically (LBYL, pathlib, ABC, imports, exceptions)
2. **Type annotations** are loaded automatically (common syntax + Python 3.13 specific features)
3. **Additional patterns** may require extra loading (CLI patterns, subprocess)
4. **Each file is self-contained** with complete guidance for its domain

**For code reviews:** See `.claude/docs/code-review/` for code smell patterns and refactoring guidance (not auto-loaded).
