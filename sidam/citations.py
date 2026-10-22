import re

PATTERN = re.compile(r"\[근거\s*([\d,\s]+)\]")


def citation_numbers(answer):
    return {int(n.strip()) for group in PATTERN.findall(answer) for n in group.split(",") if n.strip().isdigit()}


def cited_sources(answer, sources):
    return [(i, s) for i, s in enumerate(sources, 1) if i in citation_numbers(answer)]


def invalid_citations(answer, sources):
    return citation_numbers(answer) - set(range(1, len(sources) + 1))
