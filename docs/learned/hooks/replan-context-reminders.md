---
title: System Reminder Patterns for Replan Workflows
read_when:
  - "writing hooks for replan workflows"
  - "designing system reminders"
  - "implementing workflow checkpoints"
---

# System Reminder Patterns for Replan Workflows

How to structure system reminders for replan workflows to reinforce critical requirements.

## Table of Contents

- [Purpose of System Reminders](#purpose-of-system-reminders)
- [Reminder Pattern: Concise, Specific, Verifiable](#reminder-pattern-concise-specific-verifiable)
- [Examples for Context Preservation](#examples-for-context-preservation)
- [Hook Integration](#hook-integration)

---

## Purpose of System Reminders

### What Are System Reminders?

System reminders are messages injected into the agent's context at key workflow checkpoints:

- **Source:** Hooks (prompt hooks, tool hooks)
- **Delivery:** Appears as system message in conversation
- **Purpose:** Reinforce critical requirements, prevent common mistakes

### When to Use Reminders

Use system reminders when:

1. **Critical checkpoint:** Before a step that commonly causes errors
2. **Context preservation:** Ensuring investigation findings aren't lost
3. **Workflow compliance:** Enforcing required steps
4. **Anti-pattern prevention:** Blocking known failure modes

---

## Reminder Pattern: Concise, Specific, Verifiable

### Three Characteristics

#### 1. Concise

**Maximum:** 2-3 sentences

**Why:** Long reminders get ignored or skipped

**Example:**

✅ **Good:** "Gather investigation context before entering Plan Mode (Step 6a). Include file paths, line numbers, and evidence."

❌ **Too long:** "Before you enter Plan Mode, it's really important that you first gather all of the investigation context that you discovered in the previous steps, including things like file paths, line numbers, commit hashes, PR numbers, and any corrections you found, because if you don't do this, the plan will be sparse and won't have all the details that the implementing agent needs, which will cause them to have to re-discover everything..."

#### 2. Specific

**Be concrete:** Reference exact steps, file types, or actions

**Why:** Generic reminders are easy to misinterpret

**Example:**

✅ **Good:** "Step 6a: Collect completion percentages, file paths (line numbers), corrections, and codebase evidence."

❌ **Too vague:** "Make sure to collect context before planning."

#### 3. Verifiable

**Include checkpoint:** Agent can verify they completed the requirement

**Why:** Clear success criteria

**Example:**

✅ **Good:** "Before Step 6b, verify: ✓ File paths with line numbers, ✓ Function names from codebase, ✓ Corrections documented."

❌ **Not verifiable:** "Make sure you have enough context."

---

## Examples for Context Preservation

### Example 1: Before Investigation

**Checkpoint:** Before Step 4 (codebase investigation)

**Reminder:**

```
Context Preservation Reminder:
Investigation findings from Steps 4-5 MUST be preserved in the final plan.
Collect: file paths (line numbers), function names (actual, not guessed), corrections to original plan(s).
```

**Why effective:**

- Concise (2 sentences)
- Specific (lists what to collect)
- Verifiable (agent knows what "preserved" means)

### Example 2: Before Plan Mode

**Checkpoint:** Before Step 6b (entering Plan Mode)

**Reminder:**

```
Context Gathering Checkpoint:
Complete Step 6a before entering Plan Mode.
Required: ✓ Investigation status per plan, ✓ File paths with line numbers, ✓ Corrections documented, ✓ Evidence (commit hashes, PR numbers).
```

**Why effective:**

- Concise (3 items)
- Specific (Step 6a reference, 4 required items)
- Verifiable (checklist format)

### Example 3: During Plan Mode

**Checkpoint:** After entering Plan Mode

**Reminder:**

```
Plan Content Requirement:
Each implementation step MUST include: specific file path, line number for change, evidence (commit/PR), verification criteria.
Anti-pattern: "Update X" without specifics.
```

**Why effective:**

- Concise (2 sentences)
- Specific (4 required items per step)
- Verifiable (includes anti-pattern example)

---

## Hook Integration

### Prompt Hook Pattern

System reminders are delivered via prompt hooks:

**Hook file:** `.erk/prompt-hooks/before-plan-mode.md`

**Content:**

```markdown
---
hook_type: user_prompt_submit
trigger: before_plan_mode_entry
---

## System Reminder: Context Preservation

Before entering Plan Mode, complete Step 6a: Gather Investigation Context.

**Required:**

- ✓ Investigation status per plan (completion %)
- ✓ Specific discoveries (file paths with line numbers)
- ✓ Corrections found (what original plans got wrong)
- ✓ Codebase evidence (actual function names, class signatures)

**Verification:** Can you answer "which files need changes" and "what specific changes at which lines" from your gathered context?
```

### Hook Timing

| Hook Trigger           | Purpose                            | Example Reminder                                          |
| ---------------------- | ---------------------------------- | --------------------------------------------------------- |
| `before_investigation` | Remind to preserve findings        | "Investigation findings must be preserved in final plan"  |
| `before_plan_mode`     | Remind to gather context (Step 6a) | "Complete Step 6a: Gather context before Plan Mode"       |
| `after_plan_exit`      | Verify plan has specifics          | "Verify plan includes file paths, line numbers, evidence" |

### Multiple Checkpoints

For complex workflows, use multiple reminders at different stages:

```
1. Before Investigation → "Preserve findings"
2. Before Context Gathering → "Step 6a required"
3. Before Plan Mode → "Gathered context checklist"
4. After Plan Exit → "Verify plan specificity"
```

**Why multiple:** Reinforces at each critical decision point.

---

## Anti-Pattern: Overly Long Reminders

### ❌ Bad Example

```
System Reminder: Before you proceed with creating the plan, please make sure that you have thoroughly gathered all of the investigation context from the previous steps, including but not limited to: the investigation status for each of the plans you analyzed (with completion percentages like "4/11 items implemented"), specific discoveries you made while exploring the codebase (such as file paths, and not just generic "the documentation files" but actual full paths like docs/learned/architecture/foo.md, and also line numbers for specific changes in the format foo.md:45 or foo.md:45-67 for ranges), any corrections you found where the original plan got things wrong (like non-existent files, wrong file names, outdated APIs, or already-completed items), and codebase evidence including actual function names from the codebase (not guessed names like parse_session() when the actual name is parse_session_file_path()), class signatures (like class CommandExecutor(ABC, WorkspaceContext)), config values with their locations (like SINGLE_FILE_TOKEN_LIMIT = 20_000 at line 23), and data structures including dataclass fields, type annotations, and default values.
```

**Problems:**

- Way too long (175 words)
- Wall of text format
- Agent will skim or skip
- Information overload

### ✅ Good Example (Same Content)

```
Context Gathering Checkpoint (Step 6a):

Required before Plan Mode:
1. Investigation status (e.g., "4/11 items implemented")
2. File paths with line numbers (docs/learned/foo.md:45)
3. Corrections to original plans (wrong files, outdated APIs)
4. Actual names from codebase (parse_session_file_path(), not guessed)

Verify: Can you answer "which files, which lines, what changes" from your context?
```

**Why better:**

- Concise (52 words vs. 175)
- Numbered list (scannable)
- Concrete examples inline
- Verification question

---

## Summary: Reminder Best Practices

| Practice                  | Guideline                                  | Example                                                             |
| ------------------------- | ------------------------------------------ | ------------------------------------------------------------------- |
| **Length**                | 2-3 sentences max (or 4-5 bullet points)   | "Complete Step 6a. Required: status, files, corrections, evidence." |
| **Specificity**           | Reference exact steps, items, or formats   | "Step 6a" not "context gathering step"                              |
| **Verifiability**         | Include checkpoint or verification         | "Verify: ✓ File paths with line numbers, ✓ Actual function names"   |
| **Formatting**            | Use lists, checkboxes, or short paragraphs | "Required: ✓ Item 1, ✓ Item 2, ✓ Item 3"                            |
| **Examples**              | Include concrete examples inline           | "File paths (docs/learned/foo.md:45)"                               |
| **Frequency**             | One reminder per checkpoint, not repeated  | Before Plan Mode (once), not during every step                      |
| **Reinforcement pattern** | Multiple checkpoints for complex workflows | Before investigation, before context gathering, before Plan Mode    |

---

## Related Documentation

- [Context Preservation in Replan](../planning/context-preservation-in-replan.md) - Why context preservation matters
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) - Prompt structures for commands
- [Prompt Hooks](../../.erk/prompt-hooks/README.md) - Hook system overview
