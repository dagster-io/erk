# Plan: PR Review with Task Pattern for Context Isolation

## Goal
Use inline Task pattern with "prose + structured JSON" output to fetch, classify, and summarize PR review feedback. Provides context isolation while returning actionable data.

## Core Pattern: Prose + Structured JSON

Subagent returns human-readable summary AND parseable JSON:

```
## Summary
PR #5944: 1 actionable item (missing integration tests), 12 informational comments skipped.

## Actionable Items
| # | Thread ID | Path | Line | Issue |
|---|-----------|------|------|-------|
| 1 | PRRT_kwDOPxC3hc5q73Ne | abc.py | 8 | Missing integration tests |

## Structured Data
\`\`\`json
{
  "pr_number": 5944,
  "pr_title": "BeadsGateway ABC with list_issues Method",
  "actionable_threads": [
    {"thread_id": "PRRT_kwDOPxC3hc5q73Ne", "path": "abc.py", "line": 8, "action": "Add integration tests"}
  ],
  "discussion_actions": [],
  "informational_count": 12
}
\`\`\`
```

Parent agent parses JSON block and has everything needed to act (resolve threads, modify files).

## Token Savings
- Direct approach: ~2,500-3,000 tokens (raw JSON in main context)
- Task approach: ~750-900 tokens (summary + structured data)
- **Savings: ~65-70%** context reduction

## Validated
- Tested on PR #5944
- Correctly identified 1 actionable item (missing integration tests)
- Correctly detected resolved issue (LBYL pattern clarified as compliant)

## Files to Modify

### 1. `.claude/commands/erk/pr-preview-address.md`
Replace entire command with Task delegation. Output is prose-only (no action needed).

### 2. `.claude/commands/erk/pr-address.md`
**Phase 1**: Replace direct fetch with Task returning prose + structured JSON.
Parent parses JSON, displays batched plan, acts on thread IDs.

**Phase 4**: Replace verification fetch with Task returning summary only.

### 3. `.claude/commands/erk/learn.md`
**Step 3 (analysis)**: Replace with Task for prose + JSON summary.
**Step 4 (gist save)**: Keep direct fetch (needs raw JSON for file save).

### 4. `docs/learned/architecture/task-context-isolation.md` (new)
Document the pattern:
- When to use Task for context isolation
- Prose + structured JSON output format
- How parent agent parses and acts on results

## Task Prompt Template

```
Task(
  subagent_type="general-purpose",
  model="sonnet",
  description="Fetch PR #XXXX feedback",
  prompt="""Fetch and classify PR review feedback for PR #XXXX.

## Steps
1. Run: erk exec get-pr-review-comments --pr XXXX
2. Run: erk exec get-pr-discussion-comments --pr XXXX
3. Parse and classify the JSON outputs

## Classification
- **Actionable**: Code changes requested, violations to fix, missing tests
- **Informational**: Bot status updates, CI results, Graphite stack comments
- **Resolved**: Threads with clarifying follow-up (e.g., "Clarification: this is compliant")

## Output Format

### Summary
[Human-readable paragraph: PR title, actionable count, informational count]

### Actionable Items
[Table with: #, Thread ID, Path, Line, Issue summary]

### Structured Data
```json
{
  "pr_number": N,
  "pr_title": "...",
  "actionable_threads": [
    {"thread_id": "PRRT_xxx", "path": "file.py", "line": N, "action": "..."}
  ],
  "discussion_actions": [
    {"comment_id": N, "action": "..."}
  ],
  "informational_count": N
}
```
"""
)
```

## Implementation Steps

1. Update `/erk:pr-preview-address` - full Task delegation
2. Update `/erk:pr-address` Phase 1 - Task with structured JSON, parent parses and acts
3. Update `/erk:pr-address` Phase 4 - Task for verification summary
4. Update `/erk:learn` Step 3 - Task for analysis context
5. Create `docs/learned/architecture/task-context-isolation.md`

## Verification
After changes:
1. Run `/erk:pr-preview-address` on a PR with review comments
2. Run `/erk:pr-address` on same PR, verify threads get resolved correctly
3. Run `/erk:learn` on a plan with PR, verify analysis works