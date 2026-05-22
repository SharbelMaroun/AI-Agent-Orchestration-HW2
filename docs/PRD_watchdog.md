# PRD — Watchdog

**Version:** 1.00 · Parent: `docs/PRD.md` · Required by Lesson 05 ("Watchdog with keep-alive").
**Status:** Implemented Phase 4.2 with one deferred sub-item — see §9 below.

---

## 1. Purpose
Monitor every long-lived agent process. If an agent stops responding (network hang, infinite loop, OOM), the watchdog kills and restarts it so the debate can continue without manual intervention.

## 2. Responsibilities
1. Maintain a registry of `(agent_id → pid)` for every running child process.
2. Receive **heartbeat** signals from each child every `heartbeat_seconds`.
3. If no heartbeat from an agent within `kill_after_seconds` → kill that process.
4. Restart the agent with the same state (system prompt, RAG store, ping history-to-date).
5. Log every detection and restart event via the FIFO logger.
6. Stop cleanly on `SIGTERM` / `SIGINT` from the parent.

## 3. Interface
```python
class Watchdog:
    def __init__(self, config: WatchdogConfig, logger: Logger): ...
    def register(self, agent_id: str, process: Process, restart_fn: Callable) -> None: ...
    def heartbeat(self, agent_id: str) -> None: ...
    def start(self) -> None:        # spawn watchdog thread
    def stop(self) -> None: ...
    def on_timeout(self, agent_id: str) -> None:   # kill + invoke restart_fn
```

## 4. Heartbeat protocol
- Child processes send a heartbeat through a dedicated `multiprocessing.Queue` named `heartbeat_q`.
- Format: `{ "agent_id": str, "timestamp": ISO8601 }`.
- Frequency: every `heartbeat_seconds` (default 5s).
- The watchdog thread polls `heartbeat_q.get(timeout=heartbeat_seconds)` and updates an in-memory `last_seen` dict.

## 5. Restart protocol
On timeout:
1. Log `AGENT_TIMEOUT { agent_id, last_seen, current_time }`.
2. `process.terminate()`; if not dead after 2s, `process.kill()`.
3. Invoke `restart_fn(state_snapshot)` provided at registration time.
4. The new process resumes from the most recent ping in the debate history (orchestrator owns the history; not the child).
5. Log `AGENT_RESTARTED { agent_id, new_pid }`.

## 6. Configuration (`config/setup.json.timeouts`)
```json
{
  "agent_response_seconds": 60,
  "watchdog_heartbeat_seconds": 5,
  "watchdog_kill_after_seconds": 90,
  "max_restarts_per_agent": 3
}
```
After `max_restarts_per_agent` exceeded → log `AGENT_DEAD`, raise `WatchdogFatalError`, orchestrator gracefully aborts the debate and writes a partial verdict.

## 7. Acceptance criteria
- A deliberately hung child process (sleep > kill_after_seconds) is detected and restarted within 2 × heartbeat_seconds of timeout.
- After a restart, the debate continues with the next round (no lost rounds).
- Heartbeat overhead negligible (< 0.5% CPU during a debate).
- All restarts logged.

## 8. Test scenarios
- **Healthy run:** all agents heartbeat normally → 0 restarts, 0 warnings.
- **Single hang:** force the Dogs agent to sleep 200s mid-round → watchdog kills and restarts; debate completes.
- **Repeated hang:** agent hangs 4 times → after 3rd restart, raise `WatchdogFatalError`.
- **Clean shutdown:** SIGINT to parent → watchdog stops cleanly, children terminated, no zombies.
- **Crashed child:** child raises uncaught exception → watchdog detects via missed heartbeat → restart.

## 9. Implementation notes (as built)
- Watchdog runs as a daemon **thread** in the parent process. ✅ implemented (`Watchdog._loop`).
- Uses `threading.Lock` around the `_entries` dict (renamed from `last_seen` in implementation — entries now hold `last_seen` + `restart_count` + `restart_fn` + `process` + `fatal` flag). ✅ implemented.
- Heartbeats during LLM calls: defaulted to option 1 (raise `kill_after_seconds` above the longest expected LLM call). Configured via `setup.json.timeouts.watchdog_kill_after_seconds = 90`. ✅ honored.
- **Deferred:** SIGINT/SIGTERM clean-shutdown signal handling. The orchestrator currently runs synchronously in one process (no child processes yet), so the watchdog's `stop()` is invoked programmatically rather than via a signal handler. The signal-handler wiring lands together with the orchestrator's multi-process upgrade (TODO §4.2 deferred item).
- **Beyond spec:** `Watchdog.check_once()` is exposed publicly so tests can drive the timeout-detection logic without spinning up the daemon thread. The loop is `while not stop: check_once(); sleep(poll)` — the unit-of-work seam used the same pattern as the gatekeeper's `sleep_fn` injection.
