---
title: Subagent Self-Validation Pattern
read_when:
  - "implementing subagent delegation"
  - "designing validation logic for subagents"
  - "optimizing API call patterns"
  - "seeing subagents re-fetch context unnecessarily"
  - "designing prompt structure for Task tool delegation"
tripwires:
  - action: "reviewing subagent code that re-fetches context via GitHub API or other external sources"
    warning: "If subagent is re-fetching context already available or passed in the prompt, context embedding is incomplete. Add missing data to prompt instead. This is a silent performance regression (wasted API calls, added latency)."
---

# Subagent Self-Validation Pattern

## Overview

When a subagent composes content (markdown, JSON, API payloads), it should validate by analyzing what it just composed rather than re-fetching from external sources. This eliminates API latency, reduces rate limit pressure, and simplifies the validation logic.

## Core Principle

**The subagent already has the context it needs to validate its own output.**

If validation requires data that the subagent just produced or was given in its prompt, re-fetching that data is wasteful and indicates incomplete context embedding.

## When Self-Validation Works

### Deterministic Validation

- Pattern matching (regex, string checks)
- Counting elements (steps in roadmap, items in list)
- Structure validation (JSON schema, markdown format)
- Rules-based checking (length limits, required fields)

### Example: Objective Roadmap Step Counting

**Task**: Update objective roadmap body, ensure step count matches completed PRs.

**Self-validation approach**:

```
1. Compose new roadmap body with updated steps
2. Count steps in composed body (parse markdown)
3. Compare to expected count from input data
4. Validate: count matches → success
```

**Anti-pattern (unnecessary re-fetch)**:

```
1. Compose new roadmap body
2. Write to GitHub API
3. Re-fetch objective from GitHub API
4. Count steps in fetched body
5. Compare to expected count
```

The anti-pattern wastes one API call and adds latency (~500ms-1s).

## When Self-Validation Doesn't Work

### External Transformation Required

- Content modified by external system (GitHub markdown rendering)
- Server-side validation rules not known to agent
- Race conditions (concurrent modifications possible)
- External side effects must be confirmed

### Example: PR Creation

**Cannot self-validate**: PR number is assigned by GitHub after creation.
**Must re-fetch**: Get PR number from API response, cannot predict it.

## Implementation Pattern

### Subagent Prompt Structure

Include validation criteria in the prompt:

```markdown
## Task

Compose action comment and update objective roadmap body.

## Context

{pr_data}
{objective_data}
{completed_prs: [1, 2, 3]}

## Success Criteria

1. Action comment includes PR number, title, link
2. Roadmap body has exactly 3 completed steps
3. Each completed step formatted as: "- [x] Step description"

## Validation

After composing:

1. Count completed steps in roadmap body
2. Verify count = len(completed_prs) = 3
3. DO NOT re-fetch objective from GitHub API
4. Report validation result
```

### Subagent Implementation

```python
# Compose content
action_comment = compose_action_comment(pr_data)
roadmap_body = update_roadmap_body(objective_data, completed_prs)

# Self-validate (no re-fetch)
completed_step_count = count_completed_steps(roadmap_body)
expected_count = len(completed_prs)

if completed_step_count != expected_count:
    raise ValidationError(f"Expected {expected_count} completed steps, found {completed_step_count}")

# Write to API
github.update_objective(roadmap_body)

# Success!
return {"status": "success", "validated": True}
```

## Tripwire

**If a subagent is re-fetching context that was passed in the prompt or that it just composed, the context embedding is incomplete.**

Add the missing data to the prompt instead of re-fetching.

## Benefits

### Performance

- Eliminates 1 API call per validation (500ms-1s saved)
- Reduces rate limit pressure on GitHub API
- Enables true single-turn delegation

### Simplicity

- Validation logic is self-contained in subagent
- No need to parse API responses for validation
- Fewer error cases to handle

### Cost

- One fewer API call = cost savings
- Haiku processes validation in same turn (negligible cost)

## Common Mistakes

❌ **Re-fetching data passed in prompt** - "Get objective body to count steps"
❌ **Re-fetching composed content** - "Fetch issue to verify body matches"
❌ **External validation when internal works** - "Call API to check format"
✅ **Parse composed output directly** - "Count steps in body I just wrote"
✅ **Use input data for comparison** - "Check count matches input list length"
✅ **Embed validation rules in prompt** - "Success criteria: exactly 3 steps"

## Decision Framework

When designing subagent validation:

1. **What needs validation?** - Structure, content, count, format?
2. **Is input data sufficient?** - Can validate against prompt context?
3. **Is external state needed?** - Race conditions, server-assigned IDs?
4. **Can rules be embedded?** - Known patterns, deterministic checks?

If answers are "yes" to 2 and 4, use self-validation.
If answer is "yes" to 3, use external validation.

## Real-World Examples

### Self-Validation: Objective Roadmap Update

- Input: List of completed PRs with titles
- Task: Update roadmap body with completed steps
- Validation: Count completed steps = len(input list)
- ✅ Self-validate by parsing composed body

### External Validation: PR Creation

- Input: Branch name, PR title, body
- Task: Create PR via GitHub API
- Validation: PR was successfully created, get PR number
- ❌ Cannot self-validate, must check API response

### Self-Validation: Action Comment Composition

- Input: PR data (number, title, url)
- Task: Compose markdown comment
- Validation: Comment includes all required fields
- ✅ Self-validate by regex matching composed comment

## Related Patterns

- [Subagent Delegation for Optimization](subagent-delegation-for-optimization.md) - When to delegate to subagents
- [Subagent Prompt Structure](subagent-prompt-structure.md) - How to embed context and rules
- [Turn Count Profiling](../optimization/turn-count-profiling.md) - Measuring validation latency impact
