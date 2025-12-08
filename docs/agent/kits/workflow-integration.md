---
title: GitHub Actions Workflow Integration Patterns
read_when:
  - "creating GitHub Actions workflows that call kit CLI commands"
  - "parsing JSON output in workflow steps"
  - "handling workflow errors from kit CLI commands"
  - "passing data between workflow steps"
---

# GitHub Actions Workflow Integration Patterns

This guide documents patterns for calling kit CLI commands from GitHub Actions workflows with proper JSON parsing and error handling.

## Overview

Kit CLI commands are designed to be called from GitHub Actions workflows. They return structured JSON output and use exit codes for error handling, making them ideal for workflow automation.

**Key principle**: Workflows consume JSON, not human-readable text. Design for programmatic consumption.

## Pattern 1: Basic Kit CLI Command Invocation

### Simple Command Execution

```yaml
- name: Detect trunk branch
  id: trunk
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk detect-trunk-branch)
    echo "trunk_branch=$(echo "$result" | jq -r '.trunk_branch')" >> $GITHUB_OUTPUT
```

**Key elements:**

- `id: trunk` - Step identifier for referencing outputs
- `source $HOME/.cargo/env` - Load uv/cargo environment (if needed)
- `result=$(dot-agent run erk {command})` - Capture command output
- `jq -r '.field'` - Extract field from JSON (raw output, no quotes)
- `>> $GITHUB_OUTPUT` - Export for use in later steps

### Using Step Outputs in Later Steps

```yaml
- name: Create extraction branch
  id: branch
  env:
    TRUNK_BRANCH: ${{ steps.trunk.outputs.trunk_branch }}
  run: |
    result=$(dot-agent run erk create-extraction-branch \
      --issue-number "$ISSUE_NUMBER" \
      --trunk-branch "$TRUNK_BRANCH")
    echo "branch_name=$(echo "$result" | jq -r '.branch_name')" >> $GITHUB_OUTPUT
```

**Accessing previous step outputs:**

- `${{ steps.{step_id}.outputs.{output_name} }}`
- Available in `env:` blocks, conditionals, and subsequent steps

## Pattern 2: Handling Success and Error States

### Checking Command Success

```yaml
- name: Create worker-impl from issue
  id: worker_impl
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_NUMBER: ${{ github.event.issue.number }}
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk create-worker-impl-from-issue "$ISSUE_NUMBER")
    success=$(echo "$result" | jq -r '.success')
    echo "worker_impl_success=$success" >> $GITHUB_OUTPUT

- name: Implement extraction plan
  id: implement
  if: steps.worker_impl.outputs.worker_impl_success == 'true'
  run: |
    # Only runs if previous step succeeded
    claude --print "/erk:plan-implement"
```

**Key patterns:**

- Extract `success` field: `jq -r '.success'`
- Use in conditionals: `if: steps.X.outputs.Y == 'true'`
- Compare as strings (`'true'`), not booleans

### Conditional Execution Based on Success

```yaml
- name: Post completion comment
  if: steps.submit.outputs.has_changes == 'true'
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_NUMBER: ${{ github.event.issue.number }}
    PR_URL: ${{ steps.submit.outputs.pr_url }}
  run: |
    source $HOME/.cargo/env
    dot-agent run erk post-extraction-comment \
      --issue-number "$ISSUE_NUMBER" \
      --status complete \
      --pr-url "$PR_URL"

- name: Post no-changes comment
  if: steps.submit.outputs.has_changes == 'false'
  run: |
    # Alternative path when no changes were made
    dot-agent run erk post-extraction-comment \
      --issue-number "$ISSUE_NUMBER" \
      --status no-changes
```

**Pattern: Branch on outputs:**

- Separate steps for success/failure paths
- Use `if:` conditionals to select path
- Both paths complete gracefully

## Pattern 3: Error Handling and Failure Recovery

### Handling Command Failures with set +e

```yaml
- name: Implement extraction plan
  id: implement
  run: |
    set +e  # Don't exit on error
    claude --print \
      --model claude-sonnet-4-5-20250929 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      --verbose \
      "/erk:plan-implement"

    if [ $? -eq 0 ]; then
      echo "implementation_success=true" >> $GITHUB_OUTPUT
    else
      echo "implementation_success=false" >> $GITHUB_OUTPUT
    fi
    exit 0  # Always succeed at step level
```

**Key pattern:**

- `set +e` - Allow command to fail without failing step
- `$?` - Check exit code of previous command
- Capture success/failure in output variable
- `exit 0` - Step always succeeds, failure handled in later steps

### Posting Failure Comments

```yaml
- name: Post failure comment
  if: failure()
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_NUMBER: ${{ github.event.issue.number }}
    WORKFLOW_RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
  run: |
    source $HOME/.cargo/env
    dot-agent run erk post-extraction-comment \
      --issue-number "$ISSUE_NUMBER" \
      --status failed \
      --workflow-run-url "$WORKFLOW_RUN_URL"
```

**Key elements:**

- `if: failure()` - Runs only when any previous step failed
- `${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}` - Construct workflow run URL
- Kit CLI command for posting structured comments

## Pattern 4: Passing Complex Data Between Steps

### Extracting Multiple Fields

```yaml
- name: Initialize implementation
  id: init
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk impl-init --json)

    # Extract multiple fields from JSON
    valid=$(echo "$result" | jq -r '.valid')
    impl_type=$(echo "$result" | jq -r '.impl_type')
    has_issue=$(echo "$result" | jq -r '.has_issue_tracking')
    issue_num=$(echo "$result" | jq -r '.issue_number // "0"')

    # Export all fields
    echo "valid=$valid" >> $GITHUB_OUTPUT
    echo "impl_type=$impl_type" >> $GITHUB_OUTPUT
    echo "has_issue_tracking=$has_issue" >> $GITHUB_OUTPUT
    echo "issue_number=$issue_num" >> $GITHUB_OUTPUT
```

**Key patterns:**

- Extract each field separately with `jq`
- Use `// "default"` for optional fields
- Export all needed fields to `$GITHUB_OUTPUT`

### Handling Empty or Null Values

```yaml
- name: Get PR URL
  id: pr
  run: |
    PR_URL=$(gh pr view "$BRANCH_NAME" --json url -q '.url' 2>/dev/null || echo "")
    echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT

- name: Mark PR ready for review
  if: steps.pr.outputs.pr_url != ''
  run: |
    gh pr ready "$BRANCH_NAME" 2>/dev/null || true
```

**Handling empty/null:**

- `|| echo ""` - Provide empty string default on error
- `!= ''` - Check for non-empty string in conditionals
- `|| true` - Allow command to fail gracefully

## Pattern 5: Structured Command Arguments

### Passing Arguments from Environment

```yaml
- name: Create extraction branch
  id: branch
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_NUMBER: ${{ github.event.issue.number }}
    TRUNK_BRANCH: ${{ steps.trunk.outputs.trunk_branch }}
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk create-extraction-branch \
      --issue-number "$ISSUE_NUMBER" \
      --trunk-branch "$TRUNK_BRANCH")
    echo "branch_name=$(echo "$result" | jq -r '.branch_name')" >> $GITHUB_OUTPUT
```

**Key patterns:**

- Define variables in `env:` block for clarity
- Quote environment variables: `"$VAR"`
- Use multi-line `\` for readability
- Environment variables available in `run:` script

### Using GitHub Context Variables

```yaml
env:
  GH_TOKEN: ${{ github.token }}
  ISSUE_NUMBER: ${{ github.event.issue.number }}
  WORKFLOW_RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

**Common context variables:**

- `${{ github.token }}` - Automatic token for GitHub API
- `${{ github.event.issue.number }}` - Trigger issue number
- `${{ github.repository }}` - Owner/repo name
- `${{ github.server_url }}` - GitHub server URL
- `${{ github.run_id }}` - Current workflow run ID

## Pattern 6: Setup and Teardown

### Installing Dependencies

```yaml
- name: Setup all tools
  run: |
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env

    # Install Claude Code
    curl -fsSL https://claude.ai/install.sh | bash

    # Install Prettier via npm
    npm install -g prettier

    cd $GITHUB_WORKSPACE

    # Install workspace packages in dependency order
    uv tool install --from ./packages/dot-agent-kit --with ./packages/erk-shared dot-agent-kit
    uv tool install --from . --with ./packages/erk-shared --with ./packages/dot-agent-kit erk

    # Install erk kit for Claude Code
    dot-agent kit install erk
```

**Key patterns:**

- Install uv first, then source environment
- Install Claude Code if needed for slash commands
- Install packages in dependency order
- Install kits after dot-agent-kit is available

### Configuring Git

```yaml
- name: Configure git
  run: |
    git config user.name "erk-bot"
    git config user.email "erk-bot@users.noreply.github.com"
```

**Required for:**

- Creating commits in workflows
- Pushing changes to branches
- Any git operations that create objects

## Pattern 7: Conditional Steps and Job Control

### Running Jobs Conditionally

```yaml
jobs:
  implement-extraction:
    # Only run for extraction plan issues
    if: |
      contains(github.event.issue.labels.*.name, 'erk-extraction') &&
      contains(github.event.issue.labels.*.name, 'erk-plan')
    runs-on: ubuntu-latest
    steps:
      # ...
```

**Key patterns:**

- `if:` at job level - Job won't appear in UI if condition false
- `contains()` - Check if array contains value
- Multi-line conditions with `|`
- Combine conditions with `&&`, `||`

### Concurrency Control

```yaml
concurrency:
  group: process-extraction-${{ github.event.issue.number }}
  cancel-in-progress: true
```

**Purpose:**

- Prevent multiple runs for same issue
- Cancel in-progress runs when new run starts
- Use unique group identifier (e.g., issue number)

## Pattern 8: Permissions and Secrets

### Declaring Required Permissions

```yaml
jobs:
  implement-extraction:
    permissions:
      contents: write
      pull-requests: write
      issues: write
```

**Common permissions:**

- `contents: write` - Commit and push changes
- `pull-requests: write` - Create and update PRs
- `issues: write` - Comment on issues, add labels
- `id-token: write` - OIDC authentication (for Anthropic API)

### Using Secrets

```yaml
- name: Run Claude Code
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
  run: |
    claude --print "/erk:plan-implement"
```

**Secret patterns:**

- Access via `${{ secrets.SECRET_NAME }}`
- Pass through `env:` block
- Use `github.token` for default GitHub token
- Use PAT for operations requiring elevated permissions

## Complete Example: Extraction Workflow

```yaml
name: Implement Extraction Plan
run-name: "Implement Extraction: #${{ github.event.issue.number }}"

on:
  issues:
    types: [opened, labeled]

concurrency:
  group: process-extraction-${{ github.event.issue.number }}
  cancel-in-progress: true

jobs:
  implement-extraction:
    if: |
      contains(github.event.issue.labels.*.name, 'erk-extraction') &&
      contains(github.event.issue.labels.*.name, 'erk-plan')
    runs-on: ubuntu-latest
    timeout-minutes: 180
    permissions:
      contents: write
      pull-requests: write
      issues: write
    steps:
      # Phase 1: Setup
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.ERK_QUEUE_GH_PAT }}
          fetch-depth: 0

      - name: Setup all tools
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env
          curl -fsSL https://claude.ai/install.sh | bash
          npm install -g prettier
          cd $GITHUB_WORKSPACE
          uv tool install --from ./packages/dot-agent-kit --with ./packages/erk-shared dot-agent-kit
          uv tool install --from . --with ./packages/erk-shared --with ./packages/dot-agent-kit erk
          dot-agent kit install erk

      - name: Configure git
        run: |
          git config user.name "erk-bot"
          git config user.email "erk-bot@users.noreply.github.com"

      # Phase 2: Kit CLI Command - Detect trunk
      - name: Detect trunk branch
        id: trunk
        run: |
          source $HOME/.cargo/env
          result=$(dot-agent run erk detect-trunk-branch)
          echo "trunk_branch=$(echo "$result" | jq -r '.trunk_branch')" >> $GITHUB_OUTPUT

      # Phase 3: Kit CLI Command - Create branch
      - name: Create extraction branch
        id: branch
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          TRUNK_BRANCH: ${{ steps.trunk.outputs.trunk_branch }}
        run: |
          source $HOME/.cargo/env
          result=$(dot-agent run erk create-extraction-branch \
            --issue-number "$ISSUE_NUMBER" \
            --trunk-branch "$TRUNK_BRANCH")
          echo "branch_name=$(echo "$result" | jq -r '.branch_name')" >> $GITHUB_OUTPUT

      # Phase 4: Kit CLI Command - Create worker-impl
      - name: Create worker-impl from issue
        id: worker_impl
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          source $HOME/.cargo/env
          result=$(dot-agent run erk create-worker-impl-from-issue "$ISSUE_NUMBER")
          success=$(echo "$result" | jq -r '.success')
          echo "worker_impl_success=$success" >> $GITHUB_OUTPUT

      # Phase 5: Conditional execution
      - name: Implement extraction plan
        id: implement
        if: steps.worker_impl.outputs.worker_impl_success == 'true'
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GH_TOKEN: ${{ github.token }}
        run: |
          set +e
          claude --print \
            --model claude-sonnet-4-5-20250929 \
            --output-format stream-json \
            --dangerously-skip-permissions \
            --verbose \
            "/erk:plan-implement"
          if [ $? -eq 0 ]; then
            echo "implementation_success=true" >> $GITHUB_OUTPUT
          else
            echo "implementation_success=false" >> $GITHUB_OUTPUT
          fi
          exit 0

      # Phase 6: Success path
      - name: Post completion comment
        if: steps.submit.outputs.has_changes == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          PR_URL: ${{ steps.submit.outputs.pr_url }}
        run: |
          source $HOME/.cargo/env
          dot-agent run erk post-extraction-comment \
            --issue-number "$ISSUE_NUMBER" \
            --status complete \
            --pr-url "$PR_URL"

      # Phase 7: Error handling
      - name: Post failure comment
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
          WORKFLOW_RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          source $HOME/.cargo/env
          dot-agent run erk post-extraction-comment \
            --issue-number "$ISSUE_NUMBER" \
            --status failed \
            --workflow-run-url "$WORKFLOW_RUN_URL"
```

## Common Pitfalls and Solutions

### Pitfall 1: Not Quoting Variables

```yaml
# ❌ BAD - Word splitting breaks multi-word values
result=$(dot-agent run erk command $ISSUE_NUMBER)

# ✅ GOOD - Quote to preserve spaces
result=$(dot-agent run erk command "$ISSUE_NUMBER")
```

### Pitfall 2: Comparing Booleans as Booleans

```yaml
# ❌ BAD - Boolean comparison doesn't work
if: steps.init.outputs.valid == true

# ✅ GOOD - Compare as string
if: steps.init.outputs.valid == 'true'
```

### Pitfall 3: Not Sourcing uv Environment

```yaml
# ❌ BAD - Command not found
result=$(dot-agent run erk command)

# ✅ GOOD - Source environment first
source $HOME/.cargo/env
result=$(dot-agent run erk command)
```

### Pitfall 4: Not Handling Empty Fields

```yaml
# ❌ BAD - jq fails on missing field
issue_num=$(echo "$result" | jq -r '.issue_number')

# ✅ GOOD - Provide default value
issue_num=$(echo "$result" | jq -r '.issue_number // "0"')
```

### Pitfall 5: Not Using set +e for Recoverable Errors

```yaml
# ❌ BAD - Step fails immediately
claude --print "/command"

# ✅ GOOD - Capture error, continue workflow
set +e
claude --print "/command"
if [ $? -eq 0 ]; then
  echo "success=true" >> $GITHUB_OUTPUT
else
  echo "success=false" >> $GITHUB_OUTPUT
fi
exit 0
```

## Workflow Integration Checklist

When adding kit CLI command to workflow:

- [ ] Install required tools in setup step (uv, Claude Code, etc.)
- [ ] Source `$HOME/.cargo/env` before calling `dot-agent`
- [ ] Capture command output: `result=$(dot-agent run ...)`
- [ ] Extract fields with `jq -r '.field'`
- [ ] Quote environment variables: `"$VAR"`
- [ ] Export outputs to `$GITHUB_OUTPUT`
- [ ] Use step IDs for referencing outputs
- [ ] Compare strings, not booleans: `== 'true'`
- [ ] Handle missing fields: `jq -r '.field // "default"'`
- [ ] Use `set +e` for recoverable errors
- [ ] Add error handling steps with `if: failure()`
- [ ] Declare required permissions
- [ ] Add concurrency control if needed
- [ ] Use descriptive step names
- [ ] Add comments for complex logic

## Related Documentation

- [Testing Kit CLI Commands](testing-kit-cli-commands.md) - How to test commands
- [Kit CLI Push Down Pattern](push-down-pattern.md) - When to create commands
- [Kit CLI Commands](cli-commands.md) - How to build commands
