# Documentation Plan: Add Context Preservation Prompting to Replan Workflow

## Context

This implementation addressed a critical gap in the erk replan workflow: investigation findings were being lost during plan consolidation. When agents performed investigations in Steps 4-5 of the replan workflow (checking existing docs, exploring codebase), the rich contextual discoveries were not making it into the final consolidated plan. The resulting "sparse plans" contained generic placeholder content instead of specific file paths, evidence citations, and verification criteria.

The fix introduced Steps 6a (Gather Investigation Context) and 6b (Enter Plan Mode with Full Context) to the replan command, creating an explicit checkpoint before plan mode entry. This ensures all investigation-derived insights are captured and required in the plan output. The pattern was reinforced in the learn-plan-specific workflow (`/local:replan-learn-plans`) to maintain consistency across both general and documentation-focused replanning scenarios.

Future agents implementing replan workflows, learn plans, or any consolidation-style planning need to understand: (1) why sparse plans fail downstream, (2) how to structure prompts that reliably elicit investigation context, and (3) the anti-patterns to avoid. This documentation captures those learnings.

## Raw Materials

https://gist.github.com/schrockn/94ea7b548499e08d3de34647b93effee

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 13    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 5     |

## Documentation Items

### HIGH Priority

#### 1. Plan Consolidation Context Pattern (Steps 6a-6b)

**Location:** `docs/learned/planning/context-preservation-in-replan.md`
**Action:** CREATE
**Source:** [Impl]

Create a new documentation file that explains the context preservation pattern for replan workflows. This is the foundational document that describes why Steps 6a-6b were added.

**Key sections:**
- Problem statement: sparse plans and their failures
- Solution overview: explicit context gathering
- Step 6a walkthrough: what to collect
- Step 6b walkthrough: requirements for plan mode
- Reference to canonical implementation in `/erk:replan`

**Verification:** Document can stand alone; new agents understand context gathering requirement without reading implementation

---

#### 2. Anti-Patterns vs. Correct Patterns for Plan Content

**Location:** `docs/learned/planning/context-preservation-patterns.md`
**Action:** CREATE
**Source:** [Impl]

Create example-driven guidance showing the difference between sparse and comprehensive plan content. This prevents future agents from creating empty-looking plans.

**Key sections:**
- Generic file references vs. specific paths
- Missing evidence vs. citations with line numbers
- Vague verification vs. testable criteria
- Before/after examples from actual replan changes
- Core principle: plans should be executable without original investigation

**Verification:** Agents reading this document adopt comprehensive style; no more sparse plans

---

#### 3. Plan-Header Metadata Completeness

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE (extend existing)
**Source:** [Plan]

Add section to existing lifecycle documentation explaining when plan-header metadata fields are populated and how to handle graceful failures.

**Key additions:**
- Table of required fields by phase (Planning/Submitted/Implementing)
- Explanation of graceful failure pattern (`no-branch-in-plan`)
- Validation checklist before plan dispatch
- Reference to when `get-pr-for-plan` becomes available

**Verification:** Future agents understand that plan-header is not complete at creation time; prevent attempts to access `branch_name` before submission

---

#### 4. Session File Retention Policy

**Location:** `docs/learned/sessions/lifecycle.md`
**Action:** CREATE (new file)
**Source:** [Plan]

Document the non-obvious fact that session files are session-scoped, not persistent across Claude Code interactions.

**Key sections:**
- Session-scoped persistence principle
- Implications for learn workflows
- Fallback patterns and discovery mechanisms
- Session preprocessing behavior (multi-part files)
- Handling missing sessions gracefully

**Verification:** Future agents understand why planning sessions might not exist; implement fallbacks rather than failing

---

#### 5. Existing PR Detection Pattern

**Location:** `docs/learned/cli/pr-operations.md`
**Action:** CREATE (new file)
**Source:** [Impl]

Create documentation for preventing duplicate PR creation.

**Key sections:**
- Why duplicate PRs are problematic
- Pattern: query before create
- Commands for checking existing PRs (`gh pr list`, `gh pr view`)
- Reference to `/erk:git-pr-push` which handles this automatically
- Tripwire: query before `gh pr create`

**Verification:** Future agents always check for existing PRs; no duplicate PR workflow errors

---

### MEDIUM Priority

#### 1. Context Preservation Prompting Patterns

**Location:** `docs/learned/planning/context-preservation-prompting.md`
**Action:** CREATE
**Source:** [Impl]

Document specific prompt structures that reliably elicit investigation context.

**Key sections:**
- CRITICAL tag pattern for mandatory requirements
- Gather-Then-Enter two-phase prompting structure
- Anti-pattern: direct plan mode without gathering
- Reference to canonical prompts in `/erk:replan` Steps 6a-6b

**Verification:** Future agents understand how to structure prompts for context preservation

---

#### 2. Investigation Findings Checklist

**Location:** `docs/learned/checklists/investigation-findings.md`
**Action:** CREATE
**Source:** [Plan]

Create actionable checklist for verifying context preservation.

**Key sections:**
- Pre-plan-mode verification (discoveries, file paths, evidence, corrections)
- Plan content verification (specific files, testable criteria, no placeholders)
- Post-plan review (executability by other agents)

**Verification:** Agents use checklist to verify context was preserved before plan dispatch

---

#### 3. CI-Iteration Skill Pattern

**Location:** `docs/learned/ci/ci-iteration.md`
**Action:** CREATE
**Source:** [Impl]

Document the proper delegation pattern for running CI commands via devrun.

**Key sections:**
- Run-Report-Fix-Verify pattern
- devrun restrictions (read-only, no auto-fixing)
- Forbidden prompts vs. required patterns
- Prettier formatting example
- Reference to ci-iteration skill

**Verification:** Future agents delegate CI commands to devrun; never ask devrun to "fix errors"

---

#### 4. Markdown Formatting in CI

**Location:** `docs/learned/ci/markdown-formatting.md`
**Action:** CREATE
**Source:** [Impl]

Document how to handle Prettier formatting for markdown files in CI workflows.

**Key sections:**
- Problem: multi-line markdown edits trigger Prettier failures
- Solution: pre-emptive `make prettier` via devrun
- Anti-pattern: manual formatting attempts
- Standard workflow: edit → prettier → fast-ci → commit

**Verification:** Agents run `make prettier` after markdown edits; no manual formatting attempts

---

#### 5. Skill-Based Commit Message Generation

**Location:** `docs/learned/workflows/commit-messages.md`
**Action:** CREATE
**Source:** [Impl]

Document the pattern of loading diff analysis skills before committing.

**Key sections:**
- Why skill-generated messages are better (strategic, component-aware)
- Pattern: load skill → analyze changes → generate message → commit
- Comparison: hand-written vs. skill-generated
- Reference to `/erk:git-pr-push` workflow

**Verification:** Future agents load erk-diff-analysis skill when committing code

---

#### 6. Git-Only PR Workflow

**Location:** `docs/learned/cli/pr-submission.md`
**Action:** CREATE
**Source:** [Impl]

Document the git-only PR submission workflow as alternative to Graphite.

**Key sections:**
- When to use git-only vs. Graphite
- Workflow steps: analyze → skill load → commit → push → create PR
- PR validation and existing PR detection
- Reference to `/erk:git-pr-push` command

**Verification:** Agents understand when to use git-only vs. Graphite workflows

---

#### 7. Session Preprocessing Token Limits

**Location:** `docs/learned/sessions/preprocessing.md`
**Action:** CREATE
**Source:** [Plan]

Document session preprocessing behavior and token limits.

**Key sections:**
- 20K token limit for single-file sessions
- Multi-part file pattern (part1, part2, part3)
- Downstream handling requirements
- Token compression ratio (71-92%)

**Verification:** Future agents understand multi-part file handling in session preprocessing

---

### LOW Priority

#### 1. Learn Plan vs. Implementation Plan Distinctions

**Location:** `docs/learned/planning/learn-vs-implementation-plans.md`
**Action:** CREATE
**Source:** [Plan]

Create reference guide for plan type selection.

**Key sections:**
- Purpose, label, and focus of each type
- Differences table (base branch, output, context)
- When to use each type

**Verification:** Agents understand plan type selection criteria

---

#### 2. System Reminder Patterns for Replan

**Location:** `docs/learned/hooks/replan-context-reminders.md`
**Action:** CREATE
**Source:** [Plan]

Document how to structure system reminders for replan workflows.

**Key sections:**
- Purpose of reminders in workflow
- Pattern: concise, specific, verifiable
- Example reminders for context gathering

**Verification:** Future replan implementations use well-structured reminders

---

#### 3. Session Discovery and Fallback Patterns

**Location:** `docs/learned/sessions/discovery-fallback.md`
**Action:** CREATE
**Source:** [Plan]

Document how to enumerate and fallback for missing sessions.

**Key sections:**
- Discovery pattern using `erk exec list-sessions`
- Fallback strategy: log → continue → reduce scope
- Never fail entirely pattern

**Verification:** Future agents implement resilient fallback strategies

---

## Contradiction Resolutions

No contradictions were detected. All references to investigation findings align on the principle: preserve them, don't skip them. The replan and learn-plan-specific guidance is consistent.

---

## Prevention Insights

### 1. Sparse Plan Content

**What happened:** Consolidated plans contained generic placeholders instead of specific file paths and evidence
**Root cause:** Agents entered plan mode without first gathering investigation context from Steps 4-5
**Prevention:** Implement Steps 6a-6b: explicitly gather context before entering plan mode
**Recommendation:** TRIPWIRE - Add warning before plan mode entry in replan workflows

### 2. Manual Formatting Attempts

**What happened:** Agent attempted to hand-fix Prettier formatting issues in markdown files
**Root cause:** Unfamiliarity with devrun delegation pattern for CI commands
**Prevention:** Always use `make prettier` via devrun; never manually format
**Recommendation:** ADD_TO_DOC - Document in CI-iteration skill documentation

### 3. Lost Investigation Context

**What happened:** Plans were created without incorporating discoveries from codebase exploration
**Root cause:** No explicit checkpoint before plan mode to verify context capture
**Prevention:** Add mandatory context gathering step (Step 6a) before plan mode (Step 6b)
**Recommendation:** TRIPWIRE - High-severity, affects all consolidation workflows

---

## Tripwire Candidates

### HIGH-Worthiness (Score >= 4)

1. **Existing PR Check Before Creation** (Score: 6/10)
   - Trigger: Before running `gh pr create`
   - Warning: "Query for existing PRs first via `gh pr list --head <branch> --state all`. Prevents duplicate PR creation and workflow breaks."
   - Target: `docs/learned/cli/pr-operations.md`

2. **Session File Persistence Across Claude Sessions** (Score: 5/10)
   - Trigger: Before learn workflow accesses planning session
   - Warning: "Session files persist only within the current Claude Code session. If planning session is unavailable, implement fallback strategy using available sessions."
   - Target: `docs/learned/sessions/lifecycle.md`

3. **Context Gathering Before Plan Mode** (Score: 5/10)
   - Trigger: Before entering Plan Mode in replan/consolidation workflows
   - Warning: "Gather investigation context BEFORE entering plan mode. Follow Steps 6a-6b to collect file paths, evidence, and discoveries first. Sparse plans are destructive to downstream implementation."
   - Target: `docs/learned/planning/context-preservation-in-replan.md`

### MEDIUM-Worthiness (Score 2-3)

1. **Prettier Formatting in CI** (Score: 3/10)
2. **Plan-Header Metadata Validation** (Score: 3/10)
3. **Skill Loading Before Commits** (Score: 3/10)
4. **Session Preprocessing Multi-Part Files** (Score: 2/10)
5. **Branch-Issue Naming Validation** (Score: 2/10)

---

## Related Documentation

When implementing these documentation items, reference:

- `.claude/commands/erk/replan.md` - Primary source for Steps 6a-6b
- `.claude/commands/local/replan-learn-plans.md` - Learn-plan-specific context preservation
- `docs/learned/planning/lifecycle.md` - Existing plan lifecycle documentation
- AGENTS.md - Agent instruction format and skill patterns
- `docs/learned/hooks/prompt-hooks.md` - System reminder patterns