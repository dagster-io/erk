---
title: Objective Create Workflow
category: objectives
read_when:
  - "modifying the objective creation flow"
  - "understanding how objective-render-roadmap and objective-save-to-issue work together"
  - "debugging objective creation failures"
tripwires:
  - action: "manually writing roadmap YAML or metadata blocks in objective-create"
    warning: "Use erk exec objective-render-roadmap to generate the roadmap block. The skill template must produce valid JSON input for this command."
  - action: "writing objective content directly to issue body"
    warning: "Issue body holds only metadata blocks. Full content goes in the first comment (objective-body block). See the 3-layer storage model."
---

# Objective Create Workflow

The objective creation flow uses a 3-layer pipeline: the skill templates structured content, exec commands render YAML blocks, and `create_objective_issue()` assembles the final GitHub issue.

## The 3-Layer Template Flow

### Layer 1: Skill Template (`.claude/commands/erk/objective-create.md`)

The slash command guides the user through structured input:

1. Prompt for description
2. Analyze and explore codebase
3. Ask for structure preference (steelthread, linear, single, custom)
4. Propose structured objective with roadmap

The skill constructs a JSON object describing phases and steps, then generates the roadmap section:

```bash
echo '<json>' | erk exec objective-render-roadmap
```

### Layer 2: Exec Commands

**`erk exec objective-render-roadmap`** (`src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`)

Accepts JSON via stdin describing phases and steps. Produces a complete v2 YAML metadata block wrapped in `<!-- erk:metadata-block:objective-roadmap -->` HTML comment markers. This ensures all roadmap blocks have consistent formatting.

**`erk exec objective-save-to-issue`** (`src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`)

Takes the assembled objective content and creates the GitHub issue. Delegates to `create_objective_issue()` in `erk_shared.gateway.github.plan_issues`.

### Layer 3: `create_objective_issue()` (`packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py`)

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
| Roadmap         | Issue body    | `objective-roadmap` YAML (steps with status/plan/pr)                  | Frequent (via update-objective-node) |
| Content         | First comment | `objective-body` (exploration notes, context, rendered roadmap table) | After PR landing (reconciliation)    |

The `_build_objective_roadmap_block()` function extracts pre-existing metadata blocks from the plan content, validates v2 format, and re-renders to normalize structure. The skill MUST produce valid v2 YAML blocks.

## Scratch Directory

During creation, intermediate files are stored in session-scoped scratch storage:

```
.erk/scratch/sessions/${CLAUDE_SESSION_ID}/objective-body.md
```

This uses the `${CLAUDE_SESSION_ID}` substitution available in Claude Code commands since v2.1.9.

## Implementation References

| Component             | File                                                               |
| --------------------- | ------------------------------------------------------------------ |
| Skill template        | `.claude/commands/erk/objective-create.md`                         |
| Roadmap renderer      | `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`    |
| Issue creator         | `src/erk/cli/commands/exec/scripts/objective_save_to_issue.py`     |
| Shared creation logic | `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py` |
