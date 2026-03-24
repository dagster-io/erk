---
title: Objective Create Workflow
category: objectives
read_when:
  - "modifying the objective creation flow"
  - "understanding how objective-save-to-issue creates objectives"
  - "debugging objective creation failures"
tripwires:
  - action: "manually writing roadmap YAML or metadata blocks in objective-create"
    warning: "Use --roadmap-json flag on objective-save-to-issue to generate the roadmap block. The skill writes phases JSON to a separate file."
  - action: "writing objective content directly to issue body"
    warning: "Issue body holds only metadata blocks. Full content goes in the first comment (objective-body block). See the 3-layer storage model."
---

# Objective Create Workflow

The objective creation flow uses a 3-layer pipeline: the skill templates structured content, `objective-save-to-issue --roadmap-json` renders YAML blocks, and `create_objective_issue()` assembles the final GitHub issue.

## The 3-Layer Template Flow

### Layer 1: Skill Template (`.claude/commands/erk/objective-create.md`)

The slash command guides the user through structured input:

1. Prompt for description
2. Analyze and explore codebase
3. Ask for structure preference (steelthread, linear, single, custom)
4. Propose structured objective with roadmap

The skill writes two files to scratch storage:

- `objective-body.md` — prose content (no `## Roadmap` section)
- `roadmap.json` — structured phases JSON

Then creates the objective:

```bash
erk exec objective-save-to-issue --session-id=X --slug=Y \
  --roadmap-json=.erk/scratch/sessions/$SESSION/roadmap.json \
  --format=display --validate
```

### Layer 2: Exec Command

**`erk exec objective-save-to-issue`** (`src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`)

When `--roadmap-json` is provided:

1. Parses JSON and validates via `roadmap_nodes_from_json()`
2. Renders the complete `## Roadmap` section via `render_initial_roadmap_section()`
3. Appends rendered roadmap to the prose plan content
4. Passes combined content to `create_objective_issue()`

The rendering produces phase headers, markdown tables, test sections, and the YAML metadata block — all guaranteed in sync.

### Layer 3: `create_objective_issue()` (`packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py`)

Assembles the GitHub issue in a 7-step flow:

1. Get GitHub username
2. Extract/validate title
3. Build `erk-objective` label
4. **Build issue body** (metadata only): `objective-header` block + optional `objective-roadmap` block
5. **Create GitHub issue** with metadata-only body
6. **Add first comment** with full content wrapped in `objective-body` metadata block
7. **Backfill `objective_comment_id`** into the header block

## Storage Model

| Layer           | Location      | Content                                                               | Mutability                           |
| --------------- | ------------- | --------------------------------------------------------------------- | ------------------------------------ |
| Metadata header | Issue body    | `objective-header` YAML (created_at, created_by, comment_id)          | Rare                                 |
| Roadmap         | Issue body    | `objective-roadmap` YAML (steps with status/pr)                       | Frequent (via update-objective-node) |
| Content         | First comment | `objective-body` (exploration notes, context, rendered roadmap table) | After PR landing (reconciliation)    |

The `_build_objective_roadmap_block()` function extracts pre-existing metadata blocks from the plan content, validates v2 format, and re-renders to normalize structure.

## Scratch Directory

During creation, intermediate files are stored in session-scoped scratch storage:

```
.erk/scratch/sessions/${CLAUDE_SESSION_ID}/objective-body.md
.erk/scratch/sessions/${CLAUDE_SESSION_ID}/roadmap.json
```

This uses the `${CLAUDE_SESSION_ID}` substitution available in Claude Code commands since v2.1.9.

## Implementation References

| Component             | File                                                                    |
| --------------------- | ----------------------------------------------------------------------- |
| Skill template        | `.claude/commands/erk/objective-create.md`                              |
| Issue creator script  | `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`          |
| Shared creation logic | `packages/erk-shared/src/erk_shared/gateway/github/objective_issues.py` |
| Roadmap parsing       | `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` |
