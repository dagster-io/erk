---
title: Integrations Tripwires
read_when:
  - "working on integrations code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from integrations/*.md frontmatter -->

# Integrations Tripwires

Rules triggered by matching actions in code.

**adding <code> inside <summary> elements in PR bodies** → Read [Graphite PR Rendering Quirks](graphite-rendering.md) first. Graphite does not render <code> inside <summary> elements — it displays the raw HTML. Use plain text instead. GitHub renders it correctly, so test on graphite.dev specifically.

**adding a force-include entry in pyproject.toml without updating codex_portable.py** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. The portability registry and pyproject.toml force-include must stay in sync. A skill mapped to erk/data/codex/ must appear in codex_portable_skills().

**adding a new Codex event type without updating the parser** → Read [Codex Integration](codex-integration.md) first. All Codex event types must be handled in parse_codex_jsonl_line(). See codex-integration.md.

**adding a skill to codex_portable_skills() without verifying it works outside Claude Code** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. Portable skills must not use hooks, TodoWrite, EnterPlanMode, AskUserQuestion, or session log paths. Check against the portability classification table before adding.

**assuming Codex JSONL uses same format as Claude stream-json** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Completely different formats. Claude uses type: assistant/user/result with nested message.content[]. Codex uses type: thread.started/turn._/item._ with flattened item fields. See this document.

**assuming Codex custom prompts are the current approach** → Read [Codex Skills System](codex/codex-skills-system.md) first. Custom prompts (~/.codex/prompts/\*.md) are the older mechanism, deprecated in favor of skills. Target .codex/skills/ instead.

**assuming all erk skills are portable to Codex** → Read [Codex Skills System](codex/codex-skills-system.md) first. Only skills in codex_portable_skills() are portable. Skills that depend on Claude-specific features (hooks, session logs, commands) are in claude_only_skills().

**closing a <details> block without a blank line after </details>** → Read [Graphite PR Rendering Quirks](graphite-rendering.md) first. Graphite requires a blank line after </details> for proper spacing. Without it, the following content runs up against the collapsed section.

**creating a .codex/ directory in the erk repo** → Read [Bundled Artifact Portability](bundled-artifacts.md) first. There is no .codex/ directory in the erk repo. All skills live in .claude/skills/ regardless of portability. The build and sync systems handle remapping.

**installing skills only to .claude/skills/ when Codex support is needed** → Read [Codex Skills System](codex/codex-skills-system.md) first. Erk has a dual-target architecture. See get_bundled_codex_dir() in artifacts/paths.py and codex_portable_skills() in codex_portable.py for the portability registry.

**looking for session_id in Codex JSONL events** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Codex JSONL does not include session_id in events. The thread_id is provided in the thread.started event only — you must capture it from that first event and carry it forward.

**parsing item fields as nested objects** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. Codex uses Rust #[serde(flatten)] — item type-specific fields appear as siblings of id and type within the item object, not in a nested sub-object.

**passing cwd as subprocess kwarg for codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Unlike Claude (which uses subprocess cwd=), Codex requires an explicit --cd flag. Forgetting this means the agent runs in the wrong directory.

**putting Closes keyword in PR title or commit message** → Read [Issue-PR Closing Integration](issue-pr-closing-integration.md) first. GitHub only processes closing keywords in the PR body. Title and commit message references are ignored.

**resolving issue number from a single source without checking for mismatches** → Read [Issue-PR Closing Integration](issue-pr-closing-integration.md) first. Both .impl/issue.json and branch name may contain issue numbers. If both exist, they must agree — otherwise the pipeline could silently close the wrong issue.

**reusing ClaudePromptExecutor parsing logic for Codex** → Read [Codex CLI JSONL Output Format](codex/codex-jsonl-format.md) first. The two formats share almost nothing structurally. A CodexPromptExecutor needs its own parser — don't parameterize the existing Claude parser.

**using --ask-for-approval with codex exec** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. codex exec hardcodes approval to Never. Only the TUI supports --ask-for-approval. This means exec and TUI need different flag sets for the same PermissionMode.

**using --output-format with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Codex has no --output-format. Use --json (boolean flag) for JSONL. Without --json, output goes to terminal. This affects execute_command_streaming() porting.

**using --print or --verbose with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. codex exec is always headless (no --print needed). No --verbose flag exists.

**using --system-prompt or --allowedTools with codex** → Read [Codex CLI Reference for Erk Integration](codex/codex-cli-reference.md) first. Codex has no --system-prompt or --allowedTools. Prepend system prompt to user prompt. Tool restriction is not available — this affects execute_prompt() porting.

**using issue number from .impl/issue.json for a checkout footer** → Read [Issue-PR Closing Integration](issue-pr-closing-integration.md) first. The checkout footer requires the PR number, not the issue number. These are different values — the issue is the plan, the PR is the implementation.
