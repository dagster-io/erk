---
title: Autolearn Feature
read_when:
  - "landing a PR and wanting to capture session insights"
  - "configuring automatic learn plan creation"
  - "understanding the autolearn workflow"
---

# Autolearn Feature

Autolearn automatically creates a learn plan issue when landing a PR via `erk land`, capturing session insights before they're lost.

## How It Works

When you land a PR that originated from an erk-plan issue:

1. Autolearn extracts the plan issue number from the branch name
2. Discovers all sessions associated with that plan
3. Creates a new learn plan issue with `erk-learn` label
4. Links the session IDs for later processing via `erk learn`

## Configuration

Enable autolearn in `~/.erk/config.yaml`:

```yaml
autolearn: true
```

## CLI Override

Override config per-command using flags on `erk land`:

- `--autolearn` - Force enable (even if config has `autolearn: false`)
- `--no-autolearn` - Force disable (even if config has `autolearn: true`)

## When Autolearn Triggers

Autolearn only activates when ALL conditions are met:

1. `autolearn: true` in config OR `--autolearn` flag passed
2. Branch name starts with an issue number (e.g., `123-feature-name`)
3. The source issue is NOT already a learn plan (no `erk-learn` label)
4. Sessions exist for the plan issue

## Fail-Open Design

Autolearn follows a fail-open pattern: errors are reported as warnings but never block the landing operation. This ensures:

- Landing always succeeds even if GitHub API fails
- Session discovery failures don't break your workflow
- Learn plan creation errors are non-fatal

Warning messages appear with yellow indicators:

```
⚠ Autolearn: Could not fetch source issue #123: [error]
⚠ Autolearn: No sessions found for plan #123
⚠ Autolearn: Failed to create learn plan: [error]
```

## What Gets Created

The learn plan issue contains:

- Title: `Learn: [original plan title] [erk-learn]`
- Labels: `erk-plan`, `erk-learn`
- Links to source plan issue and merged PR
- Session IDs for extraction

## Processing Learn Plans

Learn plans are processed via the existing learn workflow:

```bash
erk learn <issue-number>
```

Or automatically via GitHub Actions dispatch if configured.

## Related

- [Plan Lifecycle](../planning/lifecycle.md) - Full plan lifecycle documentation
- [Session Discovery](../sessions/) - How sessions are discovered for plans
