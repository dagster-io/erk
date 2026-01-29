#!/bin/bash
# PreToolUse hook: inject dignified-python reminder when editing .py files.
# Reads tool_input.file_path from stdin JSON.

input=$(cat)
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')

if [[ "$file_path" == *.py ]]; then
  echo "dignified-python: Editing Python file. LBYL (no try/except control flow), no default params, frozen dataclasses, pathlib only. See AGENTS.md 'Python Standards' for full rules."
fi

exit 0
