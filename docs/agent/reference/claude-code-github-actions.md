---
title: Claude Code in GitHub Actions
read_when:
  - "running claude code in CI/CD"
  - "implementing remote AI workflows"
  - "configuring github actions for claude"
  - "understanding dangerously-skip-permissions"
---

# Claude Code in GitHub Actions

Guide for running Claude Code in GitHub Actions workflows for automated AI implementation tasks.

## Overview

Claude Code can be invoked in GitHub Actions to perform automated tasks like:

- Implementing plans from GitHub issues
- Extracting documentation patterns from sessions
- Processing and analyzing code changes
- Creating and updating pull requests

## Installation Pattern

Install Claude Code in your workflow using the official install script:

```yaml
- name: Setup Claude Code
  run: |
    curl -fsSL https://claude.ai/install.sh | bash
```

This installs the `claude` CLI globally, making it available for subsequent steps.

## CLI Invocation Pattern

### Basic Invocation

```yaml
- name: Run implementation
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    claude --print \
      --model claude-sonnet-4-5-20250929 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      --verbose \
      "/erk:plan-implement"
```

### Key CLI Flags

| Flag                             | Purpose                              |
| -------------------------------- | ------------------------------------ |
| `--print`                        | Output to stdout (no interactive UI) |
| `--model`                        | Pin to specific model version        |
| `--output-format stream-json`    | Structured JSONL output for parsing  |
| `--dangerously-skip-permissions` | Skip interactive permission prompts  |
| `--verbose`                      | Enable detailed logging              |

## Model Pinning

Always pin to a specific model version in automated workflows:

```yaml
--model claude-sonnet-4-5-20250929
```

**Why pin models?**

- Ensures reproducible behavior across workflow runs
- Protects against behavior changes from model updates
- Enables consistent cost and latency expectations

## Permission Skipping: `--dangerously-skip-permissions`

### Why It's Safe in GitHub Actions

The `--dangerously-skip-permissions` flag disables interactive permission prompts for tool use. In GitHub Actions, this is safe because:

1. **Isolated Environment**: Workflows run in ephemeral containers with no persistent user data
2. **Repository Scope**: Actions only have access to the checked-out repository
3. **Token-Based Access**: GitHub token permissions are explicitly configured
4. **Audit Trail**: All actions are logged in workflow run history
5. **No Interactive User**: There's no human to prompt anyway

### When NOT to Use This Flag

- Local development with access to sensitive files
- Environments with persistent storage
- Any context where unexpected file modifications could cause harm

## Repository Configuration

### Required Settings

Navigate to **Settings > Actions > General > Workflow permissions**:

1. ✓ Enable **"Read and write permissions"** for repository contents
2. ✓ Enable **"Allow GitHub Actions to create and approve pull requests"**

Without these settings, PR creation will fail with:

```
GitHub Actions is not permitted to create or approve pull requests
```

### Token Configuration

For workflows that need to trigger other workflows (like CI), use a Personal Access Token (PAT) instead of `GITHUB_TOKEN`:

```yaml
- uses: actions/checkout@v4
  with:
    token: ${{ secrets.MY_PAT }}
    fetch-depth: 0
```

**Why?** Actions triggered by `GITHUB_TOKEN` cannot trigger other workflows (to prevent infinite loops). Using a PAT allows push events to trigger CI workflows.

## Phase-Based Workflow Structure

Structure complex AI workflows into distinct phases for clarity and error handling:

```yaml
jobs:
  implement:
    runs-on: ubuntu-latest
    steps:
      # =================================================================
      # PHASE 1: CHECKOUT AND SETUP
      # =================================================================
      - uses: actions/checkout@v4
      - name: Setup tools
        run: |
          # Install dependencies
          curl -fsSL https://claude.ai/install.sh | bash

      # =================================================================
      # PHASE 2: ANALYSIS
      # =================================================================
      - name: Run analysis
        id: analyze
        run: |
          claude --print ... "analyze the codebase"

      # =================================================================
      # PHASE 3: IMPLEMENTATION
      # =================================================================
      - name: Implement changes
        if: steps.analyze.outputs.analysis_success == 'true'
        run: |
          claude --print ... "/erk:plan-implement"

      # =================================================================
      # PHASE 4: SUBMISSION
      # =================================================================
      - name: Create PR
        if: steps.implement.outputs.success == 'true'
        run: |
          gh pr create --fill
```

### Benefits of Phased Structure

- Clear separation of concerns
- Easy to identify which phase failed
- Conditional execution based on previous phase success
- Better debugging through structured logs

## Error Handling with Status Comments

Post status updates to GitHub issues for visibility:

```yaml
- name: Post failure comment
  if: failure()
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_NUMBER: ${{ inputs.issue_number }}
  run: |
    WORKFLOW_RUN_URL="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"

    cat > comment_body.md <<EOF
    ❌ **Implementation failed**

    An error occurred during the implementation process.

    [View workflow run]($WORKFLOW_RUN_URL)
    EOF

    gh issue comment "$ISSUE_NUMBER" --body-file comment_body.md
    rm -f comment_body.md
```

### Status Comment Patterns

| Status      | Emoji | Use Case                     |
| ----------- | ----- | ---------------------------- |
| Started     | ⚙️    | Workflow has begun           |
| In Progress | 🔄    | Step completed, continuing   |
| Complete    | ✅    | All phases succeeded         |
| Failed      | ❌    | An error occurred            |
| No Changes  | ℹ️    | Analysis found nothing to do |

## Integration with Erk Slash Commands

Claude Code slash commands can be invoked directly in workflows:

```yaml
- name: Implement plan
  run: |
    claude --print \
      --model claude-sonnet-4-5-20250929 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      "/erk:plan-implement"
```

Common slash commands for automation:

| Command                       | Purpose                                          |
| ----------------------------- | ------------------------------------------------ |
| `/erk:plan-implement`         | Execute implementation plan from `.impl/` folder |
| `/erk:create-extraction-plan` | Analyze session for documentation patterns       |
| `/git:pr-push <desc>`         | Create commit and submit PR                      |

## Handling Exit Codes

Claude CLI uses exit codes to indicate success or failure:

```yaml
- name: Run with exit code handling
  id: implement
  run: |
    set +e  # Don't exit on error

    claude --print \
      --model claude-sonnet-4-5-20250929 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      "/erk:plan-implement"

    EXIT_CODE=$?
    echo "exit_code=$EXIT_CODE" >> $GITHUB_OUTPUT

    if [ $EXIT_CODE -eq 0 ]; then
      echo "implementation_success=true" >> $GITHUB_OUTPUT
    else
      echo "implementation_success=false" >> $GITHUB_OUTPUT
    fi

    exit 0  # Always succeed to allow subsequent error handling
```

## Concurrency Control

Prevent multiple implementations of the same issue:

```yaml
concurrency:
  group: implement-issue-${{ github.event.inputs.issue_number }}
  cancel-in-progress: true
```

This ensures:

- Only one workflow runs per issue at a time
- New runs cancel in-progress runs for the same issue
- Prevents conflicting changes from parallel runs

## Complete Example: Plan Implementation Workflow

```yaml
name: Implement Issue
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: "Issue number to implement"
        required: true
        type: string

concurrency:
  group: implement-issue-${{ inputs.issue_number }}
  cancel-in-progress: true

jobs:
  implement:
    runs-on: ubuntu-latest
    timeout-minutes: 180
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup tools
        run: |
          curl -fsSL https://claude.ai/install.sh | bash

      - name: Run implementation
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ github.token }}
        run: |
          claude --print \
            --model claude-sonnet-4-5-20250929 \
            --output-format stream-json \
            --dangerously-skip-permissions \
            --verbose \
            "/erk:plan-implement"

      - name: Post failure comment
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh issue comment "${{ inputs.issue_number }}" \
            --body "❌ Implementation failed. [View run](${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }})"
```

## Security Considerations

### Secrets Management

- Store API keys in GitHub Secrets, never in workflow files
- Use least-privilege tokens when possible
- Rotate secrets periodically

### Repository Access

- Claude Code has full access to checked-out files
- Consider using a dedicated branch for AI changes
- Review AI-generated changes before merging to main

### Audit Trail

All Claude Code invocations are logged:

- GitHub Actions workflow run logs
- Stream-JSON output (if captured)
- Issue comments with status updates

## Related

- [Claude CLI Stream-JSON Format](./claude-cli-stream-json.md) - Parsing Claude output
- [Planning Workflow](../planning/workflow.md) - Understanding `.impl/` folders
- [Raw Extraction Workflow](../planning/raw-extraction-workflow.md) - Automated documentation extraction
