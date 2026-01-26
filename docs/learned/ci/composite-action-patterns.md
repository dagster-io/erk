---
title: Composite Action Patterns
read_when:
  - "creating reusable GitHub Actions setup steps"
  - "using erk-remote-setup composite action"
  - "understanding GitHub Actions composite patterns"
---

# Composite Action Patterns

This document describes the composite actions in `.github/actions/` and patterns for creating reusable workflow setup components.

## Available Composite Actions

| Action              | Purpose                                     | Inputs                                                    |
| ------------------- | ------------------------------------------- | --------------------------------------------------------- |
| `erk-remote-setup`  | Full remote workflow environment setup      | `erk-pat`, `anthropic-api-key`, `claude-code-oauth-token` |
| `setup-claude-code` | Install Claude Code CLI with caching        | None                                                      |
| `setup-python-uv`   | Install Python and uv, sync dependencies    | `python-version` (default: "3.12")                        |
| `setup-graphite`    | Install Graphite CLI for stack management   | None                                                      |
| `setup-claude-erk`  | Install erk tools (assumes uv/claude exist) | None                                                      |
| `setup-prettier`    | Install Node.js and Prettier                | None                                                      |
| `check-worker-impl` | Check if `.worker-impl/` folder exists      | None (outputs: `skip`)                                    |

## Primary Action: erk-remote-setup

The `erk-remote-setup` action is the consolidated setup for all remote AI workflows. It combines multiple setup steps into a single reusable action.

### Usage

```yaml
- uses: ./.github/actions/erk-remote-setup
  with:
    erk-pat: ${{ secrets.ERK_QUEUE_GH_PAT }}
    anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
    claude-code-oauth-token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
```

### What It Does

1. **Validates secrets** - Fails early with clear error messages if secrets are missing
2. **Sets up uv** - Python package management with Python 3.13
3. **Sets up Claude Code** - Native binary installation with caching
4. **Installs prettier** - For markdown formatting
5. **Installs erk** - As editable install with erk-shared
6. **Validates Claude credentials** - Runs `erk exec validate-claude-credentials`
7. **Configures git identity** - Sets bot user for commits

### Why Use It

- **DRY principle**: Avoids duplicating 7 setup steps across multiple workflows
- **Consistent configuration**: All remote workflows use identical setup
- **Easier maintenance**: Changes to setup propagate to all workflows

## Specialized Actions

### setup-claude-code

Installs Claude Code CLI using direct binary download (not the install script).

**Why direct download?**

The standard `curl | bash` install script frequently hangs in CI. Known issues:

- Subprocess hangs indefinitely
- Lock files persist after timeout
- No built-in retry mechanism

The action downloads from GCS directly, bypassing these issues.

**Features:**

- Caches binary to avoid repeated downloads
- Cleans stale lock files before installation
- Detects platform (x64/arm64) automatically

### setup-python-uv

Standard Python setup with uv package manager.

```yaml
- uses: ./.github/actions/setup-python-uv
  with:
    python-version: "3.13"
```

### check-worker-impl

Checks for `.worker-impl/` folder presence to skip CI during AI implementation.

```yaml
- uses: ./.github/actions/check-worker-impl
  id: worker-check

- name: Run tests
  if: steps.worker-check.outputs.skip != 'true'
  run: pytest
```

**Output:** `skip` - "true" if folder exists, "false" otherwise

## Creating New Composite Actions

### Structure

```
.github/actions/my-action/
└── action.yml
```

### Template

```yaml
name: "Action Name"
description: "Brief description"

inputs:
  required-input:
    description: "What this input does"
    required: true
  optional-input:
    description: "Optional parameter"
    required: false
    default: "default-value"

outputs:
  my-output:
    description: "What this output contains"
    value: ${{ steps.step-id.outputs.value }}

runs:
  using: "composite"
  steps:
    - name: Step name
      shell: bash
      run: |
        echo "Running step..."
```

### Best Practices

1. **Validate inputs early** - Fail fast with clear error messages
2. **Use caching** - Cache downloaded binaries/packages when possible
3. **Set shell explicitly** - Always specify `shell: bash` for run steps
4. **Document why** - Add comments explaining non-obvious choices
5. **Keep focused** - Each action should do one thing well

## Patterns

### Secret Validation Pattern

```yaml
- name: Validate secrets
  shell: bash
  run: |
    if [ -z "${{ inputs.api-key }}" ]; then
      echo "::error title=Missing Secret::API_KEY not configured"
      exit 1
    fi
```

### Caching Pattern

```yaml
- name: Cache binary
  id: cache
  uses: actions/cache@v4
  with:
    path: ~/.local/bin/my-tool
    key: my-tool-${{ runner.os }}-${{ runner.arch }}-v1

- name: Download (on cache miss)
  if: steps.cache.outputs.cache-hit != 'true'
  shell: bash
  run: |
    curl -fsSL https://example.com/binary -o ~/.local/bin/my-tool
    chmod +x ~/.local/bin/my-tool
```

### Conditional Output Pattern

```yaml
- name: Check condition
  id: check
  shell: bash
  run: |
    if [ -d ".worker-impl" ]; then
      echo "skip=true" >> $GITHUB_OUTPUT
    else
      echo "skip=false" >> $GITHUB_OUTPUT
    fi
```

## Related Documentation

- [GitHub Actions Workflow Patterns](github-actions-workflow-patterns.md) - Workflow-level patterns
- [Workflow Commands](../cli/workflow-commands.md) - CLI interface to trigger workflows
- [Remote Workflow Template](../erk/remote-workflow-template.md) - Complete workflow examples
