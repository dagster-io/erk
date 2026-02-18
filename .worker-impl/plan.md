# Plan: Add regeneration instructions to erk-exec reference.md

## Context

The auto-generated `.claude/skills/erk-exec/reference.md` has a minimal 2-line header:
```
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk-dev gen-exec-reference-docs' to regenerate. -->
```

Agents encountering this file have no way to understand the backwards mapping — where the generation code lives, what drives the content, or when regeneration is needed. The user wants this context embedded directly in the file so agents can self-serve.

Since this file is auto-generated, we must update the **generator** that produces the header, not the file itself.

## File to modify

`packages/erk-dev/src/erk_dev/exec_reference/generate.py` — Update the `REFERENCE_HEADER` constant (line 166-169)

### Current

```python
REFERENCE_HEADER = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk-dev gen-exec-reference-docs' to regenerate. -->
"""
```

### New

```python
REFERENCE_HEADER = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!--
  Regenerate: erk-dev gen-exec-reference-docs
  CI check:   erk-dev gen-exec-reference-docs --check (included in make fast-ci)

  Source of truth: Live Click command tree in src/erk/cli/commands/exec/group.py
  Generator code: packages/erk-dev/src/erk_dev/exec_reference/generate.py
  Generator docs: docs/learned/cli/auto-generated-reference-docs.md

  Regenerate after: adding/modifying/removing exec commands or changing help text
-->
"""
```

Then regenerate: `erk-dev gen-exec-reference-docs`

## Verification

Run via devrun agent:
```bash
erk-dev gen-exec-reference-docs --check
```