<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Objectives Documentation

- **[mutation-patterns.md](mutation-patterns.md)** — creating commands that modify objectives, implementing inference-driven updates, debugging objective corruption
- **[objective-lifecycle.md](objective-lifecycle.md)** — creating or modifying objective lifecycle code, understanding how objectives are created, mutated, and closed, adding new mutation paths to objective roadmaps
- **[objective-roadmap-check.md](objective-roadmap-check.md)** — validating objective roadmap consistency beyond structure, understanding why check command exists separate from parsing, adding new validation checks to objective check
- **[objective-workflows.md](objective-workflows.md)** — duplicating an objective, creating objective from template
- **[research-documentation-integration.md](research-documentation-integration.md)** — deciding whether objective work should produce learned docs, choosing between manual doc capture and the learn workflow during an objective, capturing cross-cutting discoveries from multi-plan investigations
- **[roadmap-format-versioning.md](roadmap-format-versioning.md)** — extending the roadmap table format with new columns, planning backward-compatible parser changes to roadmap tables, understanding the 4-col to 5-col migration
- **[roadmap-mutation-patterns.md](roadmap-mutation-patterns.md)** — deciding between surgical vs full-body roadmap updates, choosing how to update an objective roadmap after a workflow event, understanding race condition risks in roadmap table mutations
- **[roadmap-parser-api.md](roadmap-parser-api.md)** — adding a new consumer of objective_roadmap_shared.py, extending the roadmap data model with new fields, understanding why the shared parser exists separately from its consumers
- **[roadmap-parser.md](roadmap-parser.md)** — understanding how roadmap steps are parsed, working with objective roadmap check or update commands, debugging roadmap parsing issues, using erk objective check or erk exec update-roadmap-step
- **[roadmap-status-system.md](roadmap-status-system.md)** — understanding how objective roadmap status is determined, working with roadmap step status values, debugging unexpected status in an objective roadmap
- **[roadmap-validation.md](roadmap-validation.md)** — debugging roadmap validation errors or check failures, adding new validation rules to objective check or update commands, understanding why validation is split across parser and check command
- **[validation-checks.md](validation-checks.md)** — objective check fails on Check 8, working with legacy objectives, migrating objective formats
- **[validation-patterns.md](validation-patterns.md)** — implementing commands that touch objectives, choosing validation strictness, debugging legacy format errors
