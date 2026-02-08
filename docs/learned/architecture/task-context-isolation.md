---
title: Task Context Isolation Pattern
read_when:
  - "fetching large JSON responses from APIs"
  - "parsing PR review comments or GitHub issues"
  - "analyzing verbose API responses that pollute context"
  - "need to reduce context window usage"
  - "returning structured data from subagents"
  - "choosing between context: fork vs manual Task delegation"
last_audited: "2026-02-08"
audit_result: clean
---

# Task Context Isolation Pattern

## The Problem

Large API responses stay in the main conversation context indefinitely, wasting tokens on data the parent agent doesn't need. A PR review comment fetch can consume 2,500-3,000 tokens of raw JSON when the parent only needs thread IDs and action summaries (~750 tokens).

This pattern achieves 65-70% context reduction by processing verbose data in isolated subagent contexts.

## The Insight

**Subagent contexts are disposable.** When a Task completes, its context (including all the verbose API responses) disappears. Only the Task's final output enters the parent conversation.

This creates an isolation boundary: fetch and process in the subagent, return only compact summaries to the parent.

## Decision: context: fork vs Manual Task

| Aspect               | `context: fork`                   | Manual Task                             |
| -------------------- | --------------------------------- | --------------------------------------- |
| Use when             | Reusable fetch/classify patterns  | One-off operations with dynamic prompts |
| Declaration          | Frontmatter in skill/command file | Inline Task() call in command           |
| Reusability          | Skill invocable anywhere          | Single-use per command                  |
| Prompt content       | Static (in skill file)            | Dynamic (built at runtime)              |
| Maintenance          | Centralized updates               | Duplicated across commands              |
| Conversation context | None (fork isolates)              | None (Task isolates)                    |

**Prefer `context: fork`** for fetch-and-classify patterns you'll use repeatedly. See `docs/learned/claude-code/context-fork-feature.md` for frontmatter details.

**Use manual Task** when prompt content depends on runtime values from the parent conversation.

## Pattern Components

### 1. Fetch Phase (Subagent)

The subagent has full tool access. It runs bash commands, fetches API data, reads files — all the verbose operations that would pollute parent context.

### 2. Classification Phase (Subagent)

The subagent applies classification logic. For PR comments: actionable vs informational. For issues: by complexity. The parent doesn't see this reasoning, only the results.

### 3. Output Phase (Subagent)

The subagent returns two formats in one response:

- **Prose summary** — Human-readable for display to user
- **Structured JSON** — Machine-parseable for parent to act on

Both appear in the subagent's final message. The parent reads both from the Task result.

### 4. Action Phase (Parent)

The parent extracts the JSON (regex match on ` ```json ... ``` ` code blocks), parses it, and acts on the structured data without ever seeing the raw API response.

## Implementation Pointers

<!-- Source: .claude/skills/pr-feedback-classifier/SKILL.md, output format -->

See `pr-feedback-classifier` skill in `.claude/skills/pr-feedback-classifier/SKILL.md` for the canonical `context: fork` implementation. Note the output format structure — both prose table and JSON in one response.

<!-- Source: .claude/commands/erk/pr-address.md, Phase 1 classification -->
<!-- Source: .claude/commands/erk/pr-preview-address.md, Phase 1 classification -->

See `/erk:pr-address` and `/erk:pr-preview-address` commands for invocation patterns. Both invoke the skill, parse JSON from the result, and use thread IDs from the JSON to act.

<!-- Source: .claude/commands/erk/learn.md, Agent 1-4 parallel launch -->

See `/erk:learn` command for manual Task delegation. Note how it builds dynamic prompts with runtime values (session IDs, PR numbers) that couldn't be static in a skill file.

## Token Savings Measured

| Approach               | Tokens       | Why                                     |
| ---------------------- | ------------ | --------------------------------------- |
| Direct fetch in parent | ~2,500-3,000 | Raw JSON persists in context            |
| Task isolation         | ~750-900     | Only summary + structured data returned |
| **Reduction**          | **65-70%**   | Raw JSON never enters parent context    |

These measurements come from PR review comment fetches (20-30 comment threads). Larger responses see higher savings.

## When to Use

Use this pattern when:

- **API responses are verbose** — GitHub API returns full objects with metadata you don't need
- **Parent needs structured data, not raw JSON** — Thread IDs, comment IDs, classification labels
- **Context window is constrained** — You're doing multiple operations and need to preserve space
- **Classification logic is complex** — Subagent can reason through classification without bloating parent context

## When NOT to Use

Skip this pattern when:

- **Response is small** (<500 tokens) — Isolation overhead not worth it
- **Need to save raw data** — If you're writing raw JSON to gist files, fetch in parent
- **Parent needs to reason about details** — If classification might be wrong and parent needs to verify, keep data in parent context

## Anti-Pattern: Leaking Context Through Prose

WRONG:

```markdown
## Summary

Found 3 actionable threads:

Thread PRRT_abc at foo.py:42 says: "This needs to use LBYL pattern instead of EAFP. The current approach with try/except creates misleading error traces because..."

[... 2000 more tokens of quoted comment text ...]
```

This defeats the isolation. The subagent copied the verbose comment text into the prose summary, which the parent sees.

RIGHT:

```markdown
## Summary

3 actionable threads, 12 informational skipped.

| #   | Location  | Issue               | Complexity |
| --- | --------- | ------------------- | ---------- |
| 1   | foo.py:42 | Use LBYL pattern    | local      |
| 2   | bar.py:15 | Add type annotation | local      |

See JSON below for thread IDs.
```

The prose is compact. Full context lives in the JSON's `original_comment` field (first 200 chars for debugging), but parent doesn't need to parse it.

## Model Selection for Subagents

| Task Type                    | Model  | Why                                                 |
| ---------------------------- | ------ | --------------------------------------------------- |
| Mechanical classification    | haiku  | Deterministic rules, no creativity needed           |
| Context-aware classification | sonnet | Understands reviewer intent, nuance                 |
| Complex reasoning            | opus   | Multi-factor decisions, architectural understanding |

<!-- Source: .claude/commands/erk/learn.md, model choices for parallel agents -->

See `/erk:learn` command for examples: session-analyzer uses sonnet (patterns require reasoning), diff-analyzer uses sonnet (architectural significance), plan-synthesizer uses opus (creative authoring).

## Output Format: The Double-Delivery Pattern

Why return both prose AND JSON in one response?

1. **Prose displays to user** — They see what was found without parsing JSON
2. **JSON enables parent action** — Parent extracts structured data for API calls
3. **Single message** — No need for two Task invocations

The parent shows the prose to the user, then silently parses the JSON to get thread IDs for resolution.

## Error Handling in Isolation

Errors should appear in BOTH formats:

**Prose:**

```
Error: No PR found for branch feature-xyz
```

**JSON:**

```json
{
  "success": false,
  "error": "No PR found for branch feature-xyz",
  "actionable_threads": [],
  "batches": []
}
```

The parent checks `success` field first. If false, display error and exit. This prevents the parent from trying to parse empty arrays.

## Historical Context

This pattern emerged from early PR addressing commands that fetched comments directly in the parent conversation. After 3-4 addressing sessions, the context window filled with stale PR comment JSON from earlier fetches.

The first isolation attempt used a Task that returned only prose. This worked for preview commands but broke action commands — the parent needed thread IDs from the prose via regex, which was brittle.

The double-delivery pattern (prose + JSON) solved both problems: human-readable display and machine-parseable data in one output.

The `context: fork` feature (Claude Code 2.1.0+) replaced manual Task delegation for reusable patterns. `pr-feedback-classifier` became a skill instead of inline Task prompts duplicated across commands.

## Related Documentation

- [Context Fork Feature](../claude-code/context-fork-feature.md) — Declarative isolation via skill frontmatter
- [Skill Composition Patterns](../claude-code/skill-composition-patterns.md) — When to use skills vs commands
- [PR Operations](../pr-operations/pr-operations.md) — Commands that use this pattern
