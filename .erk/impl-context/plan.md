# Plan: Fix Click help strings and module docstrings (Nodes 4.1 + 4.4 + 4.5)

Part of Objective #8381, Nodes 4.1, 4.4, 4.5

## Context

PR #8386 was supposed to cover Phase 4 of the plan-as-PR terminology migration but missed Click help= strings and module/function docstrings. The reevaluation audit reverted nodes 4.1, 4.4, 4.5 to pending. This plan covers all three as a single mechanical text-replacement PR.

## Scope

~50 text replacements across 15 files. All changes are docstrings, help text, comments, and error messages. No behavioral changes.

## Changes by File

### Node 4.1: Click help= strings and command docstrings

**src/erk/cli/commands/pr/create_cmd.py**
- Line 23: `"Issue title"` -> `"Plan title"` (help= string)
- Line 32: `"Create a plan issue from markdown content."` -> `"Create a plan from markdown content."` (docstring, shared with 4.4)

**src/erk/cli/commands/pr/replan_cmd.py**
- Line 10: `"issue_refs"` -> `"plan_refs"` (Click argument name + update parameter name on line 12 and usages ~lines 40-41)
- Line 20: `"Original issues are closed"` -> `"Original plans are closed"` (docstring)

**src/erk/cli/commands/branch/create_cmd.py**
- Line 102: `"from a GitHub issue with erk-plan label"` -> `"from a plan with erk-plan label"` (docstring)
- Line 109: `"from issue, or provide"` -> `"from plan, or provide"` (error message)

**src/erk/cli/commands/branch/checkout_cmd.py**
- Line 369: `"a plan issue/PR"` -> `"a plan"` (docstring)
- Line 385: `"from issue, or provide"` -> `"from plan, or provide"` (error message)

**src/erk/cli/commands/admin.py**
- Line 419: `"--issue", "-i"` -> `"--plan", "-p"` (option name rename + update parameter name `issue` -> `plan` on line 422 and all usages in the function)

**src/erk/cli/commands/wt/create_cmd.py**
- Line 528: `"fetches the GitHub issue"` -> `"fetches the plan"` (docstring)
- Line 529: `"issue title"` -> `"plan title"` (docstring)
- Line 567: `"to use a GitHub issue."` -> `"to use a plan."` (error message)
- Lines 615, 620, 622, 624, 656, 660, 835, 906: Update ~8 code comments from "issue" -> "plan" terminology

**src/erk/cli/commands/learn/learn_cmd.py**
- Line 3: `"associated with a plan issue"` -> `"associated with a plan"` (module docstring)
- Line 8: `"Posts tracking comment to issue"` -> `"Posts tracking comment to plan"` (module docstring)
- Line 44: `"Issue number or GitHub issue URL"` -> `"Plan number or GitHub URL"` (docstring)
- Line 47: `"Issue number or None"` -> `"Plan number or None"` (docstring)

**src/erk/cli/commands/implement.py**
- Line 8: `"GitHub issue mode"` -> `"Plan number mode"` (module docstring)
- Line 335: `"GitHub issue URL"` -> `"GitHub URL"` (docstring)
- Line 400: `"erk pr co <issue>"` -> `"erk pr co <plan>"` (error message)
- Line 401: `"setup-impl --issue <issue>"` -> `"setup-impl --plan <plan>"` (error message)

**src/erk/cli/commands/pr/list_cmd.py** - No changes needed (legitimate GitHub Issues API refs)

### Node 4.4: CLI module docstrings

Most already covered above. Additional:

**src/erk/cli/commands/land_learn.py**
- Line 22: `"learn issue should be created"` -> `"learn plan should be created"` (docstring)
- Line 39: `"learn plan issue with session info"` -> `"learn plan with session info"` (docstring)
- Line 42: `"Creates a GitHub issue with erk-learn label"` -> `"Creates a plan with erk-learn label"` (docstring)
- Line 54: `"create learn issue"` -> `"create learn plan"` (error message)
- Line 62: `"learn issue creation"` -> `"learn plan creation"` (docstring)
- Line 95: `"# Create the learn issue"` -> `"# Create the learn plan"` (comment)
- Line 118: `"Learn issue creation failed"` -> `"Learn plan creation failed"` (error message)

**src/erk/cli/commands/land_pipeline.py**
- Line 428: `"learn plan issue with preprocessed sessions"` -> `"learn plan with preprocessed sessions"` (docstring)

### Node 4.5: Core module docstrings

**src/erk/core/plan_context_provider.py**
- Line 18: `"erk-plan issue for PR generation"` -> `"erk plan for PR generation"` (class docstring)
- Line 21: `"for GitHub issue numbers"` -> `"for plan numbers"` (attr docstring)
- Line 32: `"linked to erk-plan issues"` -> `"linked to erk plans"` (class docstring)

**src/erk/core/commit_message_generator.py**
- Line 40: `"linked erk-plan issue"` -> `"linked erk plan"` (attr docstring)
- Line 211: `"Issue #{plan_context.plan_id}"` -> `"Plan #{plan_context.plan_id}"` (prompt text)

**src/erk/core/plan_duplicate_checker.py**
- Line 88: `"open plan issues"` -> `"open plans"` (arg docstring)

**src/erk/core/branch_slug_generator.py**
- Line 62: `"Plan or issue title to distill"` -> `"Plan title to distill"` (arg docstring)
- Line 142: `"Plan or issue title"` -> `"Plan title"` (arg docstring)

**src/erk/core/context.py**
- Line 601: `"plan issue management"` -> `"plan management"` (comment)

**src/erk/core/services/plan_list_service.py** - No changes needed (already clean)

## Careful Handling

- **admin.py `--issue` -> `--plan` rename**: This changes a CLI flag. Check for callers of `erk admin test-implement` that pass `--issue` (search commands/, skills, tests).
- **replan_cmd.py `issue_refs` -> `plan_refs`**: This is a Click argument name rename. Update the parameter name in the function signature and all internal usages.
- **implement.py line 401 `--issue` flag**: This references an exec script flag. Only change the placeholder `<issue>` to `<plan>` in the error message — the actual exec script flag rename is a separate node (5.x scope).

## Verification

1. Run `ruff check` to verify no syntax errors
2. Run `ty` for type checking
3. Run `pytest tests/unit/cli/` to verify CLI tests pass
4. Grep for remaining "plan issue" in the 15 modified files to confirm none were missed
5. Run `erk admin test-implement --help` to verify the `--plan` flag shows up correctly
