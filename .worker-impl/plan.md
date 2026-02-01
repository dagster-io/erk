# Optimize objective-update-with-landed-pr: 4 turns → 2 turns (with Haiku delegation)

## Problem

The `/erk:objective-update-with-landed-pr` command takes 4 LLM turns (~40-60s). Each turn adds ~10-15s of latency. Two of the four turns are unnecessary:

- **Turn 2 (Load Objective Skill)**: The command file already contains the action comment template, status inference rules, and roadmap update instructions. Loading the skill is redundant.
- **Turn 4 (Validate via `erk objective check`)**: This re-fetches the issue from GitHub to re-parse the roadmap. But Claude already has the objective body in context and just edited it — it can count done/pending steps itself.

Additionally, the composition work (Turn 3) is mechanical template-filling that doesn't need a large model.

## Target: 2 turns, with Haiku doing the heavy lifting

| Turn | Model | What happens |
|------|-------|-------------|
| 1 (parent) | Sonnet/Opus | Fetch context via `erk exec objective-update-context`, then delegate |
| 2 (subagent) | **Haiku** | Compose action comment + updated body, write both in parallel, self-validate, close if all done |

The parent model does one turn to fetch context, then spawns a Haiku Task subagent with the full context blob + all templates/rules embedded in the prompt. Haiku does the composition, writes, validation, and optional closing — all in one subagent invocation.

## Changes

### File: `.claude/commands/erk/objective-update-with-landed-pr.md`

1. **Remove Step 1 (Load Objective Skill)** — delete the skill loading step entirely

2. **Rewrite Steps 2-4 as a single "Delegate to Haiku" step** — after fetching context:
   - Spawn a `Task` subagent with `model: haiku`
   - Pass into the prompt: the full JSON context blob, all templates (action comment format, status inference rules, roadmap update rules), and the `--auto-close` flag
   - The subagent prompt should instruct Haiku to:
     a. Analyze which steps the PR completed
     b. Compose the action comment (using the template already in the command)
     c. Compose the updated objective body (roadmap table edits + Current Focus update)
     d. Execute both writes in parallel (`gh issue comment` + `erk exec update-issue-body`)
     e. Self-validate: count done/pending/skipped/blocked steps from the body it just composed
     f. If all steps done/skipped + `--auto-close`: also run `gh issue close`
     g. If all steps done/skipped without `--auto-close`: report back that user should be asked
     h. Otherwise: report next focus

3. **Keep the command self-contained** — all templates, status inference rules, and format guidance stay in the command file and get passed into the subagent prompt

## Verification

- Run `/erk:objective-update-with-landed-pr` on a real objective and confirm it completes in ~2 parent turns
- Verify the action comment and body update are correct
- Verify auto-close works when all steps are complete
- Compare wall-clock time against the old 4-turn approach