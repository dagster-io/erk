REPO: {{ github.repository }}
PR NUMBER: {{ github.event.pull_request.number }}

## Task

Review Python code changes for adherence to dignified-python standards.

## Step 1: Load the Dignified Python Standards

Read these skill files from the repository:

1. .claude/skills/dignified-python/SKILL.md (routing and version detection)
2. .claude/skills/dignified-python/dignified-python-core.md (LBYL, exceptions, paths, imports, DI, performance)
3. .claude/skills/dignified-python/cli-patterns.md (Click best practices)
4. .claude/skills/dignified-python/subprocess.md (subprocess handling)

## Step 2: Get the Python Diff

```
gh pr diff {{ github.event.pull_request.number }} --name-only | grep '\.py$'
gh pr diff {{ github.event.pull_request.number }}
```

## Step 3: Analyze Code

Check each Python file against dignified-python rules:

- LBYL over EAFP (no try/except for control flow)
- Exception handling (no silent swallowing, log at boundaries)
- Path operations (exists before resolve)
- Import organization (module-level, absolute, no re-exports)
- No default parameter values
- Dependency injection with ABC
- Frozen dataclasses

## Step 4: Post Inline Comments

**IMPORTANT: You MUST post an inline comment for EACH violation found.**

```
erk exec post-pr-inline-comment \
  --pr-number {{ github.event.pull_request.number }} \
  --path "path/to/file.py" \
  --line LINE_NUMBER \
  --body "**Dignified Python**: [rule violated] - [fix suggestion]"
```

## Step 5: Post Summary Comment

```
erk exec post-or-update-pr-summary \
  --pr-number {{ github.event.pull_request.number }} \
  --marker "<!-- dignified-python-review -->" \
  --body "SUMMARY_TEXT"
```

Summary format:

```
<!-- dignified-python-review -->

## Dignified Python Review

Found X issues across Y files. Inline comments posted for each.

### Files Reviewed
- `file.py`: N issues
```
