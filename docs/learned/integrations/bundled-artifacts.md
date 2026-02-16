---
title: Bundled Artifact Portability
read_when:
  - classifying a new skill as portable vs Claude-only
  - adding or modifying force-include entries in pyproject.toml
  - debugging why editable installs resolve to unexpected artifact paths
  - understanding the artifact sync and health detection systems
tripwires:
  - action: "adding a skill to codex_portable_skills() without verifying it works outside Claude Code"
    warning: "Portable skills must not use hooks, TodoWrite, EnterPlanMode, AskUserQuestion, or session log paths. Check against the portability classification table before adding."
  - action: "adding a force-include entry in pyproject.toml without updating codex_portable.py"
    warning: "The portability registry and pyproject.toml force-include must stay in sync. A skill mapped to erk/data/codex/ must appear in codex_portable_skills()."
  - action: "creating a .codex/ directory in the erk repo"
    warning: "There is no .codex/ directory in the erk repo. All skills live in .claude/skills/ regardless of portability. The build and sync systems handle remapping."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Bundled Artifact Portability

Erk bundles `.claude/` and `.github/` artifacts into the wheel so `erk artifact sync` can install them into external projects. A subset of these artifacts are "portable" — they work with any AI coding agent, not just Claude Code. This document explains the portability classification, the dual-path bundling architecture, and why certain design choices were made.

## Why Two Bundle Targets?

<!-- Source: pyproject.toml:60-87 -->

The `force-include` section in `pyproject.toml` maps source artifacts to two different wheel locations: `erk/data/claude/` for Claude-only artifacts, and `erk/data/codex/` for portable skills.

This split exists because portable skills get installed to whichever agent directory the target project uses (`.claude/`, `.codex/`, etc.), while Claude-only artifacts always go to `.claude/`. Without separate bundle targets, the sync system couldn't distinguish which artifacts to copy where.

## Portability Classification

<!-- Source: src/erk/core/capabilities/codex_portable.py, codex_portable_skills -->
<!-- Source: src/erk/core/capabilities/codex_portable.py, claude_only_skills -->

Skills are classified into two registries in `codex_portable.py`. See `codex_portable_skills()` and `claude_only_skills()` for the current lists. The classification criteria:

| Criterion                      | Portable                                           | Claude-Only                                                 |
| ------------------------------ | -------------------------------------------------- | ----------------------------------------------------------- |
| Hooks (PreToolUse/PostToolUse) | None — all instructions self-contained in SKILL.md | May depend on hook-injected context                         |
| Tool dependencies              | Standard set (Read, Write, Edit, Bash, Grep, Glob) | Claude-specific (TodoWrite, EnterPlanMode, AskUserQuestion) |
| System prompt overrides        | None                                               | May use them                                                |
| Session log access             | None                                               | May inspect `~/.claude/projects/`                           |

**Why this matters**: Installing a skill that calls `TodoWrite` into a non-Claude project causes runtime failures. The registry prevents `erk artifact sync` from copying incompatible skills.

## Single Canonical Location Rule

Each skill must exist in exactly one portability category. This is enforced at two levels:

1. **Registry level**: A skill appears in either `codex_portable_skills()` or `claude_only_skills()`, never both
2. **Build level**: Each `force-include` entry maps to exactly one destination (`erk/data/claude/` or `erk/data/codex/`)

Violating this creates confusing sync behavior where the same skill could be installed from two different sources with potentially different content.

## The Editable Install Subtlety

<!-- Source: src/erk/artifacts/paths.py, get_bundled_codex_dir -->
<!-- Source: src/erk/artifacts/paths.py, _is_editable_install -->

The path resolution in `paths.py` uses a dual-path strategy because editable installs (development) and wheel installs (distribution) have fundamentally different directory layouts. The detection heuristic checks whether `site-packages` appears in the resolved package path.

**The non-obvious design decision**: In editable mode, `get_bundled_codex_dir()` returns the `.claude/` directory — not a `.codex/` directory — because `.claude/` and `.codex/` use identical file formats (YAML frontmatter with name and description). The sync step handles the target directory mapping at install time. This avoids maintaining a separate `.codex/` directory in the repo that would just mirror `.claude/skills/`.

## Staleness Detection: Two Signals

<!-- Source: src/erk/artifacts/artifact_health.py, _determine_status -->

The artifact health system uses version + content hash comparison (stored in `.erk/state.toml`) to classify each artifact into one of four states: `up-to-date`, `changed-upstream`, `locally-modified`, and `not-installed`.

The two-signal approach exists to distinguish two different scenarios that a single signal would conflate:

- **Hash changed, same version** → user edited the artifact locally (`locally-modified`) → sync should warn, not overwrite
- **Hash changed, different version** → new erk release changed the artifact (`changed-upstream`) → sync should update

This distinction is why `_determine_status()` checks both signals rather than just comparing hashes. Without the version signal, the system couldn't tell whether the user or an erk upgrade caused the content difference.

## Adding a New Portable Skill

When making a skill portable:

1. **Verify no Claude-only dependencies** — confirm the skill doesn't reference hooks, Claude-specific tools, or session log paths
2. **Add to `codex_portable_skills()`** in `codex_portable.py`
3. **Add force-include entry** mapping `.claude/skills/{name}` to `erk/data/codex/skills/{name}` in `pyproject.toml`
4. **Keep source in `.claude/skills/`** — the skill's source of truth stays in `.claude/`; the build system handles remapping

**Anti-pattern**: Moving the skill source directory to a `.codex/` folder in the repo. There is no `.codex/` directory in the erk repo. All skills live in `.claude/skills/` regardless of portability; the distinction only matters at build and sync time.

## Related Documentation

- [multi-agent-portability.md](multi-agent-portability.md) — Agent comparison and portability research
- [toml-handling.md](../reference/toml-handling.md) — TOML library choice and patterns
