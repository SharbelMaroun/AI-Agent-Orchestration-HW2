"""Pydantic JSON message schemas for IPC + persistence.

Mirrors docs/PLAN.md §6. Envelopes used for inter-process messaging set
`extra = "forbid"` so a typo in a sender's payload fails fast at the
receiver instead of silently dropping fields.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Side = Literal["dogs", "cats"]


class _Envelope(BaseModel):
    """Base for messages crossing process boundaries — reject unknown fields."""

    model_config = ConfigDict(extra="forbid")


class ChatMessage(BaseModel):
    """One turn in an LLM conversation history."""

    role: Literal["user", "assistant"]
    content: str


class CompletionResponse(BaseModel):
    """Normalized LLM response returned by every `LLMProvider.complete`."""

    text: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    model: str
    provider: str


class Ping(BaseModel):
    """One debate turn produced by Dogs or Cats."""

    round: int = Field(ge=1)
    side: Side
    text: str
    citations: list[str] = Field(default_factory=list)
    refers_to_ping: int | None = None
    timestamp: datetime
    tokens_in: int = 0
    tokens_out: int = 0


class Score(BaseModel):
    """Judge's per-ping evaluation. Each dimension is 0..3 (max total 15)."""

    ping_round: int = Field(ge=1)
    side: Side
    structure: int = Field(ge=0, le=3)
    logos: int = Field(ge=0, le=3)
    pathos: int = Field(ge=0, le=3)
    ethos: int = Field(ge=0, le=3)
    clash: int = Field(ge=0, le=3)
    rationale: str


class Verdict(BaseModel):
    """Final debate outcome. Ties are forbidden — see Judge tie-break logic."""

    winner: Side
    dogs_total: int = Field(ge=0)
    cats_total: int = Field(ge=0)
    margin: int
    written_rationale: str
    key_points_dogs: list[str] = Field(default_factory=list)
    key_points_cats: list[str] = Field(default_factory=list)


class DebateResult(BaseModel):
    """Full debate output written to `results/debates/<timestamp>.json`."""

    topic: str
    pings: list[Ping]
    scores: list[Score]
    verdict: Verdict
    cost_report: dict
    started_at: datetime
    finished_at: datetime


class OpeningBrief(_Envelope):
    """Sent once by the orchestrator to each agent before round 1."""

    type: Literal["OPENING_BRIEF"] = "OPENING_BRIEF"
    topic: str
    num_rounds: int = Field(ge=1)
    rules: str
    side: Side | None = None  # None for the judge
    rubric: str | None = None  # populated for the judge only


class Ready(_Envelope):
    """Agent acknowledges OPENING_BRIEF before the orchestrator starts round 1."""

    type: Literal["READY"] = "READY"
    agent_id: str


class YourTurn(_Envelope):
    """Orchestrator signals an agent to produce its next ping."""

    type: Literal["YOUR_TURN"] = "YOUR_TURN"
    round: int = Field(ge=1)
    previous_ping: Ping | None = None  # None for the very first ping


class Heartbeat(_Envelope):
    """Liveness signal from agent to watchdog."""

    type: Literal["HEARTBEAT"] = "HEARTBEAT"
    agent_id: str
    timestamp: datetime


MessageEnvelope = Annotated[
    OpeningBrief | Ready | YourTurn | Heartbeat,
    Field(discriminator="type"),
]
