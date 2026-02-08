---
title: Capabilities Tripwires
read_when:
  - "working on capabilities code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from capabilities/*.md frontmatter -->

# Capabilities Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding workflow files** → Read [Adding Workflow Capabilities](adding-workflows.md) first. Workflows must exist in bundled artifacts path resolved by get_bundled_github_dir()

**CRITICAL: Before capability not appearing in hooks or CLI** → Read [Adding New Capabilities](adding-new-capabilities.md) first. Class MUST be imported AND instantiated in registry.py \_all_capabilities() tuple. Missing registration causes silent failures—class exists but is never discovered.

**CRITICAL: Before creating a new capability type with custom installation logic** → Read [Adding New Capabilities](adding-new-capabilities.md) first. Don't subclass Capability directly unless needed. Use SkillCapability or ReminderCapability for 90% of cases—they handle state management automatically.

**CRITICAL: Before creating a review capability** → Read [Adding Review Capabilities](adding-reviews.md) first. Review definition MUST exist at .github/reviews/{review_name}.md in erk repo root. At runtime, get_bundled_github_dir() resolves this location (src/erk/artifacts/paths.py). Missing source file causes install failure.

**CRITICAL: Before creating a skill capability** → Read [Adding Skill Capabilities](adding-skills.md) first. Bundled content directory must exist or install() silently creates empty skill directory. See silent failure modes below.

**CRITICAL: Before creating workflow capability** → Read [Adding Workflow Capabilities](adding-workflows.md) first. Workflow capabilities extend Capability directly, not a template base class

**CRITICAL: Before importing artifacts.state in workflow capabilities** → Read [Adding Workflow Capabilities](adding-workflows.md) first. Use inline imports for artifacts.state to avoid circular dependencies

**CRITICAL: Before review capability installation fails** → Read [Adding Review Capabilities](adding-reviews.md) first. ReviewCapability has automatic preflight check for code-reviews-system workflow. Install will fail if .github/workflows/code-reviews.yml doesn't exist in target repo. Install code-reviews-system capability first.

**CRITICAL: Before skill not appearing in erk init capability list** → Read [Adding Skill Capabilities](adding-skills.md) first. MUST import class AND add instance to registry.py \_all_capabilities() tuple. Import alone is not sufficient.
