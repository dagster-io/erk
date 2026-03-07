---
name: refac-cli-push-down
description: Moving mechanical computation from LLM prompts into tested CLI commands. Use when writing or reviewing slash commands with embedded bash, when a skill/command exceeds ~100 lines of procedural steps, when adding parsing/validation/transformation logic to markdown prompts, when debugging flaky embedded scripts, or when refactoring commands to reduce token overhead.
---

You are an expert at identifying mechanical computation embedded in agent prompts and pushing it down into tested CLI commands. This skill documents a proven pattern for reducing prompt complexity, improving reliability, and making agent workflows testable.

## The Pattern

**If it requires understanding meaning, keep it in the agent. If it's mechanical transformation, push it to a CLI command.**

Like database query optimizers that "push down" predicates closer to the data layer for efficiency, this pattern moves computation from LLM prompts to tested code where it belongs.

| Push to CLI Command                                 | Keep in Agent                              |
| --------------------------------------------------- | ------------------------------------------ |
| Parsing/validation (URLs, formats, paths)           | Semantic analysis (summarizing, naming)    |
| Data extraction (JSON/YAML, filtering)              | Content generation (docs, code, messages)  |
| Deterministic operations (file queries, transforms) | Complex reasoning (trade-offs, ambiguity)  |
| Token reduction (compressing, pre-filtering)        | Decision-making (planning, interpretation) |

## Why It Matters

**Token reduction.** Every line of bash, parsing logic, and error handling in a markdown prompt consumes context tokens. Pushing mechanical work to code shrinks prompts by 50-70%, leaving the agent focused on decisions that require judgment.

**Testability.** You cannot unit test bash embedded in markdown. A CLI command is a regular function with pytest coverage, mocked dependencies, and edge case validation. Bugs get caught in CI, not during agent runs.

**Reliability.** Embedded bash varies between shells, lacks type safety, and fails silently on typos. A proper language provides a real execution environment with proper error handling, structured JSON output, and deterministic behavior.

**Composability.** Once logic lives in a CLI command, multiple skills and commands can invoke it. Changes to the logic propagate to all callers without updating markdown files.

## Recognizing Opportunities

A prompt is a candidate for push-down when you spot any of these smells:

- **Inline bash blocks** parsing JSON, extracting fields, or constructing commands
- **Multi-step shell pipelines** (e.g., `gh api ... | jq ... | sed ...`)
- **Conditional logic in markdown** with nested if/else decision trees
- **String manipulation** (regex matching, URL parsing, slug generation)
- **Data transformation** (YAML to JSON, filtering lists, merging objects)
- **Repeated mechanical sequences** duplicated across multiple commands/skills
- **Agent instructions for deterministic work** ("extract the plan number from the URL", "parse the config and find matching entries")
- **Prompt exceeding ~100 lines** of procedural steps (not counting context/explanation)

## The Push-Down Checklist

1. **Identify the mechanical segment.** Find the block of deterministic logic in the prompt. Ask: "Does an LLM add value here, or is it just executing instructions mechanically?"

2. **Define the JSON contract.** Design the input (CLI flags/args) and output (JSON schema) before writing code. The agent will read this JSON, so make it agent-friendly:
   - Include `success: bool` at the top level
   - On failure, include `error` with human-readable `message`
   - Include all data the agent needs for subsequent steps

3. **Create the CLI command.** Write a subcommand in your project's CLI framework (Click, argparse, Typer, or similar). Place it in a dedicated directory for helper commands — e.g., `src/myproject/cli/commands/helpers/`. The command should accept structured input via flags/args and emit JSON to stdout.

   ```python
   # Example with Click
   @click.command()
   @click.option("--repo", required=True)
   @click.option("--json", "as_json", is_flag=True)
   def check_pr_status(*, repo: str, as_json: bool) -> None:
       result = _fetch_and_validate(repo)
       if as_json:
           click.echo(json.dumps(result))
   ```

4. **Write tests first.** Create a test file alongside or in a parallel test directory. Test the happy path, error cases, and edge cases. Mock external dependencies (API calls, file system, subprocess).

   ```python
   def test_check_pr_status_returns_open_prs(fake_github: FakeLocalGitHub) -> None:
       fake_github.add_pr(number=42, state="open", title="Add feature")
       result = invoke_cli(["check-pr-status", "--repo", "myorg/myrepo", "--json"])
       data = json.loads(result.output)
       assert data["success"] is True
       assert len(data["prs"]) == 1
   ```

5. **Register the command.** Add it to the appropriate CLI group so it's discoverable:

   ```python
   # In your CLI group file
   helpers_group.add_command(check_pr_status)
   ```

6. **Update the prompt.** Replace the mechanical block with a single CLI invocation. The prompt should now focus on interpreting the JSON output and making decisions.

7. **Verify token reduction.** Compare before/after line counts. A well-executed push-down reduces the prompt section by 50-70%.

## Examples

### Example A: PR Workflow Simplification

**Before** — a slash command with inline bash to gather PR context:

```markdown
## Step 1: Gather PR Information

Run these commands and parse the output:

1. Get open PRs: `gh pr list --repo {{repo}} --json number,title,state,headRefName`
2. For each PR, check CI status: `gh pr checks {{number}} --repo {{repo}}`
3. Filter to PRs where all checks pass: parse the JSON, extract status fields,
   compare against "pass"/"success", collect matching PR numbers
4. Get review status: `gh api repos/{{owner}}/{{repo}}/pulls/{{number}}/reviews | jq '[.[] | {user: .user.login, state: .state}]'`
5. Combine results into a summary with PR number, title, CI status, and review state
```

**After** — one CLI command returning structured JSON:

```markdown
## Step 1: Gather PR Information

Run: `mytool pr-triage --repo {{repo}} --json`

This returns JSON with `success`, `prs` (each with `number`, `title`, `ci_status`, `reviews`), and `summary`.
```

The 15 lines of bash parsing and jq pipelines became a tested Python command. The agent focuses on deciding which PR to prioritize — the part that actually requires judgment.

### Example B: Config Validation

**Before** — inline YAML parsing and conditional logic in the prompt:

```markdown
## Validate Configuration

1. Read the config file at `config/settings.yaml`
2. Parse the YAML content
3. Check that `database.host` exists and is a valid hostname
4. Check that `database.port` is between 1024 and 65535
5. Check that `auth.provider` is one of: "oauth2", "saml", "local"
6. If `auth.provider` is "oauth2", verify `auth.client_id` and `auth.redirect_uri` exist
7. If any check fails, list all failures with field paths
8. If all checks pass, output the resolved configuration with defaults applied
```

**After** — a single CLI call with a JSON contract:

```markdown
## Validate Configuration

Run: `mytool config validate --file config/settings.yaml --json`

The command returns:

- On success: `{"success": true, "config": {<resolved config with defaults>}}`
- On failure: `{"success": false, "errors": [{"field": "database.port", "message": "..."}]}`

If validation fails, report the errors to the user. If it succeeds, proceed with the resolved config.
```

Eight steps of deterministic validation collapsed into one call. The agent only handles the response — reporting errors or proceeding.

### Example C: Multi-Step Data Pipeline

**Before** — an agent executing sequential shell commands:

```markdown
## Gather Release Notes

1. Fetch commits since last tag: `git log $(git describe --tags --abbrev=0)..HEAD --oneline`
2. Filter to conventional commits: parse each line, match against `feat:`, `fix:`, `docs:` patterns
3. Group by type (features, fixes, docs)
4. For each commit, extract the PR number from the message if present
5. Fetch PR details for each: `gh pr view {{number}} --json title,labels,author`
6. Format as markdown with sections per type, PR links, and author attribution
```

**After** — one command that handles the entire pipeline:

```markdown
## Gather Release Notes

Run: `mytool release-notes --since-last-tag --json`

Returns `{"success": true, "sections": {"features": [...], "fixes": [...], "docs": [...]}, "contributors": [...]}`.

Review the generated sections. Add or edit descriptions where the commit messages are unclear, then format for the changelog.
```

**Anti-pattern to avoid here:** Don't split this into `mytool list-commits`, `mytool classify-commits`, `mytool fetch-pr-details`, `mytool format-notes`. Four commands with intermediate JSON passed between them recreates the same sequential complexity in the prompt. One command that does the full pipeline is simpler for the agent.

## Anti-Patterns

### Over-pushing into scattered commands

Push-down can go too far. When each small task becomes its own CLI command, you get a proliferation of tiny commands that are hard to discover and maintain.

**Rule of thumb:** If the command is under ~30 lines of logic and only called from one place, consider whether it belongs as part of a larger command instead.

### Under-composing outputs

A push-down command that returns minimal JSON forces the agent to make additional calls for related data. Design the output to include everything the agent needs for the next decision.

**Bad:** `{"plan_number": 42}` — agent must now fetch plan details separately.
**Good:** `{"plan_number": 42, "title": "...", "phases": [...], "related_docs": {...}}` — agent can proceed immediately.

### Pushing semantic work

Not everything belongs in code. If the agent needs to understand meaning, summarize, name things, or make judgment calls, that work should stay in the prompt. Push-down is for mechanical transformation, not reasoning.

### Ignoring the JSON contract

CLI commands must return structured JSON with `success: bool`. Without a consistent contract, agents resort to text parsing, which defeats the purpose of push-down.

## Adapting to Your Project

This pattern works with any CLI framework. The key elements are:

- **A dedicated command directory** for helper subcommands (keeps them organized and discoverable)
- **Structured JSON output** with a consistent contract (`success`, `error`, payload fields)
- **Test coverage** for each command, mocking external dependencies
- **Registration in a CLI group** so commands are invocable by name

Whether you use Click, argparse, Typer, or a shell script wrapper, the push-down principle is the same: move mechanical computation out of prompts and into tested, deterministic code.
