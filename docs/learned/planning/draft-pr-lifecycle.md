---
title: Draft PR Lifecycle
read_when:
  - "working with draft-PR-backed plans"
  - "understanding PR body format for draft PR plans"
  - "debugging plan content extraction from PR bodies"
  - "building or modifying lifecycle stage transitions"
tripwires:
  - action: "adding Closes #N to a draft PR footer"
    warning: "Draft PR IS the plan. Self-referential close would close the plan itself. Use issue_number=None for draft-PR backend."
  - action: "adding footer before PR creation"
    warning: "PR footer needs the PR number, which isn't known until after create_pr returns. Add footer AFTER PR creation."
  - action: "rewriting PR body without preserving metadata"
    warning: "Extract metadata prefix on every lifecycle transition via extract_metadata_prefix() to prevent metadata loss."
  - action: "parsing plan content without backward compatibility"
    warning: "extract_plan_content() handles both details-wrapped and old flat format. Always use it instead of manual parsing."
---

# Draft PR Lifecycle

Draft PRs serve as the backing store for plans when the plan backend is `github-draft-pr`. Unlike issue-based plans (where the plan issue and implementation PR are separate), draft-PR-backed plans evolve through lifecycle stages within a single PR.

## Stage Definitions

### Stage 1: Plan Creation

`plan_save` / `DraftPRPlanBackend.create_plan()` creates a draft PR with `lifecycle_stage: planned` in the plan-header metadata. The body contains the plan-header metadata block, the plan content collapsed in a `<details>` tag, and a checkout footer.

Body format:

```
[metadata block]
\n\n---\n\n
<details>
<summary><code>original-plan</code></summary>

[plan content]

</details>
\n---\n
[checkout footer]
```

### Stage 2: Implementation

After code changes, `erk pr submit` / `erk pr rewrite` rewrites the body. The metadata block is preserved. The AI-generated summary is inserted before the collapsed plan.

Body format:

```
[metadata block]
\n\n---\n\n
[AI-generated summary]

<details>
<summary><code>original-plan</code></summary>

[plan content]

</details>
\n---\n
[checkout footer]
```

### Stage 3: Review & Merge

PR is marked ready for review. Standard review/merge flow. No body format changes in this stage.

## Key Functions

All in `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`:

| Function                                             | Purpose                                                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `build_plan_stage_body(metadata_body, plan_content)` | Build Stage 1 body: metadata + separator + details-wrapped plan. Footer NOT included (needs PR number).                  |
| `build_original_plan_section(plan_content)`          | Wrap plan content in `<details><summary><code>original-plan</code></summary>` section. Used by both Stage 1 and Stage 2. |
| `extract_plan_content(pr_body)`                      | Extract plan content from PR body at any lifecycle stage. Handles both details-wrapped and old flat format.              |
| `extract_metadata_prefix(pr_body)`                   | Extract metadata block + content separator for preservation during stage transitions.                                    |

## Separator Semantics

Two distinct separators serve different purposes:

- **Content separator** (`\n\n---\n\n`, double newline each side): Between metadata block and content section. Found with `find()`.
- **Footer separator** (`\n---\n`, single newline each side): Standard PR footer delimiter. Found with `rsplit()`.

These are distinct: `find()` matches the first (content), `rsplit()` matches the last (footer).

## Constants

**Source:** `PLAN_CONTENT_SEPARATOR`, `DETAILS_OPEN`, `DETAILS_CLOSE` in `packages/erk-shared/src/erk_shared/plan_store/draft_pr_lifecycle.py`

## Self-Referential Close Prevention

Draft PR IS the plan. The `plan_id` from prepare_state is the PR's own number. Using `Closes #N` in the footer would be self-referential, causing the plan to close itself. All three consumers of `assemble_pr_body()` set `issue_number=None` when the backend is `github-draft-pr`.

## Footer Timing Constraint

The PR footer (with checkout command) must be added AFTER `create_pr` returns, because it needs the PR number. `build_plan_stage_body()` intentionally excludes the footer.

## Backward Compatibility

`extract_plan_content()` handles both:

- **New format**: Content wrapped in `<details><summary><code>original-plan</code></summary>` tags
- **Old flat format**: Content after `PLAN_CONTENT_SEPARATOR` without details tags

## Branch Data Files

Draft PR branches contain `.erk/branch-data/plan.md` and `.erk/branch-data/ref.json`, committed before PR creation to avoid GitHub's "empty branch" rejection. `plan.md` enables inline review comments on the plan via the PR's "Files Changed" tab.

## Lifecycle Stage Tracking

Draft-PR plans participate in the same `lifecycle_stage` tracking as issue-based plans. The stage progresses through the same values (`planned` → `implementing` → `implemented`) and is stored in the plan-header metadata block within the PR body.

See [Lifecycle Stage Tracking](lifecycle.md#lifecycle-stage-tracking) for the complete stage definitions and write points.

## Related Topics

- [Draft PR Branch Sync](draft-pr-branch-sync.md) - How branches are synced with remote
- [PR Body Assembly](../architecture/pr-body-assembly.md) - How `assemble_pr_body()` handles both backends
- [Plan Lifecycle](lifecycle.md) - Overall plan lifecycle including issue-based plans
