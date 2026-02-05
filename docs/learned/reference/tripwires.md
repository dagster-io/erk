---
title: Reference Tripwires
read_when:
  - "working on reference code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from reference/*.md frontmatter -->

# Reference Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before confusing `dangerous` with `allow_dangerous`** → Read [Interactive Claude Configuration](interactive-claude-config.md) first. `dangerous` forces skip all prompts (--dangerously-skip-permissions). `allow_dangerous` allows user opt-in (--allow-dangerously-skip-permissions). They have different behaviors.

**CRITICAL: Before defining the same skill or command in multiple TOML sections** → Read [TOML File Handling](toml-handling.md) first. TOML duplicate key constraint: Each skill/command must have a single canonical destination. See bundled-artifacts.md for portability classification.

**CRITICAL: Before forgetting that CLI flags always override config file values** → Read [Interactive Claude Configuration](interactive-claude-config.md) first. The with_overrides() pattern ensures CLI flags take precedence. Never read config directly when overrides are present.

**CRITICAL: Before parsing objective summary output without structured format** → Read [Objective Summary Format](objective-summary-format.md) first. Use the documented JSON format with OBJECTIVE, STATUS, ROADMAP, PENDING_STEPS, and RECOMMENDED sections. Status mapping uses pending/done/in_progress/blocked/skipped.

**CRITICAL: Before passing non-None override values when wanting to preserve config** → Read [Interactive Claude Configuration](interactive-claude-config.md) first. Pass None to preserve config value. Pass value to override. with_overrides(model_override=False) disables model, should be model_override=None.
