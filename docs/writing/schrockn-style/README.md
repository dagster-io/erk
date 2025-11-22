# Schrockn Style Guides: A Subtle Approach

## Purpose

These style guides capture Nick Schrock's technical writing voice and approach. They're meant to help maintain consistency across technical content while preserving authenticity and readability.

## ⚠️ Critical: Subtlety is Key

**The most important rule: Apply these guides with a light touch.**

Overly literal interpretation of these guides produces stilted, formulaic writing that defeats their purpose. The goal is to internalize the principles and let them naturally influence your writing, not to mechanically check boxes.

## How to Use These Guides

### 1. Read for Understanding, Not Compliance

First, read through the relevant guides to understand the underlying philosophy:

- What problems are they solving?
- What reader experience are they creating?
- What makes this voice distinctive?

### 2. Choose Your Primary Guide

Select based on your content type:

- **[Core Style Guide](core-style-guide.md)**: Start here - foundational principles for all writing
- **[Industry Retrospectives](industry-retrospectives-style-guide.md)**: For evolution stories, trend analysis, "decade of" pieces
- **[Practical Engineering](practical-engineering-style-guide.md)**: For how-to articles, best practices, code reviews
- **[Internal Technical](internal-technical-style-guide.md)**: For code smell discussions, team documentation
- **[External Thought Leadership](external-thought-leadership-style-guide.md)**: For blog posts, conference talks

### 3. Apply Subtly

#### ✅ Good Application (Subtle)

```markdown
# Original (bland):

"The software community adopted TDD in the 2000s."

# Subtle revision:

"In the early 2000s, the software community underwent a fundamental shift."
(Adds temporal grounding and weight without forcing personal anecdotes)
```

```markdown
# Adding authority naturally:

"I've reviewed tests where the mock setup was three times longer than the actual test."
(Specific, credible, but not forced)
```

#### ❌ Bad Application (Too Literal)

```markdown
# Overly formulaic:

"I've seen this. I've built that. In my experience at Facebook where I went from E3 to E6 in 3.5 years, I learned that testing, which I call 'Production Confidence Engineering,' has three phases that I witnessed personally..."
(Checking every box produces awkward, self-important prose)
```

## Key Principles to Internalize

### 1. Personal Authority Without Ego

- Sprinkle in experience naturally: "I've seen," "I once spent a day debugging"
- Don't force credentials or company names unless they add specific value
- One personal anecdote per major section is usually enough

### 2. Memorable Concepts

- Coin terms when they genuinely capture something new
- Don't force clever names onto mundane concepts
- Let them emerge from the pain points you're describing

### 3. Constructive Frustration

- Channel real pain points you've experienced
- Don't manufacture frustration for dramatic effect
- Show you've been there, but focus on the solution

### 4. Pragmatic Honesty

- Acknowledge tradeoffs when they matter
- Don't hedge unnecessarily on clear points
- Admit uncertainty only when it's genuine

## The Subtlety Test

After writing, ask yourself:

1. **Does it sound natural when read aloud?**
   - If it sounds like you're reading a template, it's too literal

2. **Would you say this in a technical conversation?**
   - If not, you're probably forcing the style

3. **Does every personal anecdote add value?**
   - If you're adding them just to check a box, remove them

4. **Is the technical content still the focus?**
   - Personal voice should enhance, not overshadow, the technical insights

## Examples of Subtle Success

### From "The Fake Pattern" Article

**Before (no style):**

```markdown
"While this approach revolutionized software quality, years of practice revealed significant drawbacks:"
```

**After (subtle style):**

```markdown
"While this approach revolutionized software quality, years of practice revealed significant drawbacks:

**Over-abstraction plague**: The need to inject everything led to an explosion of interfaces and abstractions. I've seen codebases where finding the actual implementation required clicking through five layers of interfaces."
```

Notice how:

- The memorable concept ("Over-abstraction plague") feels natural
- The personal experience is specific but brief
- The technical point remains primary

## When to Break the Rules

### Always Break Rules When:

- Following them makes the writing worse
- The content doesn't naturally fit the pattern
- You're writing for a specific audience with different expectations
- Technical accuracy would be compromised

### Never Force:

- Personal anecdotes where you have none
- Memorable phrases that aren't actually memorable
- Predictions you don't believe
- Data you don't have

## The Bottom Line

These guides should make your writing better, not formulaic. Think of them as:

- **Inspiration**, not prescription
- **Principles**, not rules
- **Patterns**, not templates

The best adherence is invisible to the reader. They should finish your article thinking about your ideas, not your style.

## Quick Reference: Core Elements to Consider

When revising, lightly consider adding:

1. **One opening hook** that establishes why this matters
2. **2-3 personal touches** that establish credibility (not more)
3. **1-2 memorable concepts** if they naturally emerge
4. **Specific examples** over general statements
5. **Honest acknowledgment** of tradeoffs where relevant
6. **Clear next steps** or takeaways

But remember: If adding any of these makes the writing worse, don't do it.

---

_The irony of a style guide about subtlety is not lost on us. When in doubt, err on the side of clear, direct technical communication over stylistic adherence._
