Analyze this implementation session log and produce a failure diagnosis.

Focus on:

1. What was the agent doing when it stopped (which file, which task)
2. Did it encounter an error, or did it just stop mid-task
3. What specific error messages or failures appeared
4. Which files or operations were involved

Rules:

- 3-7 concise bullet points
- Use backticks for file paths, commands, and error messages
- Do NOT suggest fixes
- Do NOT include session IDs, timestamps, or GitHub URLs
- If the session is too short to analyze, say so

## Exit Code: {{ EXIT_CODE }}

## Session tail (last entries):

{{ SESSION_TAIL }}
