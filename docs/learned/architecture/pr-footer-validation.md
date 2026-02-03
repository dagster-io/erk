---
title: PR Footer Format Validation
tripwires:
  - action: "modifying PR footer format validation"
    warning: "Update generator, parser, AND validator in sync. Old PRs must remain parseable during migration. Add support for new format before deprecating old format."
read_when:
  - "Working with PR metadata footer format"
  - "Modifying PR checkout footer generation"
  - "Debugging PR footer validation errors"
---

# PR Footer Format Validation

## Overview

Pull request bodies contain a structured footer with metadata that enables CLI operations like `erk pr checkout`. The footer format is strictly validated to ensure reliable parsing.

## Footer Format

### Standard Format

````markdown
<!-- erk:pr-footer -->

```bash
# Checkout this PR
gh pr checkout 1234
```
````

<!-- /erk:pr-footer -->

````

**Components:**

1. **Opening comment** - `<!-- erk:pr-footer -->` marks the start
2. **Code fence** - Markdown code block with `bash` language tag
3. **Comment line** - `# Checkout this PR` (exactly this text)
4. **gh command** - `gh pr checkout <number>` (exactly this format)
5. **Closing comment** - `<!-- /erk:pr-footer -->` marks the end

### Validation Rules

The validation enforces:

- **Opening marker** - Must be exactly `<!-- erk:pr-footer -->`
- **Code fence** - Must use triple backticks with `bash` language tag
- **Comment line** - Must be `# Checkout this PR` (no variations)
- **gh command** - Must be `gh pr checkout <number>` where `<number>` is the PR number
- **Closing marker** - Must be exactly `<!-- /erk:pr-footer -->`
- **Spacing** - Exact whitespace between components

### Why Strict Validation?

**Reliable parsing:**

- CLI tools can extract the PR number without fragile regex
- Format changes are detected immediately, not silently misinterpreted
- Users get clear error messages instead of mysterious failures

**Consistent experience:**

- All PRs use identical footer format
- Tools like `erk pr checkout` work predictably across all PRs

**Forward compatibility:**

- When footer format changes, old PRs remain parseable
- Validation ensures migration is explicit, not implicit

## Code Reference

The validation logic lives in PR metadata parsing code:

- **Parser**: Extracts PR number from footer (likely in `src/erk/cli/commands/pr/`)
- **Validator**: Ensures footer matches expected format before parsing
- **Generator**: Creates footer when creating/updating PRs

**CRITICAL:** If you modify the generator to change footer format, you MUST also update:

1. **Parser** - Handle both old and new formats during transition
2. **Validator** - Accept both formats temporarily
3. **Migration plan** - Update old PRs or document backward compatibility

## Examples

### Valid Footer

```markdown
<!-- erk:pr-footer -->
```bash
# Checkout this PR
gh pr checkout 5678
````

<!-- /erk:pr-footer -->

````

### Invalid Footers

**Wrong comment text:**

```markdown
<!-- erk:pr-footer -->
```bash
# Check out this PR (extra space breaks validation)
gh pr checkout 5678
````

<!-- /erk:pr-footer -->

````

**Wrong gh command format:**

```markdown
<!-- erk:pr-footer -->
```bash
# Checkout this PR
gh pr checkout https://github.com/org/repo/pull/5678  (URL not allowed)
````

<!-- /erk:pr-footer -->

````

**Missing markers:**

```markdown
```bash
# Checkout this PR
gh pr checkout 5678
````

````

## Common Operations

### Extract PR Number from Footer

```python
def extract_pr_number_from_footer(pr_body: str) -> int | None:
    """Extract PR number from validated footer.

    Returns:
        PR number if footer is valid and present, None otherwise
    """
    # Find footer block
    if "<!-- erk:pr-footer -->" not in pr_body:
        return None

    # Extract code block content
    # ... (parsing logic)

    # Validate format
    if not _validate_footer_format(footer_content):
        return None

    # Extract number from: gh pr checkout <number>
    match = re.match(r"gh pr checkout (\d+)", command_line)
    if match:
        return int(match.group(1))

    return None
````

### Generate Footer

````python
def generate_pr_footer(pr_number: int) -> str:
    """Generate PR footer with checkout command.

    Args:
        pr_number: The PR number to include in checkout command

    Returns:
        Formatted footer block
    """
    return f"""<!-- erk:pr-footer -->
```bash
# Checkout this PR
gh pr checkout {pr_number}
````

<!-- /erk:pr-footer -->"""

````

### Validate Footer

```python
def validate_pr_footer(pr_body: str) -> bool:
    """Check if PR body contains valid footer.

    Returns:
        True if footer is present and valid, False otherwise
    """
    # Extract footer section
    # ... (extraction logic)

    # Validate structure
    required_components = [
        "<!-- erk:pr-footer -->",
        "```bash",
        "# Checkout this PR",
        "gh pr checkout",
        "```",
        "<!-- /erk:pr-footer -->"
    ]

    for component in required_components:
        if component not in footer_section:
            return False

    return True
````

## Migration Strategy

When changing footer format:

1. **Phase 1: Add new format support** - Parser accepts both old and new
2. **Phase 2: Update generator** - New PRs use new format
3. **Phase 3: Migration** - Optionally update existing PRs (or leave them)
4. **Phase 4: Deprecate old format** (if desired) - Remove old format support after grace period

**NEVER break existing PRs** - Old PRs should continue to work even after format changes.

## Troubleshooting

### "Invalid PR footer format" Error

**Cause:** Footer doesn't match validation rules.

**Fix:**

1. Check for extra/missing whitespace
2. Verify comment text is exactly `# Checkout this PR`
3. Ensure gh command is exactly `gh pr checkout <number>`
4. Check for missing HTML comments (`<!-- erk:pr-footer -->`, `<!-- /erk:pr-footer -->`)

### Parser Fails to Extract PR Number

**Cause:** Footer is malformed or validation is too strict.

**Debug:**

1. Print the raw footer section to see what parser receives
2. Check regex pattern matches the actual gh command format
3. Verify validation rules match generation logic

## Related Documentation

- [PR Operations](../pr-operations/pr-operations.md) - Complete PR workflow
- [PR Metadata Format](../pr-operations/pr-metadata-format.md) - Full metadata specification
- [GitHub CLI Patterns](github-cli-patterns.md) - gh command usage patterns
