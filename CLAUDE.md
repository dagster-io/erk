@AGENTS.md

## Claude Code-Specific Configuration

### Session ID Access

**In skills/commands**: Use `${CLAUDE_SESSION_ID}` string substitution (supported since Claude Code 2.1.9):

```bash
# Skills can use this substitution directly
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" ...
```

**In hooks**: Hooks receive session ID via **stdin JSON**, not environment variables. When generating commands for Claude from hooks, interpolate the actual value:

```python
# Hook code interpolating session ID for Claude
f"erk exec marker create --session-id {session_id} ..."
```

### Hook → Claude Communication

- Hook stdout becomes system reminders in Claude's context
- Exit codes block or allow tool calls

### Modified Plan Mode Behavior

Erk modifies plan mode to add a save-or-implement decision:

1. Claude is prompted: "Save the plan to GitHub, or implement now?"
2. **Save**: Claude runs `/erk:plan-save` to create a GitHub issue
3. **Implement now**: Claude proceeds to implementation

### devrun Agent Restrictions

**FORBIDDEN prompts:**

- "fix any errors that arise"
- "make the tests pass"
- Any prompt implying devrun should modify files

**REQUIRED pattern:**

- "Run [command] and report results"
- "Execute [command] and parse output"

devrun is READ-ONLY. It runs commands and reports. Parent agent handles all fixes.

### Skill Loading via Hooks

- Hook reminders fire as safety nets, not commands
- Check if loaded: Look for `<command-message>` earlier in conversation
- Just-in-time context injection: `dignified-python` core rules are automatically injected via PreToolUse hook when editing `.py` files
