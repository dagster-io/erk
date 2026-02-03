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

**CRITICAL: Before assuming Codex JSONL uses same format as Claude stream-json** → Read [Codex CLI JSONL Output Format](codex-jsonl-format.md) first. Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: item.completed with flattened item fields. See codex-jsonl-format.md.

**CRITICAL: Before assuming Codex custom prompts are the current approach** → Read [Codex Skills System](codex-skills-system.md) first. Custom prompts (~/.codex/prompts/\*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead.

**CRITICAL: Before looking for session_id in Codex JSONL** → Read [Codex CLI JSONL Output Format](codex-jsonl-format.md) first. Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only.

**CRITICAL: Before using --ask-for-approval with codex exec** → Read [Codex CLI Reference](codex-cli-reference.md) first. codex exec does NOT support --ask-for-approval. It hardcodes approval to Never in headless mode. Only the TUI supports this flag.

**CRITICAL: Before using --output-format with codex** → Read [Codex CLI Reference](codex-cli-reference.md) first. Codex does not have --output-format. Use --json (boolean flag) for JSONL output. Without --json, output goes directly to terminal.

**CRITICAL: Before using --print or --verbose with codex** → Read [Codex CLI Reference](codex-cli-reference.md) first. Codex exec mode is always non-interactive (no --print needed). There is no --verbose flag.

**CRITICAL: Before using --system-prompt or --allowedTools with codex** → Read [Codex CLI Reference](codex-cli-reference.md) first. Codex has no --system-prompt or --allowedTools equivalent. Prepend system prompt to user prompt. Tool restriction is not available.
