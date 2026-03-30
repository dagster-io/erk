# Plan: Add `metadata.internal: true` + improve skills documentation routing

## Context

Skills in this repo appeared on the skills.sh public leaderboard. While investigating, we found that `docs/learned/capabilities/npx-skill-management.md` already documents the distinction between authored and npx-installed skills — but it wasn't discovered because nothing in AGENTS.md routes to it. The existing doc is good; the problem is discoverability.

## Part 1: Add `metadata.internal: true` to authored skills

Add `metadata.internal: true` to all 20 SKILL.md files in `.claude/skills/`. The 5 symlinked skills in `.agents/skills/` are installed from external repos and should NOT be modified here.

```yaml
metadata:
  internal: true
```

**Files (20 total) — all `.claude/skills/`:**
ci-iteration, cli-skill-creator, cmux, command-creator, dignified-code-simplifier, erk-diff-analysis, erk-exec, erk-gt, erk-planning, erk-skill-onboarding, gh, learned-docs, npx-skills, objective, pr-feedback-classifier, pr-operations, refac-cli-push-down, refac-module-to-subpackage, rename-swarm, session-inspector

## Part 2: Fix documentation routing in AGENTS.md

### 2a. Add skills/capabilities row to the routing table (~line 170)

Add to the "Topic Area | Check First" table:

```
| Skills, SKILL.md, capabilities | `docs/learned/capabilities/`                 |
```

**File:** `AGENTS.md` line ~178 (after the TUI row)

### 2b. Add routing to "Skill Loading Behavior" section (~line 148)

Expand the section to point to the detailed doc when modifying or adding skills:

```markdown
**Modifying skills?** Read [NPX Skill Management](docs/learned/capabilities/npx-skill-management.md) first — covers authored vs npx-installed skills, `metadata.internal`, `skills-lock.json`, and the `_UNBUNDLED_SKILLS` registry.
```

**File:** `AGENTS.md` line ~155 (after the npx skills one-liner)

### 2c. Add description to capabilities category in docs/learned/index.md

Change the bare `- [capabilities/](capabilities/)` line to include a description and read-when guidance, matching the style of other categories like `cli/` and `hooks/`.

**File:** `docs/learned/index.md` line 12

## Part 3: Add `metadata.internal` section to npx-skill-management.md

Add a section to the existing doc covering:
- What `metadata.internal: true` does (hides from `npx skills` CLI discovery and skills.sh)
- Why all erk-authored skills use it (private repo, not for public consumption)
- NPX-managed skills are controlled by their source repos, not modified here

**File:** `docs/learned/capabilities/npx-skill-management.md` (new section after the comparison table)

## Verification

- `grep -r "internal: true" .claude/skills/` → 20 matches
- `grep -r "internal: true" .agents/skills/` → 0 matches
- AGENTS.md routing table includes skills/capabilities row
- "Skill Loading Behavior" section links to the detailed doc
- `docs/learned/index.md` capabilities category has description
