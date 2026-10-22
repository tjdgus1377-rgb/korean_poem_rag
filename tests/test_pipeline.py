class Store:
    def __init__(self, evidence):
        self.evidence = evidence
    def retrieve(self, poem_id, question, quote=""):
        return self.evidence


class Generator:
    def __init__(self, answer="설명입니다. [근거 1]"):
        self.output = answer
        self.calls = 0
    def answer(self, poem, question, evidence, mode="chat", quote="", messages=None, repair=False):
        self.calls += 1
        return self.output


def test_graph_has_only_retrieve_generate_and_handles_no_evidence():
    from sidam.pipeline import build_graph
    gen = Generator()
    graph = build_graph(Store([]), gen)
    assert set(graph.get_graph().nodes) == {"__start__", "retrieve", "generate", "__end__"}
    result = graph.invoke({"poem": {"poem_id": "a"}, "question": "미확인 의도"})
    assert "확인되지" in result["answer"]
    assert gen.calls == 0


def test_graph_rejects_bad_citations_after_one_retry():
    from sidam.pipeline import build_graph
    gen = Generator("없는 출처 [근거 99]")
    graph = build_graph(Store([{"poem_id": "a", "text": "자료", "document_type": "metadata"}]), gen)
    result = graph.invoke({"poem": {"poem_id": "a"}, "question": "제목은?"})
    assert result["citation_error"]
    assert gen.calls == 2
    assert "99" not in result["answer"]
