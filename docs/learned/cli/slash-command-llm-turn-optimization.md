---
title: Slash Command LLM Turn Optimization
read_when:
  - "writing slash commands that need to fetch multiple pieces of related data"
  - "optimizing slash commands that take too many LLM turns"
  - "noticing repeated sequential subprocess calls in slash commands"
  - "designing exec scripts for bundled API operations"
category: cli
tripwires:
  - action: "making LLM fetch data sequentially when it could be bundled"
    warning: "Extract 3+ mechanical sequential calls into an exec script. Bundle objective/plan/PR fetches into objective-update-context pattern."
  - action: "creating exec scripts for operations requiring LLM reasoning between steps"
    warning: "Keep conditional logic in slash commands. Only bundle mechanical API calls where input params are known upfront."
  - action: "forgetting to add TypedDict schemas for exec script JSON output"
    warning: "Define TypedDict in erk_shared for type-safe JSON parsing. Create separate dicts for success result and error result."
last_audited: "2026-02-05 13:19 PT"
audit_result: edited
---

# Slash Command LLM Turn Optimization

## Problem

Slash commands that fetch multiple related pieces of data sequentially waste LLM turns:

**Before optimization:**

1. LLM runs: `gh issue view --json body`
2. LLM waits for response
3. LLM runs: `gh pr view --json title,body`
4. LLM waits for response
5. LLM runs: `gh issue view <plan> --json body`
6. LLM waits for response
7. LLM analyzes all data and composes update

**Result:** ~8 LLM turns, slow execution

## Solution Pattern

Bundle mechanical API calls into a single exec script that returns all data as JSON:

**After optimization:**

1. LLM runs: `erk exec objective-update-context --pr X --objective Y --branch Z`
2. LLM receives complete JSON blob with all data
3. LLM analyzes and composes update

**Result:** ~4 LLM turns, fast execution

## Decision Framework

**Extract into exec script when:**

- ✅ 3+ sequential subprocess calls are needed
- ✅ All operations are mechanical (no reasoning between steps)
- ✅ Input parameters are known at the start
- ✅ Operations are independent or have simple dependencies

**Keep in slash command when:**

- ❌ LLM needs to reason about results between operations
- ❌ Conditional logic based on complex business rules
- ❌ Only 1-2 operations needed
- ❌ Operations require user interaction

## Implementation Example

**Slash command:** `.claude/commands/erk/objective-update-with-landed-pr.md`

**Old approach (sequential):**

```bash
# In slash command, run these one at a time:
gh issue view <objective> --json body,title,state,labels,url
gh issue view <plan> --json body,title
gh pr view <pr> --json title,body,commits
```

Each call requires a separate LLM turn to execute.

**New approach (bundled):**

```bash
# In slash command, run once:
erk exec objective-update-context --pr <number> --objective <number> --branch <name>
```

**Exec script:** `src/erk/cli/commands/exec/scripts/objective_update_context.py`

See `objective_update_context()` in `src/erk/cli/commands/exec/scripts/objective_update_context.py:52` for the full implementation.

**Impact:** Reduced from ~8 turns to ~4 turns

## TypedDict Schema Pattern

Always define TypedDict schemas in `erk_shared` for exec script output:

**File:** `packages/erk-shared/src/erk_shared/objective_update_context_result.py`

See `packages/erk-shared/src/erk_shared/objective_update_context_result.py` for the canonical TypedDict definitions (`ObjectiveInfoDict`, `PlanInfoDict`, `PRInfoDict`, `ObjectiveUpdateContextResultDict`, `ObjectiveUpdateContextErrorDict`).

**Why TypedDict:**

- Type-safe JSON parsing in slash commands
- Editor autocomplete for result fields
- Type checking catches field name typos
- Documents the contract between exec script and slash command

## Parallel Tool Invocation

After fetching bundled data, execute independent writes in parallel:

**From:** `.claude/commands/erk/objective-update-with-landed-pr.md` Step 0 subagent instructions (task 4)

```bash
# Post action comment
gh issue comment <issue-number> --body "$(cat <<'EOF'
[action comment content]
EOF
)"
```

```bash
# Update objective body
erk exec update-issue-body <issue-number> --body "$(cat <<'BODY_EOF'
<full updated body text>
BODY_EOF
)"
```

The LLM can invoke both Bash tools in a single message, running them concurrently.

## When NOT to Optimize

**Counter-example: Don't bundle conditional logic**

If operations depend on complex reasoning:

```python
# BAD: Don't bundle this into exec script
result1 = fetch_data()
if llm_needs_to_analyze(result1):
    result2 = fetch_more_data()
else:
    result2 = fetch_different_data()
```

Keep this in the slash command so the LLM can make decisions between steps.

## Related Patterns

- [Exec Script Testing](../testing/exec-script-testing.md) - How to test exec scripts
- [Output Abstraction](output-styling.md#output-abstraction) - JSON to stdout, messages to stderr
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Error return types

## Verification

To verify optimization impact, compare before/after:

1. Count subprocess calls in the old slash command
2. Count subprocess calls in the new slash command
3. Measure LLM turn count before and after (observe in Claude Code session)

**Example:** objective-update-with-landed-pr reduced from ~8 to ~4 turns
