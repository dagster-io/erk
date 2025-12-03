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

### Step 1-4: Analyze Session

@../../docs/erk/includes/suggest-docs-analysis-shared.md

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

## Output

After user confirmation, display suggestions using the output format from the analysis guide above.
