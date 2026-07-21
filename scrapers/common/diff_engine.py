"""
Gap 분석용 diff 엔진
- 개정 전(old_text) / 개정 후(new_text) 조문 텍스트를 받아
  프론트엔드(docs/app.js)가 그리는 gap JSON 스키마로 변환한다.
- CanLII(https://www.canlii.org/webdiff/...) 스타일처럼
  동일 구간은 생략(collapsed), 삭제는 red, 추가는 blue로 구분한다.
- 신규 제정(old_text 없음)인 경우 old를 N.A. 로 표기한다.

주의: 실제 조문 원문(PDF/HWP)에서 조 단위 텍스트를 추출하는 부분은
기관별로 문서 포맷이 달라 개별 파서(agency 스크립트)에서 처리해야 한다.
이 모듈은 "조문 텍스트 두 개를 받으면 diff 구조를 만들어준다"는 공통 부분만 담당한다.
"""
import difflib


def _split_sentences(text: str):
    # 아주 단순한 문장/절 단위 분리자. 실제 운영시 형태소 분석기(예: kiwipiepy)로 교체 권장.
    import re
    parts = re.split(r'(?<=[.;·]\s)|(?<=\n)', text.strip())
    return [p.strip() for p in parts if p.strip()]


def build_section_diff(section_title: str, old_text: str, new_text: str, collapse_min_len=1):
    """
    old_text 가 None/빈 문자열이면 '신규 제정'으로 처리한다.
    반환값은 docs/app.js 가 기대하는 section dict.
    """
    if not old_text:
        return {
            "section_title": section_title,
            "status": "new",
            "blocks": [
                {"type": "na", "note": "N.A. (신규 제정 조항)"},
                {"type": "added", "text": new_text.strip()},
            ],
        }

    old_sents = _split_sentences(old_text)
    new_sents = _split_sentences(new_text)

    sm = difflib.SequenceMatcher(a=old_sents, b=new_sents, autojunk=False)
    blocks = []
    changed = False
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            seg = old_sents[i1:i2]
            if len(seg) > collapse_min_len:
                blocks.append({"type": "unchanged_collapsed", "note": f"{len(seg)}개 문장 동일"})
            else:
                for s in seg:
                    blocks.append({"type": "unchanged", "text": s})
        elif tag == "delete":
            changed = True
            for s in old_sents[i1:i2]:
                blocks.append({"type": "deleted", "text": s})
        elif tag == "insert":
            changed = True
            for s in new_sents[j1:j2]:
                blocks.append({"type": "added", "text": s})
        elif tag == "replace":
            changed = True
            for s in old_sents[i1:i2]:
                blocks.append({"type": "deleted", "text": s})
            for s in new_sents[j1:j2]:
                blocks.append({"type": "added", "text": s})

    return {
        "section_title": section_title,
        "status": "changed" if changed else "unchanged",
        "blocks": blocks,
    }


def build_gap_document(gap_id, regulation_title, old_label, new_label, section_pairs):
    """
    section_pairs: [(section_title, old_text_or_None, new_text), ...]
    """
    sections = [
        build_section_diff(title, old_text, new_text)
        for (title, old_text, new_text) in section_pairs
    ]
    return {
        "id": gap_id,
        "is_sample": False,
        "regulation_title": regulation_title,
        "old_version_label": old_label,
        "new_version_label": new_label,
        "new_enactment": all(o is None for (_, o, _n) in section_pairs),
        "sections": sections,
    }
