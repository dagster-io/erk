# Plan Validation Pattern

This document provides reusable guidance for validating plan content structure using kit CLI commands.

## Kit CLI Validation Pattern

Use the `validate-plan-content` kit CLI command to validate plan structure:

```bash
# Validate plan structure
validate_result=$(echo "$plan_content" | erk kit exec erk validate-plan-content)
if ! echo "$validate_result" | jq -e '.valid' > /dev/null; then
    error_msg=$(echo "$validate_result" | jq -r '.error')
    formatted_error=$(erk kit exec erk format-error \
        --brief "Plan content is too minimal or invalid" \
        --details "$error_msg" \
        --action "Provide a more detailed implementation plan" \
        --action "Include specific tasks, steps, or phases" \
        --action "Use headers and lists to structure the plan")
    echo "$formatted_error"
    exit 1
fi
```

## Validation Requirements

The `validate-plan-content` command checks:

- **Minimum length**: Plan must be at least 100 characters
- **Structure**: Must contain headers (# ##) OR numbered lists OR bulleted lists
- **Content**: Not empty or whitespace-only

## JSON Output Format

The validation command returns JSON with this structure:

```json
{
  "valid": true|false,
  "error": null|"error message",
  "details": {
    "length": <integer>,
    "has_headers": true|false,
    "has_lists": true|false
  }
}
```

## Error Handling

When validation fails, use the `format-error` command to generate consistent error messages:

```bash
formatted_error=$(erk kit exec erk format-error \
    --brief "Brief error description" \
    --details "Detailed error context" \
    --action "First suggested action" \
    --action "Second suggested action" \
    --action "Third suggested action (optional)")
echo "$formatted_error"
exit 1
```

## Usage in Commands

### plan-save Command

In `/erk:plan-save`, validation occurs after plan extraction:

1. Extract plan content from `~/.claude/plans/`
2. Validate using `validate-plan-content` kit CLI command
3. If invalid, format error using `format-error` kit CLI command
4. Exit with error if validation fails

### session-plan-enrich Command

In `/erk:session-plan-enrich`, the same validation pattern applies:

1. Extract plan content from `~/.claude/plans/`
2. Validate using `validate-plan-content` kit CLI command
3. If invalid, format error using `format-error` kit CLI command
4. Exit with error if validation fails

## Example: Complete Validation Flow

```bash
# Step 1: Extract plan (command-specific)
plan_content="..."  # Extracted from conversation

# Step 2: Validate plan structure
validate_result=$(echo "$plan_content" | erk kit exec erk validate-plan-content)

# Step 3: Check if validation passed
if ! echo "$validate_result" | jq -e '.valid' > /dev/null; then
    # Step 4: Extract error message
    error_msg=$(echo "$validate_result" | jq -r '.error')

    # Step 5: Format error with context
    formatted_error=$(erk kit exec erk format-error \
        --brief "Plan content is too minimal or invalid" \
        --details "$error_msg" \
        --action "Provide a more detailed implementation plan" \
        --action "Include specific tasks, steps, or phases" \
        --action "Use headers and lists to structure the plan")

    # Step 6: Output error and exit
    echo "$formatted_error"
    exit 1
fi

# Step 7: Proceed with valid plan
echo "Plan validation passed"
# Continue with plan creation workflow...
```

## Benefits

### Consistency

- All plan validation uses the same criteria
- Error messages follow consistent format
- Users get uniform experience across commands

### Testability

- Validation logic is unit-tested
- No inline validation code to maintain
- Kit CLI commands can be tested independently

### Maintainability

- Single source of truth for validation rules
- Easy to update validation criteria
- No duplicate validation logic in agent markdown

## Related Kit CLI Commands

- `validate-plan-content`: Validates plan structure and quality from stdin
- `format-error`: Formats error messages with consistent structure
- `format-success-output`: Formats success output after issue creation
