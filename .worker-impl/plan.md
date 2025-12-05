# Documentation Extraction Plan

## Objective

Add documentation for shell integration handler architecture patterns discovered during the CliRunner-to-subprocess migration.

## Source Information

- **Session ID**: ecee63a5-1955-496f-b948-09e0e27ba6c3
- **Context**: Implementing fix for pr land output buffering and extraction plan URL handling

---

## Documentation Items

### Item 1: Update Shell Integration Patterns Doc

**Type**: Category A (Learning Gap)
**Location**: `docs/agent/architecture/shell-integration-patterns.md`
**Action**: Update existing doc with new section
**Priority**: High (directly caused debugging time in this session)

**Content to add**:

```markdown
## Handler Execution Model

The shell integration handler in `handler.py` can execute commands in two ways:

### CliRunner (In-Process)
- **Pros**: Fast, shares context with tests, no subprocess overhead
- **Cons**: Buffers ALL output (stdout AND stderr) until command completes
- **Use when**: Testing, or when real-time output isn't needed

### Subprocess (Out-of-Process)
- **Pros**: Allows real-time stderr streaming to terminal
- **Cons**: Spawns new process, can't share test context
- **Use when**: User-facing commands need live feedback

### Why Subprocess for Shell Integration

The handler uses subprocess because shell-integrated commands (like `pr land`) output progress messages that users need to see in real-time:

\`\`\`python
# subprocess.run with stderr=None lets stderr stream live
result = subprocess.run(
    cmd,
    stdout=subprocess.PIPE,  # Capture for script path
    stderr=None,              # Pass through to terminal
    text=True,
    check=False,
)
\`\`\`

With CliRunner, messages like "Getting current branch...", "Deleting worktree..." would all appear at once after the command completes, making it seem frozen.
```

---

### Item 2: Add Claude CLI Output Parsing Pattern

**Type**: Category B (Teaching Gap - documents what was built)
**Location**: `docs/agent/architecture/claude-cli-parsing.md` (new file)
**Action**: Create new doc
**Priority**: Medium (useful for future Claude CLI integrations)

**Content**:

```markdown
---
title: Claude CLI Output Parsing
read_when:
  - "parsing Claude CLI output"
  - "extracting JSON from Claude --print mode"
  - "integrating with Claude CLI programmatically"
---

# Claude CLI Output Parsing

## The Problem

Claude CLI with `--print` mode outputs conversation/thinking text before the final JSON result:

\`\`\`
Analyzing the session logs...
Found 3 relevant conversations.
Creating extraction plan...
{"issue_url": "https://github.com/user/repo/issues/123"}
\`\`\`

Naive `json.loads(stdout)` fails because stdout isn't pure JSON.

## Solution: Search from End

Search backwards through output lines to find the JSON result:

\`\`\`python
def extract_json_field(output: str, field: str) -> str | None:
    """Extract a field from JSON in mixed Claude CLI output."""
    if not output:
        return None
    
    for line in reversed(output.strip().split("\n")):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict):
                value = data.get(field)
                if isinstance(value, str):
                    return value
        except json.JSONDecodeError:
            continue
    return None
\`\`\`

## Why Search from End?

- Claude outputs thinking/progress text first, JSON result last
- The JSON is typically on the final non-empty line
- Searching backwards finds it immediately without parsing all the preamble

## Reference Implementation

See `_extract_issue_url_from_output()` in `src/erk/core/shell.py`
```

---

### Item 3: Document Legacy Alias Routing Pattern

**Type**: Category A (Learning Gap - caused test failures)
**Location**: `docs/agent/architecture/shell-integration-patterns.md`
**Action**: Add section to existing doc
**Priority**: High (caused integration test failures)

**Content to add**:

```markdown
## Command Routing with Subprocess

When the handler uses subprocess, commands must be invoked by their actual CLI paths, not legacy aliases.

### The Problem

Legacy aliases like `create`, `goto`, `consolidate` are registered in `SHELL_INTEGRATION_COMMANDS` for backward compatibility, but they don't exist as top-level CLI commands. The actual commands are:

| Legacy Alias | Actual CLI Path |
|-------------|-----------------|
| `create` | `wt create` |
| `goto` | `wt goto` |
| `consolidate` | `stack consolidate` |

### Solution: Map Aliases to CLI Paths

Use a dict that maps handler command names to CLI command parts:

\`\`\`python
SHELL_INTEGRATION_COMMANDS: Final[dict[str, list[str]]] = {
    # Top-level commands (key matches CLI path)
    "checkout": ["checkout"],
    "up": ["up"],
    
    # Legacy aliases (map to actual CLI paths)
    "create": ["wt", "create"],
    "goto": ["wt", "goto"],
    "consolidate": ["stack", "consolidate"],
    
    # Compound commands
    "wt create": ["wt", "create"],
    "pr land": ["pr", "land"],
}
\`\`\`

Then build the subprocess command from the mapped path:

\`\`\`python
cli_cmd_parts = SHELL_INTEGRATION_COMMANDS.get(command_name)
cmd = ["erk", *cli_cmd_parts, *args, "--script"]
\`\`\`

### Why This Matters

With the old CliRunner approach, the handler directly invoked Command objects from the dict, bypassing CLI routing. With subprocess, we go through the actual CLI, so we need proper command paths.
```

---

## Implementation Notes

- Items 1 and 3 update the same file (`shell-integration-patterns.md`)
- Item 2 creates a new file and should be added to `docs/agent/architecture/index.md`
- All content is ready to copy-paste with minor formatting adjustments