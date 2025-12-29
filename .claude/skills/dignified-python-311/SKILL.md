---
name: dignified-python-311
description: Load ONLY when Python 3.11 is the active Python environment.
  Use when writing, reviewing, or refactoring Python to ensure adherence to LBYL exception
  handling patterns, modern type syntax (list[str], str | None), pathlib operations,
  ABC-based interfaces, absolute imports, and explicit error boundaries at CLI level.
  Also provides production-tested code smell patterns from Dagster Labs for API design,
  parameter complexity, and code organization. Essential for maintaining erk's dignified
  Python standards.
erk:
  kit: dignified-python
---

# Dignified Python - Python 3.11 Coding Standards

## Core Knowledge (ALWAYS Loaded)

@dignified-python-core.md
@type-annotations.md

## Version-Specific Checklist

@checklist.md

## Conditional Loading (Load Based on Task Patterns)

Core files above cover 80%+ of Python code patterns. Only load these additional files when you detect specific patterns:

Pattern detection examples:

- If task mentions "click" or "CLI" → Load `cli-patterns.md`
- If task mentions "subprocess" → Load `subprocess.md`

## How to Use This Skill

1. **Core knowledge** is loaded automatically (LBYL, pathlib, ABC, imports, exceptions)
2. **Type annotations** are loaded automatically (Python 3.11 specific features including Self type)
3. **Additional patterns** may require extra loading (CLI patterns, subprocess)
4. **Each file is self-contained** with complete guidance for its domain

**For code reviews:** See `.erk/docs/kits/code-review/` for code smell patterns and refactoring guidance (not auto-loaded).
