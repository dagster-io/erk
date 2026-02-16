# Documentation Plan: Add progress logging to erk docs sync

## Context

This plan captures learnings from a clean implementation of progress logging for the `erk docs sync` command. The user reported that the command appeared to hang with no output when syncing ~55 documentation files. The solution added an optional callback parameter (`on_progress`) to the operations layer, allowing the CLI to inject progress logging while keeping operations framework-agnostic.

The implementation reveals an important architectural pattern not previously documented: the **callback progress pattern**. This is a simpler alternative to the existing event-based progress pattern (documented in `event-progress-pattern.md`) and is better suited for synchronous operations with lightweight, string-based progress reporting. The existing documentation only covered the complex generator-based pattern, which created subtle pressure to over-engineer simple use cases.

The sessions were executed flawlessly: zero errors, all CI checks passed on first attempt, and no user corrections. This validates the Explore -> Plan -> Implement workflow and demonstrates that detailed planning enables clean execution. The key insights worth preserving are the callback pattern itself, when to choose it over event generators, and the milestone-based approach to progress granularity.

## Raw Materials

https://gist.github.com/schrockn/54fdc94e3bc671eac7bd77fd14ba32e2

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 0     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Callback Progress Pattern

**Location:** `docs/learned/architecture/callback-progress-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Callback Progress Pattern
read_when:
  - "adding progress reporting to operations functions"
  - "choosing between callback and event-based progress"
  - "implementing synchronous progress feedback"
---

# Callback Progress Pattern

For operations that need simple progress reporting without the complexity of event generators, use an optional callback parameter.

## When to Use This Pattern

Choose callbacks over event generators when:

- Operations are synchronous
- Progress is lightweight (operation names/milestones only)
- Single consumer (typically CLI output)
- No structured event data needed

For complex async operations with multiple event types or structured data, see [Event-Based Progress Pattern](event-progress-pattern.md).

## Implementation Pattern

### Function Signature

Add an optional callback parameter as keyword-only with union type including None. See `sync_agent_docs()` in `src/erk/agent_docs/operations.py` for the reference implementation.

Key elements:
- Parameter: `on_progress: Callable[[str], None] | None`
- Position: Last parameter, after all required parameters
- Import `Callable` from `collections.abc`

### Invocation Guard

Before invoking the callback, check for None using LBYL pattern:

```python
if on_progress is not None:
    on_progress("Progress message...")
```

This allows callers to opt out by passing `None`.

### CLI Binding

In CLI commands, bind the callback to styled output. See `sync.py` in `src/erk/cli/commands/docs/` for the lambda pattern that routes progress to styled stderr.

### Test Pattern

Pass `on_progress=None` in tests to preserve existing behavior without mock complexity. Only test callback invocation if specifically testing the progress feature.

## Milestone Granularity

For operations processing many items (>10), use milestone-based progress rather than per-item reporting:

- **<10 items**: Per-item progress acceptable
- **10-100 items**: Use milestones at operation boundaries
- **>100 items**: Consider percentage or count indicators

Example: `erk docs sync` processes ~55 files but reports only 6 milestones.

## Related Documentation

- [Event-Based Progress Pattern](event-progress-pattern.md) - Generator-based alternative for complex operations
- [CLI Output Styling Guide](../cli/output-styling.md) - Progress output conventions
```

#### 2. Progress Pattern Disambiguation

**Location:** `docs/learned/architecture/event-progress-pattern.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a "When to Use This Pattern" section after the opening paragraph, before "Source Files":

```markdown
## When to Use This Pattern

Choose event generators over callbacks when:

| Criteria                        | Event Generator | Callback |
| ------------------------------- | --------------- | -------- |
| Operation complexity            | Complex         | Simple   |
| Multiple event types needed     | Yes             | No       |
| Structured progress data        | Yes             | No       |
| Multiple consumers              | Possible        | Single   |
| Async operation support         | Yes             | Limited  |
| Test assertion on progress      | Detailed        | Basic    |

**Choose event generators** for operations like PR submission with multiple phases, structured status updates, and potential JSON/UI rendering.

**Choose callbacks** for synchronous operations with string-based milestone updates (like `erk docs sync`). See [Callback Progress Pattern](callback-progress-pattern.md).
```

### MEDIUM Priority

#### 3. erk docs sync Progress Reporting

**Location:** `docs/learned/architecture/generated-files.md`
**Action:** UPDATE
**Source:** [Plan], [Impl]

**Draft Content:**

Add a "Progress Reporting" section after "Generation Pipeline":

```markdown
## Progress Reporting

The `sync_agent_docs()` function supports optional progress reporting through a callback parameter. When provided, the callback is invoked at 6 milestone points:

1. **Scanning docs** - Before document discovery
2. **Generating root index** - Before root index generation
3. **Generating category indexes** - Before category index loop
4. **Collecting tripwires** - Before tripwire collection
5. **Generating tripwire files** - Before tripwire file loop
6. **Generating tripwires index** - Before final index generation

This coarse-grained approach (6 messages for ~55 files) provides adequate user feedback without overwhelming output. The CLI binds this to styled progress output; validation commands like `erk docs check` pass `None` to suppress output.

See [Callback Progress Pattern](callback-progress-pattern.md) for the implementation pattern.
```

#### 4. CLI Progress Callback Binding

**Location:** `docs/learned/cli/output-styling.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add a "Progress Callbacks" subsection under "Async Progress Output Patterns" or as a new section:

```markdown
## Progress Callbacks

For operations using the callback progress pattern, bind the callback to CLI output at the command layer.

### Binding Pattern

Use a lambda to convert progress strings to styled CLI output. See `sync.py` in `src/erk/cli/commands/docs/` for the reference implementation.

The lambda should:
- Apply cyan styling for consistency with other progress output
- Route to stderr (`err=True`) to avoid interfering with machine-readable stdout
- Optionally add emoji prefix if appropriate for the command

### When to Use

Use this binding pattern when:
- The operations layer uses `on_progress: Callable[[str], None] | None`
- Progress should appear as styled CLI output
- The command is user-interactive (not `--json` mode)

For silent operation (validation, testing), pass `on_progress=None`.

### Related Patterns

- [Callback Progress Pattern](../architecture/callback-progress-pattern.md) - Operations layer pattern
- [Async Progress Output Patterns](#async-progress-output-patterns) - Full async progress conventions
```

### LOW Priority

#### 5. Test Maintenance for Optional Parameters

**Location:** `docs/learned/testing/test-maintenance.md`
**Action:** CONSIDER_CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Test Maintenance for Optional Parameters
read_when:
  - "adding optional parameters to widely-used functions"
  - "updating test call sites after API changes"
---

# Test Maintenance for Optional Parameters

When adding keyword-only optional parameters to functions with many call sites, follow this systematic approach.

## Finding Call Sites

Use grep to locate all call sites in the test directory. Search for the function name and check both direct calls and fixture usage.

## Update Strategy

For optional parameters with `None` default semantics:
- Pass explicit `param=None` at call sites for clarity
- Maintains existing behavior
- Documents that the parameter was considered

This approach preserves backward compatibility while making the test code explicit about its expectations.

## Example

When `sync_agent_docs()` added `on_progress: Callable[[str], None] | None`, 11 test call sites were updated to include `on_progress=None`.
```

**Note:** This is low priority because the pattern is relatively straightforward. Consider creating only if more parameter update patterns emerge.

#### 6. Progress Granularity UX Principle

**Location:** `docs/learned/cli/output-styling.md`
**Action:** UPDATE
**Source:** [Plan]

**Draft Content:**

Add to the "Async Progress Output Patterns" section or create a subsection on granularity:

```markdown
### Progress Granularity Guidelines

Choose progress granularity based on the number of items being processed:

| Item Count | Strategy | Example |
| ---------- | -------- | ------- |
| <10 | Per-item progress | "Processing file 1/5..." |
| 10-100 | Milestone-based | "Scanning...", "Generating...", "Finalizing..." |
| >100 | Percentage or count | "Processing... 45% (450/1000)" |

**Rationale:** Per-file progress for large operations creates visual noise and can slow execution. Milestone-based progress at operation boundaries provides adequate feedback without overwhelming the user.

**Example:** `erk docs sync` processes ~55 files but reports only 6 milestones (one per pipeline stage).
```

## Contradiction Resolutions

### 1. Progress Pattern Implementation Divergence

**Existing doc:** `docs/learned/architecture/event-progress-pattern.md`
**Conflict:** The existing documentation only describes generator-based event patterns (yield ProgressEvent), but the implementation used a simpler callback pattern (`on_progress: Callable[[str], None] | None`). This created an implicit suggestion that event generators are the only way to implement progress reporting.

**Resolution:** Document both patterns with clear guidance on when to use each:

1. **Create** `docs/learned/architecture/callback-progress-pattern.md` documenting the simpler callback approach
2. **Update** `docs/learned/architecture/event-progress-pattern.md` to add a comparison section explaining when to choose each pattern
3. **Cross-reference** both documents with each other

This is not a contradiction requiring one to replace the other - both patterns are valid for different use cases. The gap was in coverage, not accuracy.

## Stale Documentation Cleanup

No stale documentation found. All referenced files in existing docs exist and are current.

## Prevention Insights

### 1. Session ID Variable Expansion

**What happened:** The `erk exec impl-signal started` command failed because `${CLAUDE_SESSION_ID}` was not expanded in the Bash tool context.

**Root cause:** Environment variable interpolation works differently in different Claude tool contexts.

**Prevention:** The error was benign (`|| true` suppressed it) and the implementation proceeded successfully. No prevention needed - this is an edge case handled by existing defensive coding.

**Recommendation:** CONTEXT_ONLY (no tripwire or documentation change needed)

## Tripwire Candidates

No items met the tripwire-worthiness threshold (score >= 4).

The patterns discovered in these sessions are architectural choices (callback vs event generators) rather than error-prone gotchas. Agents choosing the wrong pattern would produce working but potentially over-engineered code, not failures. This is better addressed through documentation and comparison guidance than warning tripwires.

## Potential Tripwires

### 1. Adding optional callback parameters to operations functions

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** The callback pattern appears across multiple commands but isn't cross-cutting enough for universal tripwires. Better addressed through architecture documentation with "When to Use" guidance. The pattern is a design choice, not a gotcha - wrong choices produce working code, just with different tradeoffs.

### 2. Forgetting to check `on_progress is not None` before invoking

**Score:** 2/10 (Non-obvious +2)
**Notes:** This is the standard LBYL guard pattern. If an agent understands dignified-python standards (LBYL, check conditions first), this follows naturally. Not tripwire-worthy because:
- It's a standard Python pattern, not erk-specific
- The error (calling None) is immediately obvious in testing
- Already covered by dignified-python skill guidance