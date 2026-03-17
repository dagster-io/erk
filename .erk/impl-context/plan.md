# Plan: Surface PR-Level Reviews in get-pr-feedback Pipeline

## Context

`erk:pr-address` completely misses "requested changes" reviews when a reviewer submits a PR-level review without inline comments. The `get-pr-feedback` pipeline only fetches `reviewThreads` (inline code comments via GraphQL) but never fetches PR-level `reviews`. This means a CHANGES_REQUESTED review with just a body comment is invisible to the classifier, which reports 0 actionable items.

GitHub has two distinct review concepts:
- **Review threads** (`reviewThreads`): inline code comments on specific lines/files — currently fetched
- **Reviews** (`reviews`): PR-level review submissions with state (APPROVED, CHANGES_REQUESTED, etc.) and a body — **not fetched**

## Approach

Add a new `get_pr_reviews()` gateway method (4-place: ABC, real, fake, dry_run) that fetches PR-level reviews via a new GraphQL query, wire it into `get_pr_feedback.py` as a third parallel fetch, and update the classifier skill to handle the new data.

## Steps

### 1. Add `PRReview` type to `types.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/types.py`

- Add `PRReviewState = Literal["PENDING", "COMMENTED", "APPROVED", "CHANGES_REQUESTED", "DISMISSED"]`
- Add frozen dataclass `PRReview` with fields: `id: str`, `author: str`, `body: str`, `state: PRReviewState`, `submitted_at: str`

### 2. Add GraphQL query to `graphql_queries.py`

**File:** `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`

Add `GET_PR_REVIEWS_QUERY` — fetches `reviews(first: 100, states: [CHANGES_REQUESTED, APPROVED, COMMENTED])` with fields: `id`, `author { login }`, `body`, `state`, `submittedAt`. Excludes PENDING (drafts) and DISMISSED (superseded).

### 3. Add abstract method to ABC (4-place pattern)

**File:** `packages/erk-shared/src/erk_shared/gateway/github/abc.py`

Add `get_pr_reviews(self, repo_root: Path, pr_number: int) -> list[PRReview]` — read-only method, no `include_resolved` style filtering needed.

### 4. Implement in real, dry_run, fake

- **`real.py`** (~line 1957): Follow `get_pr_review_threads` pattern — execute GraphQL query, parse response into `PRReview` objects, sort by `submitted_at`
- **`dry_run.py`**: Delegate to wrapped (read-only method)
- **`tests/fakes/gateway/github.py`**: Add `pr_reviews: dict[int, list[PRReview]] | None = None` constructor param, return from `get_pr_reviews()`

### 5. Wire into `get_pr_feedback.py`

**File:** `src/erk/cli/commands/exec/scripts/get_pr_feedback.py`

- Add `ReviewDict` TypedDict and `_format_review()` helper
- Expand `ThreadPoolExecutor(max_workers=3)` with third parallel fetch: `github.get_pr_reviews()`
- Add `"reviews"` key to output JSON (before `review_threads`)

### 6. Update classifier skill

**File:** `.claude/skills/pr-feedback-classifier/SKILL.md`

- Document the new `reviews` field in the input description
- Add classification rules: CHANGES_REQUESTED with body = always actionable; APPROVED = informational; COMMENTED with body = actionable if request/question
- Add `type: "review_submission"` to output format to distinguish from inline `type: "review"`

### 7. Add tests

- Unit tests for `get_pr_feedback` including reviews in output
- Verify fake gateway returns configured reviews

## Verification

1. Run `make fast-ci` to verify type checking and unit tests pass
2. Manual test: run `erk exec get-pr-feedback --pr <number>` on a PR with a CHANGES_REQUESTED review to verify reviews appear in output
3. Run the classifier on that PR to verify CHANGES_REQUESTED reviews are classified as actionable

## Key Files

- `packages/erk-shared/src/erk_shared/gateway/github/types.py`
- `packages/erk-shared/src/erk_shared/gateway/github/graphql_queries.py`
- `packages/erk-shared/src/erk_shared/gateway/github/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/github/real.py`
- `packages/erk-shared/src/erk_shared/gateway/github/dry_run.py`
- `tests/fakes/gateway/github.py`
- `src/erk/cli/commands/exec/scripts/get_pr_feedback.py`
- `.claude/skills/pr-feedback-classifier/SKILL.md`
