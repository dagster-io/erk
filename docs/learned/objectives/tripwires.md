---
title: Objectives Tripwires
read_when:
  - "working on objectives code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from objectives/*.md frontmatter -->

# Objectives Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before creating a new roadmap data type without using frozen dataclass** → Read [Roadmap Parser API Reference](roadmap-parser-api.md) first. RoadmapStep and RoadmapPhase are frozen dataclasses. New roadmap types must follow this pattern.

**CRITICAL: Before creating or modifying roadmap step IDs** → Read [Roadmap Parser](roadmap-parser.md) first. Step IDs should use plain numbers (1.1, 2.1), not letter format (1A.1, 1B.1).

**CRITICAL: Before implementing roadmap parsing functionality** → Read [Roadmap Parser](roadmap-parser.md) first. The parser is regex-based, not LLM-based. Do not reference LLM inference.

**CRITICAL: Before inferring status from PR column when explicit status is set** → Read [Roadmap Status System](roadmap-status-system.md) first. Explicit status values (done, in-progress, pending, blocked, skipped) always take priority over PR-based inference. Only '-' or empty values trigger PR-based inference.

**CRITICAL: Before manually parsing objective roadmap markdown** → Read [objective-roadmap-check Command](objective-roadmap-check.md) first. Use `erk exec objective-roadmap-check` command. It handles regex patterns for phase headers, table columns, status inference, and validation.

**CRITICAL: Before modifying roadmap validation without updating this document** → Read [Roadmap Validation Rules](roadmap-validation.md) first. Keep this document in sync with validation logic in objective_roadmap_shared.py and objective_roadmap_update.py.

**CRITICAL: Before treating status as a single-source value** → Read [Roadmap Status System](roadmap-status-system.md) first. Status resolution uses a two-tier system: explicit values first, then PR-based inference. Always check both the Status and PR columns.

**CRITICAL: Before using full-body update for single-cell changes** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-roadmap-step) to preserve other cells and avoid race conditions.

**CRITICAL: Before using surgical update for complete table rewrites** → Read [Roadmap Mutation Patterns](roadmap-mutation-patterns.md) first. Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr).
