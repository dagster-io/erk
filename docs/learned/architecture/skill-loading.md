---
title: Skill Loading Best Practices
read_when:
  - "starting implementation of a plan"
  - "writing command execution workflows"
  - "creating slash commands that delegate to implementation"
tripwires:
  - action: "starting implementation without loading dignified-python and fake-driven-testing"
    warning: "Load foundational skills FIRST. Skipping leads to inconsistent code quality and test patterns. These skills persist for the entire session."
---

# Skill Loading Best Practices

Patterns for proactive skill loading to ensure coding standards apply from the start of implementation.

## The Problem

AI agents have access to vast training data, but project-specific conventions (like erk's LBYL-not-EAFP, no-default-parameters rules) are **not** in the training data. Without explicit loading of these standards, agents will write code that contradicts the project's patterns.

**Historical example**: Issue #6514 implementation initially proceeded without loading `dignified-python` or `fake-driven-testing` skills. This led to code that had to be revised to match erk standards during review.

## The Solution: Pre-Load Foundational Skills

Before writing any implementation code, load the project's foundational skills:

```python
# In /erk:plan-implement or similar workflows
Skill(skill: "dignified-python")
Skill(skill: "fake-driven-testing")
```

**When to load**: Immediately after reading the plan and before starting implementation phases.

## Foundational Skills

### dignified-python

**Purpose**: Python coding standards for erk

**Key patterns**:

- LBYL (Look Before You Leap), never EAFP (Easier to Ask Forgiveness)
- No default parameter values
- Frozen dataclasses only
- Pathlib always, never `os.path`
- Absolute imports only
- Lightweight `__init__` (no I/O)

**Load when**: Any task involving Python code in `src/` or `tests/`

### fake-driven-testing

**Purpose**: 5-layer test architecture with comprehensive fakes

**Key patterns**:

- Test placement (integration vs unit)
- Fake gateway design
- Context injection for tests
- Testing NoReturn methods

**Load when**: Any task involving test code or new gateway methods

## Skill Persistence

**Skills persist for the entire session.** Once loaded, they remain in context until the session ends.

### Checking if Already Loaded

Look for this message earlier in the conversation:

```
<command-message>The "dignified-python" skill is loading…</command-message>
```

If present, the skill is already loaded. **Do not reload.**

### Why Persistence Matters

- **Cost**: Skills contain substantial context. Reloading wastes tokens.
- **Redundancy**: The skill content is already in the conversation history.
- **Hook reminders**: Skills may fire hook reminders as safety nets, but these are not commands to reload.

## Just-In-Time Context Injection

Some patterns use hooks to inject skill content at the exact moment it's needed:

### PreToolUse Hook Example

Erk has a PreToolUse hook that injects `dignified-python` core rules when editing `.py` files:

```python
# .claude/hooks/pre-tool-use.py
if tool_name == "Edit" and file_path.endswith(".py"):
    # Inject dignified-python core rules as a pointed reminder
    return reminder_text
```

**Why both pre-loading AND hooks?**

- **Pre-loading**: Establishes foundational context for all code
- **Hook injection**: Provides pointed reminder at the exact moment Python code is being written

They complement each other: pre-loading for ambient awareness, hooks for action-specific reinforcement.

## Implementation Workflow Pattern

Recommended skill loading pattern for plan implementation:

```
1. Read plan
2. Load related documentation (if plan specifies)
3. Load foundational skills:
   - dignified-python
   - fake-driven-testing
4. Create TodoWrite entries from phases
5. Execute phases (skills are now loaded)
```

### Example: /erk:plan-implement Workflow

```markdown
### Step 4: Load Related Documentation

If plan contains "Related Documentation" section, load listed skills via Skill tool and read listed docs.

### Step 5: Create TodoWrite Entries

Create todo entries for each phase from impl-init output.

### Step 6: Execute Each Phase Sequentially

For each phase:

1. **Mark phase as in_progress** (in TodoWrite)
2. **Read task requirements** carefully
3. **Implement code AND tests together**:
   - Load `dignified-python` skill for coding standards
   - Load `fake-driven-testing` skill for test patterns
   - Follow project AGENTS.md standards
```

**Key insight**: Skills are loaded in Step 6 (before implementation), not in Step 1 (before reading plan).

## Anti-Patterns

### ❌ Loading Skills Multiple Times

```python
# WRONG - Wastes tokens, skill already in context
Skill(skill: "dignified-python")  # First load
# ... some work ...
Skill(skill: "dignified-python")  # Redundant reload
```

### ❌ Skipping Skill Loading

```python
# WRONG - Starts implementation without standards
def test_my_feature():
    # Writes test in generic Python style, not erk patterns
    with pytest.raises(Exception):  # EAFP anti-pattern!
        my_function()
```

### ❌ Loading Skills Too Late

```python
# WRONG - Writes code first, loads skills after
def my_implementation():
    result = some_function()  # Already written without standards

Skill(skill: "dignified-python")  # Too late!
```

## Correct Patterns

### ✅ Load Once, Early

```python
# Step 1: Load foundational skills FIRST
Skill(skill: "dignified-python")
Skill(skill: "fake-driven-testing")

# Step 2: Implement all phases
for phase in phases:
    # Skills are already loaded, apply standards consistently
    write_code()
    write_tests()
```

### ✅ Check Before Loading

```python
# Check conversation history for skill loading message
if not seen_message("<command-message>The \"dignified-python\" skill is loading…"):
    Skill(skill: "dignified-python")
```

### ✅ Rely on Hook Reminders

```python
# Hook fires when editing .py files
# No need to reload - just a pointed reminder
# Continue with implementation using already-loaded skill knowledge
```

## When to Load Project-Specific Skills

Beyond foundational skills, load project-specific skills when working in related areas:

| Working Area            | Load Skill        | Why                                |
| ----------------------- | ----------------- | ---------------------------------- |
| Git worktree operations | `gt-graphite`     | Worktree stack mental model        |
| Slash command creation  | `command-creator` | Command authoring patterns         |
| GitHub CLI operations   | `gh`              | gh mental model and workflows      |
| Documentation writing   | `learned-docs`    | Documentation methodology          |
| PR operations           | `pr-operations`   | Thread resolution, comment replies |

## Cost-Benefit Analysis

**Benefits of pre-loading**:

- Consistent code quality from the start
- Fewer review cycles
- Reduced refactoring work
- Standards applied to all phases

**Cost**:

- Initial token cost (one-time per session)
- Additional context in conversation history

**Verdict**: Pre-loading is worth the cost. The alternative (rewriting code to match standards after the fact) is more expensive in both tokens and time.

## Historical Context

This pattern emerged from observing implementation sessions that:

1. Started without loading skills
2. Wrote code in generic Python style
3. Required review and refactoring to match erk standards
4. Would have been faster with upfront skill loading

The learn pipeline (#6514) revealed this pattern, leading to documentation that encourages early skill loading in all implementation workflows.

## Related Documentation

- [AGENTS.md](../../AGENTS.md) - Project coding standards (references skills)
- [Agent Delegation](../planning/agent-delegation.md) - Multi-agent coordination patterns
- [Learn Pipeline](../planning/learn-pipeline.md) - How this pattern was discovered
- Source: `.claude/hooks/pre-tool-use.py` - Just-in-time context injection example
