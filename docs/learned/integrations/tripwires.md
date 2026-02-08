---
title: Integrations Tripwires
read_when:
  - "working on integrations code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from integrations/*.md frontmatter -->

# Integrations Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before assuming Codex JSONL uses same format as Claude stream-json** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: item.completed with flattened item fields. See codex-jsonl-format.md.

**CRITICAL: Before assuming Codex custom prompts are the current approach** → Read [Codex Skills System](codex/codex-skills-system.md) first. Custom prompts (~/.codex/prompts/\*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead.

**CRITICAL: Before looking for session_id in Codex JSONL** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only.
