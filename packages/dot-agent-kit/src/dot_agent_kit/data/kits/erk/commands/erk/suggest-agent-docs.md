---
description: Analyze session to suggest documentation improvements
---

# /erk:suggest-agent-docs

Analyzes the current conversation to identify documentation gaps and suggest new agent docs or skills that would make future sessions more efficient.

## Usage

```bash
/erk:suggest-agent-docs
```

Run this command after a session where you:

- Had to explain the same concept multiple times
- Went through trial-and-error to discover patterns
- Explored the codebase extensively to find conventions
- Were redirected by the user on your approach
- Searched the web for information that could be local docs

## What You'll Get

A structured list of documentation suggestions, each with:

- **Title**: Descriptive name for the doc
- **Type**: Agent Doc (`docs/agent/`) or Skill (`.claude/skills/`)
- **Action**: New doc, update existing, or merge into existing
- **Priority**: Effort/impact assessment
- **Rationale**: Why this session suggests the doc is needed
- **Draft content**: Skeleton ready to be fleshed out

---

## Agent Instructions

You are analyzing the current conversation to identify patterns that suggest missing documentation.

### Step 0: Verify Existing Documentation

Before analyzing gaps, scan the project for existing documentation:

```bash
# Check for existing agent docs
ls -la docs/agent/ 2>/dev/null || echo "No docs/agent/ directory"

# Check for existing skills
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"

# Check root-level docs
ls -la *.md README* CONTRIBUTING* 2>/dev/null
```

Create a mental inventory of what's already documented. For each potential suggestion later, verify it doesn't substantially overlap with existing docs.

### Step 1: Review Conversation History

Scan the conversation for these signals of missing documentation:

1. **Repeated explanations** - Same concept explained multiple times during the session
2. **Trial-and-error patterns** - Multiple failed attempts before finding the right approach
3. **Extensive codebase exploration** - Long search sequences for patterns that are core to the project
4. **Architecture discoveries** - Key patterns or conventions learned through exploration
5. **Workflow corrections** - User had to redirect your approach
6. **External research** - WebSearch/WebFetch for info that could be local documentation
7. **Context loading** - User provided project-specific context that could be pre-loaded

### Step 2: Categorize Findings

For each finding, determine the appropriate documentation type:

**Agent Docs** (`docs/agent/`) are best for:

- Architectural patterns and design decisions
- Workflow guides and processes
- Project-specific conventions
- Integration patterns between systems

**Skills** (`.claude/skills/`) are best for:

- Coding standards and style guides
- Tool-specific guidance (e.g., CLI tools, libraries)
- Reusable patterns across projects
- Domain-specific knowledge

### Step 3: Determine Action Type

For each finding, decide the appropriate action:

| Action              | When to use                                                                             |
| ------------------- | --------------------------------------------------------------------------------------- |
| **New doc**         | No existing doc covers this topic                                                       |
| **Update existing** | An existing doc covers the topic but is missing key information discovered this session |
| **Merge into**      | The finding is small and fits naturally into an existing doc's scope                    |

### Step 4: Generate Suggestions with Draft Content

For each documentation gap, create a full suggestion including a draft skeleton.

**Assess effort and priority:**

| Priority   | Criteria                                                        |
| ---------- | --------------------------------------------------------------- |
| **High**   | Caused significant session friction; likely to recur frequently |
| **Medium** | Caused moderate friction; will help but not critical            |
| **Low**    | Minor improvement; nice-to-have                                 |

| Effort          | Criteria                                                   |
| --------------- | ---------------------------------------------------------- |
| **Quick**       | Straightforward to write; information is fresh and clear   |
| **Medium**      | Requires some additional exploration or synthesis          |
| **Substantial** | Needs significant research, diagrams, or cross-referencing |

### Step 5: Confirm with User

Before presenting final output, ask for confirmation:

> "Based on this session, I identified these potential documentation gaps:
>
> 1. [Brief title] - [One sentence why]
> 2. [Brief title] - [One sentence why]
> 3. ...
>
> Which of these would be valuable for future sessions? I'll generate detailed suggestions and draft content for the ones you select."

Wait for user response before generating full output.

---

## Output Format

After user confirmation, display suggestions using this format:

`````markdown
## Documentation Suggestions

Based on this session, the following documentation would improve future efficiency:

---

### 1. [Suggested Doc Title]

**Type:** Agent Doc | Skill  
**Location:** `docs/agent/[name].md` | `.claude/skills/[name]/`  
**Action:** New doc | Update existing `[path]` | Merge into `[path]`  
**Priority:** High | Medium | Low  
**Effort:** Quick | Medium | Substantial

**Why needed:** [Brief explanation tied to specific session patterns]

**Draft content:**

````markdown
# [Title]

## Overview

[One paragraph summary of what this doc covers and why it matters]

## [Main Section 1]

[Description of what goes here]

- Key point 1
- Key point 2

## [Main Section 2]

[Description of what goes here]

```[language]
// Code example placeholder
```
````
`````

## Common Pitfalls

- [Pitfall discovered this session]

## Related

- [Link to related doc if applicable]

```

---

### 2. [Next suggestion...]

...

---

**Next steps:** Run `/erk:craft-plan` with a selected suggestion to create the full documentation.
```

````

---

## Anti-Pattern Guidance

**Do NOT suggest documentation for:**

- **One-off bugs or edge cases** - Problems unlikely to recur don't warrant permanent docs
- **Frequently changing information** - Link to source of truth instead of duplicating
- **Generic programming concepts** - Link to official docs (e.g., don't document "how async/await works")
- **Session-specific context** - Information that won't generalize to other sessions
- **Already well-documented patterns** - Check existing docs first; don't duplicate
- **User preferences** - Individual workflow preferences aren't project documentation

**Signs you should NOT create a doc:**

- The information exists in official library/framework documentation
- It would need updating every sprint or release
- Only one person would ever need this information
- The "pattern" was actually a bug or mistake, not a convention

---

## Guidelines

- **Be specific**: Tie each suggestion to actual patterns observed in this session
- **Prioritize impact**: Put the most impactful suggestions first
- **Verify first**: Always check existing docs before suggesting new ones
- **Focus on reusability**: Suggest docs that would help many future sessions
- **Keep drafts actionable**: Draft content should be 60-70% complete, not just headers
- **Prefer updates over new docs**: A single comprehensive doc beats many small ones

---

## If No Suggestions

If the session was efficient and no documentation gaps were identified:

```markdown
## Documentation Suggestions

This session ran smoothly with no significant documentation gaps identified.

**Checked:**

- `docs/agent/` - [X existing docs]
- `.claude/skills/` - [X existing skills]

The existing documentation appears to cover the patterns and workflows used.
```

---

## Example Signals and Responses

| Signal                                           | Suggestion Type                    | Action           |
| ------------------------------------------------ | ---------------------------------- | ---------------- |
| Searched 10+ files to understand error handling  | Agent Doc: Error Handling Patterns | New doc          |
| User corrected CLI tool usage twice              | Skill: [Tool Name] Usage Guide     | New doc          |
| Found undocumented API pattern after exploration | Agent Doc: API Conventions         | Update existing  |
| WebSearched for library config options           | Skill: [Library] Configuration     | New doc or merge |
| User explained deployment process in detail      | Agent Doc: Deployment Guide        | New doc          |
````
