"""
노트북 파싱/라벨/출력 유틸 모듈
"""

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Any, List

LABEL_PATTERN = re.compile(r'^\s*#\s*([0-9]+(?:\.[0-9]+)*)')

def _extract_label(text: str):
    if not text:
        return None
    text = text.replace("\ufeff","")
    text_norm = unicodedata.normalize("NFKC", text)
    m = LABEL_PATTERN.match(text_norm.strip())
    return m.group(1) if m else None

def _normalize_code(s: str) -> str:
    if not s: return ""
    lines = [ln for ln in s.splitlines() if not ln.strip().startswith("#")]
    import re as _re
    return _re.sub(r"\s+", " ", "\n".join(lines)).strip()

def _nb_fingerprint(nb) -> str:
    chunks=[]
    for c in nb.cells:
        if c.cell_type=="code":
            t=_normalize_code(c.source or "")
            if t: chunks.append(t)
    return " ".join(chunks)

def _nb_exec_pattern(nb) -> str:
    """
    노트북의 코드 셀 execution_count 시퀀스를 fingerprint로 변환.
    예: "1 2 3 5 6 4 None 7"
    """
    seq = []
    for c in nb.cells:
        if c.cell_type == "code":
            ec = c.get("execution_count", None)
            # 실행 안 된 셀은 'N' 같은 토큰으로 표시해도 되고, 그냥 건너뛰어도 됨
            if ec is None:
                seq.append("N")
            else:
                seq.append(str(ec))
    return " ".join(seq)


def _sim(a,b): 
    return SequenceMatcher(None, a or "", b or "").ratio()

def _label_map(nb) -> Dict[str, Dict[str, Any]]:
    m = {}
    for i, c in enumerate(nb.cells):
        if c.cell_type != "code":
            continue
        lab = _extract_label(c.source or "")
        if lab:
            m[lab] = {"idx": i, "cell": c}
    return m

def _indexes_with_labels(nb, idx_set) -> List[str]:
    items = []
    for i in sorted(idx_set):
        try:
            cell = nb.cells[i]
            lab = _extract_label(cell.source or "")
            items.append(f"{i}:{('#'+lab) if lab else '(no-label)'}")
        except Exception:
            items.append(f"{i}:(error)")
    return items

def _cell_output_text(cell) -> str:
    outs = cell.get("outputs", []) or []
    chunks = []
    for o in outs:
        ot = o.get("output_type")
        if ot in ("stream",):
            chunks.append(o.get("text", ""))
        elif ot in ("execute_result", "display_data"):
            data = o.get("data", {}) or {}
            if "text/plain" in data:
                chunks.append(data["text/plain"])
            elif "text/html" in data:
                import re as _re
                chunks.append(_re.sub(r"\s+", " ", data["text/html"]))
            elif "image/png" in data:
                chunks.append("[image/png]")
        elif ot in ("error",):
            chunks.append("ERROR:" + " ".join(o.get("traceback", [])))
    import re as _re, unicodedata as _ud
    text = "\n".join(chunks)
    text = _ud.normalize("NFC", text)
    text = _re.sub(r"\s+", " ", text).strip()
    return text

def _label_key_robust(label_str: str):
    """
    '#1.4.3' → [1,4,3] / 이상치는 뒤로 밀기
    """
    if not isinstance(label_str, str):
        return [999999]
    s = label_str.strip()
    if s.startswith('#'):
        s = s[1:]
    parts = [p for p in s.split('.') if p.isdigit()]
    if not parts:
        parts = re.findall(r'\d+', s)
    try:
        return [int(x) for x in parts] if parts else [999999]
    except Exception:
        return [999999]

# ================================================================
# @jennie 20251118
# [Course-Specific Custom Logic / Example Code]
# 이 코드는 KHCU MR24 11차시 과제(#3.5.2) 전용 커스터마이징 예제입니다.
# AutoGrader 엔진의 핵심 기능이 아니라, 개별 수업 요구사항에 맞도록
# 라벨 기반으로 특정 변수 값을 추출하는 '샘플 구현' 용도입니다.
# 향후 다른 과제/강의에서는 이 패턴을 참고해 수정하여 사용하십시오.
# ================================================================

def get_more_impact_352(nb, label: str = "3.5.2") -> str:
    """
    3.5.2 문제에서 학생이 선택한 more_impact 값을 추출.
    반환값: "reading" / "math" / ""(없거나 인식 불가)

    예:
        more_impact = "reading"
        more_impact = "reading score"
        more_impact = "Reading."
        more_impact = "math score"
    모두 인식 가능.
    """
    lmap = _label_map(nb)
    info = lmap.get(label)
    if not info:
        return ""

    cell = info.get("cell")
    if not cell:
        return ""

    src = cell.source or ""

    # more_impact = "..." 또는 '...' 형태 전체를 먼저 잡기
    m = re.search(r'more_impact\s*=\s*["\']([^"\']+)["\']', src, re.IGNORECASE)
    if not m:
        return ""

    # 따옴표 안 문자열 전체
    val = m.group(1).strip().lower()

    # 내용에 reading / math 포함 여부로 판별
    if "reading" in val:
        return "reading"
    if "math" in val:
        return "math"

    return ""