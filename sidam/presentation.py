"""독서 지면의 표현만 담당한다. 검색·자료의 의미는 변경하지 않는다."""
from html import escape


def masthead(count, compact=False):
    variant = " sidam-masthead-compact" if compact else ""
    return f'''<header class="sidam-masthead{variant}">
<div class="sidam-edition"><span>한국 근대시 아카이브</span><span>개화기에서 일제강점기까지, 시로 읽는 시대</span></div>
<div class="sidam-brand"><div><h1 class="sidam-wordmark">시담<span class="sidam-hanja" aria-hidden="true">詩談</span></h1>
<p class="sidam-tagline">시를 읽고, 시대를 묻다.</p></div>
<div class="sidam-seal" aria-hidden="true">시<br>담</div></div>
<div class="sidam-imprint"><span>시 한 편에 머무는 시간</span><span>작품 {int(count)}편 · 원문과 근거를 함께 읽는 서재</span></div>
</header>'''


def reading_heading(poem):
    return f'''<div class="sidam-reading-heading"><span class="sidam-eyebrow">작품을 읽는 시간</span>
<h2>{escape(poem['title'])}</h2><p>{escape(poem['author'])} <span>지음</span></p></div>'''


def preview(poem, number):
    lines = [line.strip() for line in poem['text'].splitlines() if line.strip()][:2]
    return f'''<div class="sidam-preview"><div class="sidam-card-index">작품 {number:02d}</div>
<h3>{escape(poem['title'])}</h3><p class="sidam-card-author">{escape(poem['author'])}</p>
<p class="sidam-excerpt">{escape(chr(10).join(lines))}</p></div>'''


def poem_page(poem):
    return f'''<article class="sidam-poem-page" aria-label="시 전문">
<div class="sidam-page-label">시 전문 <span aria-hidden="true">原文</span></div>
<h3>{escape(poem['title'])}</h3><p class="sidam-poem-author">{escape(poem['author'])}</p>
<div class="sidam-poem-lines">{escape(poem['text'])}</div>
<div class="sidam-poem-end" aria-hidden="true">―</div></article>'''
