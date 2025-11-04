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
