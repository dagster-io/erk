---
title: Code reviews
description: How erk uses tiered AI models to review and resolve PR feedback
---

Erk runs automated code reviews on every pull request. A single GitHub Actions workflow discovers review files, matches them against changed files, and runs each review as a parallel matrix job. The result is inline PR comments and a summary — no manual setup per review.

## The two-phase pattern

Code reviews happen in two phases.

**Phase 1: CI-based detection.** When a PR is opened or updated, cheap models (Haiku) run mechanical checks — style conformance, test coverage gaps, code simplification opportunities. Sonnet handles judgment-heavy reviews like tripwire detection and documentation audits. Each review posts inline comments on specific lines plus a summary comment on the PR.

**Phase 2: Human-steered resolution.** A human reads the flagged issues and decides what to act on. Running `/erk:pr-address` invokes a powerful model that classifies each comment, groups them into ordered batches by complexity, and resolves them under human oversight. Pre-existing issues in moved code are auto-resolved. Complex changes require explicit approval.

## Convention-based discovery

Reviews are markdown files in `.erk/reviews/`. Each file declares a `paths` glob pattern in its frontmatter. The CI workflow runs `erk exec discover-reviews` to match changed PR files against these patterns, then launches matching reviews as parallel GitHub Actions matrix jobs. Adding a new review means dropping a markdown file — no workflow edits needed.

## Model selection

| Review | Model | Rationale |
|--------|-------|-----------|
| Test coverage | Haiku | Mechanical file matching and line counting |
| Dignified Python | Haiku | Pattern matching against a known rule set |
| Code simplifier | Haiku | Structural analysis with clear heuristics |
| Tripwires | Sonnet | Requires reading linked docs and judging exceptions |
| Doc audit | Sonnet | Requires cross-referencing source code against prose |

Haiku reviews run fast and cost little. Sonnet reviews take longer but handle nuance — reading documentation, weighing exceptions, comparing source to claims.

## What reviews check

- **Test coverage**: Flags new source files without corresponding test files.
- **Dignified Python**: Enforces LBYL patterns, frozen dataclasses, absolute imports, and other project conventions.
- **Code simplifier**: Identifies opportunities to reduce complexity — unnecessary abstractions, dead code, redundant logic.
- **Tripwires**: Matches code changes against documented rules (subprocess wrappers, gateway patterns, path handling) and verifies exceptions before flagging.
- **Doc audit**: Checks `docs/learned/` files for verbatim source copies, inaccurate claims, and drift risk.

## What's next

- [Addressing review feedback](/guides/01-addressing-review-feedback/) — resolve PR comments using the pr-address workflow
- [Creating a review](/guides/02-creating-a-review/) — add a new automated review to your project
