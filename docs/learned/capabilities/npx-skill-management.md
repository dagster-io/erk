---
title: NPX Skill Management
read_when:
  - "adding a new skill to erk"
  - "migrating a bundled skill to npx distribution"
  - "understanding how skills-lock.json works"
  - "debugging skill installation issues"
  - "removing a skill from bundled distribution"
tripwires:
  - action: "installing a new skill without updating _UNBUNDLED_SKILLS registry"
    warning: "Skills managed by npx must be added to _UNBUNDLED_SKILLS in src/erk/capabilities/skills/bundled.py. Without this, erk will try to install the skill from its own bundle (where it doesn't exist) instead of from npx."
  - action: "migrating a skill from bundled to npx without removing from pyproject.toml force-include"
    warning: "npx-managed skills that remain in pyproject.toml force-include will be double-installed. Remove the force-include entry after migrating."
---

# NPX Skill Management

Erk uses [npx skills](https://agentskills.io) (Vercel Labs, `skills@1.4.5`) to distribute skills from external GitHub repositories. This supplements erk's own bundled skills.

## Directory Structure

- **`.agents/skills/`** — canonical installation directory for npx-managed skills
- **`.claude/skills/`** — Claude Code reads skills from here; contains symlinks to `.agents/skills/` entries

The symlinks ensure Claude Code picks up npx-managed skills alongside bundled ones.

## skills-lock.json

**Source**: `skills-lock.json` (repo root)

Tracks exact versions of installed npx skills for reproducible installation:

```json
{
  "version": 1,
  "skills": {
    "dignified-python": {
      "source": "dagster-io/skills",
      "sourceType": "github",
      "computedHash": "..."
    }
  }
}
```

Each entry maps a skill name to its GitHub source and content hash. Update by running `npx skills install <name>`.

## Current NPX-Managed Skills

From `.agents/skills/` (as of writing):

- `dignified-python` — Python coding standards (source: `dagster-io/skills`)
- `fake-driven-testing` — Test architecture patterns (source: `dagster-io/fake-driven-testing`)
- `fdt-refactor-mock-to-fake` — Refactoring patterns (source: `dagster-io/fake-driven-testing`)
- `graphite` — Graphite stacked PR management (source: `withgraphite/agent-skills`)
- `skill-creator` — Skill creation tool (source: `anthropics/skills`)

## \_UNBUNDLED_SKILLS Registry

**Source**: `src/erk/capabilities/skills/bundled.py` (lines 17-38)

Skills managed by npx are listed in `_UNBUNDLED_SKILLS`.

**Source**: `src/erk/capabilities/skills/bundled.py:17-38` — a `frozenset[str]` of skill names that erk skips during its own bundling process. Includes `dignified-python`, `fake-driven-testing`, `skill-creator`, and other npx-distributed skills.

This registry tells erk's capability system to skip these skills during its own bundling process. Without this registration, erk would try to install them from its own bundle (where they're absent).

## Migration Workflow: Bundled → NPX

When migrating a skill from erk's bundle to external npx distribution (example: `skill-creator` in PR #9265):

1. **Install via npx**: `npx skills install <name>@github:<owner>/<repo>` (creates entry in `.agents/skills/` and `skills-lock.json`)
2. **Add to `_UNBUNDLED_SKILLS`** in `bundled.py`
3. **Remove from `bundled_skills()` dict** in `bundled.py`
4. **Remove from `codex_portable_skills()`** if present
5. **Remove from `pyproject.toml` force-include** if present (npx handles distribution)

## Comparison: Skill Distribution Types

| Type                    | Where                                           | Who manages            | When to use                                               |
| ----------------------- | ----------------------------------------------- | ---------------------- | --------------------------------------------------------- |
| Required bundled        | `bundled_skills()` + `_REQUIRED_BUNDLED_SKILLS` | erk package            | Core skills needed by erk tooling itself                  |
| Bundled                 | `bundled_skills()`                              | erk package            | Erk-specific skills with no external source               |
| Unbundled (npx-managed) | `.agents/skills/` + `_UNBUNDLED_SKILLS`         | npx + skills-lock.json | Skills with separate GitHub repos/versioning              |
| Tombstone               | `bundled_skills()` with `[REMOVED]` description | erk package            | Deleted skills that need to overwrite stale installations |

## Related Documentation

- [Skill Deletion Patterns](skill-deletion-patterns.md) — How to properly delete a skill
- [AGENTS.md](../../AGENTS.md) — `npx skills -a claude` usage pattern
