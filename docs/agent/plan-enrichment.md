---
title: Plan Enrichment Guide
read_when:
  - "enriching a plan"
  - "adding metadata to plans"
  - "understanding plan enrichment workflow"
---

# Plan Enrichment Guide

Complete guide to enriching implementation plans for autonomous execution. Learn when to enrich plans, how the process works, and what makes enriched plans more valuable.

## Table of Contents

- [What is Plan Enrichment?](#what-is-plan-enrichment)
- [When to Use Enrichment](#when-to-use-enrichment)
- [Enrichment vs Raw Plans](#enrichment-vs-raw-plans)
- [The Enrichment Process](#the-enrichment-process)
- [Semantic Categories Explained](#semantic-categories-explained)
- [Command Comparison](#command-comparison)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## What is Plan Enrichment?

Plan enrichment is the process of transforming basic implementation plans into context-rich specifications for autonomous execution. Instead of just listing steps, enriched plans capture WHY decisions were made, what alternatives were rejected, and what discoveries would be expensive to rediscover.

**Key benefits:**

- **Preserves discoveries** - Captures expensive research and exploration from planning
- **Documents reasoning** - Explains WHY decisions were made, not just what to do
- **Prevents mistakes** - Records rejected alternatives and known pitfalls
- **Enables autonomy** - Provides agents with context needed to execute without supervision

**The enrichment process:**

1. **Apply guidance** - Optionally merge user corrections or additions
2. **Extract semantic understanding** - Pull valuable context from planning discussion
3. **Ask questions** - Interactively clarify ambiguities and fill gaps

## When to Use Enrichment

Use enrichment when plans contain valuable context that would be expensive to rediscover:

### ✅ Use Enrichment When:

- **Complex implementation** - Multiple architectural decisions or non-obvious constraints
- **Research-heavy planning** - Significant time spent exploring APIs, tools, or codebase
- **Multiple alternatives** - Approaches considered and rejected with clear rationale
- **Non-obvious constraints** - Domain rules, API quirks, or timing requirements discovered
- **Autonomous execution** - Plan will be executed by remote agent without human oversight

### ❌ Skip Enrichment When:

- **Trivial changes** - Simple bug fixes or mechanical updates
- **No alternatives** - Single obvious approach, no decisions made
- **No discoveries** - Nothing learned during planning that wasn't already known
- **Interactive execution** - You'll be monitoring and can answer questions as needed

### Decision Heuristic

Ask: **"Would someone else make mistakes without the planning discussion?"**

- If **yes** → Enrich the plan
- If **no** → Save as raw plan

## Enrichment vs Raw Plans

| Aspect             | Raw Plan                      | Enriched Plan                   |
| ------------------ | ----------------------------- | ------------------------------- |
| **Creation**       | Direct from ExitPlanMode      | Interactive enrichment process  |
| **Context depth**  | Implementation steps only     | Steps + Context & Understanding |
| **Interactivity**  | None                          | Clarifying questions asked      |
| **Typical size**   | 50-200 lines                  | 200-600 lines                   |
| **Best for**       | Simple, obvious tasks         | Complex, research-heavy work    |
| **Execution mode** | Supervised (human monitoring) | Autonomous (remote agent)       |

**Example comparison:**

```markdown
# Raw Plan

1. Add retry logic to API calls
2. Update error handling
3. Add tests

# Enriched Plan

## Implementation Steps

1. Add retry logic to API calls
2. Update error handling
3. Add tests

## Context & Understanding

### API/Tool Quirks

- Stripe API returns 429 rate limit without Retry-After header
- Webhook retries can arrive out of order within 10ms window

### Known Pitfalls

- DO NOT retry on 400 errors - these are permanent failures
- DO NOT use exponential backoff >60s - Stripe webhook timeout is 90s
```

## The Enrichment Process

The enrichment process has three steps that transform a basic plan into a context-rich specification.

### Step 1: Apply Optional Guidance

If you provide guidance text when enriching, it's merged contextually into the plan:

**Guidance types:**

- **Correction** - Fixes errors in approach (`"Fix: Use LBYL not try/except"`)
- **Addition** - New requirements (`"Add: Include retry logic"`)
- **Clarification** - More detail (`"Make error messages user-friendly"`)
- **Reordering** - Priority changes (`"Do validation before processing"`)

Guidance is integrated contextually throughout the plan, not just appended.

### Step 2: Extract Semantic Understanding

Analyze the planning discussion to extract valuable context using eight semantic categories (detailed below). The extraction is aggressive - include anything that:

- Took ANY time to discover (even 30 seconds)
- MIGHT influence implementation decisions
- Could POSSIBLY cause bugs or confusion
- Wasn't immediately obvious on first glance
- Required any clarification or discussion
- Involved ANY decision between alternatives

### Step 3: Interactive Enhancement

Ask clarifying questions to fill gaps:

- **Vague file references** → Request exact paths
- **Unclear operations** → Ask for specific actions and metrics
- **Missing success criteria** → Request testable outcomes
- **Unspecified dependencies** → Clarify versions, availability, fallbacks

Questions are batched and user can skip if they prefer ambiguity.

## Semantic Categories Explained

The eight categories organize discoveries from planning into structured sections.

### 1. API/Tool Quirks

Undocumented behaviors, edge cases, and external system gotchas.

**Extract when you discovered:**

- Timing issues, race conditions, ordering constraints
- Version-specific compatibility issues
- Performance characteristics affecting design
- Unexpected error conditions or return values

**Examples:**

- "Stripe webhooks often arrive BEFORE API response returns to client"
- "PostgreSQL foreign keys must be created in dependency order within same migration"
- "SQLite doesn't support DROP COLUMN in versions before 3.35"

### 2. Architectural Insights

WHY behind design decisions and component interactions.

**Extract when you discovered:**

- Why a pattern was chosen over alternatives
- Constraints that led to this design
- Non-obvious component interactions
- Reasoning behind sequencing or phasing

**Examples:**

- "Zero-downtime deployment requires 4-phase migration to maintain rollback capability"
- "State machine pattern prevents invalid state transitions from webhook retries"
- "Database transactions scoped per-webhook-event to prevent partial updates"

### 3. Domain Logic & Business Rules

Non-obvious requirements, compliance, and special conditions.

**Extract when you discovered:**

- Business rules not obvious from code
- Edge cases or special conditions
- Compliance, security, or regulatory requirements
- Assumptions about user behavior or data

**Examples:**

- "Failed payments trigger 7-day grace period before service suspension"
- "Admin users must retain ALL permissions during migration - partial loss creates security incident"
- "Tax calculation must happen before payment intent creation to ensure correct amounts"

### 4. Complex Reasoning

Alternatives considered and decision rationale.

**Format:**

```markdown
- **Rejected**: [Approach]
  - Reason: [Why it doesn't work]
- **Chosen**: [Selected approach]
  - [Why this works better]
```

**Examples:**

- **Rejected**: Synchronous payment confirmation
  - Reason: Webhooks take 1-30 seconds, creates timeout issues
- **Chosen**: Async webhook processing
  - Allows immediate API response, handles delays gracefully

### 5. Known Pitfalls

Specific gotchas and anti-patterns to avoid.

**Format:** "DO NOT [anti-pattern] - [why it breaks]"

**Examples:**

- "DO NOT use payment_intent.succeeded event alone - fires even for zero-amount test payments"
- "DO NOT store Stripe objects directly in database - schema changes across API versions"
- "DO NOT assume webhook delivery order - events can arrive out of sequence"

### 6. Raw Discoveries Log

Everything discovered during planning, without filtering.

**Extract:**

- What you looked up or verified
- Assumptions validated
- Small details clarified
- Documentation referenced
- Examples examined

**Examples:**

- Discovered: SQLite version on system is 3.39
- Confirmed: pytest is already in requirements.txt
- Learned: The codebase uses pathlib, not os.path
- Verified: Python 3.11 is the minimum version
- Noted: All configs are YAML not JSON

### 7. Planning Artifacts

Commands run, code examined, configs sampled during planning.

**Include:**

- **Commands run** - `pip list | grep stripe` → Found stripe==5.4.0
- **Code examined** - Looked at auth.py lines 45-67 for validation pattern
- **Config samples** - Database connection: `postgresql://user:pass@localhost/db`
- **Error messages** - "ImportError: circular import" when trying direct import

### 8. Implementation Risks & Concerns

Worries, uncertainties, or potential issues identified.

**Categories:**

- **Technical debt** - Tight coupling, missing abstractions
- **Uncertainty areas** - Unclear requirements or constraints
- **Performance concerns** - Potential scalability or timeout issues
- **Security considerations** - Missing protections or audit logging

**Examples:**

- **Uncertainty**: Not sure if webhook endpoint needs CSRF protection
- **Performance**: Bulk operations might timeout with current 30s limit
- **Security**: API keys stored in plain text in dev config

## Using Plan Enrichment

Plan enrichment is now integrated into the `/erk:craft-plan` workflow. When creating a plan:

1. Use `/erk:craft-plan` to start the planning process
2. The command will guide you through plan creation with interactive enrichment
3. Answer clarifying questions to add context
4. The enriched plan is saved directly to a GitHub issue
5. Implement: `erk implement <issue-number>`

**Workflow:**

```bash
# Create and save enriched plan
1. Run: /erk:craft-plan
2. Follow the interactive prompts
3. Answer clarifying questions
4. Implement: erk implement <issue-number>
```

## Examples

### Example 1: Simple Plan (No Enrichment Needed)

**Task:** Add missing type hints to auth.py

**Why no enrichment:**

- Single file, mechanical change
- No alternatives considered
- No discoveries made
- Obvious implementation

**Approach:** Skip enrichment during `/erk:craft-plan` by answering minimally

### Example 2: Complex Plan (Enrichment Required)

**Task:** Implement Stripe webhook handler for payment processing

**Why enrichment needed:**

- Discovered webhook timing quirks
- Rejected synchronous approach
- Identified idempotency requirements
- Found specific error handling needs

**Enriched sections added:**

- **API/Tool Quirks**: Webhook arrival order, retry behavior
- **Architectural Insights**: Why async processing, transaction scoping
- **Domain Logic**: Payment state transitions, grace periods
- **Complex Reasoning**: Rejected synchronous confirmation
- **Known Pitfalls**: Zero-amount events, storage anti-patterns

**Approach:** Use `/erk:craft-plan` and thoroughly answer clarifying questions

**Value:** Implementing agent knows WHY async is required, what NOT to do, and edge cases to handle.

## Best Practices

### Context Preservation Philosophy

**Extract aggressively:** When in doubt, include it. Extracting too much context is better than too little.

**Prefer "discovered" framing:**

- ✅ "Discovered: Database uses UTC timestamps"
- ❌ "The database should use UTC timestamps"

**Include research breadcrumbs:**

- What you looked up
- Where you found answers
- What you verified

### When to Skip Enrichment

Skip if ALL of these are true:

- ✅ Implementation is obvious and mechanical
- ✅ No alternatives were considered
- ✅ No discoveries were made during planning
- ✅ Plan will be executed interactively (you'll be watching)

### When to Use Enrichment

Use if ANY of these are true:

- ✅ Multiple approaches were discussed
- ✅ External APIs or tools were researched
- ✅ Non-obvious constraints were discovered
- ✅ Plan will execute autonomously (remote agent)

### Code in Plans: Behavioral, Not Literal

Plans describe WHAT to do, not HOW to code it.

**Include:**

- ✅ File paths and function names
- ✅ Behavioral requirements
- ✅ Success criteria
- ✅ Error handling approaches

**Only include code for:**

- Security-critical implementations
- Public API signatures
- Bug fixes showing exact before/after
- Database schema changes

**Example:**

- ❌ Wrong: `def validate_user(user_id: str | None) -> User: ...`
- ✅ Right: "Update validate_user() in src/auth.py to use LBYL pattern, check for None, raise appropriate errors"

## Troubleshooting

### "No plan found in context"

**Cause:** Trying to save/enrich before creating a plan with ExitPlanMode.

**Solution:**

1. Enter plan mode (if not already in it)
2. Create your implementation plan
3. Use ExitPlanMode to finalize
4. Then run `/erk:plan-save` or `/erk:plan-save-enriched`

### "Clarifying questions seem excessive"

**Cause:** Agent is trying to fill every possible gap.

**Solution:**

- You can skip questions - just say "proceed with current plan"
- Prefer ambiguity for simple tasks where you'll be monitoring
- Use enrichment selectively for complex autonomous work

### "Plan is too long after enrichment"

**Cause:** Very detailed context extraction (common for complex tasks).

**Solution:**

- This is normal for research-heavy planning
- Longer plans prevent expensive rediscovery
- Context sections aren't read during every step, only when needed
- If genuinely too long, consider breaking into multiple smaller plans

### "Enrichment didn't capture our discussion"

**Cause:** Context extraction missed valuable discoveries.

**Solution:**

- After enrichment, review the Context & Understanding sections
- Manually add missing discoveries using GitHub issue editing
- Re-run `/erk:craft-plan` with explicit guidance about what to add

---

## Related Documentation

- **Planning Workflow**: [planning-workflow.md](planning-workflow.md) - `.impl/` folder structure and commands
- **Hooks**: [hooks-erk.md](hooks-erk.md) - Understanding hook reminders during planning
- **Glossary**: [glossary.md](glossary.md) - Definitions of erk terminology
- **Documentation Guide**: [guide.md](guide.md) - Navigation hub for all agent docs
