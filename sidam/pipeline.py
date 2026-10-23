from typing import TypedDict
import time
from langgraph.graph import StateGraph, START, END

from .citations import citation_numbers, invalid_citations


class State(TypedDict, total=False):
    poem: dict
    question: str
    quote: str
    mode: str
    messages: list
    evidence: list
    answer: str
    citation_error: bool
    timings: dict
    retrieval_mode: str


def build_graph(store, generator):
    def retrieve(state):
        started = time.monotonic()
        options = {'search_type':'mmr'} if state.get('retrieval_mode') == 'mmr' else {}
        evidence = store.retrieve(state["poem"]["poem_id"], state["question"], state.get("quote", ""), **options)
        return {"evidence": evidence, "timings": {'retrieve_seconds': time.monotonic() - started}}

    def generate(state):
        evidence = state["evidence"]
        started = time.monotonic()
        def result(answer, error=False):
            return {'answer': answer, 'citation_error': error, 'timings': {**state['timings'], 'generate_seconds': time.monotonic() - started if evidence else 0.0}}
        if not evidence:
            return result("제공된 자료에서는 확인되지 않습니다.")
        for attempt in range(2):
            answer = generator.answer(state["poem"], state["question"], evidence, mode=state.get("mode", "chat"), quote=state.get("quote", ""), messages=state.get("messages"), repair=bool(attempt))
            unknown = "확인되지" in answer or "확인할 수 없" in answer
            if not invalid_citations(answer, evidence):
                if citation_numbers(answer):
                    return result(answer)
                if unknown:
                    return result("제공된 자료에서는 확인되지 않습니다.")
        return result("근거 번호를 확인하지 못했습니다. 다시 질문해 주세요.", True)

    graph = StateGraph(State)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)
    return graph.compile()
