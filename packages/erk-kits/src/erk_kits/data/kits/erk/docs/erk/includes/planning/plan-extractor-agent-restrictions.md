# Plan-Extractor Agent Tool Restrictions

The plan-extractor agent has limited tool access (enforced in agent YAML):

- ✅ Read - Can read files
- ✅ Bash - Can run git/kit CLI (read-only)
- ✅ AskUserQuestion - Can clarify ambiguities
- ❌ Edit - NO access to file editing
- ❌ Write - NO access to file writing
- ❌ Task - NO access to subagents

This structural restriction makes the agent safe - it **cannot** modify files even if prompted to do so.
