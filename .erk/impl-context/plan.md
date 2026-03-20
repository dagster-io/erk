# Plan: Migrate skill-creator to npx skills management

## Context

`skill-creator` was manually copied into `.claude/skills/skill-creator/` and all its files are committed to git. The other npx-managed skills (dignified-python, fake-driven-testing, fdt-refactor-mock-to-fake) follow a different pattern:

- Canonical content in `.agents/skills/<name>/` (committed to git)
- Symlinks from `.claude/skills/<name>` → `../../.agents/skills/<name>` (committed as symlinks)
- Entry in `skills-lock.json` at repo root

The source is `anthropics/skills@skill-creator` (93.4K installs on skills.sh).

## Steps

### 1. Remove the manually-added skill-creator from git

```bash
git rm -r .claude/skills/skill-creator/
```

This removes 18 tracked files (SKILL.md, LICENSE.txt, agents/, assets/, eval-viewer/, references/, scripts/).

### 2. Install via npx skills

```bash
npx skills add anthropics/skills -s skill-creator -y
```

This will:
- Create `.agents/skills/skill-creator/` with the canonical content
- Create symlink `.claude/skills/skill-creator` → `../../.agents/skills/skill-creator`
- Update `skills-lock.json` with the new entry

### 3. Add newly created files to git

```bash
git add .agents/skills/skill-creator/ .claude/skills/skill-creator skills-lock.json
```

### 4. Verify

- `npx skills ls --json` shows skill-creator with path in `.agents/skills/`
- `ls -la .claude/skills/skill-creator` shows it's a symlink
- `cat skills-lock.json` shows the skill-creator entry
- The skill still appears in Claude Code's skill list

## Files Modified

- `.claude/skills/skill-creator/` — removed (18 files)
- `.agents/skills/skill-creator/` — created (by npx skills)
- `.claude/skills/skill-creator` — recreated as symlink (by npx skills)
- `skills-lock.json` — updated with new entry
