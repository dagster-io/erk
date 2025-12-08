---
completed_steps: 0
steps:
- completed: false
  text: 1. Agent has >300 lines of markdown
- completed: false
  text: 2. Most operations are bash commands (mechanical, not semantic)
- completed: false
  text: 3. Error handling is rule-based (not requiring judgment)
- completed: false
  text: 4. String parsing/formatting dominates the agent
- completed: false
  text: 5. Token cost per invocation is high (>5000 tokens)
- completed: false
  text: 1. Identify mechanical vs semantic operations
- completed: false
  text: 2. Create Python operations module in `erk_shared/integrations/<name>/`
- completed: false
  text: 3. Create kit CLI commands for preflight/finalize
- completed: false
  text: 4. Write minimal agent for semantic work only
- completed: false
  text: 5. Update slash command to orchestrate phases
- completed: false
  text: 6. Add tests with FakeGit/FakeGitHub
- completed: false
  text: '1. **Testability**: Python phases use FakeGit/FakeGitHub'
- completed: false
  text: '2. **Reliability**: Auth/push errors caught before AI cost'
- completed: false
  text: '3. **Cost**: Smaller agent = fewer tokens'
- completed: false
  text: '4. **Speed**: Preflight can fail fast'
total_steps: 15
---

# Progress Tracking

- [ ] 1. Agent has >300 lines of markdown
- [ ] 2. Most operations are bash commands (mechanical, not semantic)
- [ ] 3. Error handling is rule-based (not requiring judgment)
- [ ] 4. String parsing/formatting dominates the agent
- [ ] 5. Token cost per invocation is high (>5000 tokens)
- [ ] 1. Identify mechanical vs semantic operations
- [ ] 2. Create Python operations module in `erk_shared/integrations/<name>/`
- [ ] 3. Create kit CLI commands for preflight/finalize
- [ ] 4. Write minimal agent for semantic work only
- [ ] 5. Update slash command to orchestrate phases
- [ ] 6. Add tests with FakeGit/FakeGitHub
- [ ] 1. **Testability**: Python phases use FakeGit/FakeGitHub
- [ ] 2. **Reliability**: Auth/push errors caught before AI cost
- [ ] 3. **Cost**: Smaller agent = fewer tokens
- [ ] 4. **Speed**: Preflight can fail fast