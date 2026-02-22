# Plan: LLM-Generated Branch Name Slugs

## Context

Current branch names use `sanitize_worktree_name()` which mindlessly truncates raw plan/issue titles to 31 characters, producing ugly slugs like `add-discriminated-union-validat`. This plan adds a haiku inference call to distill titles into meaningful 2-4 word slugs before they enter the branch naming pipeline. The structural format (prefixes, timestamps) stays the same.

**Before:** `P7843-add-objective-context-mark-02-22-1430`
**After:** `P7843-objective-marker-fallback-02-22-1430`

## Implementation

### 1. Create `src/erk/core/branch_slug_generator.py`

Follow the `CommitMessageGenerator` pattern from `src/erk/core/commit_message_generator.py`.

**Types:**
- `BranchSlugResult` — frozen dataclass with `success: bool`, `slug: str | None`, `error_message: str | None`
- `BranchSlugGenerator` — concrete class taking `PromptExecutor`, with `generate(title: str) -> BranchSlugResult`
- `generate_slug_or_fallback(executor: PromptExecutor, title: str) -> str` — convenience function that returns the LLM slug on success, or the raw title on failure (so `sanitize_worktree_name` handles it downstream)

**System prompt** (inline constant):
```
You are a branch name slug generator. Given a title, return ONLY a concise
2-4 word slug using lowercase letters and hyphens. No explanation.

Rules:
- Use 2-4 hyphenated words (e.g., "fix-auth-session", "add-plan-validation")
- Capture the distinctive essence, not generic words
- Drop filler words: "the", "a", "for", "and", "implementation", "plan"
- Prefer verbs: add, fix, refactor, update, consolidate, extract, migrate
- Never exceed 30 characters total
- Output ONLY the slug, nothing else
```

**Post-processing:** Strip quotes/backticks, run through `sanitize_worktree_name` as safety net, validate 2+ words and max 30 chars.

### 2. Create `tests/core/test_branch_slug_generator.py`

Unit tests using `FakePromptExecutor` (from `erk_shared.core.fakes`):
- Successful slug generation
- Strips quotes/backticks from LLM output
- Falls back on executor failure
- Rejects single-word output
- Rejects too-long output
- `generate_slug_or_fallback` returns slug on success, raw title on failure

### 3. Integrate at 5 call sites

Each call site already has access to `PromptExecutor` via `require_prompt_executor(ctx)`. The pattern at each site:

```python
executor = require_prompt_executor(ctx)
slug = generate_slug_or_fallback(executor, title)
branch_name = generate_*_branch_name(slug, ...)
```

**Call sites:**

| File | Function | Branch type |
|------|----------|-------------|
| `src/erk/cli/commands/exec/scripts/plan_save.py` ~L140 | `save_plan_as_draft_pr` | `planned/` |
| `src/erk/cli/commands/submit.py` | `_validate_issue_for_submit` | `P{issue}-` |
| `src/erk/cli/commands/one_shot_dispatch.py` ~L60 | `generate_branch_name` | `P{issue}-` or `oneshot-` |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` | `setup_impl_from_issue` | `P{issue}-` |
| `src/erk/cli/commands/exec/scripts/plan_migrate_to_draft_pr.py` | migration flow | `planned/` |

**For `one_shot_dispatch.py`:** Add `prompt_executor: PromptExecutor | None` parameter to `generate_branch_name()`. When `None` (dry-run), skip inference and use raw prompt as before.

### Key files

- `src/erk/core/commit_message_generator.py` — pattern to follow
- `packages/erk-shared/src/erk_shared/naming.py` — `sanitize_worktree_name()`, `generate_issue_branch_name()`, `generate_draft_pr_branch_name()`
- `packages/erk-shared/src/erk_shared/context/helpers.py` — `require_prompt_executor()`
- `packages/erk-shared/src/erk_shared/core/fakes.py` — `FakePromptExecutor` with queue-based `prompt_results`

### Design notes

- **Model:** Hardcode `"haiku"` — always fast/cheap, no reason to vary
- **Fallback:** If LLM fails or is unavailable, raw title passes through to `sanitize_worktree_name()` — identical to current behavior
- **Existing tests:** Won't break — default `FakePromptExecutor` returns empty prompt results, which causes fallback to raw title (same as before)
- **Latency:** ~200-500ms per call, negligible vs. git/GitHub operations already in these flows

## Verification

1. Run unit tests: `pytest tests/core/test_branch_slug_generator.py`
2. Run affected call-site tests: `pytest tests/unit/cli/commands/exec/scripts/ tests/commands/`
3. Run full CI: `make fast-ci`
4. Manual test: `erk plan save` on a plan with a long title, verify the branch name has a meaningful slug
