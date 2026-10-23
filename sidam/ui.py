"""Streamlit 화면: 작품 찾기, 원문, 작품별 대화, 구절 해설."""
from pathlib import Path
import logging
import traceback

import streamlit as st

from .citations import cited_sources
from .config import Config
from .data import normalize, read_json
from .identity import lexical_search
from .models import ModelError
from .service import Service
from .session import add_message, history, validate_quote


@st.cache_resource
def get_service(root, settings_mtime):
    return Service(Config.load(root))


def render_sources(answer, sources):
    used = cited_sources(answer, sources)
    if not used:
        st.caption("답변에 인용된 근거가 없습니다.")
        return
    with st.expander(f"답변에 사용한 근거 {len(used)}건"):
        for number, source in used:
            st.write(f"[근거 {number}] {source.get('source_title', '자료')}")
            st.caption(" · ".join(str(source.get(k, "")) for k in ("source_type", "content_origin", "access_scope", "locator")))
            if source.get("source_url", "").startswith("https://"):
                st.link_button("원문 열기", source["source_url"])
            if source.get("usage_terms"):
                st.caption(source["usage_terms"])


def choose_poem(pid):
    st.session_state["selected_poem"] = pid
    st.session_state["quick_filter"] = ""
    st.session_state["main_tab"] = "작품 읽기 · 질문"


def selection_changed():
    if st.session_state.get("selected_poem"):
        st.session_state["main_tab"] = "작품 읽기 · 질문"


def run_question(service, pid, question, mode="chat", quote=""):
    try:
        with st.status("자료를 확인하고 있습니다…", expanded=True) as progress:
            previous = list(history(st.session_state, pid))
            result = service.ask(pid, question, mode, quote, previous, status=lambda text: progress.update(label=text))
            progress.update(label="답변 준비 완료", state="complete", expanded=False)
        add_message(st.session_state, pid, {"role": "user", "content": question})
        add_message(st.session_state, pid, {"role": "assistant", "content": result["answer"], **result})
        st.rerun()
    except (ModelError, ValueError) as e:
        st.warning(str(e))
    except Exception as exc:
        frames = [(Path(f.filename).name, f.lineno, f.name) for f in traceback.extract_tb(exc.__traceback__)]
        logging.getLogger("sidam").error("응답 처리 실패: %s 위치=%s", type(exc).__name__, frames)
        st.error("처리를 완료하지 못했습니다. 연결·설정을 확인하고 다시 시도해 주세요.")


def main():
    st.set_page_config(page_title="시담 · 시를 읽고 묻다", page_icon="📖", layout="wide")
    st.title("시담")
    st.caption("한국 근대시 100편 · 원문을 읽고, 근거를 따라 해석을 나누세요.")
    root = Path(__file__).resolve().parents[1]
    try:
        service = get_service(str(root), (root / "sidam.toml").stat().st_mtime_ns)
    except Exception:
        st.error("자료 또는 색인을 열지 못했습니다. 데이터 파일과 설정을 확인하세요.")
        return
    counts = service.store.counts()
    with st.sidebar:
        st.header("읽을 시 선택")
        quick = st.text_input("제목·시인 빠른 찾기", key="quick_filter", placeholder="진달래꽃 또는 김소월")
        lexical = lexical_search(quick, service.poems, read_json(service.config.data_dir / 'curation/search_aliases.json', {})) if quick else None
        ids = lexical[0] if lexical is not None else [pid for pid, p in service.poems.items() if not quick or normalize(quick) in normalize(p["title"] + p["author"])]
        if st.session_state.get("selected_poem") not in ids:
            st.session_state["selected_poem"] = None
        selected = st.selectbox("작품 목록", ids, index=None, key="selected_poem", on_change=selection_changed, placeholder="시를 골라주세요", format_func=lambda pid: f"{service.poems[pid]['title']} · {service.poems[pid]['author']}")
        st.caption(f"작품 {len(service.poems)}편 · 작품 색인 {counts['poems']}건 · 근거 청크 {counts['poem_evidence']}건")
        if not service.models:
            st.info("GMS_KEY가 없습니다. 작품 열람은 가능하며, 의미 검색·색인·답변에는 키 설정이 필요합니다.")
        if not counts["poems"]:
            st.info("검색 색인이 없습니다. 아래에서 색인을 준비하세요.")
        if st.button("검색 색인 준비·갱신", disabled=not service.models, width="stretch"):
            try:
                with st.status("검색 색인을 준비합니다…", expanded=True) as p:
                    result = service.index(status=lambda text: p.update(label=text))
                    p.update(label=f"작품 {result['poems']}건 · 근거 {result['poem_evidence']}건 색인 완료", state="complete")
                st.success(f"{result['elapsed_seconds']}초 · 동일 자료는 다시 임베딩하지 않습니다.")
                st.rerun()
            except ModelError as e:
                st.error(str(e))
            except Exception:
                st.error("색인 준비에 실패했습니다. 연결·설정·자료를 확인하세요.")
        st.caption(f"청크 {service.config.chunk_size}자 / 중복 {service.config.chunk_overlap}자 / 외부 근거 {service.config.top_k}건")
        st.caption(f"이용 범위 미확인 등으로 제외한 자료 {len(service.excluded)}건. 미확인 자료는 근거 색인에 넣지 않습니다.")
        if selected and st.button("이 작품 대화 지우기"):
            st.session_state.setdefault("messages_by_poem_id", {})[selected] = []
            st.rerun()
    find_tab, read_tab = st.tabs(["조건으로 작품 찾기", "작품 읽기 · 질문"], key="main_tab", on_change="rerun")
    with find_tab:
        st.subheader("어떤 시를 찾고 있나요?")
        st.caption("예: 김소월의 이별을 다룬 시 / 1920년대에 처음 발표된 시 · 연도 미확인 작품은 해당 연도 조건에서 제외합니다.")
        with st.form("poem_search"):
            query = st.text_input("검색 조건", placeholder="시인, 발표 연도, 주제 등을 입력하세요")
            submitted = st.form_submit_button("조건 검색", disabled=not service.models or not counts["poems"])
        if submitted and query.strip():
            try:
                with st.spinner("조건에 맞는 작품을 찾습니다…"):
                    results, conditions = service.search(query)
                st.session_state["search_results"] = [p["poem_id"] for p in results]
                st.session_state["search_conditions"] = conditions
            except (ValueError, ModelError) as e:
                st.warning(str(e))
            except Exception:
                st.error("작품 검색을 완료하지 못했습니다. 다시 시도해 주세요.")
        if "search_results" in st.session_state:
            if st.session_state.get('search_conditions', {}).get('match_kind'):
                st.caption('오탈자 후보입니다. 제목과 시인을 확인한 뒤 작품을 선택하세요.')
            if not st.session_state["search_results"]:
                st.info("조건에 맞는 작품을 찾지 못했습니다.")
            for pid in st.session_state["search_results"]:
                p = service.poems[pid]
                with st.container(border=True):
                    st.write(f"**{p['title']}** · {p['author']}")
                    st.caption(f"최초 발표: {p.get('first_publication_year', '미확인')} · 시집 간행: {p.get('collection_publication_year', '미확인')}")
                    st.write(p["theme_summary"][:350] or "주제 설명 미확인")
                    st.button("이 작품 읽기", key=f"choose_{pid}", on_click=choose_poem, args=(pid,))
    with read_tab:
        if not selected:
            st.info("왼쪽 목록에서 읽고 싶은 시를 선택하세요.")
            return
        poem = service.poems[selected]
        st.subheader(f"{poem['title']} · {poem['author']}")
        st.caption(f"최초 발표 {poem.get('first_publication_year', '미확인')} · 시집 간행 {poem.get('collection_publication_year', '미확인')} · 창작 {poem.get('written_year', '미확인')}")
        if poem.get("reported_year") and poem.get("reported_year_kind") == "unknown":
            st.caption(f"원시 자료의 연도 {poem['reported_year']}년은 종류 확인 전이라 최초 발표 검색에 사용하지 않습니다.")
        left, right = st.columns([1, 1.3])
        with left:
            st.markdown("**시 전문**")
            with st.container(height=440, border=True):
                st.text(poem["text"])
            st.link_button("전문 출처", poem["text_source_url"])
            with st.expander("해설 기반 주제 설명"):
                st.write(poem["theme_summary"] or "주제 설명 미확인")
                st.caption("작품별 확인한 해석 노트의 요약입니다. 모든 구절의 유일한 해석이나 시인의 실제 의도를 뜻하지 않습니다.")
            with st.form(f"quote_{selected}"):
                quote = st.text_area("해설할 구절", placeholder="위 작품에 있는 구절을 입력하세요")
                card = st.form_submit_button("구절 해설 카드 만들기", disabled=not service.models or not counts["poems"])
            if card:
                if not validate_quote(poem["text"], quote):
                    st.warning("표시된 작품에 있는 구절을 선택하세요.")
                else:
                    run_question(service, selected, f"선택한 구절의 표현과 가능한 의미, 배경을 근거와 한계와 함께 설명해주세요: {quote}", "card", quote)
        with right:
            st.markdown("**작품에 질문하기**")
            st.caption("확인된 사실과 가능한 해석을 구분합니다. 자료가 부족한 부분은 단정하지 않습니다.")
            for message in history(st.session_state, selected):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if message["role"] == "assistant":
                        render_sources(message["content"], message.get("sources", []))
                        for warning in message.get("warnings", []):
                            st.caption(warning)
                        st.caption(f"처리 시간 {message.get('timings', {}).get('total_seconds', '?')}초")
            question = st.chat_input("이 시의 구절·상징·배경을 물어보세요", disabled=not service.models or not counts["poems"])
            if question:
                run_question(service, selected, question)
