---
title: Convention-Based Code Reviews
read_when:
  - adding a new code review to CI
  - understanding how code reviews work
  - modifying code review behavior
tripwires:
  - action: "using fnmatch for gitignore-style glob patterns"
    warning: "Use pathspec library instead. fnmatch doesn't support ** recursive globs. Example: pathspec.PathSpec.from_lines('gitignore', patterns)"
---

# Convention-Based Code Reviews

Code reviews run automatically on PRs by dropping a markdown file in `.github/reviews/`.

## Overview

The system consists of:

1. **Review definitions** in `.github/reviews/*.md` - YAML frontmatter + prompt content
2. **Discovery** via `erk exec discover-reviews` - finds reviews matching changed files
3. **Execution** via `erk exec run-review` - assembles prompt and invokes Claude
4. **Workflow** in `.github/workflows/code-reviews.yml` - orchestrates discovery and parallel execution

## Adding a New Code Review

Create a markdown file in `.github/reviews/`:

```bash
touch .github/reviews/my-review.md
```

Add YAML frontmatter and review content:

```markdown
---
name: My Review
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
marker: "<!-- my-review -->"
model: claude-sonnet-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Review Instructions

Your review prompt goes here. Claude will receive this along with
the PR diff and repository context.
```

That's it. The workflow automatically discovers and runs your review on matching PRs.

## Frontmatter Schema

| Field             | Required | Type         | Description                                     |
| ----------------- | -------- | ------------ | ----------------------------------------------- |
| `name`            | Yes      | string       | Human-readable review name                      |
| `paths`           | Yes      | list[string] | Gitignore-style glob patterns for file matching |
| `marker`          | Yes      | string       | HTML comment marker for summary comments        |
| `model`           | Yes      | string       | Claude model ID (e.g., `claude-sonnet-4-5`)     |
| `timeout_minutes` | Yes      | int          | Job timeout                                     |
| `allowed_tools`   | Yes      | string       | Claude `--allowedTools` value                   |
| `enabled`         | Yes      | bool         | Set `false` to disable without removing         |

### Path Patterns

Paths use gitignore-style globs via the `pathspec` library:

| Pattern           | Matches                           |
| ----------------- | --------------------------------- |
| `**/*.py`         | All Python files in any directory |
| `src/**/*.py`     | Python files under `src/`         |
| `.claude/**/*.md` | Markdown files under `.claude/`   |
| `*.sh`            | Shell scripts in root only        |

The `pathspec` library handles `**` correctly (unlike `fnmatch`).

## How Discovery Works

`erk exec discover-reviews --pr-number <N>`:

1. Lists changed files in the PR via GitHub API
2. Loads all `.github/reviews/*.md` files
3. For each review, checks if any changed file matches any path pattern
4. Returns matching reviews as a JSON matrix for GitHub Actions

Example output:

```json
{
  "success": true,
  "reviews": [{ "filename": "tripwires.md", "name": "Tripwires Review" }],
  "matrix": {
    "include": [{ "filename": "tripwires.md", "name": "Tripwires Review" }]
  }
}
```

## How Execution Works

`erk exec run-review --name <review-name> --pr-number <N>`:

1. Loads the review definition from `.github/reviews/<name>.md`
2. Assembles the prompt with standard boilerplate (repository context, PR info)
3. Invokes Claude with the assembled prompt

Use `--dry-run` to print the assembled prompt without running Claude.

## Workflow Architecture

`.github/workflows/code-reviews.yml` uses a two-job pattern:

```
┌─────────────┐     ┌─────────────────────────┐
│  discover   │────▶│  review (matrix job)    │
│             │     │  - review 1             │
│  Outputs:   │     │  - review 2             │
│  - matrix   │     │  - ...                  │
│  - has_reviews    │                         │
└─────────────┘     └─────────────────────────┘
```

1. **discover** job runs `erk exec discover-reviews` and outputs a matrix
2. **review** job runs in parallel for each matching review
3. Each review job installs erk, Claude Code, and runs `erk exec run-review`

## Existing Reviews

| Review           | File                  | Matches                                 |
| ---------------- | --------------------- | --------------------------------------- |
| Tripwires Review | `tripwires.md`        | `**/*.py`, `**/*.sh`, `.claude/**/*.md` |
| Dignified Python | `dignified-python.md` | Python files                            |

## Disabling a Review

Set `enabled: false` in the frontmatter:

```yaml
---
name: My Review
enabled: false
# ... rest of config
---
```

The review file stays in place but is skipped during discovery.

## Debugging

### Check which reviews would run

```bash
erk exec discover-reviews --pr-number 123
```

### Preview assembled prompt

```bash
erk exec run-review --name tripwires --pr-number 123 --dry-run
```

### Run locally (requires Claude Code and ANTHROPIC_API_KEY)

```bash
erk exec run-review --name tripwires --pr-number 123
```

## Migration from Individual Workflows

Before this system, each code review had its own workflow file:

- `.github/workflows/tripwires-review.yml` (deleted)
- `.github/workflows/dignified-python-review.yml` (deleted)

These were replaced by the single `code-reviews.yml` workflow with the convention-based discovery system.

## Related Topics

- [CI Prompt Patterns](prompt-patterns.md) - Embedded prompts for non-review CI tasks
- [Container-less CI](containerless-ci.md) - Native tool installation pattern
