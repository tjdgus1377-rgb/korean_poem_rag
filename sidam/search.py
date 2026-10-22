from .data import normalize

YEAR_FIELDS = {"first_publication": "first_publication_year", "collection_publication": "collection_publication_year", "written": "written_year"}


def validate_conditions(conditions, poems):
    if not isinstance(conditions, dict):
        raise ValueError("검색 조건 형식을 확인하세요.")
    c = {k: conditions.get(k) for k in ("title_query", "author", "year_kind", "year_from", "year_to", "theme_query")}
    c["year_kind"] = c["year_kind"] or "first_publication"
    if c["year_kind"] not in YEAR_FIELDS:
        raise ValueError("지원하지 않는 연도 기준입니다.")
    for key in ("year_from", "year_to"):
        if c[key] is not None and (type(c[key]) is not int or not 1000 <= c[key] <= 2100):
            raise ValueError("연도 조건을 확인하세요.")
    if c["year_from"] is not None and c["year_to"] is not None and c["year_from"] > c["year_to"]:
        raise ValueError("연도 범위가 역전되었습니다.")
    if c["author"] is not None and c["author"] not in {p["author"] for p in poems.values()}:
        raise ValueError("등록된 시인 이름인지 확인하세요.")
    for key in ("title_query", "theme_query"):
        if c[key] is not None and (not isinstance(c[key], str) or len(c[key]) > 500):
            raise ValueError("검색어 길이와 형식을 확인하세요.")
    return c


def matches_conditions(poem, conditions):
    if conditions.get("author") and poem["author"] != conditions["author"]:
        return False
    if conditions.get("title_query") and normalize(conditions["title_query"]) not in normalize(poem["title"]):
        return False
    lo, hi = conditions.get("year_from"), conditions.get("year_to")
    if lo is not None or hi is not None:
        year = poem.get(YEAR_FIELDS[conditions.get("year_kind", "first_publication")])
        if year is None or (lo is not None and year < lo) or (hi is not None and year > hi):
            return False
    if conditions.get("theme_query") and not poem.get("theme_summary"):
        return False
    return True
