# Plan: Reorganize Docs by Audience + Create User Docs Structure

## Goal

Reorganize `/docs` folder to have audience-based top-level folders and create nascent user-facing documentation with a facts scratchpad.

## New Structure

```
docs/
├── agent/           # AI agents reading/implementing code (EXISTS - keep as-is)
├── developer/       # Humans developing erk itself
├── user/            # End users of erk tool
└── public-content/  # Content for external publication
```

---

## Implementation Steps

### 1. Create New Audience Folders

```bash
mkdir -p docs/developer
mkdir -p docs/user
mkdir -p docs/public-content
```

### 2. Create User Documentation (Original Request)

**docs/user/README.md** - Index for user-facing docs

**docs/user/facts.md** - Scratchpad with first fact:
- Branch Naming Convention: `PPPP-DESC-MM-DD-HHMM`
- Example: `1904-gt-pr-prep-prepare-branch-12-02-0106`
- Rationale for each component

### 3. Move Existing Docs to Appropriate Audiences

#### To `docs/user/` (end users of erk):

| Current Location | New Location | Rationale |
|-----------------|--------------|-----------|
| `docs/project-setup.md` | `docs/user/project-setup.md` | User guide for configuring their repos |
| `docs/planner-setup.md` | `docs/user/planner-setup.md` | User guide for planner commands |
| `docs/queue-setup.md` | `docs/user/queue-setup.md` | User guide for queue setup |

#### To `docs/developer/` (people building erk):

| Current Location | New Location | Rationale |
|-----------------|--------------|-----------|
| `docs/agentic-engineering-patterns/` | `docs/developer/agentic-engineering-patterns/` | Patterns for tool developers |
| `docs/github-linked-issues.md` | `docs/developer/github-linked-issues.md` | Implementation details |
| `plan-lifecycle-improvements.md` (root) | `docs/developer/plan-lifecycle-improvements.md` | Technical proposal |

#### To `docs/public-content/` (external publication):

| Current Location | New Location | Rationale |
|-----------------|--------------|-----------|
| `docs/writing/schrockn-style/` | `docs/public-content/style-guides/` | Writing style guides |
| `docs/writing/agentic-programming/` | `docs/public-content/agentic-programming/` | Philosophy articles |
| `docs/writing/30-days-of-agentic-programming/` | `docs/public-content/30-days-series/` | Learning series |

#### Keep in `docs/agent/` (no changes):

All 21 files stay - these are agent implementation references.

### 4. Create Index Files for New Folders

- `docs/developer/README.md` - Developer docs index
- `docs/public-content/README.md` - Public content index

### 5. Delete Empty `docs/writing/` After Migration

---

## Files to Create

| File | Purpose |
|------|---------|
| `docs/user/README.md` | User docs index |
| `docs/user/facts.md` | Facts scratchpad (with branch naming convention) |
| `docs/developer/README.md` | Developer docs index |
| `docs/public-content/README.md` | Public content index |

## Files to Move

| From | To |
|------|-----|
| `docs/project-setup.md` | `docs/user/project-setup.md` |
| `docs/planner-setup.md` | `docs/user/planner-setup.md` |
| `docs/queue-setup.md` | `docs/user/queue-setup.md` |
| `docs/agentic-engineering-patterns/` | `docs/developer/agentic-engineering-patterns/` |
| `docs/github-linked-issues.md` | `docs/developer/github-linked-issues.md` |
| `plan-lifecycle-improvements.md` | `docs/developer/plan-lifecycle-improvements.md` |
| `docs/writing/schrockn-style/` | `docs/public-content/style-guides/` |
| `docs/writing/agentic-programming/` | `docs/public-content/agentic-programming/` |
| `docs/writing/30-days-of-agentic-programming/` | `docs/public-content/30-days-series/` |

## Folders to Delete After Migration

- `docs/writing/` (will be empty after moving contents)

---

## Reference Fixes Required

After moving files, update these references to point to new locations:

### In `docs/agent/` (references to moved patterns)

| File | Line | Old Reference | New Reference |
|------|------|---------------|---------------|
| `docs/agent/command-agent-delegation.md` | 6 | `../agentic-engineering-patterns/agent-delegating-commands.md` | `../developer/agentic-engineering-patterns/agent-delegating-commands.md` |
| `docs/agent/kit-cli-commands.md` | 119 | `../agentic-engineering-patterns/kit-cli-push-down.md` | `../developer/agentic-engineering-patterns/kit-cli-push-down.md` |

### In moved files (self-references that change)

| File (new location) | Line | Old Reference | New Reference |
|---------------------|------|---------------|---------------|
| `docs/public-content/agentic-programming/AGENTS.md` | 16 | `docs/writing/30-days-of-agentic-programming/01-intro.md` | `docs/public-content/30-days-series/01-intro.md` |
| `docs/public-content/agentic-programming/articles/ideas.md` | 98 | `docs/writing/30-days-of-agentic-programming/00-intro.md` | `docs/public-content/30-days-series/00-intro.md` |
| `docs/public-content/agentic-programming/articles/ideas.md` | 102 | `docs/writing/30-days-of-agentic-programming/01-verbose-mode.md` | `docs/public-content/30-days-series/01-verbose-mode.md` |
| `docs/public-content/agentic-programming/articles/ideas.md` | 106 | `docs/writing/30-days-of-agentic-programming/02-voice-input.md` | `docs/public-content/30-days-series/02-voice-input.md` |
| `docs/public-content/agentic-programming/articles/ideas.md` | 110 | `docs/writing/30-days-of-agentic-programming/03-claude-as-investigator.md` | `docs/public-content/30-days-series/03-claude-as-investigator.md` |
| `docs/developer/agentic-engineering-patterns/README.md` | 18 | `docs/agentic-engineering-patterns/` | `docs/developer/agentic-engineering-patterns/` |

---

## First Fact Content (for docs/user/facts.md)

```markdown
# Erk Facts

Scratchpad for facts to be organized into proper documentation later.

---

## Branch Naming Convention

**Format:** `PPPP-DESC-MM-DD-HHMM`

**Example:** `1904-gt-pr-prep-prepare-branch-12-02-0106`

**Components:**
- `PPPP` - Plan/issue number for quick reference
- `DESC` - Shorthand description so you don't have to memorize numbers
- `MM-DD-HHMM` - Timestamp for uniqueness on each queue submission

**Rationale:**
- Minute-level granularity is sufficient; collisions are rare in practice
- If collision occurs, a number suffix is added automatically
```