"""Shared pytest fixtures.

Tests never hit the network: the LLM signal is monkeypatched to a deterministic
stub, and the audit log is redirected to a temp directory so real logs/ stays clean.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fake_llm(text, appeal_context=None):
    """Deterministic stand-in for the Groq judge: AI-tells push the score up.

    When an appeal_context is supplied, simulate a convincing explanation by
    lowering the AI estimate (the real judge stays skeptical; the stub just needs
    to move so the reweighting machinery is exercised)."""
    low = (text or "").lower()
    tells = sum(t in low for t in ("furthermore", "moreover", "it is important",
                                   "stakeholders", "paradigm", "comprehensive"))
    casual = sum(t in low for t in ("honestly", "lol", "ok so", "gonna", "u "))
    p = 0.5 + 0.12 * tells - 0.15 * casual
    if appeal_context:
        p -= 0.30
    p = max(0.0, min(1.0, p))
    return {"p_llm": round(p, 4), "reason": "stub", "reliable": True}


@pytest.fixture
def temp_log(tmp_path, monkeypatch):
    import audit
    log_dir = tmp_path / "logs"
    monkeypatch.setattr(audit, "LOG_DIR", str(log_dir))
    monkeypatch.setattr(audit, "LOG_FILE", str(log_dir / "audit.jsonl"))
    return log_dir


@pytest.fixture
def fake_llm(monkeypatch):
    import pipeline
    monkeypatch.setattr(pipeline, "llm_score", _fake_llm)


@pytest.fixture
def client(temp_log, fake_llm):
    import app as app_module
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()
