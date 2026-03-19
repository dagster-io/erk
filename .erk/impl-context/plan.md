# Plan: Create `npx-skills` Skill

## Context

The `npx skills` CLI (npm package `skills@1.4.5` by Vercel Labs) is the package manager for the open agent skills ecosystem. It manages skill installation, discovery, and updates across 40+ AI coding agents. While the existing `find-skills` skill (globally installed) focuses narrowly on helping users discover and install skills, there's no skill that documents the full CLI, its mental model, ecosystem concepts, and command reference.

This is analogous to how `gh` and `gt` skills provide comprehensive CLI guidance. The new `npx-skills` skill will serve as the reference for agents working with the skills ecosystem.

## Approach

Create a new unbundled, Claude-only skill at `.claude/skills/npx-skills/SKILL.md` following the `gh`/`gt` CLI skill pattern: mental model first, then command reference, then workflow patterns.

### Step 1: Create the SKILL.md

**File:** `.claude/skills/npx-skills/SKILL.md`

Structure:
1. **Frontmatter** — name: `npx-skills`, description covering triggers
2. **Overview** — What is `npx skills`, the `skills@1.4.5` npm package, Vercel Labs, purpose in the ecosystem
3. **Core Mental Model** — Skills as portable agent instructions, SKILL.md format, project vs global scope, symlink vs copy, agent interoperability via shared spec (agentskills.io)
4. **Ecosystem Concepts** — skills.sh as discovery platform, skills-lock.json for reproducibility, security assessments, 40+ supported agents, `.agents/skills/` as canonical multi-agent path
5. **SKILL.md Format** — Required frontmatter (name, description), optional metadata, markdown body, progressive disclosure (SKILL.md + references/ + scripts/)
6. **Command Reference** — Organized by workflow, not alphabetically:
   - `find [query]` — search/discover
   - `add <source>` — install (with all flags: -g, -a, -s, -y, --copy, --all, --full-depth)
   - `list` / `ls` — inspect installed (with -g, -a, --json)
   - `remove` — uninstall (with -g, -a, -s, -y, --all)
   - `check` — check for updates
   - `update` — apply updates
   - `init [name]` — scaffold new skill
   - `experimental_install` — restore from skills-lock.json
   - `experimental_sync` — sync from node_modules
7. **Source Format Reference** — GitHub shorthand, full URLs, direct skill paths, GitLab, local paths
8. **Workflow Patterns** — Common multi-step workflows (install a skill globally, add to project, create and publish, update all skills, restore from lock file)
9. **Version Note** — Document that this corresponds to `skills@1.4.5`

### Step 2: Register the skill

Follow the "New Unbundled + Claude-Only Skill" checklist (3 file touches):

1. **`.claude/skills/npx-skills/SKILL.md`** — already created in step 1
2. **`src/erk/capabilities/skills/bundled.py`** — add `"npx-skills"` to `_UNBUNDLED_SKILLS`
3. **`src/erk/core/capabilities/codex_portable.py`** — add `"npx-skills"` to `claude_only_skills()`

No pyproject.toml entry needed (unbundled skills are not packaged in the wheel).

## Files to Modify

1. `.claude/skills/npx-skills/SKILL.md` — **CREATE** — skill content
2. `src/erk/capabilities/skills/bundled.py` — **EDIT** — add to `_UNBUNDLED_SKILLS`
3. `src/erk/core/capabilities/codex_portable.py` — **EDIT** — add to `claude_only_skills()`

## Key Facts to Capture in Skill

- npm package: `skills@1.4.5` (NOT `skills-cli`)
- Publisher: Vercel Labs (rauchg as maintainer)
- GitHub: https://github.com/vercel-labs/skills
- Published: 6 days ago (as of 2026-03-19)
- Registry/discovery: https://skills.sh/
- Shared spec: agentskills.io
- 40+ supported agents with distinct installation paths
- Agent-specific directories: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, etc.
- Default installation: symlink; `--copy` for independent copies
- `skills-lock.json` tracks source, sourceType, and computedHash per skill
- Security assessments shown during install (Gen, Socket, Snyk ratings)
- Environment vars: `INSTALL_INTERNAL_SKILLS=1`, `DISABLE_TELEMETRY`/`DO_NOT_TRACK`

## Verification

1. Run `make fast-ci` via devrun agent to verify:
   - `test_bundled_and_unbundled_cover_all_skills` passes
   - `test_codex_portable_and_claude_only_cover_all_skills` passes
   - `test_all_skills_have_codex_required_frontmatter` passes
2. Verify `npx skills ls` still shows the skill list correctly (no interference)
