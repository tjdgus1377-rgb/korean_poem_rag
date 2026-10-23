import copy
from types import SimpleNamespace

import pytest

from sidam.comparison import compare_case
from sidam.prompts import Prompts


class Spy:
    def __init__(self): self.calls=[]
    def complete(self, system, payload, **kw):
        self.calls.append((system,copy.deepcopy(payload),kw))
        return '제공된 원문입니다. [근거 1]'


def inputs():
    poem={'poem_id':'a','title':'작품','author':'시인','theme_summary':'외부 비밀 요약','first_publication_year':1922}
    original={'poem_id':'a','source_id':'TEXT_a','document_type':'poem_text','source_title':'전문','text':'첫 구절\n끝 구절','rights_status':'verified'}
    external={'poem_id':'a','source_id':'COMMENT_a','document_type':'commentary','source_title':'해설','text':'원문에 없는 해설','rights_status':'verified'}
    return poem,original,external


def test_comparison_has_common_original_and_never_supplies_gold_or_metadata():
    poem,original,external=inputs()
    model=Spy()
    store=SimpleNamespace(retrieve=lambda *a,**kw:[{'poem_id':'a','document_type':'metadata','text':'외부 비밀 요약'},original,external])
    result=compare_case({'case_id':'A1','question':'질문','minimum_points':['골드 정답']},poem,original,store,Prompts(model))
    assert result['order']==['without_external','with_external']
    assert len(model.calls)==2
    a,b=model.calls
    assert a[0]==b[0] and a[2]==b[2]
    assert a[1]['poem']==b[1]['poem']=={'title':'작품','author':'시인'}
    assert a[1]['question']==b[1]['question']=='질문'
    assert a[1]['documents']==b[1]['documents'][:1]
    assert len(a[1]['documents'])==1 and len(b[1]['documents'])==2
    assert '외부 비밀 요약' not in str(model.calls) and '골드 정답' not in str(model.calls)
    assert not a[1]['previous_messages'] and not b[1]['previous_messages']


@pytest.mark.parametrize('change',[{'poem_id':'b'},{'rights_status':'pending'}])
def test_bad_external_evidence_rejected_before_generation(change):
    poem,original,external=inputs(); model=Spy()
    store=SimpleNamespace(retrieve=lambda *a,**kw:[{**external,**change}])
    with pytest.raises(ValueError): compare_case({'case_id':'A1','question':'질문'},poem,original,store,Prompts(model))
    assert model.calls==[]


def test_no_external_stays_empty_and_each_arm_validates_its_own_citations():
    poem,original,external=inputs()
    class InvalidInA(Spy):
        def complete(self, system,payload,**kw):
            return '설명 [근거 2]'
    result=compare_case({'case_id':'A1','question':'질문'},poem,original,SimpleNamespace(retrieve=lambda *a,**kw:[external]),Prompts(InvalidInA()),reverse=True)
    assert result['order']==['with_external','without_external']
    assert result['arms']['without_external']['citation_error']
    assert not result['arms']['with_external']['citation_error']
    empty=compare_case({'case_id':'A2','question':'질문'},poem,original,SimpleNamespace(retrieve=lambda *a,**kw:[]),Prompts(Spy()))
    assert empty['external_count']==0
    assert len(empty['arms']['with_external']['sources'])==1
