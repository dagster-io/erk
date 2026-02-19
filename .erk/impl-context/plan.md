# Documentation Plan: Fix missing data in draft PR plans and consolidate GraphQL-based fetching

## Context

This plan was implemented across eight sessions and consolidated into PR #7619. The core work replaced an N+1 REST API pattern in `DraftPRPlanListService` with a single GraphQL call (`list_plan_prs_with_details()`), enriched `PRDetails` with timestamp and author fields, fixed missing data display in the TUI for draft PR plans, and added an operational metadata carry-over step to the plan migration tool. A secondary thread fixed `fetch_plan_content()` to handle pre-extracted draft PR plan bodies correctly.

These changes touch multiple architectural layers — gateway ABC, real/fake/dry_run/printing implementations, plan list services, plan data providers, TUI column rendering, and exec scripts. Future agents working on draft PR plan display, plan migration, or gateway extensions will repeatedly encounter the patterns and gotchas documented below. Without this documentation, agents will re-discover the same issues: missing TUI columns because `DraftPRPlanListService` was not updated in parallel with `RealPlanListService`, broken plan content display because draft PR bodies are pre-extracted, and lost operational metadata during migration.

The non-obvious insights are concentrated in three areas: (1) the dual-mode behavior of `fetch_plan_content()` where draft PR plan bodies arrive already extracted, (2) the requirement that `DraftPRPlanListService` must mirror all data-fetching changes made to `RealPlanListService`, and (3) the two-phase create-then-update pattern for preserving operational metadata during plan migration. Each of these caused real bugs during implementation that required multiple sessions to diagnose and fix.

## Raw Materials

https://gist.github.com/schrockn/090c72536a497bf4cd246cb00201ceb6

## Summary

| Metric                          | Count |
| ------------------------------- | ----- |
| Documentation items             | 25    |
| Contradictions to resolve       | 0     |
| Tripwire candidates (score>=4)  | 7     |
| Potential tripwires (score 2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. `fetch_plan_content()` dual-mode behavior

**Location:** `docs/learned/planning/draft-pr-plan-service.md` (CREATE)
**Action:** CREATE
**Source:** [Impl] Sessions 699cf377, 10ff7777; [PR #7619]

**Draft Content:**

```markdown
---
title: Draft PR Plan Service
read_when:
  - working with DraftPRPlanListService or fetch_plan_content
  - debugging plan content display in TUI for draft PR plans
  - extending plan data provider with new content sources
tripwires:
  - action: "calling fetch_plan_content(plan_id, plan_body) for draft PR plans"
    warning: "plan_body may be pre-extracted content (no plan-header metadata block). Detect via find_metadata_block(plan_body, 'plan-header') is None, then return body directly."
  - action: "extending _build_worktree_mapping() for new branch formats"
    warning: "Two paths exist: extract_leading_issue_number() for P{num}- branches; read_plan_ref() for plan-* branches. New formats need their own fallback."
---

# Draft PR Plan Service

## fetch_plan_content Dual-Mode Behavior

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, fetch_plan_content -->

`fetch_plan_content(plan_id, plan_body)` serves two distinct callers with different input shapes:

- **Issue-based plans**: `plan_body` contains a raw issue body with a `plan-header` metadata block. The function extracts `plan_comment_id` from the block and fetches the actual plan content from the comment via HTTP.
- **Draft PR plans**: `plan_body` is ALREADY the extracted plan content. `DraftPRPlanListService` calls `extract_plan_content()` before storing the body, so by the time `fetch_plan_content` receives it, there is no `plan-header` block.

Detection: call `find_metadata_block(plan_body, "plan-header")` once at the top. If `None`, return the body directly (draft PR case). If present, read `PLAN_COMMENT_ID` from `block.data` and fetch content from the comment. Empty body returns `None`.

**Gotcha**: This branching logic is invisible at the call site. Callers in `PlanBodyScreen` see a single function signature and have no indication that the body may already be final content.

## plan-\* Branch Naming and plan-ref.json Fallback

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py, _build_worktree_mapping -->

Draft PR plan branches use `plan-{slug}-{timestamp}` format with no leading numeric PR ID. `extract_leading_issue_number()` returns `None` for these branches. The fallback reads `.impl/plan-ref.json` from the worktree directory to get `plan_id` (PR number as string).

- Only `plan-*` prefix triggers the fallback path
- LBYL check `plan_ref.plan_id.isdigit()` is required before `int()` conversion
- Absent `plan-ref.json` or non-numeric `plan_id` causes the worktree to be excluded from the mapping

See `_build_worktree_mapping()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py`.
```

---

#### 2. `list_plan_prs_with_details()` — new GitHub gateway method (5-place pattern)

**Location:** `docs/learned/architecture/gateway-abc-implementation.md` (UPDATE) and `docs/learned/gateway/tripwires.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session 928b4973; [PR #7619] diff analysis items 3, 4, 12

**Draft Content:**

```markdown
## list_plan_prs_with_details — Gateway Method Example

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/abc.py, list_plan_prs_with_details -->

This method was added in PR #7619 as a concrete example of the 5-place implementation pattern. It returns `tuple[list[PRDetails], dict[int, list[PullRequestInfo]]]` — PRDetails for plan content extraction, pr_linkages dict for TUI display metadata.

Key limitation: GitHub's GraphQL `pullRequests` connection does NOT support server-side `isDraft` or `creator` filters. Both must be applied client-side after fetching all matching PRs.

See `_parse_plan_prs_with_details()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the client-side filtering implementation.

### Tripwire addition for gateway/tripwires.md:

When adding a new method to the GitHub gateway ABC, implement in all 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py. Missing any one causes a runtime AbstractMethodError or silent data gaps.
```

---

#### 3. `DraftPRPlanListService` GraphQL refactor and workflow run fetching

**Location:** `docs/learned/planning/draft-pr-plan-backend.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session 928b4973; [PR #7619]

**Draft Content:**

```markdown
## GraphQL-Based Data Fetching

<!-- Source: src/erk/core/services/plan_list_service.py, DraftPRPlanListService -->

`DraftPRPlanListService.get_plan_list_data()` uses a single GraphQL call via `list_plan_prs_with_details()` instead of the previous N+1 REST pattern (`list_prs()` + N x `get_pr()`). This returns both `PRDetails` (for plan content extraction) and `PullRequestInfo` (for TUI display with checks, review threads, merge status).

### Workflow Run Fetching

Dispatch `node_id` values are extracted from each PR body via `extract_plan_header_dispatch_info()`. These node_ids are batched into a single `get_workflow_runs_by_node_ids()` GraphQL call. The result is keyed by plan_id (PR number) in `workflow_runs`. Any exception from the workflow run fetch is caught (`except Exception`) and results in an empty `workflow_runs` dict — the service remains resilient to network failures.

The `skip_workflow_runs` parameter bypasses workflow run fetching entirely.

### Rule: Mirror RealPlanListService Changes

When adding new data fields to `RealPlanListService.get_plan_list_data()`, also update `DraftPRPlanListService.get_plan_list_data()` to mirror the same changes. The two services are parallel implementations. Missing this caused workflow run data to always show "-" for draft PR plans.

### Rule: Use GraphQL for Display Data

When adding display data to draft PR plans, use `list_plan_prs_with_details()` (GraphQL). Do NOT add new REST calls. GraphQL `pullRequests` does not support server-side `isDraft`/`creator` filters — apply client-side.
```

---

#### 4. Time injection in fakes — FakeGitHub `time` and `plan_pr_details` parameters

**Location:** `docs/learned/testing/fake-github.md` (CREATE)
**Action:** CREATE
**Source:** [Impl] Session af587ae7; [PR #7619] comments #1 and #9

**Draft Content:**

```markdown
---
title: FakeGitHub Testing Patterns
read_when:
  - writing tests that use FakeGitHub
  - adding new gateway methods to FakeGitHub
  - debugging time-related test failures in fake gateway code
tripwires:
  - action: "editing fake.py gateway files and using datetime.now()"
    warning: "Use injected self._time.now().replace(tzinfo=UTC) instead. Add time: Time | None = None to constructor defaulting to FakeTime()."
---

# FakeGitHub Testing Patterns

## Constructor Parameters for New Gateway Methods

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py, FakeGitHub -->

`plan_pr_details: tuple[list[PRDetails], dict[int, list[PullRequestInfo]]] | None` — Pre-configures the return value of `list_plan_prs_with_details()`. When `None`, the method returns `([], {})`.

## Time Injection

`time: Time | None` — Defaults to `FakeTime()`. Used for deterministic `created_at`/`updated_at` on PRs created by the fake. Pattern: `self._time.now().replace(tzinfo=UTC)`.

The time abstraction tripwire applies to fakes, not just real implementations. Using `datetime.now(UTC)` in a fake defeats the determinism that tests rely on.

The correct initialization pattern: `self._time = time if time is not None else FakeTime()`.
```

---

#### 5. `plan_migrate_to_draft_pr` — operational metadata carry-over (two-phase pattern)

**Location:** `docs/learned/planning/plan-migrate-to-draft-pr.md` (CREATE)
**Action:** CREATE
**Source:** [Impl] Session b1b68c7e; [PR #7619]

**Draft Content:**

```markdown
---
title: Plan Migration to Draft PR
read_when:
  - working on plan_migrate_to_draft_pr exec script
  - extending create_plan to handle new metadata fields
  - debugging missing operational metadata after plan migration
tripwires:
  - action: "editing plan_migrate_to_draft_pr.py or adding new plan-header fields"
    warning: "Verify the migration tool carries the new field. Check if excluded from create_plan (in _FIELDS_HANDLED_BY_CREATE) and included in the update_metadata call."
---

# Plan Migration to Draft PR

## Two-Phase Metadata Preservation

<!-- Source: src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py -->

Migration uses a two-phase pattern to preserve operational history:

**Phase 1 — `create_plan()`**: Populates structural fields: `schema_version`, `created_at`, `created_by`, `branch_name`, `plan_comment_id`, `source_repo`, `objective_issue`, `created_from_session`, `created_from_workflow_run_url`. These are tracked in `_FIELDS_HANDLED_BY_CREATE`.

**Phase 2 — `update_metadata()`**: All other non-None operational fields (dispatch IDs, impl sessions, worktree_name, learn history) from the source plan-header are carried over.

### Limitation: created_at Reflects Migration Time

`update_metadata` protects `created_at` as immutable. Migrated plans reflect the migration timestamp, not the original plan creation time. If a different `created_at` is needed, direct PR body manipulation is required.

## Migration Traceability

Closed source issues have "Migrated to draft PR #NNNN: https://..." comments. This is the canonical way to find which draft PR a given issue was migrated to. NOT a structured YAML field — fetch via `gh api repos/{owner}/{repo}/issues/{N}/comments`.
```

---

#### 6. `except Exception` at gateway call sites — intentional, accepted pattern

**Location:** `docs/learned/architecture/gateway-error-boundaries.md` (CREATE)
**Action:** CREATE
**Source:** [PR #7619] comments #6 and #8

**Draft Content:**

```markdown
---
title: Gateway Error Boundaries
read_when:
  - reviewing code that uses except Exception at gateway call sites
  - adding error handling around GitHub gateway ABC calls in service code
  - addressing bot review comments about broad exception handling
tripwires: []
---

# Gateway Error Boundaries

## `except Exception` at Gateway Call Sites

In service-level code that wraps gateway ABC calls (e.g., `get_workflow_runs_by_node_ids()`), `except Exception` is intentional and accepted. This pattern applies when:

- The gateway ABC does not declare specific exception types
- The call site is in dashboard/listing code that must remain resilient to network failures
- The outcome is degraded data (empty dict) rather than a crash

This pattern is a recurring false positive from the automated review bot. Reviewers should not flag `except Exception` in service code that wraps gateway calls with this documented rationale. The bot may flag it, but the response is to explain the gateway ABC does not expose specific exceptions.
```

---

#### 7. `PRDetails` metadata enrichment — new fields with backward-compatible defaults

**Location:** `docs/learned/architecture/github-interface-patterns.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Sessions 331b30b2, 699cf377; [PR #7619]

**Draft Content:**

```markdown
## PRDetails Field Enrichment (PR #7619)

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, PRDetails -->

Three new fields were added to `PRDetails`:

- `created_at: datetime` — default `_epoch_sentinel()` (2000-01-01 UTC)
- `updated_at: datetime` — default `_epoch_sentinel()`
- `author: str` — default `""`

The epoch sentinel is the FIELD DEFAULT for backward compatibility — existing test files constructing `PRDetails` without these fields continue to work unchanged. In production, `_parse_pr_details_from_rest_api()` always extracts real timestamps, so the sentinel only appears in tests that don't set the field.

### \_epoch_sentinel() Named Factory

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/types.py, _epoch_sentinel -->

`field(default_factory=lambda: datetime(...))` is forbidden. The named factory `_epoch_sentinel()` replaces the lambda and provides a greppable, testable function.

### ISO Timestamp Parsing

`Z` suffix in ISO timestamps is handled via `.replace("Z", "+00:00")` before `datetime.fromisoformat()`.

### Author Fallback

`author` is `""` when the GitHub user object is `None` (deleted accounts). The LBYL check pattern applies here — explicit None check on the user dict, not `.get()` chaining.
```

---

### MEDIUM Priority

#### 8. `plan-*` branch naming and plan-ref.json fallback

**Location:** `docs/learned/planning/draft-pr-plan-service.md` (covered in item 1)
**Action:** CREATE (merged into item 1)
**Source:** [Impl] Session 928b4973; [PR #7619]

This item is merged into item 1 above. The `_build_worktree_mapping()` fallback for `plan-*` branches is documented in the same file as `fetch_plan_content()` dual-mode behavior, since both relate to the draft PR plan data provider.

---

#### 9. `show_pr_column` — TUI column visibility split

**Location:** `docs/learned/tui/plan-table.md` (CREATE or UPDATE)
**Action:** CREATE
**Source:** [Impl] Sessions 331b30b2, 928b4973; [PR #7619]

**Draft Content:**

```markdown
---
title: Plan Table Column Configuration
read_when:
  - adding or hiding columns in PlanTable
  - working with PlanFilters for backend-specific TUI behavior
  - debugging column visibility in draft_pr plan mode
tripwires: []
---

# Plan Table Column Configuration

## show_pr_column Feature Flag

<!-- Source: src/erk/tui/data/types.py, PlanFilters -->

`PlanFilters.show_pr_column` (default `True`) controls whether the `pr` column is displayed. In draft_pr mode (`get_plan_backend() == "draft_pr"`), set to `False` because the plan number IS the PR number — displaying it again would be redundant.

The `chks` and `comments` columns remain visible regardless of `show_pr_column`.

### Column Index Behavior

<!-- Source: src/erk/tui/widgets/plan_table.py, PlanTable._setup_columns -->

When `show_pr_column=False`, `_pr_column_index` is never set, so click events on the pr column position do not fire. Tests for conditional column rendering must cover both enabled and disabled branches, including value count alignment and column index shifts.

### Backend Detection

<!-- Source: src/erk/cli/commands/plan/list_cmd.py -->

`list_cmd.py` sets `show_pr_column = get_plan_backend() != "draft_pr"`. This is the coupling point between plan backend selection and TUI column visibility.
```

---

#### 10. `.get()` chaining as an implicit EAFP violation

**Location:** `docs/learned/conventions.md` (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] comment #2; [Impl] Session 699cf377

**Draft Content:**

````markdown
## .get() Chaining is an EAFP Violation

The pattern `data.get("user", {}).get("login", "")` is an EAFP-style anti-pattern. It handles the `None` value case implicitly by relying on the `{}` fallback.

**Correct LBYL pattern:**

```python
# WRONG — implicit None handling via .get() chaining
author = data.get("user", {}).get("login", "")

# CORRECT — explicit LBYL checks
author = ""
if "user" in data and data["user"] and "login" in data["user"]:
    author = data["user"]["login"]
```
````

This specific anti-pattern is a subtle LBYL violation that reviewers miss repeatedly. The `.get()` chaining looks innocuous but silently swallows `None` values from the outer key.

````

---

#### 11. `lambda` in `default_factory` is forbidden — named factory pattern

**Location:** `docs/learned/conventions.md` (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] comment #4; [Impl] Session 699cf377

**Draft Content:**

```markdown
## No Lambda in default_factory

`field(default_factory=lambda: datetime(...))` is forbidden. Always define a named module-level function and reference it:

```python
# WRONG
created_at: datetime = field(default_factory=lambda: datetime(2000, 1, 1, tzinfo=UTC))

# CORRECT
def _epoch_sentinel() -> datetime:
    return datetime(2000, 1, 1, tzinfo=UTC)

created_at: datetime = field(default_factory=_epoch_sentinel)
````

Named factories are greppable, independently testable, and self-documenting. This complements the frozen dataclass rule — frozen dataclasses require `default_factory` for mutable defaults, and named functions are the required form.

````

---

#### 12. `GET_PLAN_PRS_WITH_DETAILS_QUERY` GraphQL query — client-side filter limitation

**Location:** `docs/learned/architecture/github-graphql.md` (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] diff analysis items 1, 4; [Impl] Session 928b4973

**Draft Content:**

```markdown
## GET_PLAN_PRS_WITH_DETAILS_QUERY

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py, GET_PLAN_PRS_WITH_DETAILS_QUERY -->

Fetches draft plan PRs with rich metadata (status checks, review threads, merge status) in a single GraphQL call.

**Key limitation**: GitHub's `pullRequests` connection does NOT support `filterBy` for `isDraft` or `creator`. Both filters must be applied client-side after fetching. The `states` array defaults to `["OPEN"]`.

See `_parse_plan_prs_with_details()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py` for the consumer that applies client-side filtering.
````

---

#### 13. Draft PR plan body lifecycle stages — Stage 1 vs Stage 2 formats

**Location:** `docs/learned/planning/lifecycle.md` (UPDATE — the successor of the deleted `draft-pr-lifecycle.md`)
**Action:** UPDATE
**Source:** [Impl] Session 10ff7777

**Draft Content:**

```markdown
## Draft PR Body Format by Lifecycle Stage

### Stage 1 (Plan Creation)

Body format: `[metadata block] + \n\n---\n\n + [AI summary] + <details>original-plan</details>`

The `original-plan` details block contains the full plan markdown. `extract_plan_content()` finds this block and extracts it.

### Stage 2 (Post-CI Execution)

Body format: freeform `## Summary`, `## Files Changed` (with `<details>`), `## Key Changes` sections, footer after `---`.

CI rewrites the body to a structured summary. The `original-plan` details block is removed. The `---` separator is OVERLOADED — it appears both between sections and before the footer.

Any code parsing draft PR bodies must handle BOTH formats. Detection: check for the `<details><summary><code>original-plan</code></summary>` block. If absent, the PR is Stage 2+.
```

---

#### 14. `pr_details_to_plan()` — epoch sentinel removal

**Location:** `docs/learned/planning/lifecycle.md` or draft-pr doc (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] diff analysis item 7; [Impl] Session 331b30b2

**Draft Content:**

```markdown
## pr_details_to_plan Timestamp Handling

<!-- Source: packages/erk-shared/src/erk_shared/plan_store/conversion.py, pr_details_to_plan -->

`pr_details_to_plan()` reads directly from `pr.created_at` and `pr.updated_at`. The epoch sentinel is still the DEFAULT FIELD VALUE on `PRDetails` for backward compatibility, but `_parse_pr_details_from_rest_api()` always extracts real timestamps in production. The sentinel only appears in tests that construct `PRDetails` without setting these fields.
```

---

#### 15. Pre-existing test failure verification via `git stash`

**Location:** `docs/learned/testing/testing.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Sessions 331b30b2, 928b4973

**Draft Content:**

```markdown
## Pre-Existing Test Failure Verification

When CI reports unexpected failures on a feature branch, verify whether failures pre-exist before spending time debugging:

1. `git stash` — stash all local changes
2. `pytest <failing-test-paths>` — run the specific failing tests
3. `git stash pop` — restore changes

If tests fail identically on the unmodified branch, the failures are pre-existing and not caused by the current implementation. This pattern saved multiple debugging sessions in PR #7619 where 128 pre-existing failures were initially attributed to the new changes.
```

---

#### 16. Layer 4 unit tests required for REST API parsing helpers with branching logic

**Location:** `docs/learned/testing/testing.md` (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] comment #3

**Draft Content:**

```markdown
## Layer 4 Unit Tests for Parsing Helpers

Private REST API parsing methods with branching on missing/None fields (e.g., timestamp fallback, None-user handling) require direct Layer 4 unit tests even when covered indirectly by higher-level tests. The `_parse_pr_details_from_rest_api()` case is the canonical example — its three branches (normal timestamps, Z-suffix timestamps, missing user) each need explicit test coverage.

Use `RealGitHub.for_test()` to get a minimal real instance for testing private parsing methods.
```

---

#### 17. `gt delete` replaces deprecated `gt branch delete`

**Location:** `docs/learned/erk/tripwires.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session db3abd4f

**Draft Content:**

```markdown
## Tripwire: gt branch delete is Deprecated

`gt branch delete` is deprecated. Use `gt delete` instead to avoid deprecation warnings. The old form still works but signals intent to remove. Always pass `--no-interactive` (and `--force` if needed).
```

---

#### 18. "Single extraction point" pattern for metadata blocks

**Location:** `docs/learned/architecture/` or `docs/learned/conventions.md` (UPDATE)
**Action:** UPDATE
**Source:** [PR #7619] comment #5; [Impl] Session 699cf377

**Draft Content:**

```markdown
## Single Extraction Point for Metadata Blocks

`find_metadata_block()` should be called ONCE at the top of a function, with the result used for all subsequent branches. Avoid wrapping helper functions that internally call `find_metadata_block` and then calling it again in the caller.

The anti-pattern: calling `extract_plan_header_comment_id()` (which internally calls `find_metadata_block`) and then calling `find_metadata_block` again to distinguish "no block" from "null field value." The correct pattern: call `find_metadata_block` once, check if result is `None`, then read fields directly from `block.data`.
```

---

#### 19. `DraftPRPlanListService` must mirror `RealPlanListService` data-fetching

**Location:** `docs/learned/planning/draft-pr-plan-backend.md` (covered in item 3)
**Action:** UPDATE (merged into item 3)
**Source:** [Impl] Session 699cf377

This rule is included in item 3 above as "Rule: Mirror RealPlanListService Changes."

---

#### 20. Plan branch recognition — `.worker-impl/` and `.erk/branch-data/` only = scaffolding

**Location:** `docs/learned/planning/` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session db3abd4f

**Draft Content:**

```markdown
## Plan Branch Recognition

Branches containing only `.worker-impl/` or `.erk/branch-data/` files are plan scaffolding artifacts, not code changes — safe to delete without cherry-picking.

Standard two-step assessment:

1. `git log --oneline <base>..<branch>` — check commit subjects
2. `git diff <base>..<branch> --stat` — if only `.worker-impl/` or `.erk/branch-data/` appear, the branch is pure scaffolding
```

---

### LOW Priority

#### 21. `grep -P` fails on macOS — use `grep -E`

**Location:** `docs/learned/universal-tripwires.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session b1b68c7e

**Draft Content:**

```markdown
## macOS grep Compatibility

`grep -P` (Perl regex) is not supported on macOS BSD grep. Always use `grep -E` (POSIX extended regex) in bash commands. For example, use `grep -oE '#[0-9]{4,}'` instead of `grep -oP '#\d{4,}'`.
```

---

#### 22. Shell `echo` with multiline JSON fails — use Python subprocess

**Location:** `docs/learned/commands/` or `docs/learned/hooks/` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session 699cf377

**Draft Content:**

```markdown
## Multiline JSON Piping

Piping multi-line JSON strings through shell `echo` to `erk exec` commands fails with "Invalid control character" errors when strings contain embedded newlines or special characters.

The reliable alternative: use `python3 -c "import json, subprocess; ..."` with `json.dumps()` to serialize the payload, then pipe via `stdin=subprocess.PIPE`.
```

---

#### 23. Automated tripwire review bot generates both review thread AND discussion comment

**Location:** `docs/learned/review/` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Sessions af587ae7, 699cf377

**Draft Content:**

```markdown
## Resolving Bot Review Items

The `dignified-python-review` bot posts BOTH:

1. A **review thread** (on the specific line) — resolve via `erk exec resolve-review-threads`
2. A **discussion comment** (summary-level) — resolve via `erk exec reply-to-discussion-comment`

Both must be resolved. Seeing only the review thread as actionable in Phase 1 will leave the discussion comment visible in Phase 4 verification. After resolving all review threads, re-run the classifier to catch remaining discussion_actions items.
```

---

#### 24. `prettier --write .erk/branch-data/plan.md` required before CI

**Location:** `docs/learned/planning/tripwires.md` (UPDATE)
**Action:** UPDATE
**Source:** [Impl] Session 331b30b2

**Draft Content:**

```markdown
## Tripwire: Prettier on Plan Branch Data

After `erk exec plan-save` saves a plan to the plan branch, run `prettier --write .erk/branch-data/plan.md` before committing. Plan files are generated prose (not authored markdown) and `erk exec plan-save` does not auto-format them. CI `prettier-check` step will fail if this is skipped.
```

---

#### 25. SHOULD_BE_CODE items (code changes, not documentation)

**Action:** CODE_CHANGE
**Source:** [PR #7619] gap analysis items 26, 27, 28

Three items require code changes rather than documentation:

1. **`checks_passing=None` displays as pending emoji** — Add docstring or comment to `format_checks_cell()` explaining that `None` maps to `CHECKS_PENDING_EMOJI` (not `-`).

2. **`review_thread_counts=None` displays as `0/0`** — Add comment to the display code clarifying this fall-through behavior.

3. **`update_metadata` immutable fields** — Add docstring to the `update_metadata()` method documenting that `schema_version`, `created_at`, and `created_by` are immutable.

---

## Contradiction Resolutions

No contradictions were detected. All existing docs are consistent with the changes in PR #7619.

## Stale Documentation Cleanup

No stale documentation requiring immediate cleanup. The diff shows four deleted files (`draft-pr-branch-sync.md`, `draft-pr-lifecycle.md`, `dependency-status-resolution.md`, `tui-subprocess-testing.md`) that were superseded/consolidated as part of PR #7619 itself. The existing-docs checker confirmed no phantom references to these deleted files remain in other docs.

**Note:** Verify that `docs/learned/planning/draft-pr-lifecycle.md` was truly deleted and its content merged into `lifecycle.md`. If references to the old path exist elsewhere, update them to point to the successor.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Wrong content section extracted from PR body

**What happened:** TUI showed only "Closes #7626" and a checkout command instead of the full PR summary for draft PR plans.
**Root cause:** `extract_plan_content()` fallback matched the `---` separator before the footer rather than the content separator before the summary. Post-implementation PR bodies have a different format than plan-creation bodies.
**Prevention:** When parsing draft PR bodies, first check the lifecycle stage. Stage 1 has `original-plan` details block; Stage 2 (post-CI) has freeform summary sections with overloaded `---` separators.
**Recommendation:** TRIPWIRE (score 5)

### 2. Missing workflow run data for draft PR plans

**What happened:** `run-id` and `run-state` columns always showed "-" for draft PR plans in the TUI.
**Root cause:** `DraftPRPlanListService.get_plan_list_data()` returned `workflow_runs={}` unconditionally. The dispatch node_id extraction and batch workflow run fetching pattern from `RealPlanListService` was not replicated.
**Prevention:** When adding a parallel service implementation, audit all data fields in the existing service and mirror them.
**Recommendation:** TRIPWIRE (score 6)

### 3. `fetch_plan_content` returned None for draft PR plans

**What happened:** TUI plan body modal showed "(No plan content found)" for all draft PR plans.
**Root cause:** `plan_body` passed to `fetch_plan_content` was already extracted content (no `plan-header` metadata block), but the function expected a raw issue body containing the block.
**Prevention:** Check `find_metadata_block(plan_body, "plan-header") is None` before attempting comment fetch.
**Recommendation:** TRIPWIRE (score 6)

### 4. `datetime.now(UTC)` in fake implementation

**What happened:** FakeGitHub used `datetime.now(UTC)` directly, bypassing the Time abstraction.
**Root cause:** The fake was written before Time injection was required in fakes (not just real implementations).
**Prevention:** Always grep for `datetime.now` when reviewing fakes. The time abstraction tripwire must extend to fake.py files.
**Recommendation:** TRIPWIRE (score 6)

### 5. Migration loses operational metadata

**What happened:** Plans migrated from issues to draft PRs lost all operational history (dispatch IDs, impl sessions, worktree names).
**Root cause:** `create_plan` hardcodes all operational fields to `None`. The migration tool only passed structural fields.
**Prevention:** After `create_plan`, collect non-null operational fields from the source plan-header and call `update_metadata` to restore them.
**Recommendation:** ADD_TO_DOC

### 6. `prettier-check` CI failure on plan branch data

**What happened:** CI failed because `.erk/branch-data/plan.md` was not formatted.
**Root cause:** `erk exec plan-save` generates prose but does not auto-format it. The file is committed to git and checked by CI.
**Prevention:** Run `prettier --write .erk/branch-data/plan.md` after every `erk exec plan-save` before committing.
**Recommendation:** TRIPWIRE (score 4)

### 7. Pre-existing test failures attributed to new changes

**What happened:** 128 test failures in `make fast-ci` appeared related to the implementation.
**Root cause:** Failures were pre-existing on the plan branch, unrelated to the current implementation.
**Prevention:** Use the `git stash + pytest + git stash pop` pattern to verify before debugging.
**Recommendation:** ADD_TO_DOC

### 8. Shell echo with multiline JSON causes parse errors

**What happened:** Piping multiline JSON through `echo` to `erk exec resolve-review-threads` failed with "Invalid control character" JSON parse error.
**Root cause:** Shell metacharacters and embedded newlines corrupt the JSON payload.
**Prevention:** Use Python subprocess with `json.dumps()` for JSON payloads with embedded newlines.
**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. DraftPRPlanListService must mirror RealPlanListService

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before editing `RealPlanListService.get_plan_list_data()` to add new data fields
**Warning:** Also update `DraftPRPlanListService.get_plan_list_data()` to mirror the same changes — the two services are parallel implementations. Missing this causes silent data gaps ("-" values) in the TUI for draft PR plans.
**Target doc:** `docs/learned/planning/draft-pr-plan-backend.md`

This is tripwire-worthy because the two services are in the same file but serve different plan backends. An agent modifying one may not realize the other needs the same change. The failure mode is silent — TUI columns show "-" with no error, so the gap is only discovered when a user notices missing data.

### 2. Time injection required in fakes (not just real implementations)

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before editing `fake.py` gateway files and using `datetime.now()`
**Warning:** Use injected `self._time.now().replace(tzinfo=UTC)` instead. Add `time: Time | None = None` to constructor defaulting to `FakeTime()`.
**Target doc:** `docs/learned/testing/fake-github.md`

The existing time abstraction tripwire covers production code but not fakes. Fakes using `datetime.now()` produce non-deterministic timestamps that make tests flaky and defeat time-based assertions.

### 3. fetch_plan_content plan_body is pre-extracted for draft PRs

**Score:** 6/10 (criteria: Non-obvious +2, Destructive potential +2, Silent failure +2)
**Trigger:** Before calling `fetch_plan_content(plan_id, plan_body)` for draft PR plans
**Warning:** `plan_body` may be pre-extracted content (DraftPRPlanListService calls `extract_plan_content()` before storing). Detect with `find_metadata_block(plan_body, "plan-header") is None` — return body directly.
**Target doc:** `docs/learned/planning/draft-pr-plan-service.md`

Without this tripwire, agents will assume `plan_body` always contains a raw issue body with a metadata block. For draft PR plans, the extraction has already happened upstream. The failure mode is returning `None` (no plan content found) when perfectly valid content was passed in.

### 4. New GitHub gateway method requires 5-place implementation

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +1)
**Trigger:** Before adding a new method to the GitHub gateway ABC
**Warning:** Implement in all 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py. Missing any place causes a runtime AbstractMethodError.
**Target doc:** `docs/learned/architecture/gateway-abc-implementation.md`

This tripwire exists conceptually in the gateway docs but needs explicit mention. A new method added only to the ABC and real implementation will crash in tests (FakeGitHub) or dry-run mode.

### 5. `plan-*` branches not found by `extract_leading_issue_number()`

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** Before extending `_build_worktree_mapping()` for new branch formats
**Warning:** Two paths: `extract_leading_issue_number()` for `P{num}-` branches; `read_plan_ref()` for `plan-*` branches. New formats need their own fallback.
**Target doc:** `docs/learned/planning/draft-pr-plan-service.md`

The worktree-to-plan mapping silently excludes branches it cannot parse. Adding a new branch format without adding a corresponding fallback causes those worktrees to be invisible in the TUI.

### 6. Draft PR body format differs between lifecycle stages

**Score:** 5/10 (criteria: Non-obvious +2, Destructive potential +2, External tool quirk +1)
**Trigger:** Before parsing draft PR body content
**Warning:** Check lifecycle stage: Stage 1 bodies have `original-plan` details block; Stage 2 (post-CI) bodies are freeform summaries. The `---` separator is overloaded — appears both between sections and before the footer.
**Target doc:** `docs/learned/planning/lifecycle.md`

This caused the primary bug in this plan — extracting the wrong content section from a post-implementation PR body. The format change is performed by CI and is not documented anywhere agents would naturally look.

### 7. `prettier --write .erk/branch-data/plan.md` before CI

**Score:** 4/10 (criteria: Non-obvious +2, Destructive potential +2)
**Trigger:** After `erk exec plan-save` on a plan branch before committing
**Warning:** Run `prettier --write .erk/branch-data/plan.md` — `erk exec plan-save` does not auto-format; CI `prettier-check` will fail.
**Target doc:** `docs/learned/planning/tripwires.md`

Every plan save requires this manual step. The failure is not destructive (CI catches it) but wastes a full CI cycle.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. `gt delete` replaces deprecated `gt branch delete`

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Lower priority — the old form still works and just shows a deprecation warning. Would be promoted if the old form is actually removed in a future gt release.

### 2. `lambda` in `default_factory` is forbidden

**Score:** 3/10 (criteria: Non-obvious +2, Repeated pattern +1)
**Notes:** Already partially captured in the frozen dataclass rule. Worth an explicit mention in conventions.md but the pattern is caught by code review, not by agents in the moment.

### 3. `grep -P` fails on macOS

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Cross-platform gotcha that affects all bash commands in the codebase. Low frequency because most grep usage in erk goes through the Grep tool, not raw bash. Would be promoted if agents started using raw bash grep more frequently.

### 4. Shell echo with multiline JSON fails

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** Specific to `erk exec` commands that accept JSON stdin. Rare but painful when encountered. Would be promoted if more erk exec commands adopt JSON stdin.

### 5. `except Exception` at gateway call sites is intentional

**Score:** 2/10 (criteria: Non-obvious +2)
**Notes:** This is a recurring bot false positive rather than an agent error. Documenting the rationale in `gateway-error-boundaries.md` (item 6) is sufficient — it doesn't need a tripwire because it's not an action agents take incorrectly, but rather a review comment they need to respond to correctly.
