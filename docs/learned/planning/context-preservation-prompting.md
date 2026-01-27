---
title: Context Preservation Prompting Patterns
read_when:
  - "writing slash commands that create plans"
  - "implementing replan workflows"
  - "designing consolidation prompts"
---

# Context Preservation Prompting Patterns

Specific prompt structures that reliably elicit investigation context in plan creation.

## Table of Contents

- [Core Pattern: Gather-Then-Enter](#core-pattern-gather-then-enter)
- [CRITICAL Tag Pattern](#critical-tag-pattern)
- [Anti-Pattern: Direct Plan Mode](#anti-pattern-direct-plan-mode)
- [Step 6a Prompting Structure](#step-6a-prompting-structure)
- [Step 6b Prompting Structure](#step-6b-prompting-structure)
- [Reference Implementation](#reference-implementation)

---

## Core Pattern: Gather-Then-Enter

### Two-Phase Prompting

Context preservation uses a **two-phase** prompt structure:

#### Phase 1: Explicit Gathering (Step 6a)

**Prompt agent to collect and structure investigation findings BEFORE entering Plan Mode.**

#### Phase 2: Enter Plan Mode with Requirements (Step 6b)

**After gathering, enter Plan Mode with explicit requirements for incorporating findings.**

This creates a **checkpoint** that ensures context is explicitly captured before plan creation.

---

## CRITICAL Tag Pattern

### What is the CRITICAL Tag?

A **[CRITICAL:]** prefix in prompts signals mandatory requirements:

```markdown
**CRITICAL:** The plan content MUST include investigation findings, not just reference them.
```

### When to Use CRITICAL Tags

Use `[CRITICAL:]` when:

1. **Mandatory behavior:** Agent must follow this, no exceptions
2. **Common mistakes:** Agents frequently skip this step
3. **Downstream impact:** Skipping causes serious problems

### CRITICAL Tag in Context Preservation

From `/erk:replan` Step 6b:

```markdown
**CRITICAL:** The plan content MUST include the investigation findings, not just summarize them.
```

**Why CRITICAL:**

- **Mandatory:** Plans without findings are sparse and unusable
- **Common mistake:** Agents often reference findings without incorporating them
- **Downstream impact:** Implementing agents must re-discover everything

---

## Anti-Pattern: Direct Plan Mode

### What Not to Do

```markdown
### Step 6: Create New Plan

Use EnterPlanMode to create an updated plan based on investigation findings.
```

**Problems:**

- No explicit gathering step
- Investigation findings remain scattered in conversation
- Agent enters Plan Mode without structured context
- Result: Sparse plans with generic placeholders

### Why It Fails

When agents enter Plan Mode directly:

1. Investigation findings exist in conversation history
2. But they're not explicitly collected and structured
3. Plan Mode prompt doesn't emphasize including findings
4. Agent creates plan with generic "update X" steps
5. Specific file paths, line numbers, and evidence are lost

---

## Step 6a Prompting Structure

### Purpose

Gather and structure all investigation findings **before** Plan Mode.

### Template

```markdown
#### 6a: Gather Investigation Context

Before entering Plan Mode, collect all investigation findings from Steps 4-5:

1. **Investigation status per plan**: Completion percentages (e.g., "4/11 items implemented")
2. **Specific discoveries**: File paths, line numbers, commit hashes, PR numbers
3. **Corrections found**: What the original plan(s) got wrong
4. **Codebase evidence**: Actual function names, class signatures, config values

[For consolidation mode, also gather:]

- **Overlap analysis**: Which items appeared in multiple plans
- **Merge decisions**: Why items were combined or kept separate
- **Attribution map**: Which source plan contributed each item
```

### Key Elements

#### 1. Explicit "Before entering Plan Mode"

Signals this is a **prerequisite** step, not concurrent with Plan Mode.

#### 2. Numbered List of Context Types

Makes it clear what to collect. Four categories:

1. Investigation status
2. Specific discoveries
3. Corrections found
4. Codebase evidence

#### 3. Examples in Parentheses

Shows what "investigation status" looks like: `"4/11 items implemented"`

#### 4. Concrete Artifact Types

Not "findings" but **file paths, line numbers, commit hashes, PR numbers**.

#### 5. Consolidation-Specific Context

For multi-plan consolidation, additional context is required.

---

## Step 6b Prompting Structure

### Purpose

Enter Plan Mode with explicit requirements for incorporating gathered context.

### Template

````markdown
#### 6b: Enter Plan Mode with Full Context

Use EnterPlanMode to create an updated plan.

**CRITICAL:** The plan content MUST include the investigation findings, not just summarize them. Each implementation step should have:

- **Specific file paths** (e.g., `docs/learned/architecture/gateway-inventory.md:45`)
- **What to change** (not "update X" but "add entry for CommandExecutor with ABC at line 105")
- **Evidence** (commit hashes, PR numbers, current line numbers)
- **Verification criteria** (how to confirm the step is complete)

**Anti-pattern (sparse):**

```markdown
1. Update gateway documentation
2. Add missing tripwires
```

**Correct pattern (comprehensive):**

```markdown
1. **Update gateway-inventory.md** (`docs/learned/architecture/gateway-inventory.md`)
   - Add missing entries: CommandExecutor (abc.py:105), PlanDataProvider (abc.py:142)
   - Fix import paths at lines 45, 67 (change `erk.gateways.` → `erk.gateway.`)
   - Verification: All gateways in `src/erk/gateway/` have entries
```
````

### Key Elements

#### 1. CRITICAL Tag

Signals mandatory requirement:

```markdown
**CRITICAL:** The plan content MUST include the investigation findings, not just summarize them.
```

#### 2. Four-Point Checklist

Each implementation step should have:

- Specific file paths
- What to change
- Evidence
- Verification criteria

#### 3. Anti-Pattern Example

Shows what NOT to do (sparse plan):

```markdown
1. Update gateway documentation
2. Add missing tripwires
```

#### 4. Correct Pattern Example

Shows what to do (comprehensive plan):

```markdown
1. **Update gateway-inventory.md** (`docs/learned/architecture/gateway-inventory.md`)
   - Add missing entries: CommandExecutor (abc.py:105), PlanDataProvider (abc.py:142)
   - Fix import paths at lines 45, 67
   - Verification: All gateways in `src/erk/gateway/` have entries
```

#### 5. Concrete Specificity

Not "file paths" but `` `docs/learned/architecture/gateway-inventory.md:45` `` with line numbers.

Not "update X" but "add entry for CommandExecutor with ABC at line 105".

---

## Reference Implementation

### Canonical Location

**File:** `.claude/commands/erk/replan.md`

**Steps 6a and 6b:** Lines 209-250

### Step 6a Implementation

```markdown
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
```

### Step 6b Implementation

````markdown
#### 6b: Enter Plan Mode with Full Context

Use EnterPlanMode to create an updated plan.

**CRITICAL:** The plan content MUST include the investigation findings, not just summarize them. Each implementation step should have:

- **Specific file paths** (e.g., `docs/learned/architecture/gateway-inventory.md:45`)
- **What to change** (not "update X" but "add entry for CommandExecutor with ABC at line 105")
- **Evidence** (commit hashes, PR numbers, current line numbers)
- **Verification criteria** (how to confirm the step is complete)

**Anti-pattern (sparse):**

```markdown
1. Update gateway documentation
2. Add missing tripwires
```

**Correct pattern (comprehensive):**

```markdown
1. **Update gateway-inventory.md** (`docs/learned/architecture/gateway-inventory.md`)
   - Add missing entries: CommandExecutor (abc.py:105), PlanDataProvider (abc.py:142)
   - Fix import paths at lines 45, 67 (change `erk.gateways.` → `erk.gateway.`)
   - Verification: All gateways in `src/erk/gateway/` have entries
```
````

### Learn-Plan-Specific Reinforcement

**File:** `.claude/commands/local/replan-learn-plans.md`

Learn plan consolidation reinforces this pattern with documentation-specific context gathering requirements.

---

## Adaptation Guidelines

### For Other Plan Creation Workflows

When creating new workflows that generate plans:

#### 1. Always Add Gathering Step

Before EnterPlanMode, add explicit gathering step.

#### 2. Use CRITICAL Tag

Mark mandatory requirements with `**CRITICAL:**`

#### 3. Provide Anti-Pattern Example

Show what sparse plans look like.

#### 4. Provide Correct Pattern Example

Show what comprehensive plans look like with real examples.

#### 5. List Context Types

Be explicit about what to gather (4 categories minimum).

### For Non-Replan Workflows

Even for fresh plans (not replanning), context preservation applies:

```markdown
### Before Entering Plan Mode

Collect all relevant context:

1. **Codebase discoveries**: Actual file names, function signatures, class definitions
2. **Architecture insights**: How components interact, data flow patterns
3. **Constraints found**: API limits, type requirements, validation rules
4. **Verification approach**: How to confirm each step is complete

Then enter Plan Mode with this context.

**CRITICAL:** Plan steps must reference specific files with line numbers, not generic descriptions.
```

---

## Related Documentation

- [Context Preservation in Replan](context-preservation-in-replan.md) - Why Steps 6a-6b exist
- [Context Preservation Patterns](context-preservation-patterns.md) - Anti-patterns vs. correct patterns
- [Investigation Findings Checklist](../checklists/investigation-findings.md) - Verification checklist
- [Replan Command](../../../.claude/commands/erk/replan.md) - Reference implementation
