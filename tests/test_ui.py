"""실제 Streamlit 스크립트의 키 누락·작품 전환을 검증한다."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_no_key_allows_reading_and_shows_no_index_guidance(monkeypatch, tmp_path):
    monkeypatch.setenv("GMS_KEY", "")
    from sidam.config import Config
    monkeypatch.setattr(Config, "index_path", property(lambda self: tmp_path / "index"))
    from sidam.ui import get_service
    get_service.clear()
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "step7_skeleton.py"), default_timeout=60).run()
    assert not app.exception
    assert any("GMS_KEY" in e.value for e in app.info)
    assert any("색인이 없습니다" in e.value for e in app.info)
    app.selectbox(key="selected_poem").select("9000320").run()
    assert not app.exception
    assert any("진달래꽃" in e.value for e in app.markdown)
    assert any("나 보기가 역겨워" in e.value for e in app.markdown)
    assert app.session_state["main_tab"] == "작품 읽기 · 질문"
    assert app.chat_input[0].disabled
    app.selectbox(key="selected_poem").select("13313827").run()
    assert not app.exception
    assert any("그날이 오면" in e.value for e in app.markdown)
    assert any("그날이 오면 그날이 오면은" in e.value for e in app.markdown)
    get_service.clear()
