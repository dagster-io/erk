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

**CRITICAL: Before adding a force-include entry in pyproject.toml without updating codex_portable.py** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. The portability registry and pyproject.toml force-include must stay in sync. A skill mapped to erk/data/codex/ must appear in codex_portable_skills().

**CRITICAL: Before adding a skill to codex_portable_skills() without verifying it works outside Claude Code** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. Portable skills must not use hooks, TodoWrite, EnterPlanMode, AskUserQuestion, or session log paths. Check against the portability classification table before adding.

**CRITICAL: Before assuming Codex JSONL uses same format as Claude stream-json** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: item.completed with flattened item fields. See codex-jsonl-format.md.

**CRITICAL: Before assuming Codex custom prompts are the current approach** → Read [Codex Skills System](codex/codex-skills-system.md) first. Custom prompts (~/.codex/prompts/\*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead.

**CRITICAL: Before creating a .codex/ directory in the erk repo** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. There is no .codex/ directory in the erk repo. All skills live in .claude/skills/ regardless of portability. The build and sync systems handle remapping.

**CRITICAL: Before looking for session_id in Codex JSONL** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only.

**CRITICAL: Before passing cwd as subprocess kwarg for codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Unlike Claude (which uses subprocess cwd=), Codex requires an explicit --cd flag. Forgetting this means the agent runs in the wrong directory.

**CRITICAL: Before using --ask-for-approval with codex exec** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. codex exec hardcodes approval to Never. Only the TUI supports --ask-for-approval. This means exec and TUI need different flag sets for the same PermissionMode.

**CRITICAL: Before using --output-format with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Codex has no --output-format. Use --json (boolean flag) for JSONL. Without --json, output goes to terminal. This affects execute_command_streaming() porting.

**CRITICAL: Before using --print or --verbose with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. codex exec is always headless (no --print needed). No --verbose flag exists.

**CRITICAL: Before using --system-prompt or --allowedTools with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Codex has no --system-prompt or --allowedTools. Prepend system prompt to user prompt. Tool restriction is not available — this affects execute_prompt() porting.
