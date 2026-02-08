---
title: Reviews Tripwires
read_when:
  - "working on reviews code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from reviews/*.md frontmatter -->

# Reviews Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a new untestable file category** → Read [Test Coverage Review Agent](test-coverage-agent.md) first. New categories must align with the 5-layer test architecture. Only files in Layers 0-2 qualify. If the file contains any business logic (Layer 3+), it requires tests regardless of how thin the logic appears.

**CRITICAL: Before creating a new review without checking if existing reviews can be extended** → Read [Review Development Guide](development.md) first. Before creating a new review, check if an existing review type can handle the new checks. See the review types taxonomy for the decision framework.

**CRITICAL: Before creating a separate GitHub Actions workflow file for a new review** → Read [Review Development Guide](development.md) first. Reviews use convention-based discovery from a single workflow. Drop a markdown file in .github/reviews/ — do NOT create a new .yml workflow.

**CRITICAL: Before flagging code as untested in PR review** → Read [Test Coverage Review Agent](test-coverage-agent.md) first. Check if the file is legitimately untestable first. The 5-layer architecture defines which layers need tests — Layers 0-2 (CLI wrappers, type-only files, ABCs) are excluded. See .github/reviews/test-coverage.md for the full detection logic.
