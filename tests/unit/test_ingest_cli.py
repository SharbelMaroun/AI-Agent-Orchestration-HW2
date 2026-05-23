"""CLI-edge tests for `debate.services.rag.ingest.main`.

Split off from `test_coverage_topup.py` for the 150-LOC test cap."""

from __future__ import annotations

from pathlib import Path

import pytest

from debate.services.rag.ingest import main as ingest_main


class _StubEmbedder:
    """Deterministic stand-in so the ingest run never loads sentence-transformers."""

    def __init__(self, *_a, **_kw) -> None:
        pass

    def embed_text(self, _t: str) -> list[float]:
        return [0.1] * 8

    def embed_batch(self, ts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in ts]


def test_ingest_main_smoke(tmp_path: Path, monkeypatch) -> None:
    """Exercise the CLI entrypoint with the stub embedder."""
    import debate.services.rag.ingest as ingest_mod

    monkeypatch.setattr(ingest_mod, "Embedder", _StubEmbedder)
    data_root = tmp_path / "data"
    (data_root / "dogs").mkdir(parents=True)
    (data_root / "dogs" / "x.txt").write_text(
        "---\nsource: t\n---\nbody words go here\n", encoding="utf-8"
    )
    cfg_path = tmp_path / "setup.json"
    repo_setup = Path("config/setup.json").read_text(encoding="utf-8")
    cfg_path.write_text(
        repo_setup.replace(
            '"data/{agent}/chroma"',
            f'"{(tmp_path / "chroma_{agent}").as_posix()}"'.replace("{agent}", "{agent}"),
        ),
        encoding="utf-8",
    )
    rc = ingest_main(["--agent", "dogs", "--config", str(cfg_path), "--data-root", str(data_root)])
    assert rc == 0


def test_ingest_main_rejects_unknown_agent() -> None:
    with pytest.raises(SystemExit):
        ingest_main(["--agent", "fish"])
