# Article Ideas

Topics to explore in agentic programming articles.

## Status Legend

- ✅ **Published** - Article posted to GitHub discussion (has GitHub link)
- 📝 **Draft** - Article written but not yet posted (no GitHub link)
- 💡 **Idea** - Not started (default, no marker needed)

**Note:** Articles are only considered complete when posted to internal GitHub discussions.

## Ideas by Category

### Getting Started & Mindset

- **Remember you are a context engineer** - The fundamental shift in mindset: your primary job is managing what context the agent sees, when it sees it, and how it's structured

- **Understand your context choke points** - Identifying where token limits constrain your workflow and designing around these bottlenecks

- **Think of yourself as a token factory** - Understanding token economics in agentic workflows: optimizing context usage, minimizing waste, and designing systems that scale with token constraints

- **Be conversant with software engineering jargon - agents love it** - How using precise technical terminology improves agent comprehension, reduces ambiguity, and leads to better code generation

- **Stop anthropomorphizing agents - think of them as functions** - Why treating agents as deterministic functions with inputs and outputs leads to better system design than thinking of them as conversational partners

- **Treat Claude like a compiler** - Shifting from conversational interaction to structured tool usage: providing precise inputs, expecting deterministic outputs, and integrating AI into your build pipeline

- **It turns you into a PM** - How AI coding assistants fundamentally transform the developer role from writing code to managing and directing AI agents, requiring new product management and orchestration skills

### Core Workflows & Tools

- **Ctrl-G is your friend** - How using Ctrl-G to interrupt and redirect agents mid-execution prevents wasted tokens, enables course correction, and creates a more collaborative development flow

- **Devrun for diagnostic tools to swallow context** - Using specialized agents to run diagnostic tools (pytest, ty, ruff) while keeping large outputs isolated from the main conversation context

- **Everything's a multi-agent workflow - planning is essential** - Why breaking down complex tasks into specialized agent workflows is fundamental to successful agentic programming

- **Structured process for complex tasks** - The decorator migration story: why providing structured, step-by-step processes is crucial for complex AI-assisted refactoring and ensures consistent, high-quality results

- **Incredible at searching historically** - Leveraging AI's exceptional strength in searching through historical context, codebases, git history, and documentation to surface relevant information humans would miss

- **Difficult to follow instructions** - The persistent challenge of getting AI to consistently follow coding instructions, and strategies for better prompt engineering, hooks, and workflow design to improve adherence

### Configuration & Customization

- **Using hooks to inject guidance that Claude Code will actually follow** - How to configure prompt submission hooks to enforce coding standards and inject context that agents consistently respect. Hooks are like kernel mode for Claude Code - they execute with elevated authority

- **Skills are new, but they are almost always better than MCPs for local development** - Why Claude Code skills provide a more lightweight and effective approach than MCP servers for project-specific tooling and workflows

- **Packaged run commands in .agent** - Using `.agent/` directory to bundle execution scripts alongside skills and commands, creating portable agent toolkits

- **Build your own tools and workflows - it's the only way to learn** - Why creating custom workflows and tooling, rather than just using existing tools, is essential for deeply understanding agentic programming

- **Repo built-in CLI** - Every repository should have a built-in CLI to organize and manage the random Python scripts and tools that get "vibe coded" during AI development, creating a structured home for ad-hoc automation

### Testing & Code Quality

- **The unreasonable effectiveness of fakes** - How using in-memory fakes instead of mocks transforms testing and enables agentic development workflows

- **Fast tests and high-quality error messages have never been so important** - How agent-driven development amplifies the value of instant feedback loops and clear diagnostic messages for rapid iteration and debugging

- **Write agent-optimized codebase guide** - Best practices for structuring codebases to maximize agent effectiveness: clear boundaries, explicit interfaces, searchable patterns, and semantic organization

- **Coarse-grained modules important** - Why refactoring into coarse-grained modules becomes more critical in AI-assisted development: reducing context fragmentation, improving agent comprehension, and enabling more effective code generation

- **Manual review still important** - Why human review remains critical in AI-assisted development workflows despite automation capabilities: catching subtle bugs, maintaining architectural vision, and ensuring code quality standards

- **Refactoring good, token intensive** - AI excels at refactoring but it's computationally expensive: strategies for balancing code quality improvements with token costs, knowing when to refactor vs. when to move forward

### Advanced Techniques

- **Planning workflow with erk enrichment** - How to plan implementations, create worktrees from plans, and customize the enrichment step to inject project-specific context before autonomous execution

- **Parallel execution of worktrees** - Leveraging git worktrees to run multiple feature branches in parallel, enabling true concurrent development workflows

- **Worktrees are just a view** - Understanding git worktrees as filesystem projections of branches rather than heavyweight copies, demystifying how they enable parallel development without repository duplication

- **Worktrees are the final boss** - Why git worktrees represent the advanced frontier of agentic development: powerful but complex, requiring deep understanding of git internals and workflow design

- **Merge conflict resolution through thesis reapplication** - How to resolve merge conflicts by having agents re-apply the original thesis or intent of changes rather than mechanically merging line-level diffs

- **Vibe coding technique** - A workflow for rapid prototyping: vibe-code to get a user-facing outcome, rederive specification from the concrete code, eliminate implementation details, then rewrite in phases with proper code review

- **Refactor to generalization technique** - A specific prompting pattern: asking AI to "refactor to generalization" as an effective way to improve code abstraction, reduce duplication, and identify common patterns

- **AI makes porous borders** - How AI breaks down traditional boundaries in software development: blurring lines between roles (dev/PM/QA), tools (IDE/CLI/docs), and development phases (design/implementation/testing)

### Documentation & Knowledge Management

- **Two types of documentation: one for humans, one for machines** - In the era of agentic programming, machine documentation serves as a "token cache" - a materialization of semantic knowledge at a specific point in time, optimized for agent consumption rather than human reading

- **Compaction Considered Harmful** - Why automatically compacting conversation history destroys crucial context, breaks agent reasoning chains, and how to design workflows that preserve the full conversational thread

## Published Articles

0. **30 days of agentic programming** ✅ (Intro) - A comprehensive series exploring daily tips, techniques, and patterns for effective agentic development workflows
   - Location: `docs/public-content/30-days-series/00-intro.md`
   - Posted: https://github.com/dagster-io/internal/discussions/19182

1. **Always run Claude in verbose mode** ✅ - Why enabling verbose output is essential for understanding agent reasoning, debugging workflows, and building trust in agentic development
   - Location: `docs/public-content/30-days-series/01-verbose-mode.md`
   - Posted: https://github.com/dagster-io/internal/discussions/19183

2. **Use voice input** ✅ - You'll naturally provide more context when speaking than typing, your bit rate is higher, and Claude is excellent at distilling meaningful information from conversational input
   - Location: `docs/public-content/30-days-series/02-voice-input.md`
   - Posted: https://github.com/dagster-io/internal/discussions/19184

3. **Start with Claude as investigator** ✅ - LLMs excel at synthesizing scattered context into compressed understanding. Software engineering has many read-only tasks that fit this pattern perfectly - use them to build confidence with zero risk
   - Location: `docs/public-content/30-days-series/03-claude-as-investigator.md`
   - Posted: https://github.com/dagster-io/internal/discussions/19185
