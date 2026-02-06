---
title: Research Documentation Integration with Objectives
read_when:
  - "creating research documentation during objective work"
  - "linking learned docs to objective issues"
  - "working with objective research phases"
  - "documenting discoveries from objective investigations"
last_audited: "2026-02-05"
audit_result: edited
---

# Research Documentation Integration with Objectives

When working on objectives that involve research phases, create learned documentation to capture discoveries and link it bidirectionally to the objective issue.

## When to Create Research Documentation

Create learned documentation during objectives when:

1. **You discover architectural patterns** worth documenting for future work
2. **You encounter tripwires** that should be codified
3. **You learn integration patterns** between systems
4. **You document mental models** for complex domains

Not every objective needs documentation - only create it when you discover reusable knowledge.

## When NOT to Create Documentation

Don't create documentation for:

- **One-time fixes**: Bugs specific to this objective
- **Temporary workarounds**: Things you plan to change
- **Speculative patterns**: Patterns not yet proven in practice
- **Obvious patterns**: Things well-covered by existing docs or common knowledge

Only document reusable knowledge that will help future work.

## Documentation Creation Workflow

1. **Identify the category** - See [Guide](../guide.md) for category descriptions
2. **Write with proper frontmatter** - See [Generated Files Architecture](../architecture/generated-files.md) for schema
3. **Run `erk docs sync`** to regenerate indexes and tripwires
4. **Verify** the doc appears in the appropriate category index

## Objective Linking Workflow

Create bidirectional links between objectives and documentation:

1. **In the objective issue**: Add a "Learned Documentation" section listing docs produced
2. **In the documentation**: Reference the objective that prompted the discovery in a Context section

## Integration with Learn Workflow

If the objective produces a PR, extract additional documentation via the learn workflow after the PR merges. See [Learn Workflow](../planning/learn-workflow.md) for details. Note: `erk learn` takes an **issue number** (the plan issue), not a PR number.

## Related Documentation

- [Generated Files Architecture](../architecture/generated-files.md) - Frontmatter schema and sync process
- [Guide](../guide.md) - Documentation category descriptions
- [Learn Workflow](../planning/learn-workflow.md) - Automated documentation extraction
