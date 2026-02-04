---
title: Codex Skills Registries
read_when:
  - "adding a new skill to the registry"
  - "understanding which skills work with Codex vs Claude-only"
  - "working with codex_portable.py"
---

# Codex Skills Registries

The erk codebase maintains two skill registries that distinguish between skills portable to Codex (compatible with multiple AI providers) and skills specific to Claude Code.

## Registry Functions

<!-- Source: src/erk/core/capabilities/codex_portable.py, codex_portable_skills -->

See `codex_portable_skills()` in `src/erk/core/capabilities/codex_portable.py` for the registry of skills that work across AI providers.

<!-- Source: src/erk/core/capabilities/codex_portable.py, claude_only_skills -->

See `claude_only_skills()` in `src/erk/core/capabilities/codex_portable.py` for skills that require Claude-specific features.

## When to Use Each Registry

**Portable skills** (`codex_portable_skills()`):

- Work with any AI provider (Claude, OpenAI, etc.)
- No Claude-specific tool use or features
- Can be bundled for Codex deployments

**Claude-only skills** (`claude_only_skills()`):

- Require Claude Code features (hooks, special tools)
- Not portable to other AI providers

## Adding a New Skill

When adding a skill to the codebase, determine which registry it belongs in:

1. Does the skill use Claude-specific features (hooks, tool restrictions)? → `claude_only_skills()`
2. Is the skill general-purpose documentation or guidance? → `codex_portable_skills()`

## API Pattern

Both registries are wrapped behind `@cache` functions following dignified-python module design standards. Call them as functions:

```python
from erk.core.capabilities.codex_portable import codex_portable_skills, claude_only_skills

# Correct - function calls
portable = codex_portable_skills()
claude_specific = claude_only_skills()
```

This pattern avoids import-time side effects from mutable collections.
