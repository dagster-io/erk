---
title: Skill Scope Boundaries
description: Guidelines for what belongs in skills vs learned docs
category: documentation
read_when:
  - Creating or modifying skills in .claude/skills/
  - Deciding where to document a pattern
  - Reviewing skill content for project-specific leakage
---

# Skill Scope Boundaries

Skills in `.claude/skills/` must be **portable and project-agnostic**. Project-specific patterns belong in `docs/learned/`.

## What Belongs in Skills

- Generic language patterns (Python idioms, TypeScript patterns)
- Framework-agnostic CLI patterns (Click, argparse best practices)
- Universal best practices (LBYL, error handling, testing principles)
- Tool-specific guidance (git, gh, pytest) that applies to any project

## What Does NOT Belong in Skills

- Project-specific imports (`from erk_shared import ...`, `from myproject import ...`)
- Project context types (`ErkContext`, `AppContext`, custom gateway types)
- Internal module references specific to this codebase
- Patterns that only make sense with project infrastructure

## Why This Matters

Skills may be:

- Shared across multiple projects
- Used as templates for new projects
- Referenced by agents unfamiliar with project internals

When a skill contains project-specific code, agents working on other projects (or unfamiliar with this one) get confused or produce errors.

## Where to Put Project-Specific Patterns

| Pattern Type            | Location                             |
| ----------------------- | ------------------------------------ |
| Generic Python/CLI      | `.claude/skills/dignified-python/`   |
| Erk CLI output patterns | `docs/learned/cli/output-styling.md` |
| Erk context usage       | `docs/learned/architecture/`         |
| Erk gateway patterns    | `docs/learned/testing/`              |

## Example: Confirmation Prompts

**In skill (generic)**:

```python
import sys
sys.stderr.flush()  # Prevent buffering issues
if click.confirm("Proceed?"):
    do_thing()
```

**In docs/learned (project-specific)**:

```python
# Preferred: Use context for testability
if ctx.console.confirm("Proceed?"):
    do_thing()

# Fallback: When no context available
from erk_shared.output import user_confirm
if user_confirm("Proceed?"):
    do_thing()
```

## Source

Learned from Plan #4747 - dignified-python skill contained erk-specific imports that caused false positives in automated review.
