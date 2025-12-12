# Extract Agent Docs - Analysis Logic

Shared analysis logic for `/erk:extract-agent-docs` and `/erk:extract-agent-docs-from-log` commands.

## Two Categories of Documentation Needs

This command detects TWO distinct types of documentation gaps:

### Category A: Exploration Friction (Learning Gaps)

Documentation that would have made the session more efficient - things we had to discover through exploration.

### Category B: Net New Implementation (Teaching Gaps)

Documentation needed because we BUILT something new that future agents/users need to understand.

---

## Category A: Exploration Friction Signals

Scan for these signals of missing documentation:

1. **Repeated explanations** - Same concept explained multiple times during the session
2. **Trial-and-error patterns** - Multiple failed attempts before finding the right approach
3. **Extensive codebase exploration** - Long search sequences for patterns that are core to the project
4. **Architecture discoveries** - Key patterns or conventions learned through exploration
5. **Workflow corrections** - User had to redirect the agent's approach
6. **External research** - WebSearch/WebFetch for info that could be local documentation
7. **Context loading** - User provided project-specific context that could be pre-loaded

## Category B: Net New Implementation Signals

Scan for these signals that new code needs documentation:

1. **New CLI commands** - Any new command needs at minimum: glossary entry, routing table update
2. **New constants/labels** - Domain concepts introduced (e.g., new GitHub labels, status values)
3. **New patterns introduced** - If the implementation establishes a pattern others should follow
4. **New integration points** - APIs, webhooks, or interfaces that external code may consume
5. **New configuration options** - Settings users need to know about
6. **New file structures** - Directories or file conventions established

### Category B Checklist

For each net new implementation, consider:

| What was added?   | Documentation action                             |
| ----------------- | ------------------------------------------------ |
| CLI command       | Update command reference, add routing entry      |
| Constant/label    | Add to glossary                                  |
| New pattern       | Document in relevant agent doc or create new one |
| Config option     | Add to configuration guide                       |
| New ABC/interface | Update architecture docs if significant          |
| Test utilities    | Update testing docs if reusable                  |

## Categorization

For each finding, determine the appropriate documentation type:

**Agent Docs** (`.erk/docs/agent/`) are best for:

- Architectural patterns and design decisions
- Workflow guides and processes
- Project-specific conventions
- Integration patterns between systems

**Skills** (`.claude/skills/`) are best for:

- Coding standards and style guides
- Tool-specific guidance (e.g., CLI tools, libraries)
- Reusable patterns across projects
- Domain-specific knowledge

## Action Types

For each finding, decide the appropriate action:

| Action              | When to use                                                                             |
| ------------------- | --------------------------------------------------------------------------------------- |
| **New doc**         | No existing doc covers this topic                                                       |
| **Update existing** | An existing doc covers the topic but is missing key information discovered this session |
| **Merge into**      | The finding is small and fits naturally into an existing doc's scope                    |

## Priority and Effort Assessment

**Assess priority:**

| Priority   | Criteria                                                        |
| ---------- | --------------------------------------------------------------- |
| **High**   | Caused significant session friction; likely to recur frequently |
| **Medium** | Caused moderate friction; will help but not critical            |
| **Low**    | Minor improvement; nice-to-have                                 |

**Assess effort:**

| Effort          | Criteria                                                   |
| --------------- | ---------------------------------------------------------- |
| **Quick**       | Straightforward to write; information is fresh and clear   |
| **Medium**      | Requires some additional exploration or synthesis          |
| **Substantial** | Needs significant research, diagrams, or cross-referencing |

## Routing Entries

**For Agent Docs, always include a routing entry:**

The routing entry enables discoverability via the AGENTS.md routing table. Format:

```
| [Trigger phrase] | → [.erk/docs/agent/[name].md](.erk/docs/agent/[name].md) |
```

Good trigger phrases:

- Start with action verbs: "Parse", "Work with", "Implement", "Debug"
- Be specific to the use case, not the doc title
- Match patterns in the existing AGENTS.md routing table

## Output Format

Display suggestions organized by category:

````markdown
## Documentation Suggestions

Based on this session analysis:

---

## Category A: Exploration Friction (Learning Gaps)

Documentation that would have made THIS session more efficient:

### A1. [Suggested Doc Title]

**Type:** Agent Doc | Skill
**Location:** `.erk/docs/agent/[name].md` | `.claude/skills/[name]/`
**Routing:** `| [Trigger phrase] | → [.erk/docs/agent/[name].md](.erk/docs/agent/[name].md) |`
**Action:** New doc | Update existing `[path]` | Merge into `[path]`
**Priority:** High | Medium | Low
**Effort:** Quick | Medium | Substantial

**Why needed:** [Brief explanation tied to specific exploration patterns]

**Draft content:**

```markdown
# [Title]

## Overview

[One paragraph summary]

## [Main Section]

[Content]
```

---

## Category B: Net New Implementation (Teaching Gaps)

Documentation needed for what was BUILT this session:

### B1. [Suggested Doc Title]

**Type:** Glossary entry | Routing update | Agent Doc | Reference update
**Location:** `[path to file]`
**Action:** Update existing `[path]` | New section in `[path]`
**Priority:** High | Medium | Low
**Effort:** Quick | Medium | Substantial

**What was implemented:** [Brief description of the new feature/component]

**Draft content:**

```markdown
[Specific content to add]
```

---

**Next steps:**

- For Category A: Enter Plan Mode to create exploration docs, then `/erk:save-plan`
- For Category B: Apply updates directly (usually quick glossary/routing updates)
````

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

## Before Dismissing as "Edge Case"

Before concluding something is too niche to document, validate:

1. **Is this pattern used in multiple commands/workflows?**
   - Example: "worktree deletion" appears in `pr land`, `wt rm`, `stack` commands
   - If yes → NOT an edge case, it's a core pattern

2. **Is this infrastructure used across the codebase?**
   - Example: SentinelPath is used in every test file
   - Test infrastructure docs help every test-writing session

3. **Did exploration take significant time (30+ minutes)?**
   - If yes → others will likely hit the same friction
   - Time spent is a signal of documentation value

4. **Would this help a new contributor?**
   - Even "internal" patterns matter for onboarding

**Test infrastructure documentation is EQUALLY valuable as feature documentation.**
Dismissing something as "internal" or "test-related" is not a valid reason to skip it.

## Guidelines

- **Be specific**: Tie each suggestion to actual patterns observed in the session
- **Prioritize impact**: Put the most impactful suggestions first
- **Verify first**: Always check existing docs before suggesting new ones
- **Focus on reusability**: Suggest docs that would help many future sessions
- **Keep drafts actionable**: Draft content should be 60-70% complete, not just headers
- **Prefer updates over new docs**: A single comprehensive doc beats many small ones
- **Include routing**: Every Agent Doc suggestion must include an AGENTS.md routing entry

## If No Suggestions

If the session was efficient and no documentation gaps were identified:

```markdown
## Documentation Suggestions

This session ran smoothly with no significant documentation gaps identified.

**Checked:**

- `.erk/docs/agent/` - [X existing docs]
- `.claude/skills/` - [X existing skills]

The existing documentation appears to cover the patterns and workflows used.
```

## Example Signals and Responses

### Category A Examples (Exploration Friction)

| Signal                                           | Suggestion Type                    | Action           |
| ------------------------------------------------ | ---------------------------------- | ---------------- |
| Searched 10+ files to understand error handling  | Agent Doc: Error Handling Patterns | New doc          |
| User corrected CLI tool usage twice              | Skill: [Tool Name] Usage Guide     | New doc          |
| Found undocumented API pattern after exploration | Agent Doc: API Conventions         | Update existing  |
| WebSearched for library config options           | Skill: [Library] Configuration     | New doc or merge |
| User explained deployment process in detail      | Agent Doc: Deployment Guide        | New doc          |

### Category B Examples (Net New Implementation)

| What was implemented                   | Suggestion Type    | Action                        |
| -------------------------------------- | ------------------ | ----------------------------- |
| New CLI command `erk plan docs`        | Glossary + Routing | Update glossary.md, AGENTS.md |
| New GitHub label `docs-extracted`      | Glossary entry     | Update glossary.md            |
| New ABC interface for integration      | Architecture doc   | Update or create agent doc    |
| New test utility `build_xyz_context()` | Testing doc        | Update testing patterns doc   |
| New configuration option               | Config reference   | Update config docs            |
| New constants in `constants.py`        | Glossary entries   | Update glossary.md            |
