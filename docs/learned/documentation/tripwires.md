---
title: Documentation Tripwires
read_when:
  - "working on documentation code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from documentation/*.md frontmatter -->

# Documentation Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a code block longer than a few lines to a learned doc** → Read [Stale Code Blocks Are Silent Bugs](stale-code-blocks-are-silent-bugs.md) first. Check if this falls under the One Code Rule exceptions (data formats, third-party APIs, anti-patterns, I/O examples). If not, use a source pointer.

**CRITICAL: Before adding prettier-ignore to docs/learned/** → Read [Markdown Authoring and Prettier Interactions](markdown-and-prettier.md) first. prettier-ignore is almost never needed in docs. If Prettier is mangling your content, the structure may need rethinking rather than suppression.

**CRITICAL: Before assuming the verbatim copy prohibition only applies to Python** → Read [Language Scope Auditing](language-scope-auditing.md) first. Assuming the verbatim copy prohibition only applies to Python

**CRITICAL: Before bulk deleting documentation files** → Read [Documentation Audit Methodology](audit-methodology.md) first. After bulk deletions, run 'erk docs sync' to fix broken cross-references.

**CRITICAL: Before classifying constants or defaults in prose as duplicative** → Read [Documentation Audit Methodology](audit-methodology.md) first. Constants and defaults in prose are HIGH VALUE, not DUPLICATIVE. They provide scannability that code alone cannot — an agent shouldn't need to grep to learn a default value.

**CRITICAL: Before continuing to code after discovering scope is larger than expected** → Read [Planless vs Planning Workflow Decision Framework](when-to-switch-pattern.md) first. Stop and switch to planning. Mid-task warning signs (uncertainty accumulating, scope creeping, multiple valid approaches) indicate you should plan. See when-to-switch-pattern.md.

**CRITICAL: Before copying erk source code into a docs/learned/ markdown file** → Read [Stale Code Blocks Are Silent Bugs](stale-code-blocks-are-silent-bugs.md) first. Verbatim source in docs silently goes stale. Use a source pointer instead — see source-pointers.md.

**CRITICAL: Before copying source code into a docs/learned/ markdown file** → Read [Source Pointers](source-pointers.md) first. Use a source pointer instead. See source-pointers.md for the two-part format (HTML comment + prose reference).

**CRITICAL: Before creating a doc in docs/learned/ without read_when field** → Read [Frontmatter and Tripwire Format](frontmatter-tripwire-format.md) first. read_when is required. Without it, the doc won't appear in any index and agents will never discover it.

**CRITICAL: Before creating a two-option doc where every matrix row favors the same option** → Read [Two-Option Decision Documentation](two-option-template.md) first. That's a best-practice doc, not a decision doc. Don't create false balance.

**CRITICAL: Before declaring canonical authority in a learned doc** → Read [Canonical Authority Declarations](canonical-authority-declarations.md) first. Authority without substance misleads. Only declare canonical authority if the doc is the comprehensive deep-dive, not a summary. If AGENTS.md has the abbreviated version and this doc has the full treatment, that's the right split.

**CRITICAL: Before documenting implementation details that are derivable from code** → Read [Documentation Simplification Patterns](simplification-patterns.md) first. Use source pointers instead of duplication. See simplification-patterns.md for the three simplification patterns.

**CRITICAL: Before documenting non-Python code** → Read [Language Scope Auditing](language-scope-auditing.md) first. Assuming the verbatim copy prohibition only applies to Python

**CRITICAL: Before documenting type definitions without verifying they exist** → Read [Documentation Audit Methodology](audit-methodology.md) first. Type references in docs must match actual codebase types — phantom types are the most common audit finding. Verify with grep before committing.

**CRITICAL: Before including TypeScript/Bash code blocks from erkdesk/ without checking the One Code Rule** → Read [Language Scope Auditing](language-scope-auditing.md) first. Including TypeScript/Bash code blocks from erkdesk/ without checking the One Code Rule

**CRITICAL: Before manually wrapping lines or aligning tables in markdown** → Read [Markdown Authoring and Prettier Interactions](markdown-and-prettier.md) first. Never manually format markdown. Prettier rewrites all formatting on save. Write naturally, then run `make prettier` via devrun.

**CRITICAL: Before never expect agents to self-diagnose knowledge gaps** → Read [Passive Context vs. On-Demand Retrieval](passive-context-vs-retrieval.md) first. use passive context or structural triggers

**CRITICAL: Before rationalizing erkdesk source as 'third-party API pattern'** → Read [Language Scope Auditing](language-scope-auditing.md) first. Rationalizing erkdesk source as 'third-party API pattern' because it uses React/Electron

**CRITICAL: Before restructuring or deleting doc content** → Read [Documentation Simplification Patterns](simplification-patterns.md) first. Run 'erk docs sync' after structural changes to regenerate indexes and fix broken cross-references.

**CRITICAL: Before starting a multi-file change without entering plan mode** → Read [Planless vs Planning Workflow Decision Framework](when-to-switch-pattern.md) first. If the change touches 5+ files or has uncertain approach, plan first. See the decision matrix in when-to-switch-pattern.md.

**CRITICAL: Before two learned docs claiming canonical authority over the same topic** → Read [Canonical Authority Declarations](canonical-authority-declarations.md) first. Contradicts the purpose. Consolidate into one doc, or differentiate scope explicitly (e.g., 'canonical for hook patterns' vs 'canonical for command patterns').

**CRITICAL: Before using line numbers in source pointers** → Read [Source Pointers](source-pointers.md) first. Prefer name-based identifiers (ClassName.method) over line numbers. Names survive refactoring; line numbers go stale silently.

**CRITICAL: Before using this pattern** → Read [Passive Context vs. On-Demand Retrieval](passive-context-vs-retrieval.md) first. skills without explicit invocation triggers perform identically to having no documentation

**CRITICAL: Before writing a decision doc with only prose 'use X when...' bullets** → Read [Two-Option Decision Documentation](two-option-template.md) first. Add a decision matrix table. Tables let agents scan trade-offs at a glance without parsing paragraphs. See two-option-template.md.

**CRITICAL: Before writing a decision doc without concrete examples** → Read [Two-Option Decision Documentation](two-option-template.md) first. Include at least one situation→decision→reasoning example. Abstract criteria are hard to apply without concrete illustrations.

**CRITICAL: Before writing a tripwire as a plain string instead of {action, warning} dict** → Read [Frontmatter and Tripwire Format](frontmatter-tripwire-format.md) first. The validator requires structured dicts with action and warning keys. Plain strings fail validation with 'must be an object'.
