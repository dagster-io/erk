# Rename "instruction" to "prompt" throughout one-shot feature

## Context

The one-shot feature consistently uses the term "instruction" for the user-provided task description. The more standard term is "prompt". This is a terminology rename across the entire feature — CLI arguments, dataclass fields, variable names, user-facing messages, workflow inputs, skills, docs, and tests.

## Scope

~170 occurrences across ~15 files. Pure rename, no behavioral changes.

## Files to modify

### Python source

1. **`src/erk/cli/commands/one_shot.py`**
   - Click argument: `"instruction"` → `"prompt"`
   - `--file` help text: "Read instruction from..." → "Read prompt from..."
   - Function parameter: `instruction: str | None` → `prompt: str | None`
   - Docstring, comments, error messages: all "instruction" → "prompt"
   - Example: `--file instructions.md` → `--file prompt.md`

2. **`src/erk/cli/commands/one_shot_dispatch.py`**
   - `OneShotDispatchParams.instruction` → `.prompt`
   - `generate_branch_name(instruction: str, ...)` → `generate_branch_name(prompt: str, ...)`
   - All `params.instruction` → `params.prompt`
   - All user_output strings, PR body strings, comments, docstrings
   - Workflow input key: `"instruction": truncated_instruction` → `"prompt": truncated_prompt`

3. **`src/erk/cli/commands/objective/plan_cmd.py`**
   - Variable: `instruction = ...` → `prompt = ...`
   - `OneShotDispatchParams(instruction=...)` → `OneShotDispatchParams(prompt=...)`
   - User output: `f"Instruction: {instruction}"` → `f"Prompt: {prompt}"`

### GitHub Actions workflow

4. **`.github/workflows/one-shot.yml`**
   - Input name: `instruction:` → `prompt:`
   - Step name: "Write instruction to .impl/task.md" → "Write prompt to .impl/task.md"
   - Env var: `INSTRUCTION: ${{ inputs.instruction }}` → `PROMPT: ${{ inputs.prompt }}`
   - Echo messages: "Instruction already committed..." → "Prompt already committed..."

### Claude commands/skills

5. **`.claude/commands/erk/one-shot.md`**
   - `argument-hint: <instruction>` → `argument-hint: <prompt>`
   - All occurrences of "instruction" in prose and comments
   - Scratch filename: `one-shot-instruction.md` → `one-shot-prompt.md`
   - Heredoc delimiter: `INSTRUCTION_EOF` → `PROMPT_EOF`

6. **`.claude/commands/erk/one-shot-plan.md`**
   - Description line: "one-shot instruction" → "one-shot prompt"
   - "read an instruction" → "read a prompt"
   - Step heading: "Read the Instruction" → "Read the Prompt"
   - "related to the instruction" → "related to the prompt"
   - "focused on the instruction" → "focused on the prompt"

### Documentation

7. **`docs/learned/planning/one-shot-workflow.md`** — all "instruction" → "prompt"
8. **`docs/learned/workflows/one-shot-workflow.md`** — all "instruction" → "prompt"

### Tests

9. **`tests/commands/one_shot/test_one_shot.py`**
   - Error message assertions: `"Instruction must not be empty"` → `"Prompt must not be empty"`
   - Variable names: `long_instruction` → `long_prompt`, `instruction_file` → `prompt_file`
   - Dict key assertions: `inputs["instruction"]` → `inputs["prompt"]`
   - All comments referencing "instruction"

10. **`tests/commands/one_shot/test_one_shot_dispatch.py`**
    - All `instruction=` keyword args → `prompt=`
    - All `inputs["instruction"]` assertions → `inputs["prompt"]`
    - Variable names: `long_instruction` → `long_prompt`

11. **`tests/commands/one_shot/test_branch_name.py`**
    - Test names, docstrings, variables containing "instruction"
    - Function call args: `generate_branch_name(long_instruction, ...)` → `generate_branch_name(long_prompt, ...)`

12. **`tests/commands/objective/test_plan_one_shot.py`**
    - `inputs["instruction"]` assertions → `inputs["prompt"]`

## Approach

Use a combination of `Edit` with `replace_all` for simple string swaps within each file, and targeted edits for context-sensitive renames (e.g., where "instruction" appears in different grammatical forms).

Order: Python source first (to establish the new API), then workflow, then skills/commands, then docs, then tests.

## Verification

1. `make fast-ci` — all unit tests pass (test assertions updated to match new strings)
2. `ruff check` / `ty` — no lint or type errors from the rename
3. Grep for any remaining "instruction" in one-shot context files to confirm completeness
