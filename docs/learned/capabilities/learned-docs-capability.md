---
title: Learned Docs Capability
read_when:
  - "modifying the learned-docs capability install or uninstall logic"
  - "debugging partial learned-docs installation"
  - "understanding how learned-docs artifacts are bundled in the wheel"
  - "adding new artifacts to the learned-docs capability"
tripwires:
  - action: "checking only one directory for learned-docs installation"
    warning: "Installation requires all three directories: docs/learned/, .claude/skills/learned-docs/, and .claude/agents/learn/. Checking fewer causes false positives."
  - action: "removing docs/learned/ during uninstall"
    warning: "Uninstall preserves docs/learned/ because it contains user-created documentation. Only framework artifacts (.claude/skills/learned-docs/, .claude/agents/learn/, .claude/commands/erk/learn.md) are removed."
---

# Learned Docs Capability

The `LearnedDocsCapability` manages the agent-discoverable documentation system. It installs three directory structures and preserves user content during uninstall.

## Three-Directory Installation Check

<!-- Source: src/erk/capabilities/learned_docs.py:210-217 -->

The `is_installed()` method checks for all three directories:

1. `docs/learned/` — user-facing documentation directory
2. `.claude/skills/learned-docs/` — skill definition for Claude Code
3. `.claude/agents/learn/` — learn agent configuration

All three must exist for the capability to report as installed. A partial installation (e.g., `docs/learned/` exists but skill is missing) returns `False`, triggering a reinstall that fills in the missing pieces.

## Install Artifacts

<!-- Source: src/erk/capabilities/learned_docs.py:219-278 -->

Installation creates:

| Artifact                               | Source                   | Purpose                          |
| -------------------------------------- | ------------------------ | -------------------------------- |
| `docs/learned/`                        | Generated from templates | Documentation root               |
| `docs/learned/README.md`               | `LEARNED_DOCS_README`    | Getting started guide            |
| `docs/learned/index.md`                | `LEARNED_DOCS_INDEX`     | Auto-populated doc index         |
| `.claude/skills/learned-docs/SKILL.md` | `LEARNED_DOCS_SKILL`     | Skill for doc authoring guidance |
| `.claude/agents/learn/`                | Bundled wheel artifact   | Learn agent configuration        |
| `.claude/commands/erk/learn.md`        | Bundled wheel artifact   | Learn slash command              |

The learn agent and command are copied from bundled artifacts (`get_bundled_claude_dir()`), not generated from templates. This means they're versioned with the erk package and updated on `erk init` or capability reinstall.

## Wheel Bundling

The `.claude/agents/learn/` directory is included in the wheel via `pyproject.toml` force-include directives. This allows the learn agent to be distributed as part of the erk package without requiring a separate installation step.

## Uninstall Preservation

<!-- Source: src/erk/capabilities/learned_docs.py:280-315 -->

Uninstall removes framework artifacts but preserves user content:

**Removed:**

- `.claude/skills/learned-docs/` — framework skill
- `.claude/agents/learn/` — framework agent
- `.claude/commands/erk/learn.md` — framework command

**Preserved:**

- `docs/learned/` — contains user-created documentation that may have significant value

This asymmetry is intentional. The skill, agent, and command are framework artifacts that can be regenerated. The `docs/learned/` directory contains user-authored documentation that cannot be recovered.

## Partial Installation Detection

When `is_installed()` returns `False`, the `install()` method is idempotent — it only creates artifacts that don't already exist. This handles partial installations gracefully:

- Missing skill? Created.
- Missing agent? Copied from bundle.
- `docs/learned/` already exists? Skipped (preserves existing docs).

## Managed Artifacts

<!-- Source: src/erk/capabilities/learned_docs.py:202-208 -->

The capability declares three managed artifacts for the capability framework:

- `learned-docs` (skill)
- `learn` (command)
- `learn` (agent)

These declarations allow `erk init` to track which artifacts belong to this capability and manage them during upgrades.

## Related Documentation

- [Adding New Capabilities](adding-new-capabilities.md) — How to implement a new capability
- [Adding Skills](adding-skills.md) — Skill creation patterns
