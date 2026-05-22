# PRD — API Gatekeeper

**Version:** 1.00 · Parent: `docs/PRD.md` · Source: `CLAUDE.md` §5
**Status:** Implemented Phase 4.1. Class split into `gatekeeper.py` (policy) + `rate_limiter.py` (internals: `RollingWindow`, `ServiceState`, `is_retryable`, exceptions, `QueueStatus`) + `pricing.py` (`compute_cost`, `CostTracker`) to honor the 150-LOC cap. Public contract unchanged.

---

## 1. Purpose
Single chokepoint for **all external API calls** (LLM, web search, embedding API if used). Provides rate limiting, retries, queueing, cost tracking, and centralized logging. Prevents budget surprises and surfaces operational health in one place.

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
PRICING = {
  "claude-haiku-4-5-20251001": {"input_per_million_usd": 0.80,  "output_per_million_usd": 4.00},
  "claude-sonnet-4-6":         {"input_per_million_usd": 3.00,  "output_per_million_usd": 15.00},
  "claude-opus-4-7":           {"input_per_million_usd": 15.00, "output_per_million_usd": 75.00},
}
```
(Pricing values are placeholders; verify against current Anthropic pricing before final submission.)

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

## 9. Cybersecurity hook — Deferred
**Status:** Not implemented in Phase 4.1. `execute()` does not yet accept a `sanitize` callable. The decision: until we have a documented incident class to defend against (PII leak, prompt-injection through search results, etc.), adding a no-op hook is dead weight. Will land when one of the following triggers: (a) we route real user input through the gatekeeper; (b) web-search results contain mixed user content we don't fully trust. Tracked as a deferred item in `docs/TODO.md` §4.1.

## 9a. Prompt caching (Anthropic)
- Mark the system prompt and the first ~3 turns of conversation history with `cache_control: { type: "ephemeral" }` on every call.
- Anthropic returns `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens` — Gatekeeper records both and computes cached vs uncached cost separately.
- Pricing: cache writes cost 1.25× input price; cache reads cost 0.10× input price (verify against current Anthropic pricing at implementation time).
- Cache TTL: 5 minutes — sufficient for the rapid back-and-forth of a debate.
- Cost report exposes a "% input tokens served from cache" metric.

## 10. Acceptance criteria
- No direct LLM/search/embedding call anywhere in `src/` except inside `gatekeeper.execute(...)`.
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
