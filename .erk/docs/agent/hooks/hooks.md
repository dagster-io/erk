---
title: Claude Code Hooks Guide
read_when:
  - "creating hooks"
  - "modifying hooks"
  - "understanding hook lifecycle"
---

# Claude Code Hooks Guide

Complete guide to Claude Code hooks: general capabilities and project-specific usage.

## Table of Contents

**Part 1: General Guide (Claude Code Hooks)**

- [What Are Hooks?](#what-are-hooks)
- [Hook Types](#hook-types)
- [Lifecycle Events](#lifecycle-events)
- [Matchers](#matchers)
- [Configuration Structure](#configuration-structure)
- [Output and Decision Control](#output-and-decision-control)
- [Exit Code Decision Patterns](#exit-code-decision-patterns)
- [Security Considerations](#security-considerations)
- [Best Practices](#best-practices)

**Part 2: Project-Specific Supplement**

- See [erk.md](erk.md) for erk-specific usage

## Part 1: General Guide (Claude Code Hooks)

### What Are Hooks?

Hooks are automated triggers that execute commands or evaluate prompts at specific points in Claude's execution lifecycle. They enable:

- **Context injection**: Provide reminders or warnings before actions
- **Validation**: Check conditions before tool execution
- **Automation**: Run scripts at session start/end
- **Decision control**: Programmatically allow/deny operations

**Official Documentation**: [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)

### Hook Types

Claude Code supports two hook types:

#### Command-Based Hooks

Execute shell commands and capture their output.

```json
{
  "type": "command",
  "command": "python -m myproject.check_style",
  "timeout": 30
}
```

**Use cases**:

- Run validation scripts
- Output reminder messages
- Invoke external tools
- Check system state

#### Prompt-Based Hooks

Use Claude Haiku to evaluate a prompt and return structured decisions.

```json
{
  "type": "prompt",
  "prompt": "Should I allow this operation? Return JSON with decision.",
  "timeout": 60
}
```

**Use cases**:

- Complex validation logic
- Natural language condition checking
- Dynamic decision-making based on context
- LLM-powered policy enforcement

### Lifecycle Events

Claude Code provides 10 lifecycle events for hook execution:

| Event                 | When It Fires                    | Common Use Cases                           |
| --------------------- | -------------------------------- | ------------------------------------------ |
| **UserPromptSubmit**  | Before processing user input     | Context reminders, input validation        |
| **PreToolUse**        | Before executing any tool        | Parameter validation, tool-specific checks |
| **PermissionRequest** | Before showing permission dialog | Auto-approve/deny, audit logging           |
| **PostToolUse**       | After tool execution completes   | Result validation, side effects            |
| **Notification**      | When system notifications appear | Custom notification handling               |
| **Stop**              | When main agent execution stops  | Cleanup, status updates                    |
| **SubagentStop**      | When subagent (Task tool) stops  | Subagent-specific cleanup                  |
| **PreCompact**        | Before context compaction        | Save state, checkpoint progress            |
| **SessionStart**      | At session initialization        | Environment setup, credential loading      |
| **SessionEnd**        | When session terminates          | Cleanup, final reporting                   |

**Most commonly used**: `UserPromptSubmit` (reminders), `PreToolUse` (validation), `SessionStart` (setup)

### Matchers

Matchers determine when a hook fires. Three types:

#### 1. Wildcard Matchers

Match all events or specific file patterns:

```json
{
  "matcher": "*" // Fires on every event
}
```

```json
{
  "matcher": "*.py" // Fires when context includes Python files
}
```

```json
{
  "matcher": "tests/**/*.py" // Fires for test files only
}
```

#### 2. Tool Matchers

Match specific tool executions:

```json
{
  "matcher": "Bash" // Fires before Bash tool use
}
```

**Available tool matchers**:

- `Task` - Subagent launches
- `Bash` - Shell command execution
- `Glob` - File pattern searches
- `Grep` - Content searches
- `Read` - File reads
- `Edit` - File edits
- `Write` - File writes
- `WebFetch` - Web requests
- `WebSearch` - Web searches
- `mcp__<server>__<tool>` - MCP server tools

#### 3. Glob Patterns

Standard glob syntax for file matching:

- `*.md` - All markdown files
- `src/**/*.ts` - All TypeScript in src/
- `{test,spec}/**/*.py` - Test files in test/ or spec/

### Configuration Structure

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*.py",
        "hooks": [
          {
            "type": "command",
            "command": "python -m myproject.python_reminder",
            "timeout": 30
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Validate this bash command is safe",
            "timeout": 60
          }
        ]
      }
    ]
  }
}
```

**Structure notes**:

- Each lifecycle event contains an array of matcher configurations
- Each matcher can have multiple hooks
- Hooks within a matcher execute in parallel (order not guaranteed)

### Output and Decision Control

#### Command-Based Hook Output

**Exit codes**:

- `0` - Success, output shown as system reminder
- `2` - Blocking error, output shown as error, operation halts
- Other - Non-blocking error, logged but doesn't halt

**Example (reminder)**:

```python
#!/usr/bin/env python3
import click

@click.command()
def check() -> None:
    click.echo("⚠️ Remember to run tests before committing")
    # Exit 0 (default) - shows as reminder

if __name__ == "__main__":
    check()
```

**Example (blocking error)**:

```python
#!/usr/bin/env python3
import sys
import click

@click.command()
def validate() -> None:
    if not is_valid():
        click.echo("❌ Validation failed: operation blocked")
        sys.exit(2)  # Blocks operation

if __name__ == "__main__":
    validate()
```

#### Blocking to Redirect Pattern

Use exit code 2 strategically to redirect Claude's behavior. Instead of just stopping an action, you can instruct Claude to take an alternative approach:

**Example (redirect to ask user):**

```python
#!/usr/bin/env python3
import sys
import click

@click.command()
def validate_action() -> None:
    if needs_user_confirmation():
        click.echo("❌ Action requires user confirmation")
        click.echo("")
        click.echo("Use the AskUserQuestion tool to ask the user:")
        click.echo('  - Option A: "Save to GitHub"')
        click.echo('  - Option B: "Implement immediately"')
        sys.exit(2)  # Block - Claude will see instructions

    # Allow action
    click.echo("✅ Action permitted")

if __name__ == "__main__":
    validate_action()
```

The output message becomes Claude's instruction for what to do instead.

#### Prompt-Based Hook Output

Return JSON with decision fields:

```json
{
  "decision": "allow", // "allow", "deny", "block", or omit
  "message": "Operation approved",
  "updatedInput": {
    // Optional: modify tool parameters
    "newParameter": "newValue"
  }
}
```

**Decisions**:

- `allow` - Permit operation, show message
- `deny` - Refuse operation silently
- `block` - Refuse operation with error message
- No decision field - Show message only (no control)

**Example (PreToolUse parameter modification)**:

```json
{
  "decision": "allow",
  "message": "Added safety flag to command",
  "updatedInput": {
    "command": "rm --interactive file.txt"
  }
}
```

### Exit Code Decision Patterns

Hook exit codes control whether the tool proceeds, but the semantics are about **flow control**, not success/failure:

| Exit Code | Meaning               | When to Use                                                   |
| --------- | --------------------- | ------------------------------------------------------------- |
| 0         | Allow tool to proceed | Tool should run its normal flow                               |
| 2         | Block tool execution  | You've handled the situation; tool's default flow is unwanted |

**Key Insight: Blocking as Success**

Exit 2 (block) is often the RIGHT choice for successful terminal states:

```python
# Example: Plan already saved to GitHub
if saved_marker.exists():
    saved_marker.unlink()
    click.echo("✅ Plan saved to GitHub. Session complete.")
    sys.exit(2)  # BLOCK - prevents ExitPlanMode's plan approval dialog
```

Why block here? Because:

1. The user's goal (save plan) is already accomplished
2. The tool's default behavior (show plan approval dialog) serves no purpose
3. Blocking prevents unwanted UI while the message communicates completion

**Decision Framework:**

Ask: "What happens if I allow the tool to proceed?"

- If the tool's normal flow is helpful → Exit 0 (allow)
- If the tool's normal flow is unnecessary/harmful → Exit 2 (block)

The exit code is about **what should happen next**, not whether your hook succeeded.

### Security Considerations

**⚠️ Hooks execute arbitrary commands with your credentials**

#### Security Best Practices

1. **Audit hook sources**: Only install hooks from trusted sources
2. **Review hook code**: Inspect commands before installation
3. **Limit hook scope**: Use specific matchers, not wildcards
4. **Sandbox when possible**: Run hooks in restricted environments
5. **Validate inputs**: Sanitize any dynamic data in hook commands
6. **Monitor execution**: Use `claude --debug` to track hook activity

#### Common Security Risks

- **Command injection**: Hook commands constructed from untrusted input
- **Credential exposure**: Hooks accessing sensitive environment variables
- **Filesystem access**: Hooks modifying files outside project scope
- **Network calls**: Hooks sending data to external services
- **Long-running operations**: Hooks with no timeout causing hangs

**Example (unsafe)**:

```json
{
  "command": "bash -c \"echo User input: $USER_DATA\"" // ❌ Command injection risk
}
```

**Example (safe)**:

```json
{
  "command": "python -m myproject.validate --strict", // ✅ No dynamic input
  "timeout": 30
}
```

### Best Practices

#### Performance

- **Keep hooks fast**: Hooks run on every matching event
- **Set timeouts**: Default 60s, reduce for simple checks
- **Use specific matchers**: Avoid `*` matcher when possible
- **Cache expensive checks**: Don't recompute on every invocation

#### Reliability

- **Test hooks independently**: Run commands manually before hooking
- **Handle errors gracefully**: Use appropriate exit codes
- **Provide clear output**: Help users understand what happened
- **Version control hooks**: Track hook changes alongside code

#### Maintainability

- **Document hook purpose**: Explain WHY the hook exists
- **Keep logic simple**: Complex validation belongs in scripts, not hooks
- **Use consistent naming**: Follow project conventions
- **Group related hooks**: Organize by kit or feature

#### Development Workflow

1. **Write script**: Create standalone command for hook logic
2. **Test manually**: Verify script works independently
3. **Add to settings**: Configure hook in `.claude/settings.json`
4. **Test in context**: Trigger hook through normal workflow
5. **Debug with `--debug`**: Use `claude --debug` to see hook execution
6. **Iterate**: Refine based on actual usage patterns

#### State Coordination with Skip Markers

When a hook needs to allow future operations after user confirmation, use a skip marker file:

**Pattern:**

1. Hook checks for marker file → if exists, delete and allow
2. Hook blocks if no marker → Claude asks user
3. On user confirmation, Claude creates marker file
4. Next invocation succeeds

**Implementation:**

```python
def _get_skip_marker_path(session_id: str, repo_root: Path) -> Path:
    return repo_root / ".erk" / "scratch" / "sessions" / session_id / "skip-plan-save"

def check_and_consume_marker(session_id: str, repo_root: Path) -> bool:
    marker = _get_skip_marker_path(session_id, repo_root)
    if marker.exists():
        marker.unlink()  # Consume marker
        return True
    return False
```

**Use cases:**

- "Confirm once, proceed" workflows
- User-acknowledged bypasses
- One-time permission grants

#### Example: Well-Designed Hook

```python
#!/usr/bin/env python3
"""
Pre-commit validation hook.

Checks that:
- No debug statements in code
- All tests pass
- Code is formatted

Exit codes:
- 0: All checks pass (reminder shown)
- 2: Checks fail (operation blocked)
"""
import sys
import subprocess
import click

@click.command()
def pre_commit_check() -> None:
    """Run pre-commit validation checks."""

    # Fast check first
    if has_debug_statements():
        click.echo("❌ Debug statements found - remove before committing")
        sys.exit(2)

    # Expensive checks only if needed
    if not run_tests():
        click.echo("❌ Tests failing - fix before committing")
        sys.exit(2)

    click.echo("✅ All pre-commit checks passed")
    # Exit 0 (default)

def has_debug_statements() -> bool:
    """Check for debug statements (fast)."""
    result = subprocess.run(
        ["grep", "-r", "debugger", "src/"],
        capture_output=True,
        check=False  # Don't raise on non-zero exit
    )
    return result.returncode == 0

def run_tests() -> bool:
    """Run test suite (expensive)."""
    result = subprocess.run(
        ["pytest", "tests/"],
        capture_output=True,
        check=False
    )
    return result.returncode == 0

if __name__ == "__main__":
    pre_commit_check()
```

---

## Part 2: Project-Specific Supplement

For erk-specific hook usage, see **[erk.md](erk.md)**

This includes:

- How erk-kits manages hooks in this project
- Current hooks (devrun, dignified-python, fake-driven-testing)
- Common tasks (viewing, modifying, creating, testing hooks)
- Troubleshooting guide

---

## Additional Resources

- **Project-Specific Supplement**: [erk.md](erk.md)
- **Official Claude Code Hooks**: https://code.claude.com/docs/en/hooks
- **Official Hooks Guide**: https://code.claude.com/docs/en/hooks-guide.md
- **erk-kits Hook Development**: `../../packages/erk-kits/docs/HOOKS.md`
- **Kit System Overview**: `../../.erk/kits/README.md`
- **Project Glossary**: `glossary.md`
