#!/bin/bash
# PreToolUse hook to block gt commands until the gt skill is loaded.
# Read stdin JSON and extract command and session_id
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // ""')

# Only check gt commands
if [[ "$COMMAND" != gt\ * ]]; then
  exit 0
fi

# Check for skill-loaded marker
MARKER_DIR=".erk/scratch/sessions/${SESSION_ID}"
MARKER_FILE="${MARKER_DIR}/gt-skill-loaded.marker"

if [[ -f "$MARKER_FILE" ]]; then
  # Skill was loaded, allow command
  exit 0
fi

# Block and instruct
echo "gt command blocked: Load \`gt\` skill first."
echo ""
echo "To proceed:"
echo "1. Load the gt skill: use Skill tool with skill='gt'"
echo "2. Create marker: erk exec marker create --session-id ${SESSION_ID} gt-skill-loaded"
echo "3. Retry your gt command"
exit 2
