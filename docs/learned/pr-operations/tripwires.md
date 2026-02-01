---
title: Pr Operations Tripwires
read_when:
  - "working on pr-operations code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from pr-operations/*.md frontmatter -->

# Pr Operations Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before writing checkout footer with issue number from .impl/issue.json** → Read [Checkout Footer Syntax](checkout-footer-syntax.md) first. Use PR number (from gh pr create), NOT issue number (from .impl/issue.json). Checkout command expects PR number format: 'gh pr checkout <pr-number>'. Issue numbers in checkout footers cause validation errors.
