---
title: GitHub Actions Output Patterns
read_when:
  - "setting outputs in GitHub Actions workflows"
  - "passing data between workflow steps"
  - "handling multi-line content in GITHUB_OUTPUT"
  - "parsing JSON from workflow step outputs"
tripwires:
  - action: "using echo with multi-line content to GITHUB_OUTPUT"
    warning: "Multi-line content requires heredoc syntax with EOF delimiter. Simple echo only works for single-line values."
---

# GitHub Actions Output Patterns

Patterns for setting and consuming step outputs in GitHub Actions workflows using `$GITHUB_OUTPUT`.

## Basic Output Pattern

For single-line values:

```yaml
- name: Set output
  id: my_step
  run: echo "my_value=hello" >> $GITHUB_OUTPUT

- name: Use output
  run: echo "Got: ${{ steps.my_step.outputs.my_value }}"
```

## Multi-Line Content (Heredoc Pattern)

For multi-line content, use heredoc with EOF delimiter:

```yaml
- name: Set multi-line output
  id: rebase
  run: |
    REBASE_OUTPUT=$(some_command_with_multiline_output)
    echo "rebase_output<<EOF" >> "$GITHUB_OUTPUT"
    echo "$REBASE_OUTPUT" >> "$GITHUB_OUTPUT"
    echo "EOF" >> "$GITHUB_OUTPUT"

- name: Use multi-line output
  run: |
    echo "Full output:"
    echo "${{ steps.rebase.outputs.rebase_output }}"
```

The heredoc pattern:

1. Write `key<<EOF` to start
2. Write the content (can span multiple lines)
3. Write `EOF` on its own line to end

## Boolean Outputs

Set boolean-like outputs for conditional steps:

```yaml
- name: Check condition
  id: check
  run: |
    if [ -d ".impl" ]; then
      echo "skip=true" >> $GITHUB_OUTPUT
    else
      echo "skip=false" >> $GITHUB_OUTPUT
    fi

- name: Conditional step
  if: steps.check.outputs.skip != 'true'
  run: echo "Running because skip was not true"
```

Note: All outputs are strings. Use string comparison (`!= 'true'`) not boolean comparison.

## JSON Outputs

For structured data, output JSON and parse in consuming steps:

### Setting JSON Output

```yaml
- name: Create matrix
  id: matrix
  run: |
    MATRIX='{"include":[{"file":"a.py"},{"file":"b.py"}]}'
    echo "matrix=$MATRIX" >> "$GITHUB_OUTPUT"
```

### Consuming JSON Output

```yaml
jobs:
  matrix-job:
    strategy:
      matrix: ${{ fromJson(steps.matrix.outputs.matrix) }}
```

### Parsing JSON in Shell

```yaml
- name: Parse JSON output
  run: |
    RESULT='${{ steps.previous.outputs.json_data }}'
    VALUE=$(echo "$RESULT" | jq -r '.some_field')
    echo "Extracted: $VALUE"
```

## Common Patterns in Erk Workflows

### Capturing Git State

```yaml
- name: Save pre-implementation HEAD
  id: pre_impl
  run: echo "head=$(git rev-parse HEAD)" >> $GITHUB_OUTPUT

- name: Check for changes
  run: |
    if git diff --quiet ${{ steps.pre_impl.outputs.head }}..HEAD; then
      echo "No changes"
    fi
```

### Detecting PR Numbers

```yaml
- name: Get PR info
  id: pr
  run: |
    if [ "${{ github.event_name }}" = "pull_request" ]; then
      echo "pr_number=${{ github.event.pull_request.number }}" >> $GITHUB_OUTPUT
      echo "has_pr=true" >> $GITHUB_OUTPUT
    else
      # For push events, find PR by branch
      pr_number=$(gh api repos/${{ github.repository }}/pulls \
        --jq ".[] | select(.head.ref == \"${{ github.ref_name }}\") | .number" \
        | head -1)
      if [ -n "$pr_number" ]; then
        echo "pr_number=$pr_number" >> $GITHUB_OUTPUT
        echo "has_pr=true" >> $GITHUB_OUTPUT
      else
        echo "has_pr=false" >> $GITHUB_OUTPUT
      fi
    fi
```

### Collecting Job Results

```yaml
- name: Collect failures
  id: failures
  run: |
    echo "format_result=${{ needs.format.result }}" >> $GITHUB_OUTPUT
    echo "lint_result=${{ needs.lint.result }}" >> $GITHUB_OUTPUT
    echo "tests_result=${{ needs.tests.result }}" >> $GITHUB_OUTPUT
```

### Session Capture

```yaml
- name: Capture session info
  id: session
  run: |
    if OUTPUT=$(erk exec capture-session-info --path "$GITHUB_WORKSPACE"); then
      eval "$OUTPUT"
      echo "session_id=$SESSION_ID" >> "$GITHUB_OUTPUT"
      echo "session_file=$SESSION_FILE" >> "$GITHUB_OUTPUT"
    fi
```

## Error Handling

### Exit Code Capture

```yaml
- name: Run with exit code capture
  id: run
  run: |
    set +e  # Don't exit on error
    some_command
    EXIT_CODE=$?
    set -e
    echo "exit_code=$EXIT_CODE" >> $GITHUB_OUTPUT
    if [ $EXIT_CODE -eq 0 ]; then
      echo "success=true" >> $GITHUB_OUTPUT
    else
      echo "success=false" >> $GITHUB_OUTPUT
    fi
```

### Conditional on Success

```yaml
- name: Only if succeeded
  if: steps.run.outputs.success == 'true'
  run: echo "Previous step succeeded"
```

## Best Practices

1. **Always quote variable references** in echo commands to handle special characters
2. **Use double quotes** around `$GITHUB_OUTPUT` for consistency
3. **Prefer explicit booleans** (`true`/`false`) over empty/non-empty
4. **Document output names** when they're consumed by other jobs
5. **Use jq for JSON parsing** - more reliable than shell string manipulation

## Common Mistakes

### Missing Quotes

```yaml
# Wrong - breaks on values with spaces
echo my_value=$SOME_VAR >> $GITHUB_OUTPUT

# Correct
echo "my_value=$SOME_VAR" >> "$GITHUB_OUTPUT"
```

### Newlines in Simple Echo

```yaml
# Wrong - only captures first line
echo "content=$MULTI_LINE_VAR" >> $GITHUB_OUTPUT

# Correct - use heredoc
echo "content<<EOF" >> "$GITHUB_OUTPUT"
echo "$MULTI_LINE_VAR" >> "$GITHUB_OUTPUT"
echo "EOF" >> "$GITHUB_OUTPUT"
```

### Boolean String Comparison

```yaml
# Wrong - comparing to boolean literal
if: steps.check.outputs.skip == true

# Correct - comparing to string
if: steps.check.outputs.skip == 'true'
```

## Related Documentation

- [GitHub Actions Security Patterns](github-actions-security.md) - Security considerations
- [CI Prompt Patterns](prompt-patterns.md) - Working with prompts in CI
- [erk-impl Change Detection](erk-impl-change-detection.md) - Specific change detection patterns
