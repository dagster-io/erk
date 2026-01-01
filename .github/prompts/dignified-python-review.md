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

Study these documents thoroughly before analyzing code.

## Step 2: Get the Python Diff

Get the list of changed Python files:

```
gh pr diff {{ github.event.pull_request.number }} --name-only | grep '\.py$'
```

Get the full diff:

```
gh pr diff {{ github.event.pull_request.number }}
```

## Step 3: Analyze Code

For each Python file changed, analyze against ALL dignified-python rules including:

- LBYL over EAFP (no try/except for control flow)
- Exception handling patterns
- Path operations (exists before resolve)
- Import organization (module-level, absolute)
- No re-exports or **all**
- No default parameter values unless justified
- Dependency injection with ABC
- Performance (O(1) properties)
- Code organization (variable placement, indentation depth)

## Step 4: Post Inline Comments

For each specific violation, post an inline comment using the erk exec command:

```
erk exec post-pr-inline-comment \
  --pr-number {{ github.event.pull_request.number }} \
  --path "path/to/file.py" \
  --line LINE_NUMBER \
  --body "**Dignified Python**: [explanation with fix suggestion]"
```

Use the line number from the diff where the violation occurs.
The comment body should explain the rule violated and suggest a fix.

## Step 5: Post Summary Comment

Post or update a summary comment with a marker:

```
erk exec post-or-update-pr-summary \
  --pr-number {{ github.event.pull_request.number }} \
  --marker "<!-- dignified-python-review -->" \
  --body "SUMMARY_TEXT"
```

Summary comment format (the body must include the marker):

```
_Last updated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')_

<!-- dignified-python-review -->

## Dignified Python Review

### Summary

Found X issues across Y files.

### Issues by Category

- **LBYL Violations**: N instances
- **Exception Handling**: N instances
- **Import Organization**: N instances
- **Path Operations**: N instances
- (other categories as applicable)

### Files Reviewed

- `path/to/file1.py`: N issues (inline comments posted)
- `path/to/file2.py`: N issues (inline comments posted)

### Overall Assessment

[Brief assessment of code quality against dignified-python standards]
```

The marker MUST be included in all summary comments so they can be found and updated on subsequent runs.
