# Plan: Document OSC 52 Clipboard Pattern

## Summary

Add documentation for the OSC 52 clipboard copy pattern to `docs/learned/cli/output-styling.md`, parallel to the existing OSC 8 hyperlink section.

## Context

Plan #5170 implemented OSC 52 clipboard support for activation commands. The code works but the pattern isn't documented, making it harder for future agents to discover and use correctly.

**Source issue:** #5170 (Clickable/Copyable Activation Commands)
**Related PR:** #5171

## Files to Modify

1. `docs/learned/cli/output-styling.md` - Add new "Clipboard Copy (OSC 52)" section

## Implementation

### Phase 1: Update output-styling.md

Add new section after "Clickable Links (OSC 8)" (~line 95):

```markdown
## Clipboard Copy (OSC 52)

The CLI supports automatic clipboard copy using OSC 52 escape sequences. When emitted, supported terminals copy the text to the system clipboard silently.

### When to Use

Copy text to clipboard when:
- Providing a command the user should paste and run
- The command is long/complex and manual copying would be error-prone
- There's a clear "primary" command among multiple options

### Implementation Pattern

```python
from erk.core.display_utils import copy_to_clipboard_osc52
from erk_shared.output.output import user_output

import click

# Display command with hint
cmd = f"source {script_path}"
clipboard_hint = click.style("(copied to clipboard)", dim=True)
user_output(f"  {cmd}  {clipboard_hint}")

# Emit invisible OSC 52 sequence
user_output(copy_to_clipboard_osc52(cmd), nl=False)
```

### Terminal Compatibility

- Supported: iTerm2, Kitty, Alacritty, WezTerm, Terminal.app (macOS 13+)
- Unsupported terminals silently ignore the sequence (no errors)
- No action required for graceful degradation

### Reference Implementation

- `src/erk/cli/activation.py` - `print_activation_instructions()` function
- `src/erk/core/display_utils.py` - `copy_to_clipboard_osc52()` function
```

## Verification

1. Run `make format` to ensure markdown is formatted correctly
2. Run `make fast-ci` to verify no issues introduced
3. Visual inspection: confirm section fits naturally after OSC 8 section