---
title: Tui Tripwires
read_when:
  - "working on tui code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from tui/*.md frontmatter -->

# Tui Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before using subprocess.Popen in TUI code without stdin=subprocess.DEVNULL** → Read [Command Execution Strategies](command-execution.md) first. Child processes inherit stdin from parent; in TUI context this creates deadlocks when child prompts for user input. Always set `stdin=subprocess.DEVNULL` for TUI subprocess calls.
