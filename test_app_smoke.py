"""Headless check that the Streamlit app runs, both with and without a model."""
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


def _run(note, error):
    with patch("llm.explain", return_value=(note, error)):
        at = AppTest.from_file("app.py", default_timeout=30).run()
        assert not at.exception, at.exception
        for key in ("go_shift", "go_daily", "go_trek"):
            at.button(key=key).click().run()
            assert not at.exception, at.exception
        return at


def test_app_with_model_note():
    at = _run("Stay steady and sip often.", None)
    assert any("Stay steady" in m.value for m in at.markdown)


def test_app_without_model_still_shows_plan():
    at = _run(None, "ConnectError: refused")
    assert len(at.dataframe) >= 1          # schedule tables rendered
    assert any("isn't reachable" in c.value for c in at.caption)
