# Documentation Plan: Upgrade objective-plan command with safety guardrails and model improvement

## Context

PR #7750 upgraded the `/erk:objective-plan` command with three significant changes: adding `allowed-tools` frontmatter for tool restriction enforcement, upgrading the Task agent model from `haiku` to `sonnet`, and adding explicit safety guardrails against script generation during CLI parsing. These changes reveal important patterns for command authors working with delegated agents.

The safety guardrail pattern is particularly valuable: agents naturally default to writing scripts when asked to perform "programmatic" tasks like JSON parsing, even though LLMs can parse JSON natively. Multiple commands now include explicit "Do NOT write scripts" instructions to prevent this anti-pattern. Documenting this pattern will help future command authors avoid unnecessary complexity and token waste.

The model upgrade from haiku to sonnet for objective data analysis is also noteworthy because it contradicts existing documentation guidance. The current `token-optimization-patterns.md` explicitly cites `/erk:objective-plan` as the canonical example of using haiku for mechanical work. This contradiction must be resolved to prevent confusion.

## Raw Materials

https://gist.github.com/schrockn/3a6159c8441de665d1b8ff4cb9f100ce

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Model Selection Boundary Criteria

**Location:** `docs/learned/planning/token-optimization-patterns.md`
**Action:** UPDATE
**Source:** [PR #7750]

**Draft Content:**

```markdown
## Model Selection for Delegated Work

### Haiku vs Sonnet Boundary

The boundary between haiku and sonnet for delegated work is not simply "mechanical vs reasoning" but depends on specific task characteristics.

**Use haiku when the task is purely mechanical:**
- Fetching data via CLI commands
- Simple parsing without validation
- Format conversion with fixed rules
- No judgment or recommendations required

**Upgrade to sonnet when the task requires:**
- Validation logic beyond simple existence checks
- Mapping between multiple status taxonomies
- Making recommendations based on analyzed data
- Deduplication or conflict detection
- Interpreting ambiguous or incomplete data

**Example:** See `.claude/commands/erk/replan.md` for a command using haiku for pure mechanical parallel delegation (fetch and format without validation).

**Anti-example:** The `/erk:objective-plan` command was upgraded from haiku to sonnet because objective data analysis involves validation, status mapping, and generating recommendations - crossing from mechanical into reasoning territory.
```

---

#### 2. Tool Restriction Pattern for Commands with Delegation

**Location:** `docs/learned/commands/tool-restriction-safety.md`
**Action:** UPDATE
**Source:** [PR #7750]

**Draft Content:**

```markdown
## Tool Restrictions with Task Delegation

When a command delegates work to Task agents, the subagent inherits the parent command's tool restrictions. This creates a transitive restriction pattern.

### Required Pattern

Commands that use Task delegation must:

1. Include `Task` in the `allowed-tools` frontmatter
2. Declare all tools the Task agent might need (transitively)
3. Explicitly exclude tools the subagent should not use

### Example

From `/erk:objective-plan`:

The command has `allowed-tools: Bash, Task, Skill, AskUserQuestion, EnterPlanMode`. This means:
- The parent command can use these 5 tools
- Delegated Task agents inherit these restrictions
- Task agents cannot use Write or Edit (intentionally excluded)

### Validation

Automated tripwires review validates `allowed-tools` declarations. See the tripwires case study for how PR #7750's missing frontmatter was caught and corrected.
```

---

### MEDIUM Priority

#### 3. CLI Parsing Anti-Pattern: Script Generation

**Location:** `docs/learned/planning/cli-parsing-anti-patterns.md`
**Action:** CREATE
**Source:** [PR #7750], [Impl]

**Draft Content:**

```markdown
---
description: Anti-patterns for parsing CLI output in delegated agents
read-when:
  - instructing agents to parse JSON from CLI tools
  - writing Task delegation prompts
  - debugging unnecessarily complex agent workflows
tripwires: 1
---

# CLI Parsing Anti-Patterns

## The Script Generation Anti-Pattern

### The Problem

When instructed to parse JSON output from CLI tools, agents often default to writing Python or bash scripts to do the parsing. This is unnecessary because LLMs can parse JSON natively.

### Anti-Pattern Example

Agent workflow when parsing `erk objective check --json-output`:
1. Run CLI command, capture JSON
2. Write Python script to parse JSON
3. Run Python script via Bash tool
4. Format the parsed data

### Correct Pattern

Agent workflow for the same task:
1. Run CLI command, capture JSON
2. Parse JSON directly (LLMs can do this natively)
3. Format the data inline

### Why This Matters

Script generation causes:
- Unnecessary complexity (scripts can have bugs)
- Token waste (script code + execution in context window)
- Slower execution (extra tool use round-trips)
- Harder debugging (failure could be in CLI, script, or formatting)

### Prevention

Add explicit guardrails to Task delegation prompts:

"CRITICAL: Do NOT write scripts or code. Only use the Bash tool to run the CLI commands listed below."

Or more specifically:

"Do NOT write Python or any other scripts to parse the data - just read the JSON output directly and format it yourself."

### Commands Using This Pattern

See `.claude/commands/erk/objective-plan.md` and `.claude/commands/local/audit-scan.md` for examples of this guardrail in practice.
```

---

#### 4. Inline Data Transformation Pattern

**Location:** `docs/learned/planning/agent-delegation.md`
**Action:** UPDATE
**Source:** [PR #7750]

**Draft Content:**

```markdown
## Agent Output Contracts: Inline Transformation

When delegating work that involves data transformation, explicitly instruct agents to transform data inline rather than generating helper scripts.

### Pattern

Add this instruction to Task delegation prompts:

"Format the [output type] output from step N into the structured summary below. Do NOT write Python or any other scripts to parse the data - just read the [output type] output directly and format it yourself."

### Benefits

- Fewer moving parts (no intermediate script)
- Less failure surface (no script bugs)
- Token efficiency (no script code in context)
- Clearer debugging (failure must be in CLI or formatting)

### Related

See `docs/learned/planning/cli-parsing-anti-patterns.md` for why agents default to script generation and how to prevent it.
```

---

#### 5. Batch Thread Resolution Pattern

**Location:** `docs/learned/pr-operations/batch-thread-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
description: Efficient batch resolution of PR review threads
read-when:
  - resolving multiple PR review threads
  - automating PR comment workflows
  - building batch operations for GitHub
tripwires: 0
---

# Batch Thread Resolution

## Pattern

Use `erk exec resolve-review-threads` with JSON stdin for batch operations instead of individual calls.

## Format

```bash
echo '[{"thread_id": "...", "resolution": "..."}]' | erk exec resolve-review-threads
```

## Benefits

- More efficient than N individual API calls
- Atomic batch operation
- Single network round-trip

## Related Patterns

Combine with complexity-based classification for optimal workflow:
1. Classify threads by complexity (local, multi-location, cross-cutting, complex)
2. Execute batches from simplest to most complex
3. Resolve all threads in a single batch call after fixes

## Example

PR #7750 session resolved threads using this pattern after addressing review comments.
```

---

#### 6. Task Tool vs Skill Invocation for Isolation

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Subagent Isolation Methods

### Task Tool vs Skill Invocation

Skills with `context: fork` metadata do NOT create true subagent isolation when invoked via skill invocation in `--print` mode. To guarantee separate agent context, use explicit Task tool invocation.

### When This Matters

- Running classifiers or analyzers that should not affect parent context
- Delegating work that might modify state unintentionally
- Any skill with `context: fork` metadata

### Correct Pattern

Use Task tool explicitly:

```
Task(prompt="Run the pr-feedback-classifier skill against PR #N...")
```

### Incorrect Pattern

Do NOT use skill invocation for isolation:

```
Skill(name="pr-feedback-classifier")
```

This appears to work but does not create true isolation in `--print` mode.
```

---

### LOW Priority

#### 7. Tripwires System Case Study

**Location:** `docs/learned/ci/tripwires-case-study.md`
**Action:** CREATE
**Source:** [PR #7750]

**Draft Content:**

```markdown
---
description: Case study of automated tripwires review catching and correcting violations
read-when:
  - understanding tripwires value proposition
  - debugging tripwires review failures
  - building confidence in automated review
tripwires: 0
---

# Tripwires Case Study: PR #7750

## Summary

PR #7750 demonstrates the automated tripwires review system working correctly to catch and correct a tool restriction violation.

## Timeline

1. PR submitted with `/erk:objective-plan` command changes
2. Automated tripwires review detected missing `allowed-tools` frontmatter
3. Bot comment provided specific, actionable guidance (exact tools list)
4. Author used `/erk:pr-address` to address the comment
5. Fix pushed within ~30 minutes
6. Automated re-check confirmed compliance

## Key Observations

### Specificity Matters

The tripwires review provided exact guidance: which tools to include and why. This enabled fast resolution without back-and-forth.

### Automated Re-validation

The re-check after fix confirmed compliance with the minimal-set principle. This closed the feedback loop without human review.

### Fast Feedback

~30 minute resolution time from detection to fix demonstrates the value of automated review. Security/safety issues don't wait for human reviewer availability.

## Lessons for Tripwire Authors

1. Tripwire warnings should be specific and actionable
2. Include examples of correct patterns when possible
3. Automated re-validation builds confidence in the system
4. Fast feedback prevents issues from merging
```

---

## Contradiction Resolutions

### 1. Model Selection for Objective Data Analysis: Haiku vs Sonnet

**Existing doc:** `docs/learned/planning/token-optimization-patterns.md`
**Conflict:** The existing doc explicitly cites `/erk:objective-plan` Step 2 as the canonical example of "use haiku for mechanical work", but PR #7750 upgrades this to sonnet.
**Resolution:** Update the existing document to:
1. Remove `/erk:objective-plan` as the canonical haiku example
2. Add criteria for when to upgrade from haiku to sonnet
3. Use `.claude/commands/erk/replan.md` as the new canonical haiku example (it performs parallel fetch-parse-format without validation or recommendations)

The upgrade is justified because objective data analysis involves validation logic, status taxonomy mapping, and recommendation generation - crossing from mechanical into reasoning territory.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Missing allowed-tools Frontmatter

**What happened:** PR #7750 initially lacked `allowed-tools` frontmatter on a command that delegates to Task agents.
**Root cause:** Command delegated to Task agent but author didn't consider transitive tool restrictions.
**Prevention:** Automated tripwires review catches this. Add as a checklist item when creating commands that use Task delegation.
**Recommendation:** ADD_TO_DOC - Document in tool-restriction-safety.md as part of the delegation pattern.

### 2. Script Generation for JSON Parsing

**What happened:** Agents sometimes write Python scripts to parse JSON output from CLI tools when they could parse it directly.
**Root cause:** Agents default to "write a script" for tasks that seem "programmatic" like JSON parsing.
**Prevention:** Add explicit "Do NOT write scripts" instruction in task prompts.
**Recommendation:** TRIPWIRE - This is non-obvious and crosses multiple command contexts.

### 3. Wrong Subagent Isolation Method

**What happened:** Using skill invocation instead of Task tool for skills with `context: fork` metadata in `--print` mode doesn't create true isolation.
**Root cause:** Skill invocation appears to work but doesn't create separate agent context in print mode.
**Prevention:** Document the distinction in planning tripwires.
**Recommendation:** TRIPWIRE - Silent failure makes this particularly dangerous.

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Task Tool Invocation for Subagent Isolation

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before loading a skill with `context: fork` metadata in `--print` mode
**Warning:** Use Task tool invocation (NOT skill invocation) to guarantee true subagent isolation. Skill invocation doesn't create separate agent context for forked skills in print mode.
**Target doc:** `docs/learned/planning/tripwires.md`

This tripwire is particularly important because the failure is silent - skill invocation appears to work but the subagent context is not actually isolated. PR #7750 session correctly used Task tool instead of skill invocation for the pr-feedback-classifier skill, demonstrating awareness of this distinction.

### 2. Script Generation Anti-Pattern in CLI Parsing

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +1, Repeated pattern +1, External tool quirk +1)
**Trigger:** Before instructing agents to parse JSON output from CLI tools
**Warning:** Add explicit "Do NOT write scripts" instruction. Agents can parse JSON natively - writing scripts adds unnecessary complexity, token waste, and failure modes.
**Target doc:** `docs/learned/planning/cli-parsing-anti-patterns.md`

This pattern appears in multiple commands (objective-plan, audit-scan) and addresses a natural agent tendency to reach for scripts for "programmatic" tasks. The anti-pattern wastes tokens and adds failure modes without benefit.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Missing allowed-tools Frontmatter

**Score:** 3/10 (criteria: Non-obvious +1, Cross-cutting +1, External tool quirk +1)
**Notes:** Already caught by automated tripwires review in PR #7750. Since the automated system successfully detects this, it may not need a manual tripwire in learned docs. However, adding it to the tool-restriction-safety.md doc as a checklist item provides ambient awareness before commands are written.

### 2. Batch Thread Resolution Efficiency

**Score:** 2/10 (criteria: Non-obvious +1, Cross-cutting +1)
**Notes:** This is an optimization pattern rather than a safety concern. Documenting as a reference pattern is more appropriate than a tripwire. Individual calls work fine, just slower - no silent failure or correctness issue.
