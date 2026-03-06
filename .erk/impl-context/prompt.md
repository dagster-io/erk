⎿  Found 0 lines

⏺ User answered Claude's questions:
  ⎿  · By 'local-only' do you mean code-stats shouldn't be in `claude_only_skills()` either — it should just be in `_UNBUNDLED_SKILLS` (which is where I put it)? The test requires every skill to be in either codex_portable OR claude_only, so it needs to be in one of those two. → codex_portable
      + unbundled



if a skill is unbundled it does not have to be in the claude_only_skills and codex_portable_skills, those are oly for bundled skills
