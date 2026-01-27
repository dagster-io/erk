# Plan: Add Context Preservation Prompting to Replan Workflow

## Problem

After running `/local:replan-learn-plans`, the consolidated plan has sparse content despite extensive investigation. The investigation findings from Step 4 aren't being incorporated into the plan content in Step 6.

**Root cause:** `/erk:replan` Step 6 (lines 205-209) says only:
```
Use EnterPlanMode to create an updated plan.
```

No explicit instruction to include investigation findings in the plan content.

## Solution

1. Fix the root cause in `/erk:replan` Step 6 with explicit context inclusion instructions
2. Add reinforcement prompting in `/local:replan-learn-plans.md` for learn-plan-specific context

## Files to Modify

1. `/workspaces/erk/.claude/commands/erk/replan.md` (root cause)
2. `/workspaces/erk/.claude/commands/local/replan-learn-plans.md` (reinforcement)

---

## Change 1: /erk:replan Step 6 Enhancement

**Location:** Lines 205-209 (after "### Step 6: Create New Plan (Always)")

**Current content:**
```markdown
### Step 6: Create New Plan (Always)

**Always create a new plan issue**, regardless of implementation status.

Use EnterPlanMode to create an updated plan.
```

**Replace with:**
```markdown
### Step 6: Create New Plan (Always)

**Always create a new plan issue**, regardless of implementation status.

#### 6a: Gather Investigation Context

Before entering Plan Mode, collect all investigation findings from Steps 4-5:

1. **Investigation status per plan**: Completion percentages (e.g., "4/11 items implemented")
2. **Specific discoveries**: File paths, line numbers, commit hashes, PR numbers
3. **Corrections found**: What the original plan(s) got wrong
4. **Codebase evidence**: Actual function names, class signatures, config values

For consolidation mode, also gather:
- **Overlap analysis**: Which items appeared in multiple plans
- **Merge decisions**: Why items were combined or kept separate
- **Attribution map**: Which source plan contributed each item

#### 6b: Enter Plan Mode with Full Context

Use EnterPlanMode to create an updated plan.

**CRITICAL:** The plan content MUST include the investigation findings, not just summarize them. Each implementation step should have:

- **Specific file paths** (e.g., `docs/learned/architecture/gateway-inventory.md:45`)
- **What to change** (not "update X" but "add entry for CommandExecutor with ABC at line 105")
- **Evidence** (commit hashes, PR numbers, current line numbers)
- **Verification criteria** (how to confirm the step is complete)

**Anti-pattern (sparse):**
```
1. Update gateway documentation
2. Add missing tripwires
```

**Correct pattern (comprehensive):**
```
1. **Update gateway-inventory.md** (`docs/learned/architecture/gateway-inventory.md`)
   - Add missing entries: CommandExecutor (abc.py:105), PlanDataProvider (abc.py:142)
   - Fix import paths at lines 45, 67 (change `erk.gateways.` → `erk.gateway.`)
   - Verification: All gateways in `src/erk/gateway/` have entries
```
```

---

## Change 2: /local:replan-learn-plans.md Reinforcement

**Location:** After Step 3 (lines 119-137)

**Add new section:**
```markdown
### Step 3.5: Context Preservation for Learn Plans (CRITICAL)

Learn plans document patterns discovered during implementation sessions. When the `/erk:replan` skill creates the consolidated plan, ensure it captures:

#### Session-Derived Insights
- **What was built**: Actual code changes with file paths and line numbers
- **Decisions made**: Architectural choices, API designs, naming conventions
- **Gaps identified**: Documentation needs discovered during implementation

#### Documentation-Specific Context
For each documentation item, include:
- **Target file path**: Where the doc will be created/updated
- **Content source**: Which investigation finding informs this item
- **Related code**: File paths that the documentation describes
- **Category placement**: Where in docs/learned/ hierarchy it belongs

#### Actionable Implementation Steps
Each step should specify:
- Exact file to create/modify
- Content outline or template
- Source references (investigation findings, code locations)
- Verification: How to confirm documentation is accurate

**Example of comprehensive learn plan step:**
```markdown
### Step 3: Create flatten-subgateway-pattern.md

**File:** `docs/learned/architecture/flatten-subgateway-pattern.md`

**Content outline:**
1. Problem: Nested subgateways (e.g., `git.branch.branch`) create confusing API
2. Pattern: Flatten to single level (`git.branch`)
3. Implementation: Phase 2A (PR #6159) and Phase 2B (PR #6162)
4. Examples: Before/after code showing the transformation
5. Tripwire: Add to tripwires-index.md under "Gateway Patterns"

**Source:** Investigation of #6160 and #6163 found 14 query methods and 5 mutation methods moved

**Verification:** Document accurately describes the pattern shown in `src/erk/gateway/git/branch.py`
```
```

---

## Verification

1. Run `/local:replan-learn-plans` on a test set of erk-learn issues
2. Check that resulting consolidated plan includes:
   - Per-plan investigation status with percentages
   - File paths with line numbers
   - Commit/PR references
   - Detailed implementation steps with templates
   - Verification criteria for each step