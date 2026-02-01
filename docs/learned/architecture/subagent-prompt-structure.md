---
title: Subagent Prompt Structure for Complete Context Embedding
read_when:
  - "writing Task tool prompts for subagent delegation"
  - "debugging subagent failures or incorrect behavior"
  - "delegating mechanical work to subagents"
  - "optimizing command performance via delegation"
  - "subagent requesting unavailable skills or re-fetching data"
tripwires:
  - action: "delegating to subagents via Task tool"
    warning: "Verify prompt includes: (1) full context blob, (2) all templates, (3) 'DO NOT re-fetch' instructions, (4) clear success criteria. Incomplete context causes silent failures (subagent makes wrong decisions without exceptions)."
---

# Subagent Prompt Structure for Complete Context Embedding

## Overview

Subagent prompts must be **completely self-contained**. The subagent cannot access parent context, load skills, or reference external documentation. All necessary information must be embedded directly in the prompt.

## Core Principle

**If the subagent needs it to complete the task, it must be in the prompt.**

Incomplete context causes silent subagent failures:

- Subagent requests unavailable skills
- Subagent re-fetches data passed in parent context
- Subagent makes wrong decisions based on incomplete rules
- Subagent asks for clarification instead of executing

## Required Prompt Components

### 1. Context Blob

All data needed for the task:

```markdown
## Context

### PR Data

{pr_json}

### Objective Data

{objective_json}

### Completed PRs

{completed_prs_json}
```

**Format**: JSON or structured markdown, not references.

### 2. Templates

All templates the subagent needs to compose output:

```markdown
## Templates

### Action Comment Template

When a PR lands, compose:
"""
**PR #{pr_number} landed**: {pr_title}

{pr_url}

Status: Advancing to next objective step.
"""

### Roadmap Step Format

Completed steps:

- [x] Step description

Pending steps:

- [ ] Step description
```

**Format**: Literal templates with placeholder syntax, not "use skill X template".

### 3. Rules

All validation and composition rules:

```markdown
## Rules

1. Action comment MUST include PR number, title, and URL
2. Roadmap body MUST have exactly {n} completed steps
3. Step descriptions are copied verbatim from PR titles
4. DO NOT re-fetch objective from GitHub API for validation
5. Validate by counting steps in composed body
```

**Format**: Explicit, numbered list with DO/DON'T directives.

### 4. Instructions

Step-by-step task breakdown:

```markdown
## Instructions

1. Validate input: Ensure all context is present
2. Compose action comment using template
3. Update roadmap body with completed steps
4. Self-validate: Count completed steps = {n}
5. Write changes via GitHub API
6. Report result with validation status
```

**Format**: Ordered steps, clear verbs (validate, compose, write).

### 5. Success Criteria

Clear definition of correct output:

```markdown
## Success Criteria

- [ ] Action comment posted as issue comment
- [ ] Roadmap body updated with {n} completed steps
- [ ] Step count validated (no re-fetch required)
- [ ] All API calls succeeded
- [ ] Result returned with validation status
```

**Format**: Checklist, measurable outcomes.

## Anti-Patterns

### ❌ Referencing External Skills

**Bad**:

```markdown
Use the `objective` skill templates for action comment composition.
```

**Why it fails**: Subagent cannot load skills from parent context.

**Good**:

```markdown
## Action Comment Template

When a PR lands, compose:
"""
**PR #{pr_number} landed**: {pr_title}

{pr_url}

Status: Advancing to next objective step.
"""
```

### ❌ Incomplete Context

**Bad**:

```markdown
Update the objective roadmap body. The objective data is in the parent context.
```

**Why it fails**: Subagent has no access to parent context.

**Good**:

```markdown
## Context

### Objective Data

{
"objective_number": 6542,
"title": "Optimize workflow",
"current_step": 2,
"completed_prs": [1, 2]
}

Update this objective's roadmap body to mark PRs 1 and 2 as completed.
```

### ❌ Vague Validation

**Bad**:

```markdown
Validate the output is correct.
```

**Why it fails**: Subagent doesn't know what "correct" means.

**Good**:

```markdown
## Validation

After composing roadmap body:

1. Count completed steps (parse markdown for "- [x]")
2. Verify count = len(completed_prs) = 2
3. If count mismatch, report error
4. DO NOT re-fetch objective from GitHub API
```

## Template: Complete Subagent Prompt

```markdown
# Task: {Brief Task Description}

## Context

### {Context Section 1}

{data_json_or_markdown}

### {Context Section 2}

{data_json_or_markdown}

## Templates

### {Template 1 Name}

{literal_template_with_placeholders}

### {Template 2 Name}

{literal_template_with_placeholders}

## Rules

1. {Rule with explicit DO/DON'T}
2. {Rule with explicit DO/DON'T}
3. DO NOT re-fetch data passed in context
4. DO NOT request skills (all templates embedded above)

## Instructions

1. {Step 1 with clear verb}
2. {Step 2 with clear verb}
3. Self-validate: {specific check}
4. {Final step with output format}

## Success Criteria

- [ ] {Measurable outcome 1}
- [ ] {Measurable outcome 2}
- [ ] {Validation outcome}

## Output Format

Return JSON:
{
"status": "success" | "error",
"validation": {"check": "result"},
"error": "optional error message"
}
```

## Checklist for Subagent Prompts

Before launching subagent, verify prompt includes:

- [ ] **All context data** - No references to parent context
- [ ] **All templates** - Literal templates, not skill references
- [ ] **Explicit rules** - DO/DON'T directives for validation
- [ ] **Step-by-step instructions** - Clear verbs, ordered steps
- [ ] **Success criteria** - Measurable outcomes
- [ ] **Self-validation guidance** - How to validate without re-fetching
- [ ] **Output format** - Structured result for parent to parse

## Common Mistakes

❌ **"Use the X skill"** - Subagent cannot load skills
❌ **"Refer to parent context"** - Subagent has no access
❌ **"Follow best practices"** - Too vague, embed explicit rules
❌ **"Validate correctly"** - Define "correct" with criteria
✅ **Embed all templates** - Literal, with placeholders
✅ **Embed all data** - JSON or markdown, not references
✅ **Explicit validation** - Step-by-step, no re-fetch
✅ **Clear instructions** - Ordered, actionable steps

## Debugging Subagent Failures

If subagent is:

- **Requesting skills** → Embed templates in prompt
- **Re-fetching data** → Embed data in prompt + add "DO NOT re-fetch" rule
- **Asking clarifications** → Add explicit rules and instructions
- **Producing wrong output** → Add validation criteria and examples

## Real-World Example: objective-update-with-landed-pr

### Before (Incomplete Context)

```markdown
Update the objective roadmap when PR lands. Use the objective skill templates.
```

**Result**: Subagent requests skill, parent must load, wastes 1 turn.

### After (Complete Context)

```markdown
# Task: Update Objective Roadmap on PR Land

## Context

### PR Data

{"number": 6540, "title": "Optimize workflow", "url": "..."}

### Objective Data

{"objective_number": 6542, "current_step": 2, "completed_prs": [1]}

## Templates

### Action Comment

"""
**PR #{pr_number} landed**: {pr_title}

{pr_url}

Status: Advancing to next objective step.
"""

### Roadmap Step

- [x] {pr_title} (completed)

## Rules

1. Action comment includes PR number, title, URL
2. Roadmap body has exactly 2 completed steps (1 previous + this PR)
3. DO NOT re-fetch objective from GitHub API
4. Validate by counting "- [x]" in composed body

## Instructions

1. Compose action comment using template
2. Update roadmap body with new completed step
3. Count completed steps in body → expect 2
4. Write via GitHub API
5. Return result with validation

## Success Criteria

- [ ] Action comment posted
- [ ] Roadmap has 2 completed steps
- [ ] Validated without re-fetch
```

**Result**: Subagent executes in single turn, no skill load needed.

## Related Patterns

- [Subagent Delegation for Optimization](subagent-delegation-for-optimization.md) - When to delegate
- [Subagent Self-Validation](subagent-self-validation.md) - How to validate without re-fetching
- [Turn Count Profiling](../optimization/turn-count-profiling.md) - Measuring prompt optimization impact
- [Subagent Model Selection](../reference/subagent-model-selection.md) - Choosing right model for task
