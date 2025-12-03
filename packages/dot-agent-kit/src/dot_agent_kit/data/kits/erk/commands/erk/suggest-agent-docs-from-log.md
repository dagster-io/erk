---
description: Analyze a session log to suggest documentation improvements
---

# /erk:suggest-agent-docs-from-log

Analyzes a session log file (by session ID) to identify documentation gaps and suggest new agent docs or skills that would make future sessions more efficient.

## Usage

```bash
/erk:suggest-agent-docs-from-log <session-id>
```

**Arguments:**

- `<session-id>` - Full or partial (first 8 chars) session ID to analyze

Run this command to review past sessions for:

- Repeated explanations that could be pre-loaded docs
- Trial-and-error patterns indicating missing guidance
- Extensive codebase exploration for core patterns
- Architecture discoveries that should be documented
- Workflow corrections suggesting unclear conventions
- External research that could be local documentation

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

You are analyzing a session log file to identify patterns that suggest missing documentation.

### Step 0: Load and Preprocess Session Log

First, find the project directory and locate the session log:

```bash
# Get the project directory for this codebase
dot-agent run erk find-project-dir
```

The output contains the project directory path (e.g., `/Users/name/.claude/projects/-Users-name-code-myproject`).

Next, list session logs to find one matching the provided session ID:

```bash
# List recent sessions for this project
ls -la <project-dir>/sessions/
```

Session directories are named by session ID (e.g., `70e91b45-c320-442f-9ddc-7122098285ce/`).

Match the provided session ID argument:

- If full ID provided: exact match
- If partial ID (8+ chars): prefix match

Once you find the matching session directory, preprocess it:

```bash
# Preprocess the session log for analysis
dot-agent run erk preprocess-session <project-dir>/sessions/<session-id>/logs/ --stdout
```

This outputs compressed XML with:

- Tool calls and results (most recent per batch)
- User messages
- Assistant responses
- Correlated agent subprocess logs (via `--include-agents` default)

### Step 1: Review Session Content

Scan the preprocessed session for these signals of missing documentation:

1. **Repeated explanations** - Same concept explained multiple times during the session
2. **Trial-and-error patterns** - Multiple failed attempts before finding the right approach
3. **Extensive codebase exploration** - Long search sequences for patterns that are core to the project
4. **Architecture discoveries** - Key patterns or conventions learned through exploration
5. **Workflow corrections** - User had to redirect the agent's approach
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

**For Agent Docs, always include a routing entry:**

The routing entry enables discoverability via the AGENTS.md routing table. Format:

```
| [Trigger phrase] | → [docs/agent/[name].md](docs/agent/[name].md) |
```

Good trigger phrases:

- Start with action verbs: "Parse", "Work with", "Implement", "Debug"
- Be specific to the use case, not the doc title
- Match patterns in the existing AGENTS.md routing table

### Step 5: Output Suggestions Directly

**Note:** Unlike `/erk:suggest-agent-docs`, this command skips the confirmation step and outputs all suggestions immediately since the user explicitly chose to analyze a specific session.

---

## Output Format

Display suggestions using this format:

`````markdown
## Documentation Suggestions

Based on session `<session-id>`, the following documentation would improve future efficiency:

---

### 1. [Suggested Doc Title]

**Type:** Agent Doc | Skill
**Location:** `docs/agent/[name].md` | `.claude/skills/[name]/`
**Routing:** `| [Trigger phrase] | → [docs/agent/[name].md](docs/agent/[name].md) |`
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

- **Be specific**: Tie each suggestion to actual patterns observed in the session
- **Prioritize impact**: Put the most impactful suggestions first
- **Verify first**: Always check existing docs before suggesting new ones
- **Focus on reusability**: Suggest docs that would help many future sessions
- **Keep drafts actionable**: Draft content should be 60-70% complete, not just headers
- **Prefer updates over new docs**: A single comprehensive doc beats many small ones
- **Include routing**: Every Agent Doc suggestion must include an AGENTS.md routing entry

---

## If No Suggestions

If the session was efficient and no documentation gaps were identified:

```markdown
## Documentation Suggestions

Session `<session-id>` ran smoothly with no significant documentation gaps identified.

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
