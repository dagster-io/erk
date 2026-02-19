# Plan: One-Shot Instruction Enrichment

## Context

When `erk one-shot` receives messy input (e.g., pasted PR review feedback), the raw text is used directly for issue titles, PR titles, branch names, and commit messages — producing unreadable garbage like `[erk-plan] One-shot: fix this:\n\ngithub-actions\ngithub-actions\n2m ago\n\nTripwires ...` (see issue #7548).

This adds a lightweight inference step ("enrichment") that uses Haiku to extract a clean title and summary from the raw instruction before creating the skeleton issue. The raw instruction is preserved verbatim for the planning workflow.

## Implementation

### 1. New file: `src/erk/core/instruction_enricher.py`

Follows the `CommitMessageGenerator` pattern (same file: `src/erk/core/commit_message_generator.py`).

**Data model:**
```python
@dataclass(frozen=True)
class EnrichmentRequest:
    raw_instruction: str

@dataclass(frozen=True)
class EnrichedInstruction:
    title: str          # Clean short title, max 60 chars (for issue/PR/branch)
    summary: str        # 1-3 sentence summary (for issue/PR bodies)
    raw_instruction: str  # Original input, preserved verbatim
```

**`InstructionEnricher` class:**
- Constructor takes `PromptExecutor` (injectable, testable with `FakePromptExecutor`)
- `enrich(request) -> EnrichedInstruction` — main method
- **Short-circuit**: If instruction is already short (<=60 chars) and single-line, skip inference entirely — return as-is
- **Inference**: Call `execute_prompt()` with `model="haiku"`, custom system prompt, `tools=None`
- **Parsing**: Model outputs `TITLE: ...` and `SUMMARY: ...` on separate lines; parse with simple prefix matching
- **Fallback**: If inference fails OR output is unparseable, use first line truncated to 60 chars as title, first 200 chars as summary

**System prompt** instructs the model to:
- Extract the core actionable task from noisy input (GitHub UI artifacts, timestamps, usernames)
- Generate an imperative-mood title (max 60 chars)
- Generate a 1-3 sentence summary
- Output in `TITLE:` / `SUMMARY:` format

### 2. Modify: `src/erk/cli/commands/one_shot_dispatch.py`

Call enricher early in `dispatch_one_shot()`, after validation but before creating the skeleton issue. In dry-run mode, use fallback only (no inference call).

**Substitution map** — use `enriched.title` instead of raw instruction at these sites:

| Site | Currently | After |
|------|-----------|-------|
| PR title (L131) | `params.instruction[:60]` | `enriched.title` |
| Issue title (L169) | `params.instruction[:60]` | `enriched.title` |
| Branch name slug (L181) | `params.instruction` | `enriched.title` |
| Commit message (L214) | `params.instruction[:60]` | `enriched.title` |
| Skeleton issue body (L161-164) | `params.instruction` | `enriched.summary` |

**Preserved as raw** (no change):
- `.worker-impl/task.md` (L210) — raw instruction for the planning workflow
- Workflow inputs (L255) — raw instruction passed to CI
- PR body (L241) — raw instruction in "Instruction:" field
- Queued comment (L329) — raw instruction for audit trail

### 3. New test file: `tests/core/test_instruction_enricher.py`

Unit tests using `FakePromptExecutor` from `tests/fakes/prompt_executor.py`:

- **Success**: Messy input → clean TITLE/SUMMARY parsed correctly, raw preserved
- **Short-circuit**: Short single-line input → no inference call made (`len(executor.prompt_calls) == 0`)
- **Fallback on failure**: `simulated_prompt_error` set → first-line truncation used
- **Fallback on bad output**: Model returns no `TITLE:`/`SUMMARY:` markers → fallback
- **Title truncation**: Model returns >60 char title → truncated with `...`
- **Raw preserved**: `raw_instruction` field always equals original input

### 4. Update: `tests/commands/one_shot/test_one_shot_dispatch.py`

Existing tests continue to work without modification — the default `FakePromptExecutor` returns `"Test Title\n\nTest body"` which has no `TITLE:`/`SUMMARY:` markers, triggering the fallback path automatically.

Add one new test verifying the enriched path: configure `FakePromptExecutor` with `simulated_prompt_output="TITLE: Fix tripwire validation\nSUMMARY: ..."`, assert PR title and branch name use the enriched title while `task.md` still contains the raw instruction.

## Verification

1. `uv run pytest tests/core/test_instruction_enricher.py` — all enricher unit tests pass
2. `uv run pytest tests/commands/one_shot/` — existing dispatch tests still pass
3. `uv run ruff check src/erk/core/instruction_enricher.py` — lint clean
4. `uv run ty check src/erk/core/instruction_enricher.py` — type check clean