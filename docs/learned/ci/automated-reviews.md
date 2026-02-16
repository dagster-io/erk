---
title: Automated Review Bots
read_when:
  - "understanding PR review automation"
  - "interpreting bot feedback"
---

# Automated Review Bots

## Effectiveness

PR #7124 demonstrates bots catching:

- LBYL violations (try/except for control flow)
- Test coverage gaps
- Format consistency issues

## Bot Behavior

- Bots run multiple times during PR iteration
- Activity logs track each review pass
- Conflicting bot feedback requires human judgment

## Value

Prevents manual review time on mechanical checks, freeing humans for architectural review.
