---
description: Interview user in-depth to gather requirements for a plan or objective
argument-hint: [topic or feature description]
allowed-tools: AskUserQuestion, Read, Glob, Grep
---

# /local:interview

Interview the user in-depth about a feature or task, then return a structured summary oriented toward creating a plan or objective.

## Usage

```bash
# With a topic hint
/local:interview authentication system

# Without arguments (will ask about the topic)
/local:interview
```

---

## Agent Instructions

Execute the interview workflow in four phases: explore, interview, scope determination, and summary.

### Phase 1: Explore Codebase

**1.1 Parse arguments**

Extract the topic from `$ARGUMENTS`:

- If non-empty, use it as the initial topic
- If empty, proceed to ask about the topic in Phase 2

**1.2 Identify relevant code**

If a topic was provided, explore the codebase before asking questions:

1. **Search for relevant files** using Glob:
   - Look for files related to the topic (e.g., if topic is "authentication", search for `**/*auth*`)
   - Look for configuration files, test files, and implementation files

2. **Search for relevant code** using Grep:
   - Search for key terms from the topic
   - Identify main entry points, APIs, and interfaces

3. **Read key files**:
   - Read 2-4 most relevant files to understand current implementation
   - Note: Keep exploration focused - don't read more than necessary

**1.3 Build initial context**

Create a mental model of:

- What exists already (if anything)
- Where the work would likely happen
- What patterns/conventions are used in this area

### Phase 2: Interview Rounds

Conduct 4-8 rounds of questions, with 1-4 questions per round.

**Interview structure:**

1. **Round 1: Topic and goals**
   - If no topic was provided, start by asking what the user wants to work on
   - Ask about the high-level goal and motivation
   - Ask what problem this solves or what value it provides

2. **Round 2: Requirements**
   - Ask about must-have requirements
   - Ask about nice-to-have features
   - Ask what's explicitly out of scope

3. **Round 3-N: Deep dive** (continue as needed)
   - Between each round, read additional code files if needed based on user answers
   - Ask about specific behavior, edge cases, and design decisions
   - Ask about constraints (performance, compatibility, security)
   - Ask about acceptance criteria and definition of done
   - Probe areas where the user's answers raise new questions

**Question guidelines:**

- Ask 1-4 questions per round (prefer fewer, more focused questions)
- Let user responses guide the next round
- Read additional code between rounds if user mentions specific files/areas
- Continue until you have enough detail to write a plan or objective

**Between-round processing:**

After each round of answers:

1. Summarize what you learned (internally, not to user)
2. Identify gaps or ambiguities
3. Read additional code files if needed
4. Prepare next round's questions

### Phase 3: Scope Determination

**During a late interview round** (round 4-6), ask about scope:

```
Based on what you've described, this work could be:

A) A single PR (plan-sized): Can be implemented in one focused pull request
B) Multiple PRs (objective-sized): Requires breaking into multiple independent PRs

Which approach makes sense for this work?
```

Listen for signals:

- **Plan-sized**: "This is straightforward", "Should be one PR", "It's focused"
- **Objective-sized**: "This is complex", "Multiple parts", "Will take several PRs"

### Phase 4: Structured Summary

After completing the interview, output a structured summary to the conversation.

**Output format:**

```markdown
## Interview Summary: [Topic]

### Context

[1-2 paragraphs summarizing what exists now and what's being requested]

### Requirements

**Must have:**

- [Bulleted list of must-have requirements]

**Nice to have:**

- [Bulleted list of nice-to-have features]

**Out of scope:**

- [Bulleted list of explicitly excluded items]

### Behavior

[Description of expected behavior, user flows, or interaction patterns]

### Edge Cases & Constraints

[Bulleted list of edge cases to handle and constraints to respect]

### Design Decisions

[Key architectural or design choices that should be made]

### Acceptance Criteria

[Bulleted checklist of how to verify the work is complete]

### Open Questions

[Bulleted list of any remaining ambiguities or decisions needed]

---

### Recommendation

**Scope assessment:** This is [plan-sized / objective-sized] work.

**Reasoning:** [1-2 sentences explaining why]

**Next step:** [Enter plan mode / Run `/erk:objective-create`]
```

**Important:**

- The summary should be comprehensive enough to start planning without re-asking questions
- All key information from the interview should be captured
- The recommendation should be clear and actionable

### Key Principles

1. **Explore before asking** - Read relevant code first to ask informed questions
2. **Listen and adapt** - Let user responses guide subsequent questions
3. **Read between rounds** - Consult code when user mentions specific areas
4. **Be thorough** - Gather enough detail for effective planning
5. **No side effects** - This command only reads and asks questions; it doesn't create files or enter plan mode itself

---

## Error Cases

| Error                    | Message                                        |
| ------------------------ | ---------------------------------------------- |
| Codebase search fails    | Continue with interview (exploration optional) |
| User declines to answer  | Note the gap in "Open Questions"               |
| Unclear scope assessment | Default to plan-sized, note uncertainty        |

---

## Examples

### Example: Plan-sized work

```
User: /local:interview add logout button
[Agent explores auth-related files, asks 4-6 questions about placement, behavior, confirmation]
[Agent outputs summary with recommendation: "This is plan-sized work. Next step: Enter plan mode"]
```

### Example: Objective-sized work

```
User: /local:interview redesign authentication system
[Agent explores current auth implementation, asks 6-8 questions about requirements, migration, scope]
[Agent outputs summary with recommendation: "This is objective-sized work. Next step: Run `/erk:objective-create`"]
```
