---
title: PR Footer Format Validation
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
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

## Why Strict Validation?

- **Reliable parsing** - CLI tools extract PR number without fragile regex; format changes detected immediately
- **Consistent experience** - All PRs use identical footer format; `erk pr checkout` works predictably
- **Forward compatibility** - When footer format changes, old PRs remain parseable; migration is explicit

## CRITICAL: Generator/Parser/Validator Sync

If you modify the generator to change footer format, you MUST also update:

1. **Parser** - Handle both old and new formats during transition
2. **Validator** - Accept both formats temporarily
3. **Migration plan** - Update old PRs or document backward compatibility

The validation logic lives in PR metadata parsing code (likely in `src/erk/cli/commands/pr/`).

## Migration Strategy

When changing footer format:

1. **Phase 1: Add new format support** - Parser accepts both old and new
2. **Phase 2: Update generator** - New PRs use new format
3. **Phase 3: Migration** - Optionally update existing PRs (or leave them)
4. **Phase 4: Deprecate old format** (if desired) - Remove old format support after grace period

**NEVER break existing PRs** - Old PRs should continue to work even after format changes.

## Troubleshooting

### "Invalid PR footer format" Error

1. Check for extra/missing whitespace
2. Verify comment text is exactly `# Checkout this PR`
3. Ensure gh command is exactly `gh pr checkout <number>`
4. Check for missing HTML comments (`<!-- erk:pr-footer -->`, `<!-- /erk:pr-footer -->`)

### Parser Fails to Extract PR Number

1. Print the raw footer section to see what parser receives
2. Check regex pattern matches the actual gh command format
3. Verify validation rules match generation logic

## Related Documentation

- [PR Operations](../pr-operations/pr-operations.md) - Complete PR workflow
- [PR Metadata Format](../pr-operations/pr-metadata-format.md) - Full metadata specification
