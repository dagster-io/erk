# Launch Plan-Extractor Agent (Enriched Mode)

Use the Task tool to launch the specialized agent with the plan content:

```json
{
  "subagent_type": "plan-extractor",
  "description": "Enrich plan with context",
  "prompt": "Enrich the implementation plan with semantic understanding.\n\nInput:\n{\n  \"mode\": \"enriched\",\n  \"plan_content\": \"[plan content]\",\n  \"guidance\": \"\"\n}\n\nYour job:\n1. Ask clarifying questions via AskUserQuestion tool\n2. Extract semantic understanding (8 categories) from the plan content\n3. Return markdown output with enrichment details.\n\nExpected output: Markdown with `# [title]` heading (no 'Plan:' prefix), Enrichment Details section, and full enriched plan content.",
  "model": "haiku"
}
```

**What the agent does:**

1. Receives plan content
2. Asks clarifying questions via AskUserQuestion tool
3. Extracts semantic understanding (8 categories) from plan content
4. Returns enriched markdown output

**Agent tool restrictions:**

The plan-extractor agent has limited tool access (enforced in agent YAML):

- ✅ Read - Can read files
- ✅ Bash - Can run git/kit CLI (read-only)
- ✅ AskUserQuestion - Can clarify ambiguities
- ❌ Edit - NO access to file editing
- ❌ Write - NO access to file writing
- ❌ Task - NO access to subagents

This structural restriction makes the agent safe - it **cannot** modify files even if prompted to do so.
