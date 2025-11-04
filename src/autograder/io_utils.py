"""
경로/시간/파일/이름 유틸 + 설정 로더
"""

import os, re, unicodedata, datetime as dt
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime, timedelta, timezone

# ---- Time (KST)
KST = dt.timezone(dt.timedelta(hours=9))
def now_kst(): 
    return dt.datetime.now(tz=KST)

def mtime_kst(path_str: str):
    ts = os.path.getmtime(path_str)
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).astimezone(KST)

def _mtime_kst_str(path: str) -> str:
    try:
        ts = os.path.getmtime(path)
        return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).astimezone(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    except Exception:
        return ""

def _filesize_bytes(path: str) -> int:
    try:
        return os.path.getsize(path)
    except Exception:
        return -1

# ---- Student id / name
def extract_id_and_name(p: Path) -> Tuple[str, str]:
    name = ""
    sid = None
    fname = unicodedata.normalize("NFC", p.name)
    stem  = unicodedata.normalize("NFC", p.stem)

    m = re.search(r"(\d{7,})[ _-]+(.+)\.ipynb$", fname, re.IGNORECASE)
    if m:
        sid = m.group(1)
        name = m.group(2)
        name = re.sub(r"[_ ]?\((\d+)\)$", "", name)
        name = re.sub(r"[_ ]?（(\d+)）$", "", name)  # 전각
        name = name.strip().replace("_"," ")
        name = re.sub(r"\s{2,}", " ", name)
    else:
        m2 = re.search(r"(\d{7,})", stem)
        if m2:
            sid = m2.group(1)

    if not name:
        try:
            import nbformat
            nb_ = nbformat.read(str(p), as_version=4)
            for c in nb_.cells:
                if c.cell_type == "code":
                    src = unicodedata.normalize("NFC", c.source or "")
                    m3 = re.search(r"(?:NAME|STUDENT_NAME|학생명|이름|성명)\s*=\s*['\"]([^'\"]+)['\"]", src, re.I)
                    if m3: name = m3.group(1).strip(); break
            if not name:
                for c in nb_.cells:
                    if c.cell_type == "markdown":
                        txt = unicodedata.normalize("NFC", c.source or "")
                        m4 = re.search(r"(?:이름|성명)\s*[:：]\s*([^\n]+)", txt)
                        if m4: name = m4.group(1).strip(); break
            if not name:
                md = getattr(nb_, "metadata", {}) or {}
                for key in ("student_name","name","성명","이름"):
                    if key in md and str(md[key]).strip():
                        name = str(md[key]).strip(); break
        except Exception:
            pass

    if not sid:  sid = f"UNIDENTIFIED_{stem}"
    if not name: name = "이름미상"
    name = unicodedata.normalize("NFC", name)
    return sid, name

# ---- Config loader (optional)
def load_config(toml_path: str, session: int, env: str) -> Dict[str, Any]:
    """
    config/sessions.toml 에서 세션/환경별 경로 로드
    """
    try:
        import tomllib  # Python 3.11+
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
    except Exception:
        # tomllib가 없으면 최소 파서(단일 depth)로 대체 가능하지만
        # 운영에서는 tomllib(또는 tomli) 사용을 권장.
        raise

    key = f"session_{int(session)}"
    env = env.upper()
    block = data[key][env]
    return {
        "template_path": block["TEMPLATE_PATH"],
        "answer_path": block["ANSWER_PATH"],
        "submit_dir":    block["SUBMIT_DIR"],
        "out_dir":       block["OUT_DIR"],
    }
