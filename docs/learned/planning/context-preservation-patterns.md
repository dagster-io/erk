---
title: Context Preservation Patterns
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "writing implementation plans (any workflow)"
  - "reviewing plan content before saving to GitHub"
  - "creating consolidated plans from multiple sources"
  - "debugging why an implementing agent had to re-investigate"
tripwires:
  - action: "writing a plan step that says 'update X' without a file path"
    warning: "Generic references force re-discovery. Include the full path, line numbers, and evidence. See the five dimensions below."
  - action: "writing verification criteria like 'documentation is complete'"
    warning: "Vague verification is unverifiable. Criteria must be testable with grep, file inspection, or running code."
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
---

# Context Preservation Patterns

Five dimensions of plan specificity that determine whether an implementing agent can execute immediately or must repeat the entire investigation. Each dimension is a failure mode: missing any one forces re-discovery.

For why this matters (the sparse plan problem and its economics), see [Context Preservation in Replan](context-preservation-in-replan.md). For the pre-Plan-Mode checklist, see [Investigation Findings Checklist](../checklists/investigation-findings.md).

> **Note:** The examples below are illustrative — they show the format and level of detail, not actual current file paths or function names.

## Core Principle

**Plans must be executable without the original investigation.**

The investigating agent and the implementing agent run in separate sessions. The plan is the only artifact that crosses the boundary. Every piece of context that doesn't make it into the plan must be re-discovered — burning 10-30K tokens and risking divergent conclusions when a different agent searches the codebase.

## The Five Dimensions

Each dimension addresses a specific re-discovery cost. A plan missing any one of them is "sparse" in that dimension.

### 1. File References

Generic references force the implementing agent to search the entire codebase for the right file.

```markdown
<!-- WRONG: sparse -->

1. Update gateway documentation
2. Fix the session preprocessing docs

<!-- RIGHT: specific -->

1. Update `docs/learned/architecture/gateway-inventory.md`
2. Fix `docs/learned/sessions/preprocessing.md`
```

The fix is mechanical: every plan step that touches a file must include its full path. If the investigating agent found the file, its path belongs in the plan.

### 2. Evidence and Citations

Without evidence, the implementing agent must re-search for constants, function locations, and current values.

```markdown
<!-- WRONG: sparse -->

1. Document the token limit for session preprocessing
2. Update model references from Haiku to Sonnet

<!-- RIGHT: specific -->

1. Document token limit: `SINGLE_FILE_TOKEN_LIMIT = 20_000` at
   `src/erk/claude/session_preprocessor.py:23`
2. Fix model reference at line 67 of `prompt-executor-gateway.md`:
   change "claude-3-haiku-20240307" to value from `src/erk/claude/models.py:12`
```

Evidence proves discoveries are real and anchors the implementing agent's work to verified locations.

### 3. Verification Criteria

Vague verification ("documentation is complete") is unfalsifiable. The implementing agent has no way to know when a step is actually done.

```markdown
<!-- WRONG: sparse -->

1. Update documentation
   - Verification: Documentation is complete

<!-- RIGHT: specific -->

1. Update `docs/learned/sessions/preprocessing.md`
   - Verification: Document includes `SINGLE_FILE_TOKEN_LIMIT` constant
     with value (20K), explains multi-part file pattern
     `{id}.part{N}.jsonl`, and references `session_preprocessor.py`
```

Good verification criteria are testable with grep, file inspection, or running code. If you can't describe a mechanical check, the step is underspecified.

### 4. Function and Class Names

Guessed names are the most insidious form of sparsity — they look specific but may be wrong.

```markdown
<!-- WRONG: guessed -->

1. Document the session parsing function
2. Add entry for the command executor class

<!-- RIGHT: verified -->

1. Document `parse_session_file_path()` at
   `src/erk/claude/session_preprocessor.py:78-92`
2. Add entry for `CommandExecutor` at `src/erk/gateway/abc.py:105-142`
```

The difference between "the session parsing function" and `parse_session_file_path()` is the difference between a search and a direct navigation. When the investigating agent has already verified the name, omitting it from the plan is pure waste.

### 5. Change Descriptions

"Update X" without specifics is a delegation of decision-making, not a plan step. The implementing agent must figure out what to change, which is the hard part.

```markdown
<!-- WRONG: sparse -->

1. Update gateway inventory
2. Fix import paths

<!-- RIGHT: specific -->

1. Add entries to `gateway-inventory.md` after line 105:
   - `CommandExecutor` (ABC at `src/erk/gateway/abc.py:105`)
   - `PlanDataProvider` (ABC at `src/erk/gateway/abc.py:142`)
2. Fix import paths at lines 45, 67, 89:
   change `erk.gateways.` to `erk.gateway.`
   (package renamed in PR #5432)
```

Specific changes include: what to add/remove/modify, where (line numbers), and why (reasoning or PR reference).

## Consolidation Amplifies Every Dimension

When consolidating multiple plans, each dimension compounds:

- **File references**: Multiple plans may reference the same file with different names
- **Evidence**: Each source plan has its own discoveries that must be preserved
- **Verification**: Merged steps need combined criteria from all source plans
- **Names**: Different plans may use different (possibly guessed) names for the same symbol
- **Changes**: Overlapping items must be identified, merged, and attributed to source plans

Without explicit attribution ("from #123, #456"), the implementing agent has no way to trace decisions back to their source investigation.

## Applying the Dimensions

### Quick Self-Check

For each plan step, verify:

1. Does it name a specific file path? (not "the docs")
2. Does it cite evidence? (constants, line numbers, PR numbers)
3. Does it have testable verification? (greppable, inspectable)
4. Are function/class names verified from source? (not guessed)
5. Does it describe specific changes? (not "update X")

For the complete pre-Plan-Mode checklist with per-category checks, see [Investigation Findings Checklist](../checklists/investigation-findings.md).

### Historical Context

The five dimensions were identified through repeated failures in the replan workflow (issues #6139, #6167). The two-phase checkpoint (Steps 6a-6b in `/erk:replan`) was the architectural fix — forcing explicit context gathering before plan creation. See [Context Preservation in Replan](context-preservation-in-replan.md) for the full problem analysis.

---

## Related Documentation

- [Context Preservation in Replan](context-preservation-in-replan.md) — the sparse plan problem, root cause, and two-phase checkpoint
- [Context Preservation Prompting](context-preservation-prompting.md) — prompt structures for eliciting context in new workflows
- [Investigation Findings Checklist](../checklists/investigation-findings.md) — pre-Plan-Mode verification checklist
- [Plan Lifecycle](lifecycle.md) — full plan workflow with investigation findings section
