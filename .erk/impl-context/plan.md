# Renumber fractional steps to whole numbers in skills and commands

## Context

Several `.claude/commands/` and `.claude/agents/` files use fractional step numbering (e.g., Step 3.5, Step 7.75) where steps were inserted between existing whole-number steps over time. This makes the step sequences harder to follow and is inconsistent. The fix is simple: renumber all steps to use consecutive whole numbers, and update any prose cross-references that mention fractional step numbers.

**Scope clarification:** Two files (`check-relevance.md` and `audit-skill.md`) use a "Phase N / Step N.M" pattern where N.M represents logical subsections within a phase (e.g., Phase 4 has substeps 4.1, 4.2, ...). These are NOT the "inserted fractional step" pattern and should NOT be renumbered — they are hierarchical subsections and the numbering is intentional.

## Files to Modify

### 1. `.claude/commands/erk/git-pr-push.md`

**Current step structure:**
- Step 1: Verify Prerequisites
- Step 2: Stage Changes
- Step 3: Analyze Staged Diff
- Step 3.5: Add Planned Prefix (if from plan)
- Step 4: Create Commit
- Step 5: Push to Remote
- Step 6: Check for Existing PR
- Step 7: Create GitHub PR (if no existing PR)
- Step 7.5: Add Checkout Footer
- Step 7.75: Link PR to Objective (if applicable)
- Step 8: Validate PR Rules
- Step 9: Report Results

**New step structure:**
- Step 1: Verify Prerequisites
- Step 2: Stage Changes
- Step 3: Analyze Staged Diff
- Step 4: Add Planned Prefix (if from plan)
- Step 5: Create Commit
- Step 6: Push to Remote
- Step 7: Check for Existing PR
- Step 8: Create GitHub PR (if no existing PR)
- Step 9: Add Checkout Footer
- Step 10: Link PR to Objective (if applicable)
- Step 11: Validate PR Rules
- Step 12: Report Results

**Prose cross-references to update:**
- Line 103: `"When generating the commit message in Step 4"` → `"When generating the commit message in Step 5"`
- Line 141: `"skip Step 7 and go directly to Step 7.5 (Add Checkout Footer)"` → `"skip Step 8 and go directly to Step 9 (Add Checkout Footer)"`
- Line 146: `"Only push code (Step 5) and add the checkout footer (Step 7.5)."` → `"Only push code (Step 6) and add the checkout footer (Step 9)."`
- Line 157-158: References to "Step 7 was executed" in "Skip this step" → `"Skip this step if an existing PR was found in Step 7."`
- Line 182: `"from Step 7 if PR was created, or from Step 6.5 if existing PR was found"` → `"from Step 8 if PR was created, or from Step 7 if existing PR was found"`
- Line 186-187: `"If Step 7 was executed"` / `"If Step 7 was skipped"` → `"If Step 8 was executed"` / `"If Step 8 was skipped"`
- Line 233-234: `"If a NEW PR was created (Step 7 was executed):"` → `"If a NEW PR was created (Step 8 was executed):"`
- Line 250: `"If an EXISTING PR was found (Step 7 was skipped):"` → `"If an EXISTING PR was found (Step 8 was skipped):"`
- Line 310: `"handled automatically in Step 6.5"` → `"handled automatically in Step 7"`

### 2. `.claude/commands/erk/plan-save.md`

**Current step structure:**
- Step 1: Parse Arguments
- Step 1.5: Generate Branch Slug
- Step 1.75: Generate Plan Summary
- Step 2: Run Save Command
- Step 3: Verify Objective Link (if applicable)
- Step 3.5: Update Objective Roadmap (if objective linked)
- Step 4: Display Results

**New step structure:**
- Step 1: Parse Arguments
- Step 2: Generate Branch Slug
- Step 3: Generate Plan Summary
- Step 4: Run Save Command
- Step 5: Verify Objective Link (if applicable)
- Step 6: Update Objective Roadmap (if objective linked)
- Step 7: Display Results

**Prose cross-references to update:**
- Line 82: `"Parse the JSON output to extract plan_number for verification in Step 3."` → `"...for verification in Step 5."`
- Line 88: `"Only run this step if objective_issue is non-null in the JSON output from Step 2."` → `"...from Step 4."`
- Line 121 area: `"Only run this step if objective_issue was non-null in JSON output and verification passed."` — update "was non-null in JSON output" context if it references a step number
- Line 159: `"Return immediately (skip Steps 3, 3.5 above if not already executed)."` → `"Return immediately (skip Steps 5, 6 above if not already executed)."`

### 3. `.claude/commands/erk/one-shot-plan.md`

**Current step structure:**
- Step 1: Read the Prompt
- Step 2: Read Objective Context (if present)
- Step 3: Load Context
- Step 4: Explore the Codebase
- Step 5: Write the Plan
- Step 5.5: Generate Plan Summary
- Step 6: Save Plan to GitHub
- Step 7: Write Plan Result

**New step structure:**
- Step 1: Read the Prompt
- Step 2: Read Objective Context (if present)
- Step 3: Load Context
- Step 4: Explore the Codebase
- Step 5: Write the Plan
- Step 6: Generate Plan Summary
- Step 7: Save Plan to GitHub
- Step 8: Write Plan Result

**Prose cross-references to update:**
- Line 60: `"extract the first # heading from .erk/impl-context/plan.md"` — references "Step 5" context (the plan); no step number change needed here since it says "from .erk/impl-context/plan.md"
- Line 88: `"Use the plan_number and title extracted from the Step 6 output."` → `"...from the Step 7 output."`

### 4. `.claude/commands/erk/pr-submit.md`

**Current step structure:**
- Step 1: Push and Create PR
- Step 2: Get PR Context
- Step 3: Generate Title and Body
- Step 4: Apply Description
- Step 4.5: Link PR to Objective (if applicable)
- Step 5: Report Results

**New step structure:**
- Step 1: Push and Create PR
- Step 2: Get PR Context
- Step 3: Generate Title and Body
- Step 4: Apply Description
- Step 5: Link PR to Objective (if applicable)
- Step 6: Report Results

**Prose cross-references to update:**
- Line 85: `"<pr_number> is the PR number from Step 1"` — still Step 1, no change needed
- Line 89 area: "step 2 JSON" → still Step 2, no change needed

### 5. `.claude/commands/erk/objective-plan.md`

**Current step structure:**
- Step 0: Check for Known Node (Fast Path)
- Step 1: Parse Issue Reference (Interactive Flow)
- Step 2: Launch Task Agent for Data Fetching
- Step 2.5: Verify Objective Context Marker
- Step 3: Load Objective Skill
- Step 4: Display Roadmap and Prompt User
- Step 5: Invoke Inner Skill

**New step structure:**
- Step 0: Check for Known Node (Fast Path)
- Step 1: Parse Issue Reference (Interactive Flow)
- Step 2: Launch Task Agent for Data Fetching
- Step 3: Verify Objective Context Marker
- Step 4: Load Objective Skill
- Step 5: Display Roadmap and Prompt User
- Step 6: Invoke Inner Skill

**Prose cross-references to update:**
- Line 34: `"This skips the interactive selection flow (Steps 1-4 below)"` → `"(Steps 1-5 below)"`

### 6. `.claude/commands/erk/system/objective-plan-node.md`

**Current step structure:**
- Step 1: Parse Arguments
- Step 2: Create Objective Context Marker
- Step 2.5: Verify Objective Context Marker
- Step 3: Create Roadmap Node Marker and Mark as Planning
- Step 4: Load Objective Skill
- Step 5: Gather Context
- Step 6: Enter Plan Mode
- Step 7: Save Plan with Objective Link
- Step 8: Verify Objective Link

**New step structure:**
- Step 1: Parse Arguments
- Step 2: Create Objective Context Marker
- Step 3: Verify Objective Context Marker
- Step 4: Create Roadmap Node Marker and Mark as Planning
- Step 5: Load Objective Skill
- Step 6: Gather Context
- Step 7: Enter Plan Mode
- Step 8: Save Plan with Objective Link
- Step 9: Verify Objective Link

**Prose cross-references to update:**
- Line 9: `"Steps 3-4 of the outer command"` → `"Steps 4-5 of the outer command"` (refers to objective-plan.md's old Steps 3-4 which become 4-5)
- Line 11: No change needed (refers to "steps" conceptually)

### 7. `.claude/commands/local/replan-learn-plans.md`

**Current step structure:**
- Step 1: Query Open erk-learn Plans
- Step 1b: Filter Out Already-Consolidated Plans
- Step 2: Handle Edge Cases (2a, 2b, 2c)
- Step 3: Invoke /erk:replan
- Step 3.5: Context Preservation for Learn Plans (CRITICAL)

**New step structure:**
- Step 1: Query Open erk-learn Plans
- Step 2: Filter Out Already-Consolidated Plans
- Step 3: Handle Edge Cases (3a, 3b, 3c)
- Step 4: Invoke /erk:replan
- Step 5: Context Preservation for Learn Plans (CRITICAL)

**Prose cross-references to update:**
- Sub-items `2a`, `2b`, `2c` → `3a`, `3b`, `3c`
- Line 137 area: References to `"Per Step 4e of that skill"` — this refers to the `/erk:replan` skill's steps, NOT this file's steps; no change needed

### 8. `.claude/commands/local/plan-update.md`

**Current step structure:**
- Step 1: Parse Plan Number
- Step 1.5: Generate Plan Summary
- Step 2: Run Update Command
- Step 3: Display Results

**New step structure:**
- Step 1: Parse Plan Number
- Step 2: Generate Plan Summary
- Step 3: Run Update Command
- Step 4: Display Results

**Prose cross-references to update:** None (no step number references in prose).

### 9. `.claude/agents/learn/documentation-gap-identifier.md`

**Current step structure:**
- Step 1: Read All Agent Outputs
- Step 2: Build Unified Candidate List
- Step 3: Deduplicate Against Existing Documentation
- Step 3.5: Adversarial Verification of Contradictions
- Step 4: Cross-Reference Against Diff Inventory
- Step 5: Classify Each Item
- Step 6: Score Tripwire Worthiness
- Step 7: Prioritize by Impact

**New step structure:**
- Step 1: Read All Agent Outputs
- Step 2: Build Unified Candidate List
- Step 3: Deduplicate Against Existing Documentation
- Step 4: Adversarial Verification of Contradictions
- Step 5: Cross-Reference Against Diff Inventory
- Step 6: Classify Each Item
- Step 7: Score Tripwire Worthiness
- Step 8: Prioritize by Impact

**Prose cross-references to update:** None.

## Files NOT Changing

- `.claude/commands/local/audit-skill.md` — Uses Phase/subsection pattern (`4.1, 4.2, ...`) which is intentional hierarchical numbering, not inserted fractional steps
- `.claude/commands/local/check-relevance.md` — Uses Phase/substep pattern (`Step 1.1, 1.2, 4.1, ...`) which is intentional hierarchical numbering within phases, not inserted fractional steps
- Any other `.claude/` files that don't have fractional step numbering

## Implementation Details

- Each file is a standalone markdown document. Changes are purely textual: renumber headings and update prose references.
- The heading format varies: some use `### Step N:` and others use `## Step N:`. Preserve the existing heading level.
- Sub-step labels like `1b` in `replan-learn-plans.md` should be renumbered to match the new parent (e.g., `2a, 2b, 2c` → `3a, 3b, 3c`).
- Prose references to step numbers (e.g., "from Step 6.5 if existing PR was found") must be updated to match the new numbering.
- Be especially careful with `git-pr-push.md` which has the most cross-references and the most complex renumbering (3 fractional steps and many prose references).

## Verification

1. After making changes, search all modified files for any remaining fractional step patterns: `Step \d+\.\d+` (excluding `check-relevance.md` and `audit-skill.md` which use intentional hierarchical numbering)
2. Verify that step numbers in each file are consecutive (no gaps, no duplicates)
3. Verify that all prose cross-references point to the correct renumbered steps
4. Run `ruff` and `prettier` via devrun to ensure markdown formatting is clean (if applicable)