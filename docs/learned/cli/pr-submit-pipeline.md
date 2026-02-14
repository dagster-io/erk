---
title: PR Submit Pipeline Architecture
read_when:
  - "modifying the PR submit workflow"
  - "adding new steps to the submit pipeline"
  - "debugging PR submission failures"
  - "understanding the Graphite-first vs core submit dispatch"
tripwires:
  - action: "adding a new step to the submit pipeline"
    warning: "Each step must return SubmitState | SubmitError. Use dataclasses.replace() for state updates. Add the step to _submit_pipeline() tuple."
  - action: "mutating SubmitState fields directly"
    warning: "SubmitState is frozen. Use dataclasses.replace(state, field=value) to create new state."
  - action: "adding discovery logic outside prepare_state()"
    warning: "All discovery (branch name, issue number, parent branch, etc.) must happen in prepare_state() to prevent duplication. Later steps assume these fields are populated."
---

# PR Submit Pipeline Architecture

The PR submit pipeline is erk's reference implementation of the state threading pattern. This document explains **why** the architecture choices matter, not what the code does (read the source for that).

## Why Linear Pipelines: The Dual-Path Problem

Before the linear pipeline refactor, PR submission used branching orchestration with two paths (Graphite-first vs core). **The problem:** discovery code was duplicated between paths, issue linkage validation happened in multiple places, and error handling varied between branches.

Linear pipelines solve this by **deferring the dispatch decision**. Discovery happens once in step 1, then step 3 dispatches internally to Graphite or core flow. Both paths share the same state type and error handling.

## Discovery Consolidation: Why Step 1 Does Everything

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, prepare_state -->

Step 1 (`prepare_state()`) resolves 6 fields: `repo_root`, `branch_name`, `parent_branch`, `trunk_branch`, `issue_number`, and validates `.impl/issue.json` linkage.

**Why consolidate all discovery in one step?**

1. **DRY** — Before this pattern, `issue_number` was derived independently in 3+ places with subtly different logic
2. **Fail fast** — If branch detection or `.impl` validation fails, no later steps run (no wasted work)
3. **Type narrowing** — Later steps assume `branch_name` is `str`, not `str | None`, because step 1 checks and errors if unresolved
4. **Single source of truth** — Grep for "where does `issue_number` come from?" finds one place, not four

**Anti-pattern:** Lazy discovery (re-running `get_repository_root()` in step 5 because "we need it again"). If a field is needed by multiple steps, step 1 populates it. State carries it forward.

## Graphite-First Dispatch: Why Not a Separate Pipeline

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, push_and_create_pr, _graphite_first_flow, _core_submit_flow -->

Step 3 (`push_and_create_pr`) dispatches to `_graphite_first_flow()` or `_core_submit_flow()` based on Graphite authentication and branch tracking.

**Why dispatch internally instead of two separate pipelines?**

- **Shared state type** — Both paths accumulate the same 15 fields (no conversion code)
- **Shared error handling** — Both return `SubmitState | SubmitError`, uniform consumption at CLI layer
- **Shared phases 1-2 and 4-8** — Only the push+PR creation differs; discovery, diff extraction, AI generation, finalization are identical

**Why Graphite-first exists:** `gt submit` handles push + PR creation atomically, avoiding tracking divergence caused by direct `git push`. When Graphite is available, we prefer it. When not, core flow provides the fallback.

**Trade-off:** Internal dispatch adds branching within one step. But the alternative (duplicating 7 other steps across two pipelines) is worse.

## Why 8 Steps: Granularity Trade-offs

The pipeline has 8 steps: prepare, commit WIP, push+PR, extract diff, fetch plan, generate description, Graphite enhancement, finalize.

**Why not fewer steps?** Merging "extract diff + generate description" would make testing harder (can't test diff extraction without running AI generation). Each step represents a **failure boundary** — a distinct phase where errors need different handling.

**Why not more steps?** Splitting "finalize PR" into "update metadata", "add labels", "amend commit" would create coupling (amend depends on updated metadata, label depends on PR number). Steps that always run together should be one step.

**Decision test:** If the step can fail independently and that failure requires distinct error handling, it deserves to be a separate step.

## Auto-Repair Pattern: .impl/issue.json Creation

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, prepare_state, auto-repair section -->

`prepare_state()` auto-creates `.impl/issue.json` if the issue number is inferred from the branch name but the file is missing.

**Why auto-repair instead of erroring?** Early erk workflows created `.impl/` but not `issue.json`. Erroring would break existing worktrees. Auto-repair maintains forward compatibility while migrating to the new structure.

**Why in prepare_state() instead of a separate "repair" step?** Because the repair needs `issue_number` (discovered in prepare), `repo_root` (discovered in prepare), and `remote_url` (fetched for repair). Preparing and repairing are coupled — no value in separating them.

**When to remove this:** When no worktrees exist with `.impl/` but missing `issue.json`, grep for `.impl` directories and check for `issue.json` presence. If all have it, the auto-repair is dead code.

## Why Amend the Local Commit: Git Hygiene vs Metadata Footer

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, finalize_pr, amend section -->

Step 8 (`finalize_pr()`) updates the PR with a full body including metadata footer, but amends the local commit with **only** the title and body (no footer).

**Why this split?**

- **PR body needs metadata** — The footer contains `erk pr checkout` commands and links to plans/objectives
- **Commit message should be clean** — If the footer is in the commit message, `git log` and changelogs become cluttered with metadata that's only relevant on GitHub

**Why amend?** The initial commit message is "WIP: Prepare for PR submission" (step 2). Amending rewrites it with the AI-generated title and body, so local git history matches PR intent.

**Trade-off:** Amending causes Graphite tracking divergence (the commit SHA changes). That's why step 8 calls `retrack_branch()` afterward — Graphite must re-learn the mapping between branch and commit.

## Plan Embedding: Why in PR Body, Not Commit Message

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, _build_plan_details_section, finalize_pr -->

When a plan context is available, step 8 embeds it in the PR body as a collapsed `<details>` section. It does **not** go in the commit message.

**Why only in PR body?**

1. **Plans are verbose** — 500-1000 lines, would dwarf the commit message
2. **Reviewers need context, git log doesn't** — GitHub PR view benefits from inline plan reference; `git log` doesn't need it
3. **Separation of concerns** — Commit message describes the change, PR body provides review context

**Why `<details>` collapse?** Plans are reference material, not the primary content. Collapsing them keeps the PR description scannable.

## Diff Truncation: Why in Extract Diff, Not AI Generation

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, extract_diff -->

Step 4 (`extract_diff`) truncates diffs to fit AI context limits **before** writing the scratch file.

**Why truncate in step 4 instead of step 6 (generation)?**

- **Separation of concerns** — Diff extraction knows about diffs, not AI limits; but truncation is a diff operation (line-based splitting), so it belongs with extraction
- **Reusable scratch file** — If AI generation fails and needs retry, the truncated diff is already prepared
- **Fail fast** — If truncation makes the diff unusable, we know in step 4, not after running AI generation

**Trade-off:** Truncation happens even when Graphite is unavailable (step 6 runs regardless). This is intentional — better to always truncate than to branch on "will we use this later?"

## Why dict[str, str] for SubmitError.details

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, SubmitError -->

`SubmitError.details` is `dict[str, str]`, not `dict[str, str] | None` or `dict[str, Any]`.

**Why always present, never None?** Every error has details, even if empty `{}`. Making it optional adds ceremony (callers must check `if details is not None`) for no benefit.

**Why `str` values, not `Any`?** Error details are for logging and debugging. String values enable consistent serialization (JSON, log files) without type uncertainty. If you need structured data, that belongs in a dedicated error type, not in `details`.

## Related Documentation

- [State Threading Pattern](../architecture/state-threading-pattern.md) — The underlying architectural pattern
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — SubmitError as discriminated union
- [Linear Pipeline Architecture](../architecture/linear-pipelines.md) — The broader two-pipeline pattern (validation + execution)

## Reference Implementation

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py -->

See `src/erk/cli/commands/pr/submit_pipeline.py` for the complete implementation (789 lines). The module docstring and step signatures document the contract. This learned doc explains the **why** behind the design choices.
