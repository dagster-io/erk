# Push PR Feedback Classification into CLI Command

## Context

The `pr-feedback-classifier` skill (~245 lines) runs as a haiku agent to classify PR review feedback before `pr-address` processes it. Most of the work is mechanical: fetching data (3 bash commands), applying deterministic rules (APPROVED = informational, CHANGES_REQUESTED = actionable, bot detection), and constructing batched JSON output. Only action summaries, complexity estimation, and ambiguous classification genuinely need LLM judgment.

This is a textbook refac-cli-push-down opportunity: move mechanical computation into a tested CLI command, shrinking the skill from ~245 to ~50 lines.

## Approach

Create `erk exec classify-pr-feedback` that handles all deterministic work. The skill shrinks to: run command, fill in semantic fields, construct final output.

### What moves to CLI

| Work | Currently | After |
|------|-----------|-------|
| Data fetching (reviews, threads, comments) | 3 bash commands in skill | Single gateway call in CLI |
| Trunk detection + restructuring context | `detect-trunk-branch` + `git diff` | Inline in CLI |
| APPROVED reviews → informational | LLM rule-following | Python `if state == "APPROVED"` |
| CHANGES_REQUESTED → actionable | LLM rule-following | Python `if state == "CHANGES_REQUESTED"` |
| COMMENTED + empty body → informational | LLM rule-following | Python `if not body` |
| Bot detection (`[bot]` suffix) | LLM pattern matching | Python `author.endswith("[bot]")` |
| Pre-existing candidacy (bot + restructured) | LLM multi-factor check | Python boolean logic |
| Known informational discussion comments | LLM pattern matching | Python pattern matching |
| Output JSON scaffold + field names | ~100 lines of schema in prompt | Not needed in prompt |

### What stays in LLM

- **action_summary**: Summarizing what each comment requests
- **complexity**: local / single_file / cross_cutting / complex
- **COMMENTED reviews with body**: Is it a request/question or acknowledgment?
- **pre_existing confirmation**: Is the bot+restructured pattern truly generic?
- **Batch construction**: Depends on LLM-assigned complexity (simple 5-line rule table)

## Implementation

### 1. Create `src/erk/cli/commands/exec/scripts/classify_pr_feedback.py`

**Core design**: Pure `_classify_impl()` function + thin Click wrapper.

**Input**: `--pr <number>` (optional), `--include-resolved` (optional)

**Internal flow**:
1. Gateway calls: `get_pr_reviews`, `get_pr_review_threads`, `get_pr_discussion_comments` (parallel, same as `get-pr-feedback`)
2. Detect trunk branch via `git.branch.branch_exists_on_remote()` (same logic as `detect-trunk-branch`)
3. Run `git diff --name-status -M -C {trunk}...HEAD` via subprocess for rename detection
4. Apply mechanical classification rules
5. Output JSON

**Output JSON** (intermediate format, not final classifier schema):

```json
{
  "success": true,
  "pr_number": 5944,
  "pr_title": "...",
  "pr_url": "...",
  "review_submissions": [
    {
      "id": "PRR_abc",
      "author": "reviewer",
      "state": "CHANGES_REQUESTED",
      "body_preview": "Fix the auth flow...",
      "classification": "actionable",
      "is_bot": false
    },
    {
      "id": "PRR_xyz",
      "author": "reviewer",
      "state": "COMMENTED",
      "body_preview": "Looks good but...",
      "classification": "needs_llm",
      "is_bot": false
    }
  ],
  "review_threads": [
    {
      "thread_id": "PRRT_abc",
      "path": "src/api.py",
      "line": 42,
      "is_outdated": false,
      "author": "reviewer",
      "comment_preview": "Add integration tests...",
      "is_bot": false,
      "pre_existing_candidate": false
    }
  ],
  "discussion_comments": [
    {
      "comment_id": 12345,
      "author": "user",
      "body_preview": "Please update docs...",
      "classification": "needs_llm",
      "is_bot": false
    }
  ],
  "restructured_files": [
    {"old_path": "src/old.py", "new_path": "src/new.py", "status": "R"}
  ],
  "mechanical_informational_count": 5,
  "error": null
}
```

Key differences from final schema:
- No `action_summary`, `complexity`, or `batches` (LLM fills these)
- Reviews with mechanical classification have it pre-filled; ambiguous ones say `"needs_llm"`
- Threads have `pre_existing_candidate` flag for LLM to confirm
- `mechanical_informational_count` covers items the CLI pre-filtered

**Key helper functions**:
- `_parse_name_status_output(output: str) -> tuple[RestructuredFile, ...]` - Pure function parsing git diff output
- `_is_bot(author: str) -> bool` - `[bot]` suffix check
- `_is_known_informational_discussion(author: str, body: str) -> bool` - Pattern matching for CI/Graphite bots
- `_classify_impl(reviews, threads, comments, restructured_files) -> ClassificationResult` - Core logic

**Frozen dataclasses** for the output types (ClassifiedReview, ClassifiedThread, ClassifiedDiscussionComment, RestructuredFile, ClassificationResult).

### 2. Create `tests/unit/cli/commands/exec/scripts/test_classify_pr_feedback.py`

Test the pure functions directly:

- `_parse_name_status_output`: R100, R085, C100, A/M/D lines, empty input
- `_is_bot`: `user[bot]` → True, `user` → False
- `_is_known_informational_discussion`: CI bot, Graphite stack, regular user comment
- `_classify_impl`:
  - APPROVED review → informational count, not in review_submissions
  - CHANGES_REQUESTED → actionable review_submission
  - COMMENTED empty body → informational count
  - COMMENTED with body → needs_llm
  - Bot + restructured path → pre_existing_candidate=True
  - Human + restructured path → pre_existing_candidate=False
  - No feedback → empty result
- CLI integration: CliRunner with FakeGit/FakeLocalGitHub

### 3. Register in `src/erk/cli/commands/exec/group.py`

Add import and `exec_group.add_command(classify_pr_feedback, name="classify-pr-feedback")`.

### 4. Simplify `.claude/skills/pr-feedback-classifier/SKILL.md`

**Before**: ~245 lines (data fetching, classification model, batch rules, full output schema, field notes, error cases)

**After**: ~50 lines:

```markdown
# PR Feedback Classifier

## Steps

1. Run: `erk exec classify-pr-feedback [--pr <number>] [--include-resolved]`

2. For each item in the output:
   - **review_submissions with classification "needs_llm"**: Determine if actionable or informational
   - **All actionable items**: Write action_summary (brief description of requested change)
   - **All actionable items**: Assign complexity (local/single_file/cross_cutting/complex)
   - **Threads with pre_existing_candidate=true**: Confirm if truly pre-existing (generic code quality issue, not specific to restructuring). If confirmed, set complexity to "pre_existing"

3. Construct final JSON output with batches grouped by complexity.

## Complexity Levels
- local: Single line change at specified location
- single_file: Multiple changes in one file
- cross_cutting: Changes across multiple files
- complex: Architectural changes

## Batch Ordering
0. Pre-Existing (auto_proceed: true)
1. Local Fixes (auto_proceed: true)
2. Single-File (auto_proceed: true)
3. Cross-Cutting (auto_proceed: false)
4. Complex (auto_proceed: false)
5. Informational (auto_proceed: false)

## Output Format
[existing JSON schema preserved - same contract with pr-address]
```

The output schema section stays (it's the contract with pr-address) but the ~100 lines of classification rules, data fetching instructions, and field notes are eliminated.

## Files Changed

| File | Action |
|------|--------|
| `src/erk/cli/commands/exec/scripts/classify_pr_feedback.py` | Create |
| `tests/unit/cli/commands/exec/scripts/test_classify_pr_feedback.py` | Create |
| `src/erk/cli/commands/exec/group.py` | Modify (add import + registration) |
| `.claude/skills/pr-feedback-classifier/SKILL.md` | Modify (simplify ~245 → ~50 lines) |

No changes to: `get-pr-feedback` (still useful independently), `pr-address.md` (output contract preserved), gateway ABCs.

## Verification

1. Run `erk exec classify-pr-feedback --pr <test-PR>` and verify JSON output has correct mechanical classifications
2. Run tests: `pytest tests/unit/cli/commands/exec/scripts/test_classify_pr_feedback.py`
3. Invoke the simplified skill via Task and verify it produces the same final output schema as before
4. Run `/erk:pr-address` end-to-end on a PR with review comments and verify the workflow still works
5. Run CI: `make fast-ci`
