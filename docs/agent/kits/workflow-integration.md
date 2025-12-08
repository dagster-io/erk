---
title: GitHub Actions Workflow Integration
read_when:
  - "integrating kit CLI commands with GitHub Actions workflows"
  - "calling kit CLI from CI/CD pipelines"
  - "parsing JSON output in GitHub Actions"
  - "handling errors gracefully in workflow automation"
---

# GitHub Actions Workflow Integration

Patterns for calling kit CLI commands from GitHub Actions workflows with proper JSON parsing, error handling, and step orchestration.

## Overview

Kit CLI commands are designed for both human and machine consumption. When integrated with GitHub Actions:

- Commands return structured JSON for reliable parsing
- Exit codes are 0 even for errors (graceful degradation)
- Output is captured in workflow step outputs for downstream steps
- Errors are handled with conditional step execution

## Core Integration Patterns

### Pattern 1: JSON Output to Step Outputs

**Use for**: Passing data between workflow steps

Kit CLI commands output JSON that can be parsed with `jq` and stored in `$GITHUB_OUTPUT`:

```yaml
- name: Detect trunk branch
  id: trunk
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk detect-trunk-branch)
    echo "trunk_branch=$(echo "$result" | jq -r '.trunk_branch')" >> $GITHUB_OUTPUT

- name: Use trunk branch in later step
  run: |
    echo "Trunk branch is: ${{ steps.trunk.outputs.trunk_branch }}"
```

**Key elements**:

- Capture command output in variable: `result=$(...)`
- Parse JSON with `jq`: `jq -r '.field_name'`
- Store in step outputs: `>> $GITHUB_OUTPUT`
- Reference in later steps: `${{ steps.step_id.outputs.output_name }}`

### Pattern 2: Conditional Execution Based on Success Field

**Use for**: Running downstream steps only on success

Kit CLI commands include a `success` boolean field:

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

- name: Implement plan (only if worker-impl succeeded)
  if: steps.worker_impl.outputs.worker_impl_success == 'true'
  run: |
    claude --print "/erk:plan-implement"
```

**Key elements**:

- Extract success field: `jq -r '.success'`
- Store as output: `echo "worker_impl_success=$success" >> $GITHUB_OUTPUT`
- Conditional execution: `if: steps.step_id.outputs.success == 'true'`
- String comparison: Use `'true'`, not boolean `true`

### Pattern 3: Error Handling with set +e

**Use for**: Preventing workflow failures while capturing status

```yaml
- name: Implement extraction plan
  id: implement
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
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

- name: Handle failure case
  if: steps.implement.outputs.implementation_success == 'false'
  run: |
    echo "Implementation failed, posting comment..."
```

**Key elements**:

- `set +e`: Continue on error
- Capture exit code: `if [ $? -eq 0 ]`
- Always exit 0: `exit 0` at end
- Check result in later steps

### Pattern 4: Multi-Value Output Extraction

**Use for**: Extracting multiple fields from JSON response

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
    echo "success=$(echo "$result" | jq -r '.success')" >> $GITHUB_OUTPUT
```

**Alternative: Store entire JSON output**:

```yaml
- name: Get session metadata
  id: metadata
  run: |
    result=$(dot-agent run erk get-session-metadata "$SESSION_ID")
    # Store entire JSON (escape properly)
    echo "metadata<<EOF" >> $GITHUB_OUTPUT
    echo "$result" >> $GITHUB_OUTPUT
    echo "EOF" >> $GITHUB_OUTPUT

- name: Parse metadata in later step
  run: |
    metadata='${{ steps.metadata.outputs.metadata }}'
    session_id=$(echo "$metadata" | jq -r '.session_id')
    branch=$(echo "$metadata" | jq -r '.branch')
```

### Pattern 5: Sourcing Environment for uv Tools

**Use for**: Ensuring uv-installed tools are in PATH

```yaml
- name: Install tools
  run: |
    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env

    # Install erk via uv tool
    uv tool install --from ./packages/dot-agent-kit dot-agent-kit
    uv tool install --from . --with ./packages/dot-agent-kit erk

- name: Use erk CLI
  run: |
    source $HOME/.cargo/env  # Required in each step
    result=$(dot-agent run erk detect-trunk-branch)
    echo "Result: $result"
```

**Key elements**:

- Source environment: `source $HOME/.cargo/env`
- Required in EVERY step that uses uv tools
- Tools installed via `uv tool install` go to `~/.local/bin`

## Complete Workflow Example

This example shows a full GitHub Actions workflow integrating kit CLI commands:

```yaml
name: Implement Extraction Plan
run-name: "Implement Extraction: #${{ github.event.issue.number }}"

on:
  issues:
    types: [opened, labeled]

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
      # =================================================================
      # PHASE 1: SETUP
      # =================================================================
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup tools
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          source $HOME/.cargo/env

          uv tool install --from ./packages/dot-agent-kit dot-agent-kit
          uv tool install --from . --with ./packages/dot-agent-kit erk

          dot-agent kit install erk

      - name: Configure git
        run: |
          git config user.name "erk-bot"
          git config user.email "erk-bot@users.noreply.github.com"

      # =================================================================
      # PHASE 2: DETECT TRUNK AND CREATE BRANCH
      # =================================================================
      - name: Detect trunk branch
        id: trunk
        run: |
          source $HOME/.cargo/env
          result=$(dot-agent run erk detect-trunk-branch)
          echo "trunk_branch=$(echo "$result" | jq -r '.trunk_branch')" >> $GITHUB_OUTPUT

      - name: Create extraction branch
        id: branch
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          source $HOME/.cargo/env
          result=$(dot-agent run erk create-extraction-branch \
            --issue-number "$ISSUE_NUMBER" \
            --trunk-branch "${{ steps.trunk.outputs.trunk_branch }}")
          echo "branch_name=$(echo "$result" | jq -r '.branch_name')" >> $GITHUB_OUTPUT

      # =================================================================
      # PHASE 3: CREATE IMPLEMENTATION FOLDER
      # =================================================================
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

      # =================================================================
      # PHASE 4: IMPLEMENTATION
      # =================================================================
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

      # =================================================================
      # PHASE 5: CREATE PR
      # =================================================================
      - name: Create PR with documentation changes
        id: submit
        if: steps.implement.outputs.implementation_success == 'true'
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          if [ -z "$(git status --porcelain)" ]; then
            echo "has_changes=false" >> $GITHUB_OUTPUT
            exit 0
          fi

          echo "has_changes=true" >> $GITHUB_OUTPUT

          claude --print \
            --model claude-sonnet-4-5-20250929 \
            --output-format stream-json \
            --dangerously-skip-permissions \
            --verbose \
            "/git:pr-push Documentation extraction from issue #$ISSUE_NUMBER"

          BRANCH_NAME="${{ steps.branch.outputs.branch_name }}"
          PR_URL=$(gh pr view "$BRANCH_NAME" --json url -q '.url' 2>/dev/null || echo "")
          echo "pr_url=$PR_URL" >> $GITHUB_OUTPUT

      # =================================================================
      # PHASE 6: POST COMMENTS
      # =================================================================
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

      - name: Post failure comment
        if: failure()
        env:
          GH_TOKEN: ${{ github.token }}
          ISSUE_NUMBER: ${{ github.event.issue.number }}
        run: |
          source $HOME/.cargo/env
          dot-agent run erk post-extraction-comment \
            --issue-number "$ISSUE_NUMBER" \
            --status failed \
            --workflow-run-url "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
```

## JSON Parsing Patterns

### Basic Field Extraction

```bash
result=$(dot-agent run erk command)
field_value=$(echo "$result" | jq -r '.field_name')
```

### Nested Field Extraction

```bash
result=$(dot-agent run erk command)
nested_value=$(echo "$result" | jq -r '.parent.child.field')
```

### Array Element Extraction

```bash
result=$(dot-agent run erk command)
first_item=$(echo "$result" | jq -r '.items[0].name')
```

### Boolean Field Extraction

```bash
result=$(dot-agent run erk command)
success=$(echo "$result" | jq -r '.success')  # Returns "true" or "false" as string

if [ "$success" = "true" ]; then
  echo "Success!"
fi
```

### Handling Missing Fields

```bash
result=$(dot-agent run erk command)
# Use // for default value if field is null
field_value=$(echo "$result" | jq -r '.field_name // "default"')
```

### Checking for Success Before Parsing

```bash
result=$(dot-agent run erk command)

# Check if command succeeded
if ! echo "$result" | jq -e '.success' > /dev/null 2>&1; then
  error_msg=$(echo "$result" | jq -r '.message // "Unknown error"')
  echo "Error: $error_msg"
  exit 1
fi

# Safe to parse other fields now
value=$(echo "$result" | jq -r '.data.value')
```

## Error Handling Patterns

### Pattern 1: Fail Early on Critical Errors

```yaml
- name: Critical setup step
  run: |
    source $HOME/.cargo/env
    result=$(dot-agent run erk critical-setup)

    if ! echo "$result" | jq -e '.success' > /dev/null; then
      error_msg=$(echo "$result" | jq -r '.message')
      echo "::error::Critical setup failed: $error_msg"
      exit 1  # Stop workflow
    fi
```

### Pattern 2: Continue on Optional Failures

```yaml
- name: Optional enhancement
  continue-on-error: true
  run: |
    source $HOME/.cargo/env
    dot-agent run erk optional-enhancement
```

### Pattern 3: Capture Failure and Post-Process

```yaml
- name: Try operation
  id: operation
  run: |
    set +e
    source $HOME/.cargo/env
    result=$(dot-agent run erk operation)

    success=$(echo "$result" | jq -r '.success // "false"')
    echo "operation_success=$success" >> $GITHUB_OUTPUT

    if [ "$success" = "false" ]; then
      error_type=$(echo "$result" | jq -r '.error_type')
      error_msg=$(echo "$result" | jq -r '.message')
      echo "error_type=$error_type" >> $GITHUB_OUTPUT
      echo "error_message=$error_msg" >> $GITHUB_OUTPUT
    fi

    exit 0

- name: Handle specific error types
  if: steps.operation.outputs.operation_success == 'false'
  run: |
    error_type="${{ steps.operation.outputs.error_type }}"

    case "$error_type" in
      "not_found")
        echo "Resource not found, creating it..."
        ;;
      "validation_failed")
        echo "Validation failed, posting comment..."
        ;;
      *)
        echo "Unknown error type: $error_type"
        exit 1
        ;;
    esac
```

## Best Practices

### 1. Always Source Environment for uv Tools

```yaml
- name: Any step using erk CLI
  run: |
    source $HOME/.cargo/env  # REQUIRED in every step
    dot-agent run erk command
```

### 2. Use Step IDs and Outputs for Data Flow

```yaml
- name: Generate data
  id: generate # Give step an ID
  run: |
    echo "data=value" >> $GITHUB_OUTPUT

- name: Use data
  run: |
    echo "Data is: ${{ steps.generate.outputs.data }}"
```

### 3. Check Success Before Parsing Other Fields

```yaml
result=$(dot-agent run erk command)

# Check success first
if ! echo "$result" | jq -e '.success' > /dev/null 2>&1; then
  # Handle error case
  exit 1
fi

# Safe to parse other fields
value=$(echo "$result" | jq -r '.data.value')
```

### 4. Use Descriptive Step Names

```yaml
# Good: Clear and specific
- name: Detect trunk branch for worktree creation
  run: |
    # ...

# Bad: Vague
- name: Run command
  run: |
    # ...
```

### 5. Group Related Steps with Comments

```yaml
# =================================================================
# PHASE 1: SETUP AND INITIALIZATION
# =================================================================

- name: Install tools
  run: |
    # ...

- name: Configure environment
  run: |
    # ...

# =================================================================
# PHASE 2: MAIN WORKFLOW
# =================================================================
```

## Common Pitfalls

### ❌ Forgetting to Source Environment

**Bad**:

```yaml
- name: Use erk
  run: |
    dot-agent run erk command  # Will fail: command not found
```

**Good**:

```yaml
- name: Use erk
  run: |
    source $HOME/.cargo/env
    dot-agent run erk command
```

### ❌ Using Boolean Comparison Instead of String

**Bad**:

```yaml
if: steps.check.outputs.success == true # Won't work
```

**Good**:

```yaml
if: steps.check.outputs.success == 'true' # String comparison
```

### ❌ Not Handling JSON Parsing Errors

**Bad**:

```yaml
value=$(echo "$result" | jq -r '.field') # Fails if JSON is malformed
```

**Good**:

```yaml
if ! value=$(echo "$result" | jq -r '.field' 2>&1); then
  echo "::error::Failed to parse JSON: $value"
  exit 1
fi
```

### ❌ Assuming Exit Code 1 for Errors

Kit CLI commands exit with code 0 even on errors:

**Bad**:

```yaml
- name: Run command
  run: |
    dot-agent run erk command
    # Assumes exit code 1 on error - won't happen
```

**Good**:

```yaml
- name: Run command
  run: |
    result=$(dot-agent run erk command)
    if ! echo "$result" | jq -e '.success' > /dev/null; then
      echo "Command failed"
      exit 1
    fi
```

### ❌ Storing Multi-Line Output Without EOF Delimiter

**Bad**:

```yaml
echo "data=$result" >> $GITHUB_OUTPUT # Breaks on multi-line
```

**Good**:

```yaml
echo "data<<EOF" >> $GITHUB_OUTPUT
echo "$result" >> $GITHUB_OUTPUT
echo "EOF" >> $GITHUB_OUTPUT
```

## Debugging Tips

### Enable Verbose Output

```yaml
- name: Debug command
  run: |
    set -x  # Enable command tracing
    source $HOME/.cargo/env
    result=$(dot-agent run erk command)
    echo "Result: $result"
```

### Print Parsed Values

```yaml
- name: Debug parsing
  run: |
    result=$(dot-agent run erk command)
    echo "Raw result: $result"

    success=$(echo "$result" | jq -r '.success')
    echo "Parsed success: $success"

    value=$(echo "$result" | jq -r '.value')
    echo "Parsed value: $value"
```

### Use GitHub Actions Debugging

Enable debug logging in workflow runs:

- Settings → Secrets → Actions → Add secret: `ACTIONS_STEP_DEBUG=true`

## Related Documentation

- [Testing Kit CLI Commands](testing-kit-cli-commands.md) - Unit testing patterns
- [Push-Down Pattern](push-down-pattern.md) - Design philosophy for kit CLI
- [Kit CLI Commands](cli-commands.md) - Building kit CLI commands
