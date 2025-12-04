# Documentation Extraction Plan: Shell Integration Handler Architecture

## Source Session
- Session: e0281245-4d0e-46e5-917e-189c594e7e8b
- Context: Debugging `erk --debug pr land` failure

## Extraction Items

### 1. Shell Integration Handler - Global Flag Handling (Priority: HIGH)

**Category:** B (Teaching Gap) - Documenting what was BUILT

**Location:** `docs/agent/cli/script-mode.md` (extend existing) or new `docs/agent/architecture/shell-integration-handler.md`

**Content to Document:**

The shell integration handler (`handler.py`) has a specific requirement for command matching:

1. **Global flags must be stripped before command lookup** - When the shell wrapper passes args like `('--debug', 'pr', 'land')`, the handler must strip `--debug` before matching against `SHELL_INTEGRATION_COMMANDS`

2. **Failure mode**: Without stripping, compound command lookup fails:
   - `"--debug pr"` doesn't match anything
   - Falls back to single command `"--debug"` which also doesn't match
   - Returns passthrough
   - Passthrough runs without `--script` flag
   - Command shows misleading "requires shell integration" error

3. **Known global flags to strip**: `--debug`, `--dry-run`, `--verbose`, `-v`

**Draft Content:**
```markdown
### Global Flag Handling in Shell Integration

The shell integration handler must strip global CLI flags before matching commands:

```python
GLOBAL_FLAGS: Final[set[str]] = {"--debug", "--dry-run", "--verbose", "-v"}

# Strip from beginning of args before command matching
args_list = list(args)
while args_list and args_list[0] in GLOBAL_FLAGS:
    args_list.pop(0)
```

**Why this matters:** Without stripping, `erk --debug pr land` becomes args `('--debug', 'pr', 'land')`. The handler tries to match `"--debug pr"` as a compound command, which fails, leading to passthrough without the `--script` flag.
```

### 2. Shell Integration Debugging Guide (Priority: MEDIUM)

**Category:** A (Learning Gap) - Would have made session faster

**Location:** `docs/agent/cli/script-mode.md` (new section) or `docs/agent/troubleshooting/`

**Content to Document:**

How to debug shell integration issues:

```bash
# Test what the shell handler receives and returns
ERK_SHELL=zsh command erk __shell pr land

# With debug output
ERK_DEBUG=1 ERK_SHELL=zsh command erk __shell pr land
```

- `__ERK_PASSTHROUGH__` output means command matching failed
- Check `handler.py:_invoke_hidden_command()` for why passthrough occurred
- Exit code 1 + passthrough = handler invoked command but it failed

## Implementation Steps

1. Decide location: extend `script-mode.md` or create `shell-integration-handler.md`
2. Add the global flag handling documentation
3. Add debugging section with examples
4. Update `docs/agent/index.md` with "read when" condition