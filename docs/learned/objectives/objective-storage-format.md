---
title: Objective v2 Storage Format
read_when:
  - "understanding how objective issues store their data"
  - "creating or modifying objective creation code"
  - "working with objective metadata blocks"
tripwires:
  - action: "storing objective content directly in the issue body"
    warning: "Objective content goes in the first comment (objective-body block), not the issue body. The issue body holds only metadata blocks (objective-header, objective-roadmap)."
  - action: "using plan-* metadata block names for objective data"
    warning: "Metadata block names must match their entity type: plan-header/plan-body for plans, objective-header/objective-roadmap/objective-body for objectives."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Objective v2 Storage Format

Objectives use a two-part storage strategy where metadata lives in the issue body and content lives in the first comment. This separation exists because the issue body is frequently mutated (roadmap updates, status changes) while the original objective content is immutable.

## Storage Structure

**Issue body** contains metadata blocks only:

1. `objective-header` — creation timestamp, creator username, comment ID pointer
2. `objective-roadmap` — YAML frontmatter with step data (optional, for roadmap-enabled objectives)

**First comment** contains the objective content:

3. `objective-body` — the full objective description, context, and exploration notes

## Metadata Block Naming Convention

Block names use the entity type as prefix:

| Entity    | Block Names                                               |
| --------- | --------------------------------------------------------- |
| Plan      | `plan-header`, `plan-body`                                |
| Objective | `objective-header`, `objective-roadmap`, `objective-body` |

This convention is enforced by the schemas in `erk_shared.gateway.github.metadata.schemas`.

## 7-Step Creation Flow

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py:278-398, create_objective_issue -->

`create_objective_issue()` implements:

1. **Get GitHub username** — returns error if authentication fails
2. **Extract title** — from parameter or first heading in content
3. **Build labels** — adds `erk-objective` (not `erk-plan`)
4. **Build issue body** — creates `objective-header` block, optionally adds `objective-roadmap` block
5. **Create GitHub issue** — with metadata-only body
6. **Add first comment** — wraps content in `objective-body` block
7. **Update issue body** — backfills `objective_comment_id` pointing to the comment

The two-step creation (issue then comment) is necessary because the comment ID isn't known until after creation.

## ObjectiveHeaderSchema

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py -->

| Field                  | Type          | Description                                                                       |
| ---------------------- | ------------- | --------------------------------------------------------------------------------- |
| `created_at`           | `str`         | ISO 8601 timestamp                                                                |
| `created_by`           | `str`         | GitHub username                                                                   |
| `objective_comment_id` | `int \| None` | Comment ID containing objective-body (null during creation, backfilled in step 7) |

## Rendering

Metadata blocks are rendered as `<details>` elements with YAML code blocks inside HTML comments, using `render_metadata_block()` from `erk_shared.gateway.github.metadata.core`. This makes them collapsible in GitHub's UI while remaining parseable by code.

## Related Documentation

- [Objective Lifecycle](objective-lifecycle.md) — Full mutation and reading lifecycle
- [Metadata Blocks](../architecture/metadata-blocks.md) — Block infrastructure
- [Roadmap Parser](roadmap-parser.md) — How roadmap data is parsed from objectives
