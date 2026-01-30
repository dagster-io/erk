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

**CRITICAL: Before manually parsing objective roadmap markdown** → Read [objective-roadmap-check Command](objective-roadmap-check.md) first. Use `erk exec objective-roadmap-check` command. It handles regex patterns for phase headers, table columns, status inference, and validation.

**CRITICAL: Before modifying roadmap validation without updating this document** → Read [Roadmap Validation Rules](roadmap-validation.md) first. Keep this document in sync with validation logic in objective_roadmap_shared.py and objective_roadmap_update.py.
