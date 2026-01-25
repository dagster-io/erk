# Encouraging Doc-First Behavior in Explore Agents

## Problem

The Explore subagent doesn't automatically check `docs/learned/` before exploring raw codebase files. AGENTS.md has "Documentation-First Exploration" instructions, but these apply to the main agent—not to subagents spawned via Task.

## Chosen Approach: Hook-Based Reminder (Option 3)

Use erk's existing capability/reminder system to inject a reminder on every prompt that instructs the main agent to include doc-first instructions when spawning Explore agents.

### How It Works

Erk has a `UserPromptSubmit` hook that fires on every user prompt. It already injects reminders for:
- `devrun`: "Use Task(subagent_type='devrun') for pytest/ty/ruff..."
- `dignified-python`: Coding standards reminders
- `tripwires`: "Check tripwires.md before taking actions"

We add a new **`explore-docs`** reminder capability that outputs:

```
explore-docs: When spawning Explore agents via Task tool, ALWAYS include in the prompt:
"FIRST check docs/learned/index.md for existing documentation on this topic.
Read relevant docs before exploring raw files."
```

This reminds the main agent what to include in Explore prompts.

### Why This Approach

1. **Follows existing pattern** - Uses proven capability/reminder infrastructure
2. **Opt-in via `erk init`** - Project owners control whether it's enabled
3. **Persistent reminder** - Fires every prompt, survives long contexts
4. **Non-invasive** - Doesn't require modifying Claude Code internals

## Implementation

### Files to Modify

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/user_prompt_hook.py` | Add `build_explore_docs_reminder()` function and check |
| `src/erk/core/capabilities/reminders.py` | Add `ExploreDocsReminderCapability` class |
| `src/erk/core/capabilities/registry.py` | Import and register the new capability |

### 1. Add reminder function to `user_prompt_hook.py`

```python
def build_explore_docs_reminder() -> str:
    """Return explore-docs reminder for doc-first exploration."""
    return """explore-docs: When spawning Explore agents via Task tool, ALWAYS include:
"FIRST check docs/learned/index.md for existing documentation on this topic.
Read relevant docs before exploring raw files. Only explore raw codebase for gaps."
"""
```

Add to the hook's reminder checks:

```python
if is_reminder_installed(hook_ctx.repo_root, "explore-docs"):
    context_parts.append(build_explore_docs_reminder())
```

### 2. Add capability class to `reminders.py`

```python
class ExploreDocsReminderCapability(ReminderCapability):
    """Reminder to check docs/learned/ first when spawning Explore agents."""

    @property
    def reminder_name(self) -> str:
        return "explore-docs"

    @property
    def description(self) -> str:
        return "Remind agent to include doc-first instructions in Explore prompts"
```

### 3. Register in capability registry

In `src/erk/core/capabilities/registry.py`:
- Import `ExploreDocsReminderCapability` from `reminders.py`
- Add `ExploreDocsReminderCapability()` to the `_all_capabilities()` tuple

### 4. Add tests

Add unit tests to `tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py`:
- Test `build_explore_docs_reminder()` returns expected string
- Test hook includes explore-docs reminder when capability is installed
- Test hook excludes explore-docs reminder when capability is not installed

## Verification

1. Run tests: `devrun` agent with `uv run pytest tests/unit/cli/commands/exec/scripts/test_user_prompt_hook.py -v`
2. Install the capability: `erk init capability install explore-docs-reminder`
3. Start a new Claude session
4. Verify the reminder appears in system context
5. Spawn an Explore agent and check if it reads docs first

## Future Enhancement

If this proves insufficient, we could also:
- Create a custom `doc-explore` agent with behavior baked in
- Add a PreToolUse hook that blocks Explore spawns without doc-first instructions (aggressive)