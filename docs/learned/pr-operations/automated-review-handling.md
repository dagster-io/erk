---
title: Handling Automated Review False Positives
read_when:
  - "automated review bot flags an issue in a PR"
  - "deciding whether to fix or investigate a bot complaint"
tripwires:
  - action: "fixing code flagged by automated reviewers without investigation"
    warning: "Automated reviewers can produce false positives. Always investigate by reading the flagged code and running formatters/linters before making changes."
---

# Handling Automated Review False Positives

## Investigation Before Action

When automated review bots (tripwires review, lint bots, etc.) flag issues in a PR, always investigate before acting:

1. **Read the flagged code** — understand the context and intent
2. **Run the project's formatter** — if prettier/linter disagrees with the bot, the formatter is correct
3. **Verify the issue exists** — the complaint may be a false positive from the bot misunderstanding complex structure
4. **If false positive:** Reply to the review thread explaining why the code is correct
5. **If real issue:** Fix it

## Example: Nested Code Block False Positive

In PR #6949, the tripwires review bot flagged a "stray closing backtick" in plan-synthesizer.md. Investigation revealed the backtick was part of a multi-level code block template. Prettier confirmed this by restoring the backtick when the agent initially removed it.

## Related Documentation

- [Prettier as Markdown Formatting Authority](../ci/prettier-fixes.md) — Prettier as source of truth
