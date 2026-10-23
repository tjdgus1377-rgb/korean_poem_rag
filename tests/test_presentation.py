"""HTML 독서 지면에서 외부 텍스트가 태그로 실행되지 않고 보존되는지 확인한다."""
from html.parser import HTMLParser

import pytest


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
