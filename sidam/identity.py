"""작품 ID를 보존하는 표기·작가·구절 검색."""
import re

from .data import normalize


def title_forms(title):
    title = title.replace('（', '(').replace('）', ')')
    outside = re.sub(r'\([^)]*\)', '', title)
    forms = {normalize(title), normalize(outside)}
    for match in re.finditer(r'\(([^)]*)\)', title):
        inner = normalize(match[1])
        before, after = normalize(title[:match.start()]), normalize(title[match.end():])
        if not inner or len(inner) > len(before):
            continue
        paired = before[-len(inner):]
        if (re.fullmatch(r'[一-鿿]+', inner) and re.fullmatch(r'[가-힣]+', paired)) or (re.fullmatch(r'[가-힣]+', inner) and re.fullmatch(r'[一-鿿]+', paired)):
            forms.add(before[:-len(inner)] + inner + after)
    return {f for f in forms if f}


def same_title(left, right):
    return bool(title_forms(left) & title_forms(right))


def edit_distance_one(left, right):
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right)) <= 1
    if len(left) > len(right):
        left, right = right, left
    return any(left == right[:i] + right[i+1:] for i in range(len(right)))


def lexical_search(query, poems, aliases):
    text = normalize(query)
    authors = {normalize(p['author']): p['author'] for p in poems.values()}
    authors.update({normalize(a['alias']): a['author'] for a in aliases.get('authors', []) if a['author'] in authors.values()})
    author = None
    for name in sorted(authors, key=len, reverse=True):
        if text.startswith(name) or text.endswith(name):
            author = authors[name]
            text = text[len(name):] if text.startswith(name) else text[:-len(name)]
            break
    for ending in ('찾아주세요', '찾아줘', '찾기'):
        if text.endswith(ending): text = text[:-len(ending)]
    candidates = {pid:p for pid,p in poems.items() if not author or p['author'] == author}
    conditions = {'author': author} if author else {}
    if not text and author:
        return list(candidates), conditions
    if not text:
        return None
    exact = [pid for pid,p in candidates.items() if text in title_forms(p['title'])]
    hints = [a['poem_id'] for a in aliases.get('input_hints', []) if normalize(a['alias']) == text and a['poem_id'] in candidates]
    if exact or hints:
        return list(dict.fromkeys(exact + hints)), conditions
    partial = [pid for pid,p in candidates.items() if len(text) >= 3 and any(text in f for f in title_forms(p['title']))]
    verse = [pid for pid,p in candidates.items() if len(text) >= 6 and text in normalize(p['text'])]
    if partial or verse:
        return list(dict.fromkeys(partial + verse)), conditions
    if author and len(text) >= 4 and not re.search(r'\d', text):
        fuzzy = [pid for pid,p in candidates.items() if any(len(f) >= 4 and not re.search(r'\d',f) and edit_distance_one(text, f) for f in title_forms(p['title']))]
        if fuzzy:
            return fuzzy, {**conditions, 'match_kind': '오탈자 후보'}
    return None
