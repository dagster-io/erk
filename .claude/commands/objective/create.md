---
description: Create a structured objective through guided conversation
---

# /objective:create

Create a new objective through an interactive, guided process. You describe what you want to accomplish, and Claude proposes a structured objective for your approval.

## Usage

```bash
/objective:create
```

---

## Agent Instructions

### Step 1: Prompt for Description

Ask the user to describe what they want to accomplish:

```
What do you want to accomplish? Describe it however makes sense to you - goals,
constraints, design decisions you've already made, context about the codebase, etc.

I'll structure it into a formal objective for your review.
```

Wait for the user's response. They may provide:
- A brief summary
- A detailed brain dump
- Existing notes or documentation
- A combination of the above

### Step 2: Analyze and Explore

Based on the user's description:

1. **Identify key elements:**
   - What is the transformation/goal?
   - What design decisions are mentioned or implied?
   - What constraints exist?
   - What's the scope?

2. **Explore the codebase if needed:**
   - If the user references specific code, read it to understand context
   - If architecture decisions are mentioned, verify current state
   - Gather enough context to propose realistic phases

### Step 3: Propose Structured Objective

Write a structured objective proposal and show it to the user. Use this template as a guide (sections are flexible based on complexity):

```markdown
# Objective: [Clear, Concise Title]

[1-2 sentence summary of the transformation]

## Goal

[What the end state looks like - concrete examples of the new API/behavior/architecture]

## Design Decisions

- **[Decision 1]**: [rationale]
- **[Decision 2]**: [rationale]

## Roadmap

### Phase 1: [Name] (1 PR)
[Description of what this phase accomplishes]

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1  | ...         | pending | |
| 1.2  | ...         | pending | |

Test: [How to verify this phase is complete]

### Phase 2: [Name] (1 PR)
[Description]

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1  | ...         | pending | |

Test: [Verification criteria]

## Implementation Context

[Current architecture, target architecture, patterns to follow - include if helpful]

## Related Documentation

- Skills to load: [relevant skills]
- Docs to reference: [relevant docs]
```

**Section guidelines:**
- **Goal**: Always include - this is the north star
- **Design Decisions**: Include if there are meaningful choices already made
- **Roadmap**: Include for bounded objectives - break into shippable phases (1 PR each typically)
- **Principles/Guidelines**: Include for perpetual objectives instead of a roadmap
- **Implementation Context**: Include for larger refactors where current/target state matters
- **Related Documentation**: Include if specific skills or docs are relevant

**For perpetual objectives**, replace the Roadmap section with:

```markdown
## Principles

- [Guiding principle 1]
- [Guiding principle 2]

## Current Focus

[What to prioritize right now - can be updated as the objective evolves]
```

After showing the proposal, ask:

```
Does this capture what you're thinking? I can adjust any section, add more detail
to the roadmap, or restructure the phases.
```

### Step 4: Iterate Until Approved

The user may:
- **Approve as-is**: Proceed to Step 5
- **Request changes**: Make the requested adjustments and show again
- **Add information**: Incorporate new details and show again
- **Restructure**: Reorganize phases/steps based on feedback

Continue iterating until the user approves.

### Step 5: Write to Plan File and Create Issue

Once approved:

1. **Write the objective to the session's plan file:**
   - Get the plan file path from the session context
   - Write the approved objective content to that file

2. **Create the GitHub issue:**
   ```bash
   erk exec objective-save-to-issue --session-id=<session-id> --format=display
   ```

3. **Report success:**
   ```
   Objective created: #<number>
   URL: <issue-url>

   Next steps:
   - Use `/objective:create-plan <number>` to create implementation plans for specific steps
   - Track progress by updating step status in the issue
   ```

---

## Output Format

- **Start**: Single prompt asking what they want to accomplish
- **After description**: Show proposed structured objective
- **Iteration**: Show updated objective after each change
- **Success**: Issue number, URL, and next steps

---

## Differences from /erk:plan-save

| Feature          | /erk:plan-save     | /objective:create     |
| ---------------- | ------------------ | --------------------- |
| Label            | `erk-plan`         | `erk-plan` + `erk-objective` |
| Purpose          | Implementation plan | Roadmap or perpetual focus area |
| Title suffix     | `[erk-plan]`       | None                  |
| Metadata block   | Yes                | No                    |
| Commands section | Yes                | No                    |
| Body content     | Metadata only      | Objective directly    |
| Input            | Existing plan file | Interactive creation  |

---

## Types of Objectives

**Bounded objectives** - Have a clear end state and roadmap:
- "Refactor GitHub gateway into facade pattern"
- "Add dark mode support"

**Perpetual objectives** - Ongoing areas of focus without a defined end:
- "Improve test coverage"
- "Documentation maintenance"
- "Performance optimization"

The structure adapts to the type - perpetual objectives may have principles/guidelines instead of a phased roadmap.

---

## Error Cases

| Scenario             | Action                                     |
| -------------------- | ------------------------------------------ |
| User provides no description | Re-prompt with examples |
| Not authenticated    | Report GitHub auth error                   |
| Issue creation fails | Report API error, offer to retry           |
| Plan file write fails | Report error with path                    |
