# Plan: Add commit-history relevance check to `erk plan duplicate-check`

## Context

The `erk plan duplicate-check` command currently only checks a new plan against existing open plan issues for semantic duplicates. It doesn't check whether the plan's work has already been implemented via recent commits merged to master. This means a plan could pass the duplicate check even though its goal was already accomplished by merged work.

## Approach

Add a second LLM-based check that compares the plan content against recent master commit messages to detect if the work is already implemented. This is a separate concern from duplicate detection (plan-vs-plan) so it gets its own class, system prompt, and result type.

## Changes

### 1. Extend `get_recent_commits` gateway with `branch` parameter

**Files** (5-file gateway pattern):
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/abc.py` — add `branch: str | None = None` kwarg
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/real.py` — append branch ref to `git log` command when specified
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/fake.py` — add `recent_commits_by_branch: dict[tuple[Path, str], list[dict[str, str]]]` constructor param; look up from it when branch is specified, fall back to existing `_recent_commits` dict when branch is None
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/dry_run.py` — pass through `branch` kwarg
- `packages/erk-shared/src/erk_shared/gateway/git/commit_ops/printing.py` — pass through `branch` kwarg

### 2. Create `PlanRelevanceChecker`

**New file**: `src/erk/core/plan_relevance_checker.py`

Mirrors `plan_duplicate_checker.py` pattern:
- `RelevantCommit` frozen dataclass: `sha`, `message`, `explanation`
- `RelevanceCheckResult` frozen dataclass: `already_implemented: bool`, `relevant_commits: list[RelevantCommit]`, `error: str | None`
- `PlanRelevanceChecker` class: `__init__(executor: PromptExecutor)`, `check(plan_content: str, recent_commits: list[dict[str, str]]) -> RelevanceCheckResult`
- `RELEVANCE_CHECK_SYSTEM_PROMPT` — instructs Haiku to compare plan intent against commit messages, respond with JSON `{"already_implemented": bool, "relevant_commits": [{"sha": "...", "explanation": "..."}]}`
- Same graceful degradation pattern: LLM failure → `RelevanceCheckResult(already_implemented=False, relevant_commits=[], error="...")`
- Empty commits list → immediate return without LLM call

### 3. Extend `tests/fakes/prompt_executor.py` to support sequential outputs

Add `simulated_prompt_outputs: list[str] | None = None` constructor param. When provided and not exhausted, return successive outputs from this list. When exhausted (or not provided), fall back to existing `simulated_prompt_output` behavior. This lets command tests that make 2 LLM calls configure different responses for each.

### 4. Wire into CLI command

**File**: `src/erk/cli/commands/plan/duplicate_check_cmd.py`

After the existing duplicate check:
1. Detect trunk branch via `ctx.git.branch.detect_trunk_branch(repo_root)`
2. Fetch recent commits: `ctx.git.commit.get_recent_commits(repo_root, limit=20, branch=trunk_branch)`
3. If commits exist, run `PlanRelevanceChecker(ctx.prompt_executor).check(content, recent_commits)`
4. Display results: "Work may already be implemented:" with relevant commit SHAs and explanations
5. Exit code 1 if duplicates found OR already implemented, 0 otherwise

### 5. Tests

**New file**: `tests/core/test_plan_relevance_checker.py`
- `test_no_relevant_commits_found` — LLM says no match
- `test_relevant_commit_detected` — LLM returns match with SHA and explanation
- `test_executor_failure_graceful_degradation` — LLM error → safe default
- `test_empty_commits_no_llm_call` — empty list short-circuits
- `test_malformed_llm_response_graceful_degradation` — bad JSON handling
- `test_unknown_sha_filtered_out` — SHA not in input commits is dropped
- `test_json_wrapped_in_code_fence` — markdown fence handling

**Extend**: `tests/commands/plan/test_duplicate_check.py`
- `test_already_implemented_detected` — relevance check finds match, exit 1
- `test_no_duplicates_no_relevance_issues` — both checks pass, exit 0
- `test_relevance_error_does_not_block_duplicate_check` — relevance fails gracefully, duplicate result still shown

## Key patterns to follow

- `PlanDuplicateChecker` (`src/erk/core/plan_duplicate_checker.py`) — class structure, system prompt, parsing, graceful degradation
- `FakeGitCommitOps` (`packages/erk-shared/.../commit_ops/fake.py`) — constructor injection pattern for branch-specific data
- `detect_trunk_branch` (`ctx.git.branch.detect_trunk_branch(repo_root)`) — already exists in GitBranchOps, used in 30+ places

## Verification

1. Run core tests: `uv run pytest tests/core/test_plan_relevance_checker.py`
2. Run command tests: `uv run pytest tests/commands/plan/test_duplicate_check.py`
3. Run existing duplicate checker tests (no regressions): `uv run pytest tests/core/test_plan_duplicate_checker.py`
4. Type check: `ty`
5. Lint: `ruff check`
6. Manual: `erk plan duplicate-check --plan <number>` — should show both duplicate and relevance results
