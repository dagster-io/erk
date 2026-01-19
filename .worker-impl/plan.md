# Plan: Fix Documentation Warnings for Release

## Summary

Fix all mkdocs warnings before release by addressing README/index conflicts, missing files, incomplete navigation, and broken links.

## Issues Identified

### 1. README.md vs index.md Conflicts (6 warnings)
Directories with both files - mkdocs uses index.md and excludes README.md:
- `docs/README.md` ↔ `docs/index.md`
- `docs/faq/README.md` ↔ `docs/faq/index.md`
- `docs/howto/README.md` ↔ `docs/howto/index.md`
- `docs/ref/README.md` ↔ `docs/ref/index.md`
- `docs/topics/README.md` ↔ `docs/topics/README.md`
- `docs/tutorials/README.md` ↔ `docs/tutorials/index.md`

### 2. Missing shell-integration.md (7 broken link warnings)
Referenced from: tutorials/index.md, faq/index.md, topics/worktrees.md, howto/navigate-branches-worktrees.md, tutorials/prerequisites.md, tutorials/graphite-integration.md

### 3. Pages Not in Nav (15 files)
- `tutorials/graphite-integration.md`
- `howto/conflict-resolution.md`, `documentation-extraction.md`, `planless-workflow.md`, `pr-checkout-sync.md`, `remote-execution.md`
- `faq/index.md`, `general.md`, `graphite-issues.md`
- `ref/index.md`, `commands.md`, `configuration.md`, `file-locations.md`, `slash-commands.md`
- `contributing/writing-documentation.md`

### 4. Other Broken Links
- `faq/general.md` links to `README.md` (excluded file)
- `topics/plan-oriented-engineering.md` links to `../../TAO.md` (outside docs/)

## Implementation Plan

### Step 1: Merge README.md content into index.md, then delete README.md

The README.md files have more comprehensive content than index.md. Strategy:
1. Merge unique content from README.md into index.md
2. Delete the README.md files

Files to process:
| README.md | index.md | Action |
|-----------|----------|--------|
| `docs/README.md` | `docs/index.md` | README has full docs overview; merge sections into index |
| `docs/howto/README.md` | `docs/howto/index.md` | README has 6 items, index has 3; merge missing items |
| `docs/faq/README.md` | `docs/faq/index.md` | Similar content; keep index, delete README |
| `docs/ref/README.md` | `docs/ref/index.md` | Similar content; keep index, delete README |
| `docs/topics/README.md` | `docs/topics/index.md` | Check and merge if needed |
| `docs/tutorials/README.md` | `docs/tutorials/index.md` | Check and merge if needed |

### Step 2: Create shell-integration.md
Create `docs/tutorials/shell-integration.md` with content about:
- What shell integration does (allows `erk` commands to change your directory)
- How to enable it (`erk init capability add shell-integration`)
- Supported shells (bash, zsh, fish)
- Troubleshooting common issues

### Step 3: Update mkdocs.yml nav
Add missing pages to navigation:

```yaml
nav:
  - Getting Started:
      - index.md
  - Tutorials:
      - tutorials/index.md
      - tutorials/prerequisites.md
      - tutorials/installation.md
      - tutorials/first-plan.md
      - tutorials/shell-integration.md      # ADD
      - tutorials/graphite-integration.md   # ADD
  - Topics:
      - topics/index.md
      - topics/worktrees.md
      - topics/plan-mode.md
      - topics/the-workflow.md
      - topics/plan-oriented-engineering.md
      - topics/why-github-issues.md
  - How-To Guides:
      - howto/index.md
      - howto/local-workflow.md
      - howto/navigate-branches-worktrees.md
      - howto/test-workflows.md
      - howto/conflict-resolution.md        # ADD
      - howto/planless-workflow.md          # ADD
      - howto/pr-checkout-sync.md           # ADD
      - howto/remote-execution.md           # ADD
      - howto/documentation-extraction.md   # ADD
  - Reference:                              # ADD SECTION
      - ref/index.md
      - ref/commands.md
      - ref/slash-commands.md
      - ref/configuration.md
      - ref/file-locations.md
  - FAQ:                                    # ADD SECTION
      - faq/index.md
      - faq/general.md
      - faq/graphite-issues.md
  - Contributing:                           # ADD SECTION
      - contributing/writing-documentation.md
```

### Step 4: Move TAO.md to docs/
Move `TAO.md` from repo root to `docs/TAO.md` and update the link in `topics/plan-oriented-engineering.md` to `../TAO.md`.

### Step 5: Fix broken links in content files
1. `docs/faq/general.md:65` - Change `[FAQ](README.md)` to `[FAQ](index.md)`
2. `docs/faq/index.md:8` - shell-integration.md reference (will be fixed by Step 2)

### Step 6: Fix directory link warnings
- `docs/faq/general.md` - Change `../tutorials/` to `../tutorials/index.md`
- `docs/howto/documentation-extraction.md` - Change `../learned/` to `../learned/index.md`

## Files to Modify

| File | Action |
|------|--------|
| `docs/index.md` | Merge content from README.md |
| `docs/howto/index.md` | Merge content from README.md |
| `docs/README.md` | DELETE (after merge) |
| `docs/faq/README.md` | DELETE |
| `docs/howto/README.md` | DELETE (after merge) |
| `docs/ref/README.md` | DELETE |
| `docs/topics/README.md` | DELETE |
| `docs/tutorials/README.md` | DELETE |
| `TAO.md` | MOVE to `docs/TAO.md` |
| `docs/tutorials/shell-integration.md` | CREATE |
| `mkdocs.yml` | Edit nav section |
| `docs/faq/general.md` | Fix links |
| `docs/topics/plan-oriented-engineering.md` | Fix TAO.md link to `../TAO.md` |
| `docs/howto/documentation-extraction.md` | Fix directory link |

## Verification

Run `make docs-serve` and verify:
- No WARNING messages in output
- All nav sections render correctly
- Links in pages work (spot check)