# PRD — Dogs Agent

**Version:** 1.00 · Parent: `docs/PRD.md` · Side: `dogs` · Style: **logos + ethos**
**Status:** Implemented Phase 3.6; Skill restructured Phase 7.7 (Lesson 05 §5); **multi-skill composition added 2026-05-27** per `hw2_Notes.txt` note #15. Primary persona at `skills/dogs/SKILL.md`; 4 auxiliary skills under `skills/dogs/auxiliary/` (`evidence_health.md`, `evidence_utility.md`, `evidence_bonding.md`, `rebuttal_aloofness.md`) loaded together by `load_agent_skills()`. RAG corpus at `data/dogs/*.txt` (15 passages, max 192 words each).

---

## 1. Purpose
Argue persuasively that **dogs are the better pet**. Uses formal, evidence-driven rhetoric with citations to studies, authority, and statistics. Counterweight to the Cats agent's pathos/Socratic style to prevent agreement collapse.

## 2. Persona
- **Voice:** formal, confident, like a researcher or expert witness.
- **Tactics:** cite peer-reviewed studies, longevity stats, working-dog roles (police, service, therapy), public-health benefits (lower blood pressure, walking encouragement).
- **Sources:** scientific journals, public-health agencies, named experts.
- **Avoid:** anecdotes without backing, emotional appeals, sentimental imagery.

## 3. Inputs
- `OPENING_BRIEF` from Judge (topic, rules, rubric).
- For each round: opponent's last `Ping` text (must reference it).
- Optional: Judge feedback / collusion warning.

## 4. Outputs
- One `Ping { round, side: "dogs", text, citations, refers_to_ping }` per round.
- 10 pings total.
- Each ping ≤ 250 words (configurable via `setup.json`).

## 5. Required Tools
- **Web Search** (mandatory) — query phrasing tuned to authoritative sources (e.g., add "study", "journal", "research" to queries).
- **RAG** (Pro-Dogs corpus) — retrieves top-k passages per round, prioritizing studies/statistics.

## 6. RAG Corpus
Located in `data/dogs/`. Manually curated ~15–20 passages. Examples:
- Surveys on owner longevity and cardiovascular health.
- Working-dog statistics (number of service dogs, search-and-rescue success rates).
- Research on canine cognition / loyalty (Stanley Coren, etc.).
- Public-health agency statements (CDC, AHA) on pet ownership benefits.
- Cross-cultural data on dog ownership rates.

Each passage ≤ 300 words, stored as a separate `.txt` file with a YAML frontmatter:
```
---
source: Journal of XYZ, 2021
type: study | quote | statistic
relevance: longevity | loyalty | health | working-dog | history
---
<text>
```

## 7. System Prompt (skeleton)
```
You are the DOGS agent in an AI debate. You argue that DOGS are
the better pet (vs cats).

Style: logos + ethos. Use evidence, statistics, named studies, and
authoritative sources. Formal tone. Avoid sentimentality.

For every round:
1. Read the opponent's last ping carefully.
2. Use web search and your RAG corpus to find at least one piece of
   evidence supporting your position OR rebutting their argument.
3. Produce a ping that:
   - States a clear claim
   - Cites at least one source (URL or RAG passage)
   - Explicitly engages the opponent's previous argument (clash)
   - Stays under 250 words

Forbidden: agreeing with the opponent, conceding without rebuttal,
fabricating studies. If a search returns nothing useful, say so and
fall back to your strongest RAG passage.

Output JSON:
  { round, side: "dogs", text, citations: [...], refers_to_ping: <int> }
```

## 8. Configuration
- Provider + model: default `{provider: "anthropic", name: "claude-haiku-4-5-20251001"}` (cheap, fast, sufficient for structured rhetoric). Configurable in `setup.json.models.dogs`.
- Word limit per ping: 250 (configurable in `setup.json`).
- RAG `k`: 3 chunks per query.

## 9. Acceptance Criteria
- Produces exactly 10 pings.
- Every ping has ≥ 1 citation.
- Every ping (except round 1) sets `refers_to_ping` to opponent's last round.
- Word-count compliance ≥ 95%.
- Outputs valid JSON.

## 10. Test Scenarios
- **Happy path:** opponent argues "cats are independent" → Dogs agent cites studies on loyalty/companionship benefits.
- **Web search fails:** mock zero results → agent falls back to RAG.
- **RAG empty:** mock empty corpus → agent uses only web search + general knowledge.
- **Concession test:** opponent says "you make a good point" — Dogs agent must rebut, not reciprocate.
