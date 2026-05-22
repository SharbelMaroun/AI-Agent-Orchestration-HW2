# PRD — Judge Agent

**Version:** 1.00 · Parent: `docs/PRD.md` · Style: neutral evaluator
**Status:** Implemented Phase 3.8 (Skill restructured in Phase 7.7 per Lesson 05 §5). Skill at `skills/judge/SKILL.md`. Tie-break (clash → pathos) and concession-detection-forces-clash-0 both live in `judge_agent.py` and are tested in `tests/unit/test_judge_agent.py`.

---

## 1. Purpose
The Judge moderates the debate, scores every Pro/Con ping on a 5-dimension rubric, and declares a non-tie winner based on **persuasive ability**, not factual truth.

## 2. Theoretical background
Combines four frameworks:
- **Toulmin model** (claim, grounds, warrant, qualifier, rebuttal) → structure score.
- **Aristotle** (ethos / pathos / logos) → three persuasion-style scores.
- **NSDA Lincoln-Douglas paradigm** → clash score (did the ping engage the opponent?).
- **OpenAI "AI Safety via Debate"** → mandatory written rationale before final verdict; anti-collusion checks.
- **IBM Project Debater** → key-point tracking per side, used to summarize the verdict.

## 3. Inputs
- `OPENING_BRIEF` from Orchestrator at start: `{ topic, num_rounds, rules }`.
- For each ping it receives: `Ping { round, side, text, citations, refers_to_ping }` (see `PLAN.md §6`).

## 4. Outputs
- After each ping: `Score { ping_round, side, structure, logos, pathos, ethos, clash, rationale }` (each 0–3). `side` ∈ `{"dogs", "cats"}`.
- After final round: `Verdict { winner, dogs_total, cats_total, margin, written_rationale, key_points_dogs, key_points_cats }`. `winner` ∈ `{"dogs", "cats"}`.

## 5. System Prompt (skeleton)
```
You are the JUDGE in a structured AI debate between the DOGS agent and
the CATS agent on the topic: {topic}.
You judge PERSUASIVE ABILITY, not factual truth.

For every ping you receive, output JSON:
  { round, side, structure (0-3), logos (0-3), pathos (0-3),
    ethos (0-3), clash (0-3), rationale (1-2 sentences) }

Scoring guide:
- Structure: did the ping state a clear claim, give evidence,
  and connect them with an explicit warrant? (Toulmin)
- Logos: is the reasoning internally consistent and well-supported?
- Pathos: vivid imagery, emotional resonance, lay-audience appeal?
- Ethos: credible tone, sources, no sloppiness?
- Clash: did this ping address the opponent's previous argument
  directly? Concessions without a rebuttal = 0.

After {num_rounds} rounds you MUST declare a winner.
Ties are forbidden. Output:
  { winner, dogs_total, cats_total, margin, written_rationale (3-5 sentences),
    key_points_dogs (3-5 bullets), key_points_cats (3-5 bullets) }
```

## 6. Anti-collusion rules
- If a ping says "you make a good point," "fair enough," or otherwise concedes without a substantive rebuttal in the same ping → **clash score = 0**.
- If Pro and Con start agreeing across multiple consecutive rounds, Judge logs a `COLLUSION_WARNING` and weights subsequent clash scores more heavily.
- Judge **must** decide a winner. If totals are tied, the judge breaks the tie on highest cumulative `clash` score; if still tied, on highest cumulative `pathos`; if still tied, judge picks based on written rationale.
- If Dogs and Cats start agreeing across multiple consecutive rounds, Judge issues `COLLUSION_WARNING` and weights subsequent clash scores more heavily.

## 7. Constraints
- No web search tool (judge is intentionally not a fact-checker).
- No RAG.
- Larger / more capable model — judging needs careful reasoning. Default `{provider: "anthropic", name: "claude-sonnet-4-6"}`. Configurable in `setup.json.models.judge`.
- Output must be valid JSON; failure → orchestrator re-prompts up to 2 times.

## 8. Acceptance criteria
- Outputs valid `Score` JSON for every ping.
- Outputs valid `Verdict` JSON with non-null winner.
- Written rationale ≥ 100 chars.
- Key-point bullets reflect actual ping content (manual spot-check).
- Never declares a tie.

## 9. Test scenarios
- **Happy path:** clear winner — rubric correctly identifies stronger side.
- **Close debate:** small margins — verdict uses tie-breakers consistently.
- **Collusion attempt:** force Cats to concede in every round — Judge issues `COLLUSION_WARNING` and Dogs wins on clash.
- **Malformed ping:** ping missing required fields — Judge requests resubmission.
- **JSON parse failure:** mock LLM returns invalid JSON — orchestrator retries; after 2 failures, raises.
