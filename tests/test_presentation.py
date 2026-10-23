"""HTML 독서 지면에서 외부 텍스트가 태그로 실행되지 않고 보존되는지 확인한다."""
from html.parser import HTMLParser

import pytest
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


@pytest.mark.parametrize("field", ["title", "author", "text"])
def test_poem_page_preserves_text_without_interpreting_external_html(field):
    from sidam.presentation import poem_page

    poem = {"title": "진달래꽃", "author": "김소월", "text": "나 보기가 역겨워\n가실 때에는\n\n말없이 고이 보내 드리우리다."}
    payload = '<script>alert("작품")</script><img src=x onerror=alert(1)> & <바람>'
    poem[field] = payload + ("\n둘째 행\n\n넷째 행" if field == "text" else "")
    parser = PageParser()
    parser.feed(poem_page(poem))
    assert not {"script", "img", "바람"} & {tag for tag, _ in parser.tags}
    for tag, attrs in parser.tags:
        assert not any(key.startswith("on") for key in attrs)
    rendered_text = "".join(parser.text)
    assert poem[field] in rendered_text
    assert poem["text"] in rendered_text


def test_reading_ui_does_not_turn_poem_markdown_into_external_assets(monkeypatch, tmp_path):
    from markdown_it import MarkdownIt
    from streamlit.testing.v1 import AppTest
    from sidam.config import Config
    from sidam.service import Service
    from sidam import ui

    monkeypatch.setenv("GMS_KEY", "")
    monkeypatch.setattr(Config, "index_path", property(lambda self: tmp_path / "index"))
    root = Path(__file__).resolve().parents[1]
    service = Service(Config.load(root))
    payload = '첫 행\n\n![tracker](https://example.invalid/tracker.png)\n\n# 원문 속 기호\n\n[링크 모양](https://example.invalid/link)'
    service.poems["9000320"]["text"] = payload
    monkeypatch.setattr(ui, "get_service", lambda *_: service)
    app = AppTest.from_file(str(root / "step7_skeleton.py"), default_timeout=60).run()
    app.selectbox(key="selected_poem").select("9000320").run()
    assert not app.exception
    pages = [(e.value, True) for e in app.markdown if '<article class="sidam-poem-page"' in e.value]
    pages += [(e.proto.body, False) for e in app.get("html") if '<article class="sidam-poem-page"' in e.proto.body]
    assert len(pages) == 1
    body, uses_markdown = pages[0]
    parser = PageParser()
    parser.feed(MarkdownIt().render(body) if uses_markdown else body)
    assert not {"img", "a", "h1"} & {tag for tag, _ in parser.tags}
    assert payload in "".join(parser.text)
