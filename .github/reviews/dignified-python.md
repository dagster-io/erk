---
name: Dignified Python Review
paths:
  - "**/*.py"
marker: "<!-- dignified-python-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Load the Dignified Python Standards

Read these skill files from the repository:

1. .claude/skills/dignified-python/SKILL.md (routing and version detection)
2. .claude/skills/dignified-python/dignified-python-core.md (LBYL, exceptions, paths, imports, DI, performance)
3. .claude/skills/dignified-python/cli-patterns.md (Click best practices)
4. .claude/skills/dignified-python/subprocess.md (subprocess handling)

## Step 2: Identify Changed Lines

For each Python file, determine which lines were actually modified (not just context):

- Lines starting with `+` in the diff are additions/modifications
- Lines starting with ` ` (space) are unchanged context

For the `__all__` / re-export rule specifically:

- If `__all__` appears on a `+` line → Flag as violation (actively being modified)
- If `__all__` only appears in context lines → Skip (pre-existing, not being modified)

This allows file moves/refactors to pass while catching active modifications.

## Step 3: Analyze Code

Check each Python file against dignified-python rules:

- LBYL over EAFP (no try/except for control flow)
- Exception handling (no silent swallowing, log at boundaries)
- Path operations (exists before resolve)
- Import organization (module-level, absolute, no re-exports)
- No default parameter values
- Dependency injection with ABC
- Frozen dataclasses
- Keyword-only arguments for 5+ parameter functions
  **Detection for keyword-only arguments:** When checking multi-line function signatures, look for a standalone `*` or `*,` on its own line. This is the keyword-only separator. There are two valid patterns:

  **Pattern A: All parameters keyword-only** (separator is first):

  ```python
  def validate_flags(
      *,                    # ← First thing - ALL params are keyword-only
      submit: bool,
      no_interactive: bool,
  ) -> None:
  ```

  **Pattern B: Mixed positional and keyword-only** (separator between):

  ```python
  def func(
      ctx: Context,         # ← Positional
      *,                    # ← Separator
      param1: str,          # ← Keyword-only
      param2: int,
  ) -> None:
  ```

  Only flag as violation if there are 5+ parameters AND no `*` or `*,` line exists in the signature.

**IMPORTANT: Only output entries for VIOLATIONS.** Do NOT:

- Post inline comments for compliant code
- Include file:line references in the summary for compliant code
- Create "informational" or "review confirmed correct" entries

If a function has 5+ parameters AND has the `*` marker, it is compliant - skip it entirely without mention.

**CRITICAL: Check for exceptions before flagging violations.**

Many rules have explicit exceptions documented in the skill files you loaded in Step 1. Before flagging a violation, verify that NO exception applies. Common exceptions include:

- **5+ parameters rule**: Does NOT apply to ABC/Protocol method signatures or Click command callbacks (Click injects parameters positionally)
- **LBYL rule**: Exceptions allowed at error boundaries, for third-party API compatibility, or when adding context before re-raising
- **Import-time side effects**: Static constants are acceptable

If the code matches a documented exception, it is NOT a violation. Do not flag it.

**For `__all__` / re-exports:**

- Only flag if `__all__` appears in the **changed lines** (Step 2 analysis)
- Skip if `__all__` is pre-existing and unchanged in this PR

## Step 4: Inline Comment Format

When posting inline comments for violations, use this format:

```
**Dignified Python**: [rule violated] - [code location detail]
```

## Step 5: Summary Comment Format

Summary format (preserve existing Activity Log entries and prepend new entry):

```
### Files Reviewed
- `file.py`: N issues
```

Activity log entry examples:

- "Found 2 issues (LBYL violation in x.py, inline import in y.py)"
- "All issues resolved"
- "False positive dismissed: CLI error boundary pattern"

Keep the last 10 log entries maximum.
