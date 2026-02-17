---
title: Slash Command LLM Turn Optimization
read_when:
  - "writing a slash command that makes 3+ sequential tool calls to fetch data"
  - "optimizing a slash command that feels slow due to many LLM round-trips"
  - "deciding whether to bundle API calls into an exec script or keep them in the command"
category: cli
tripwires:
  - action: "making LLM fetch data sequentially when it could be bundled"
    warning: "Extract 3+ mechanical sequential calls into an exec script. Each tool call costs a full LLM round-trip."
  - action: "creating exec scripts for operations requiring LLM reasoning between steps"
    warning: "Keep conditional logic in slash commands. Only bundle mechanical API calls where all input params are known upfront."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Slash Command LLM Turn Optimization

## Why This Matters

Every tool call in a slash command costs a full LLM round-trip: the agent generates the call, waits for execution, then processes the result before generating the next call. For slash commands that fetch multiple pieces of related data (objective body, plan body, PR details), sequential tool calls dominate execution time — the LLM spends most of its turns on mechanical data fetching rather than the reasoning that actually requires intelligence.

The fix is to push mechanical fetching into a single exec script, giving the LLM all the data it needs in one round-trip.

## Decision Framework: Bundle vs Keep Sequential

| Condition                      | Bundle into exec script       | Keep in slash command                                    |
| ------------------------------ | ----------------------------- | -------------------------------------------------------- |
| Number of calls                | 3+ sequential fetches         | 1-2 calls                                                |
| Reasoning needed between calls | No — all params known upfront | Yes — LLM must analyze result N before deciding call N+1 |
| Dependency structure           | Independent or simple chain   | Complex conditional branching                            |
| User interaction needed        | No                            | Yes                                                      |

**The key test**: Can you write all the API calls as a straight-line script with no conditionals? If yes, bundle them. If the LLM needs to make decisions between fetches, keep them in the slash command.

## The Two-Phase Pattern

Optimized slash commands follow a two-phase structure:

**Phase 1 — Bulk fetch (1 turn):** A single `erk exec` call returns all needed data as JSON.

**Phase 2 — Reason and act (2-3 turns):** The LLM analyzes the complete dataset, composes outputs, and executes writes (ideally in parallel).

<!-- Source: .claude/commands/erk/objective-update-with-landed-pr.md, Step 0 -->
<!-- Source: src/erk/cli/commands/exec/scripts/objective_fetch_context.py, objective_fetch_context -->

The `objective-update-with-landed-pr` command demonstrates this: Step 0 calls `erk exec objective-fetch-context` once to fetch the objective issue, plan issue, PR details, and parsed roadmap context. The subagent then has everything it needs to compose the update and post the comment in parallel — reducing ~8 turns to ~4.

## Write-Side Parallelism

After the bulk fetch, independent _writes_ can also be parallelized. When a slash command needs to both post a comment and update an issue body, instruct the LLM to invoke both Bash tools in a single message. Claude Code executes parallel tool calls concurrently, saving another round-trip.

## Anti-Pattern: Bundling Conditional Logic

```python
# WRONG: Don't put this in an exec script
result1 = fetch_data()
if llm_needs_to_analyze(result1):
    result2 = fetch_more_data()
else:
    result2 = fetch_different_data()
```

If the choice of what to fetch next depends on LLM reasoning about previous results, that logic must stay in the slash command. Exec scripts are for mechanical operations with predetermined control flow.

## Relationship to TypedDict Schemas

Bundled exec scripts produce JSON consumed by the LLM. The TypedDict schema pattern (documented in [Exec Script Schema Patterns](exec-script-schema-patterns.md)) applies here: define the result shape in `erk_shared` so both the script and any Python consumers get type-safe access. For slash commands specifically, the TypedDict also documents the JSON contract the LLM will receive, making the command easier to maintain.

## See Also

- [Exec Script Patterns](exec-script-patterns.md) — Context injection, gateway imports, result dataclass pattern
- [Exec Script Schema Patterns](exec-script-schema-patterns.md) — TypedDict in erk_shared, cast() consumer pattern
- [Exec Script Testing](../testing/exec-script-testing.md) — How to test exec scripts
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — Error return types for exec script output
