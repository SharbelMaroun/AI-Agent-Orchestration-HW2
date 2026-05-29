# PRD — API Gatekeeper

**Version:** 1.00 · Parent: `docs/PRD.md` · Source: `CLAUDE.md` §5
**Status:** Implemented Phase 4.1. Class split into `gatekeeper.py` (policy) + `rate_limiter.py` (internals: `RollingWindow`, `ServiceState`, `is_retryable`, exceptions, `QueueStatus`) + `pricing.py` (`compute_cost`, `CostTracker`) to honor the 150-LOC cap. Public contract unchanged.

---

## 1. Purpose
Single chokepoint for **all external API calls** — LLM completions and web search. Provides rate limiting, retries, queueing, cost tracking, and centralized logging. Prevents budget surprises and surfaces operational health in one place.

> **Embeddings are out of scope by design.** The RAG embedder (`sentence-transformers/all-MiniLM-L6-v2`) and ChromaDB run **locally** — no network call, no rate limit, no per-token billing — so they are intentionally *not* routed through the gatekeeper (CLAUDE.md §5 governs *external* API calls). If a remote embedding API is ever configured, it must be wrapped in `execute(..., service="embedding")`.

## 2. Responsibilities
1. **Rate limiting** — block calls that would exceed configured limits.
2. **Queueing** — when limit reached, FIFO-queue rather than reject.
3. **Retries** — transient failures (429, 503, network timeouts) retried with exponential backoff.
4. **Token + cost tracking** — record input/output tokens per model and dollar cost.
5. **Centralized logging** — every call logged via the project's FIFO logger.
6. **Cyber-security hook** — optional layer for sanitizing prompts (PII scrubbing, etc.).

## 3. Interface (from `CLAUDE.md`)
```python
class ApiGatekeeper:
    def __init__(self, config: RateLimitConfig, logger: Logger, pricing: PricingTable): ...
    def execute(self, api_call: Callable, *args, service: str = "default", **kwargs) -> Any:
        """
        1. Check rate limits (per-service)
        2. Queue if limit reached
        3. Call api_call(*args, **kwargs)
        4. Retry on transient failures
        5. Read response.usage (if LLM) → log tokens + cost
        6. Return response
        """
    def get_queue_status(self) -> QueueStatus: ...
    def get_token_summary(self) -> CostReport: ...
```

## 4. Configuration
Read from `config/rate_limits.json` — see `PLAN.md §7`. Pricing table read from `config/setup.json.pricing` or hardcoded in a Pydantic `PricingTable`:

```python
# Per-provider per-model pricing (see config/setup.json.pricing for the live values).
PRICING = {
  "google": {
    "gemini-2.5-flash":      {"input_per_million_usd": 0.30, "output_per_million_usd": 2.50},
    "gemini-2.5-pro":        {"input_per_million_usd": 1.25, "output_per_million_usd": 10.00},
    "gemini-2.5-flash-lite": {"input_per_million_usd": 0.10, "output_per_million_usd": 0.40},
  },
  "anthropic": {
    "claude-haiku-4-5-20251001": {"input_per_million_usd": 0.80,  "output_per_million_usd": 4.00},
    "claude-sonnet-4-6":         {"input_per_million_usd": 3.00,  "output_per_million_usd": 15.00},
    "claude-opus-4-7":           {"input_per_million_usd": 15.00, "output_per_million_usd": 75.00},
  },
  "openai": {
    "gpt-4o-mini": {"input_per_million_usd": 0.15, "output_per_million_usd": 0.60},
    "gpt-4o":      {"input_per_million_usd": 2.50, "output_per_million_usd": 10.00},
  },
}
```
(Pricing values are list prices; verify against current provider pricing before the final submission run.)

## 5. Cost tracking
Every LLM call:
- Read `response.usage.input_tokens` / `response.usage.output_tokens`.
- Compute cost: `(in × price_in + out × price_out) / 1_000_000`.
- Append to internal counter, keyed by model name.
- Persist to `results/cost_log.jsonl` (one JSON object per call).

`get_token_summary()` produces a `CostReport` matching Table 4 of the source PDF:

| Model | Input Tokens | Output Tokens | Total Cost (USD) |
|---|---|---|---|

Used by README, the analysis notebook, and the budget alert.

## 6. Budget alert
Configured via `config/setup.json.budget_usd`. If running total exceeds 80% of budget → `WARNING` log. If exceeds 100% → `ERROR` log + raise `BudgetExceededError` (orchestrator catches, halts debate gracefully).

## 7. Queue behavior
- FIFO `queue.Queue` per service.
- Max depth from config (default 100). At max → log backpressure alert + raise `QueueFullError`.
- Drain mechanism: every `retry_after_seconds`, attempt next queued call.

## 8. Retry policy
- Retryable HTTP codes: 408, 429, 500, 502, 503, 504.
- Network exceptions (timeout, connection reset) also retried.
- Backoff: `retry_after_seconds × attempt_number`.
- Max attempts from config (default 3). Final failure → raise `ApiCallFailedError`.

## 9. Cybersecurity hook — Implemented
**Status:** Implemented 2026-05-27 via `src/debate/shared/security.py` (`SecuritySanitizer`). Closes `hw2_Notes.txt` note #24. Trigger (b) materialised: every Pro/Con ping consumes DuckDuckGo search snippets and RAG passages, both of which are untrusted text crossing into the agent's prompt.

**Design:** stateless `SecuritySanitizer` with `sanitize_external(text) -> text` and `wrap_untrusted(text, source) -> "<source>...</source>"`. Applied at the trust boundary inside `DebateAgent._collect_evidence` (via `sanitize_hits` / `sanitize_passages` helpers), not inside the gatekeeper, because the threat is the *content* of the external response, not the request itself.

**Defenses:** Unicode NFKC normalization; control-character stripping; regex redaction of common prompt-injection patterns ("ignore previous instructions", role hijacks like "you are now…", fake `### SYSTEM ###` blocks, `system:` / `assistant:` role prefixes); per-snippet truncation (4000 chars default).

**Tests:** `tests/unit/test_security.py` — 10 cases covering empty input, clean passthrough, every redaction pattern, truncation, control-char stripping, idempotence, and the wrap-delimiter helper.

## 9a. Prompt caching (Anthropic)
- Mark the system prompt and the first ~3 turns of conversation history with `cache_control: { type: "ephemeral" }` on every call.
- Anthropic returns `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` — Gatekeeper records both and computes cached vs uncached cost separately.
- Pricing: cache writes cost 1.25× input price; cache reads cost 0.10× input price (verify against current Anthropic pricing at implementation time).
- Cache TTL: 5 minutes — sufficient for the rapid back-and-forth of a debate.
- Cost report exposes a "% input tokens served from cache" metric.

## 10. Acceptance criteria
- No direct **external** LLM or web-search call anywhere in `src/` except inside `gatekeeper.execute(...)`. (Local RAG embedding + ChromaDB make no external call and are intentionally exempt — see §1.)
- 100% coverage of retry, queue, and budget paths.
- `get_token_summary()` matches sum of `cost_log.jsonl` exactly.
- Concurrent calls respect `concurrent_max` (verified by a concurrency test).

## 11. Test scenarios
- **Single call success** — happy path returns response, logs tokens.
- **Rate limit hit** — calls beyond `requests_per_minute` queue; drain succeeds after window.
- **Transient 429** — first call returns 429, second succeeds → counted as one logical call.
- **Hard failure** — 3 consecutive 503s → raises `ApiCallFailedError`.
- **Budget exceeded** — mock pricing to exceed budget mid-debate → raises `BudgetExceededError`.
- **Concurrent excess** — 10 simultaneous calls with `concurrent_max=2` → only 2 in flight at a time.

## 12. Alternatives considered
| Option | Chosen? | Rationale |
|---|---|---|
| **Rolling-window** rate limiting (deque of timestamps) vs token-bucket | ✅ rolling window | Enforces exact `requests_per_minute`/`_per_hour` simultaneously; O(1) amortized prune. Token-bucket smooths bursts but needs refill tuning we don't need at this scale. |
| **Polling spin-wait for a slot** vs a real `queue.Queue` + worker pool | ✅ spin-wait (documented) | At ~60 calls/debate against a depth-100 cap the queue never fills; a worker pool adds threads + lifecycle complexity for no benefit. Trade-off and the `QueueFullError`-vs-"never reject" spec tension are noted in §7. |
| **Per-request `timeout` kwarg** vs a client-level timeout | ✅ per-request | Threaded from `setup.timeouts.agent_response_seconds` so the cap is config-driven and sits below the watchdog kill; per-request is uniform across providers. |
| **Middleware chain** (composable cross-cutting decoration) vs hardcoding logging/timing inside `execute` | ✅ middleware | Lets consumers add logging/auth/metrics around every call without editing the gatekeeper (CLAUDE.md §19). See PLAN "Extension points". |
| Local-embedding routing through the gatekeeper | ❌ | Embeddings are a *local* model — no external API, no rate limit, no billing — so routing them adds overhead with no benefit (§1). |

## 13. Performance metrics
- **Rate-window ops:** O(1) amortized `add`/`prune` per call (deque).
- **Concurrency:** bounded by `concurrent_max` (semaphore); default 5 for LLM, 2 for search.
- **Retry cost:** linear backoff `retry_after_seconds × attempt`, ≤ `max_retries` attempts.
- **Per-debate load:** ≈ 41 LLM + ≈ 20 search `execute()` calls; each records tokens + cost and checks the budget (O(1)).
- **Cost-tracking overhead:** one dict update + one JSONL append per call; negligible vs the network round-trip.
