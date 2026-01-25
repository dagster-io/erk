# Consolidated erk-learn Documentation Plan

> **Consolidates:** #5983, #5982, #5958, #5956, #5954, #5952, #5945, #5937, #5933, #5921

## Executive Summary

This plan consolidates 10 open erk-learn documentation plans into a unified documentation update. All source implementations have been merged to master. The documentation work focuses on capturing patterns, adding tripwires, and updating existing docs with implementation-specific details.

## Source Plans

| #     | Title                                         | Status     | Items |
| ----- | --------------------------------------------- | ---------- | ----- |
| #5983 | Fix Duplicate Plan Creation Loop              | Implemented| 5     |
| #5982 | Fix Agent Session Slug Lookup                 | Implemented| 6     |
| #5958 | Add Objective Number to erk-statusline        | Implemented| 18    |
| #5956 | Phase 2: Reconciler Core                      | Implemented| 7     |
| #5954 | Encouraging Doc-First Behavior in Explore     | Implemented| 7     |
| #5952 | Add BeadsGateway ABC                          | Implemented| 2     |
| #5945 | Add LLM-based Objective Step Inference        | Implemented| 17    |
| #5937 | Phase 1 - Roadmap Parser                      | Implemented| 10    |
| #5933 | Plan Lookup Priority Bug Fix                  | Implemented| 5     |
| #5921 | Phase 2A: Branch Subgateway Steelthread       | Implemented| 11    |

**Total raw items:** 88 documentation items across all plans

After deduplication and consolidation: **23 unique documentation items**

---

## Investigation Findings

### Codebase Verification

**Confirmed Implementations:**
- `erk_shared/objectives/` package with `roadmap_parser.py`, `reconciler.py`, `next_step_inference.py`, `types.py`
- `erk_shared/git/branch_ops/` subgateway with 5-file pattern (abc, real, fake, dry_run, printing)
- Agent session extraction fix: `_read_agent_session_entries()` in `claude_installation/real.py`
- Exit-plan-mode hook marker persistence fix (plan-saved.marker no longer deleted when blocking)
- Capability registry pattern: `src/erk/core/capabilities/reminders.py` and `registry.py`

### Overlap Analysis

**Highly Overlapping Topics (Merged):**
- Objectives module docs (#5937, #5945, #5956) → Single "Objectives Package" documentation
- Gateway patterns (#5952, #5921) → Consolidated "Gateway Pattern Updates"
- Session handling (#5982, #5933) → Unified "Session and Plan Lookup" docs
- Hook/marker lifecycle (#5983, #5954) → Consolidated "Workflow State Management"

---

## Implementation Steps

### PHASE 1: HIGH Priority - New Documentation (5 items)

#### 1.1 Create `docs/learned/objectives/index.md` _(from #5937, #5945, #5956)_

**Purpose:** Central overview of the objectives package for LLM-based roadmap analysis

**Content outline:**
- Package overview: `packages/erk-shared/src/erk_shared/objectives/`
- Module summary: `roadmap_parser.py`, `next_step_inference.py`, `reconciler.py`, `types.py`
- Key types: `RoadmapStep`, `RoadmapParseResult`, `NextStepResult`, `InferenceError`, `ReconcileAction`
- PR column format reference (empty=pending, #XXXX=done, plan #XXXX=in-progress)
- Cost model: Haiku for inference (~$0.001/call)
- When to use: Auto-advance objective workflows

#### 1.2 Create `docs/learned/planning/plan-lookup-strategy.md` _(from #5933)_

**Purpose:** Document the 3-tier plan lookup priority system

**Content outline:**
- Priority order: (1) `--plan-file`, (2) scratch storage, (3) `~/.claude/plans/`
- Session-scoped vs mtime-based lookup
- When scratch is checked (only with `--session-id`)
- Decision tree diagram
- Troubleshooting "wrong plan saved" issues

#### 1.3 Create `docs/learned/sessions/agent-session-files.md` _(from #5982)_

**Purpose:** Document agent session file handling for parallel planning

**Content outline:**
- File naming: `agent-{uuid}.jsonl` vs `{session-id}.jsonl`
- Why agent sessions are different (isolated files, no sessionId filtering needed)
- Detection: `session_id.startswith("agent-")`
- Implementation reference: `_read_agent_session_entries()`
- Why this matters for `/erk:learn` workflows

#### 1.4 Create `docs/learned/planning/session-deduplication.md` _(from #5983)_

**Purpose:** Document session-based plan deduplication pattern

**Content outline:**
- Two-layer defense: hook blocking + command-level deduplication
- Marker lifecycle: reusable (plan-saved) vs one-time (implement-now, objective-context)
- `_get_existing_saved_issue()` helper pattern
- Why marker persistence is critical

#### 1.5 Create `docs/learned/capabilities/adding-new-capabilities.md` _(from #5954)_

**Purpose:** Document the 3-file capability pattern

**Content outline:**
- Pattern: `reminders.py` → `registry.py` → `user_prompt_hook.py`
- Example: explore-docs reminder capability
- Registration checklist (both files required)
- Silent failure modes

---

### PHASE 2: HIGH Priority - Tripwires (8 items)

Add to `docs/learned/tripwires.md`:

#### 2.1 Marker Lifecycle Semantics _(from #5983)_
```markdown
**CRITICAL: Before modifying marker deletion behavior in exit-plan-mode hook** → Read [Session Deduplication](planning/session-deduplication.md) first. Reusable markers (plan-saved) must persist; one-time markers (implement-now, objective-context) are consumed. Deleting reusable markers breaks state machines and enables retry loops that create duplicates.
```

#### 2.2 Agent Session Handling _(from #5982)_
```markdown
**CRITICAL: Before reading or extracting data from agent session files** → Read [Agent Session Files](sessions/agent-session-files.md) first. Agent session files use `agent-` prefix and require dedicated reading logic. Check `session_id.startswith("agent-")` and route to `_read_agent_session_entries()`. Using generic `_iter_session_entries()` skips agent files silently.
```

#### 2.3 Status Column Override Precedence _(from #5937)_
```markdown
**CRITICAL: Before accessing PR column value without checking Status column first** → Read [Objectives Index](objectives/index.md) first. Status column (blocked, skipped) overrides PR column inference. Always check Status column first or data will be lost.
```

#### 2.4 Step Readiness Blocking Semantics _(from #5937)_
```markdown
**CRITICAL: Before adding new step status values to StepStatus** → Read [Objectives Index](objectives/index.md) first. New statuses must be explicitly handled in get_next_actionable_step() or they may unintentionally block forward progress.
```

#### 2.5 Missing Capability in Registry _(from #5954)_
```markdown
**CRITICAL: Before using `is_reminder_installed()` in hook check** → Read [Adding New Capabilities](capabilities/adding-new-capabilities.md) first. Capability class MUST be defined in reminders.py AND registered in registry.py @cache tuple. Incomplete registration causes silent hook failures.
```

#### 2.6 .worker-impl/ Artifact Cleanup _(from #5954)_
```markdown
**CRITICAL: After plan-implement execution completes** → Always clean .worker-impl/ with `git rm -rf .worker-impl/` and commit. Transient artifacts cause CI formatter failures (Prettier).
```

#### 2.7 PR Footer Format Validation _(from #5956)_
```markdown
**CRITICAL: Before implementing PR body generation with checkout footers** → HTML `<details>` tags will fail `has_checkout_footer_for_pr()` validation. Use plain text backtick format: `` `gh pr checkout <number>` ``
```

#### 2.8 erk exec Command Option Consistency _(from #5956)_
```markdown
**CRITICAL: Before using erk exec commands in scripts** → Some erk exec subcommands don't support `--format json`. Always check with `erk exec <command> -h` first.
```

---

### PHASE 3: MEDIUM Priority - Doc Updates (6 items)

#### 3.1 Update `docs/learned/architecture/gateway-abc-implementation.md` _(from #5921, #5952)_

Add sections:
- Reference implementation: BeadsGateway (5-file pattern for new service)
- Sub-Gateway Pattern: Branch ops example showing abc.py property with TYPE_CHECKING guard
- Linked mutation tracking in FakeGit

#### 3.2 Update `docs/learned/sessions/parallel-session-awareness.md` _(from #5982)_

Add "Agent Session Special Handling" section explaining:
- Why agent sessions are different
- Routing pattern for session extraction
- Implementation reference

#### 3.3 Update `docs/learned/planning/lifecycle.md` _(from #5958, #5933)_

Add sections:
- "Session Idempotency" explaining retry handling
- Update storage location table with scratch storage priority

#### 3.4 Update `docs/learned/planning/scratch-storage.md` _(from #5933, #5956)_

Add sections:
- "Plan-Specific Storage" for session-scoped plan files
- `${CLAUDE_SESSION_ID}` substitution pattern for paths

#### 3.5 Update `docs/learned/hooks/erk.md` _(from #5983)_

Add "Marker State Machine" subsection under exit-plan-mode-hook:
- Marker lifecycle categories
- Critical persistence behavior

#### 3.6 Update `docs/learned/planning/learn-workflow.md` _(from #5945)_

Add sections:
- Tier layering note (parallel → synthesis → extraction)
- Session preprocessing validation pattern

---

### PHASE 4: LOW Priority - Reference Updates (4 items)

#### 4.1 Update `docs/learned/glossary.md`
- Add StepStatus definition
- Add ReconcileAction definition

#### 4.2 Update `docs/learned/index.md`
- Add objectives/ category
- Add capabilities/ category

#### 4.3 Create `docs/learned/objectives/roadmap-parser.md`
- Detailed RoadmapStep and RoadmapParseResult documentation
- PR column format reference
- Error handling patterns

#### 4.4 Create `docs/learned/architecture/optional-field-propagation.md` _(from #5958)_
- 3-tier pattern: Model → Storage → Display
- Backward compatibility patterns
- Code examples from objective_issue implementation

---

## Verification

After implementation:

1. **Tripwires regeneration:**
   ```bash
   erk docs sync
   ```
   Verify tripwires.md is regenerated with all new entries

2. **Index validation:**
   ```bash
   erk docs validate
   ```
   Check for broken links and missing entries

3. **Manual review:**
   - Each new doc has frontmatter with `read_when` conditions
   - Cross-references between related docs are correct
   - No duplicate tripwire entries

---

## Files to Create

| File | Phase |
| ---- | ----- |
| `docs/learned/objectives/index.md` | 1.1 |
| `docs/learned/planning/plan-lookup-strategy.md` | 1.2 |
| `docs/learned/sessions/agent-session-files.md` | 1.3 |
| `docs/learned/planning/session-deduplication.md` | 1.4 |
| `docs/learned/capabilities/adding-new-capabilities.md` | 1.5 |
| `docs/learned/objectives/roadmap-parser.md` | 4.3 |
| `docs/learned/architecture/optional-field-propagation.md` | 4.4 |

## Files to Update

| File | Phase |
| ---- | ----- |
| `docs/learned/tripwires.md` | 2 |
| `docs/learned/architecture/gateway-abc-implementation.md` | 3.1 |
| `docs/learned/sessions/parallel-session-awareness.md` | 3.2 |
| `docs/learned/planning/lifecycle.md` | 3.3 |
| `docs/learned/planning/scratch-storage.md` | 3.4 |
| `docs/learned/hooks/erk.md` | 3.5 |
| `docs/learned/planning/learn-workflow.md` | 3.6 |
| `docs/learned/glossary.md` | 4.1 |
| `docs/learned/index.md` | 4.2 |

---

## Attribution

Items by source:

- **#5983**: Steps 1.4, 2.1, 3.5
- **#5982**: Steps 1.3, 2.2, 3.2
- **#5958**: Steps 3.3, 4.4
- **#5956**: Steps 2.7, 2.8, 3.4
- **#5954**: Steps 1.5, 2.5, 2.6
- **#5952**: Step 3.1
- **#5945**: Steps 1.1, 3.6
- **#5937**: Steps 1.1, 2.3, 2.4, 4.1, 4.3
- **#5933**: Steps 1.2, 3.3, 3.4
- **#5921**: Step 3.1