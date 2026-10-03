"""Checks how llm.explain handles the different answers a local model can give."""
from types import SimpleNamespace

import llm


def _fake_client(content, finish_reason="stop"):
    choice = SimpleNamespace(message=SimpleNamespace(content=content), finish_reason=finish_reason)
    completions = SimpleNamespace(create=lambda **kw: SimpleNamespace(choices=[choice]))
    models = SimpleNamespace(list=lambda: SimpleNamespace(data=[SimpleNamespace(id="google/gemma-4-e4b")]))
    return SimpleNamespace(chat=SimpleNamespace(completions=completions), models=models)


def test_normal_answer(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda url: _fake_client("Sip often."))
    assert llm.explain("plan") == ("Sip often.", None)


def test_ran_out_of_length_gives_clear_message(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda url: _fake_client("", "length"))
    note, err = llm.explain("plan")
    assert note is None and "thinking" in err


def test_empty_answer(monkeypatch):
    monkeypatch.setattr(llm, "get_client", lambda url: _fake_client(None, "stop"))
    note, err = llm.explain("plan")
    assert note is None and "empty" in err
