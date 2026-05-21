# Prompt Engineering Log

Log every significant prompt used to build this project: the context, the goal, what came back, refinements, and lessons learned. Required by the submission rubric (§17 of `CLAUDE.md`).

---

## Format for each entry

```
## YYYY-MM-DD — <short title>

**Context:** <what we were trying to do>
**Goal:** <what we wanted from the LLM>
**Prompt used:**
> <verbatim prompt>

**Result summary:** <1–3 sentences>
**Refinements:** <what we changed and why>
**Lesson:** <one takeaway for future prompts>
```

---

## 2026-05-21 — Research: debate-judging frameworks

**Context:** Designing the Judge agent. Needed a scoring rubric grounded in actual debate-judging practice, not invented from scratch.
**Goal:** Identify 1–2 published frameworks (Toulmin, ethos/pathos/logos, NSDA) that can be encoded into the Judge's system prompt.
**Prompt used (to research sub-agent):**
> "Research debate-judging frameworks. Cover: (1) OpenAI's 'AI Safety via Debate' paper (arXiv:1805.00899), (2) Toulmin model, (3) Aristotle ethos/pathos/logos, (4) NSDA Lincoln-Douglas rubrics, (5) IBM Project Debater lessons. For each, give the practical takeaway for our Judge prompt. Report under 800 words."

**Result summary:** Got a tight synthesis combining all five frameworks into a 5-dimension rubric (Structure / Logos / Pathos / Ethos / Clash, 0–3 each). IBM's "Key Point Analysis" insight informed the anti-collusion design.
**Refinements:** None — first-pass output was usable.
**Lesson:** When designing prompts for evaluation tasks, anchor them in published rubrics. Reduces variance and makes the design defensible.

---

## 2026-05-21 — Topic selection criteria

**Context:** Choosing a debate topic that favors persuasion over facts.
**Goal:** Identify properties of "persuasion-friendly" topics + propose options.
**Prompt used:** Embedded in the same research run above.
**Result summary:** Checklist: normative not empirical · no ground truth · low-stakes · symmetric · familiar to lay judge · generates vivid examples · has values trade-off. Selected "Cats vs Dogs as the better pet" from 4 candidates.
**Lesson:** Always derive selection criteria *before* picking — prevents post-hoc justification.

---

## TODO: Prompts to log as we build them

- [ ] Pro-Dogs agent system prompt (logos/ethos persona)
- [ ] Pro-Cats agent system prompt (pathos/Socratic persona)
- [ ] Judge agent system prompt (5-dim rubric, key-point tracking)
- [ ] Opening brief prompt (Judge → Pro/Con at debate start)
- [ ] Web search query templates (per side, per round)
- [ ] RAG retrieval query prompt
- [ ] Cost-report summarization prompt (for README)
