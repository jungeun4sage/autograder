# src/autograder/grading.py
from __future__ import annotations
from pathlib import Path
from typing import Iterable, Dict, List, Tuple
import nbformat
import pandas as pd
import re

from .policy import (
    BASE_SCORE,
    PENALTY_REQUIRED_MISS,
    PENALTY_REQUIRED_MISMATCH,
    PENALTY_OPTIONAL_MISS,
    outputs_equal,
    decide_status_and_match,
)
from .nb_utils import _label_map, _nb_fingerprint, _cell_output_text, _nb_exec_pattern
from .io_utils import now_kst, mtime_kst, extract_id_and_name

# summary normalizer for statsmodels (Date/Time line remover)
# 전역 스위치: 기본 ON, 필요시 False로 바꿔도 됨
NORMALIZE_DATETIME_DEFAULT = True

_DATE_TIME_PATTERNS = [
    r"Date:\s+[A-Za-z]{3},\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}",
    r"Time:\s*\d{2}:\d{2}:\d{2}",
]
_NORMALIZER_RE = re.compile("|".join(_DATE_TIME_PATTERNS),flags=re.MULTILINE)

def _normalize_summary_text(s: str) -> str:
    if not isinstance(s, str):
        return s
    s = _NORMALIZER_RE.sub("", s)
    return s.strip()

def _maybe_normalize(s: str, enable: bool = NORMALIZE_DATETIME_DEFAULT) -> str:
    return _normalize_summary_text(s) if enable else s



def _label_key(x: str) -> List[int]:
    """라벨 정렬 키: '1.2.3' -> [1,2,3]"""
    try:
        return [int(t) for t in x.split(".")]
    except Exception:
        return [999999]


def _exec_and_out_expected(stu_map: dict, ans_map: dict, lab: str) -> Tuple[bool, str, bool]:
    """
    expected_output: 정답 셀 출력 유무(True/False)
      - True  → 학생 출력이 있어야 '실행' 인정
      - False → 채점 제외(정보만 반환)
    Returns: (executed, stu_out_text, expected_output)
    """
    sinfo = stu_map.get(lab)
    anscell = ans_map.get(lab, {}).get("cell")
    ans_out = _cell_output_text(anscell) if anscell else ""
    expected_output = bool(ans_out)

    if not sinfo:
        return False, "", expected_output

    scell = sinfo["cell"]
    stu_out = _cell_output_text(scell)
    executed = bool(stu_out) if expected_output else (
        bool(stu_out) or (scell.get("execution_count") not in (None, 0))
    )
    return executed, stu_out, expected_output


def grade_submissions(
    submit_paths: Iterable[Path],
    template_path: Path,
    answer_path: Path,
    tagged_template_path: Path,
    req_labels: List[str],
    opt_labels: List[str],
    template_fingerprint: dict,
    template_sim_threshold: float = 0.98,
) -> Tuple[
    pd.DataFrame,                 # summary_df
    Dict[str, dict],              # fps
    Dict[str, str],               # sid2file
    Dict[str, str],               # sid2name
    Dict[str, Path],              # sid2path
    List[list],                   # today_rows_tmp (summary row 리스트)
    set,                          # EXCLUDED_REQ_ALL
    set,                          # EXCLUDED_OPT_ALL
]:
    """
    제출물 전체 채점. (이전 Step5 로직을 함수화)
    """

 
    rows: List[list] = []
    today_rows_tmp: List[list] = []
    fps: Dict[str, dict] = {}
    eps : Dict [str, dict] ={}
    sid2file: Dict[str, str] = {}
    sid2name: Dict[str, str] = {}
    sid2path: Dict[str, Path] = {}
    EXCLUDED_REQ_ALL, EXCLUDED_OPT_ALL = set(), set()

    # 템플릿/정답/태깅본 제외
    skip_names = {template_path.name, answer_path.name, tagged_template_path.name}

    # 정답/태깅본 로드
    ans = nbformat.read(answer_path, as_version=4)

    for p in submit_paths:
        if p.name in skip_names:
            continue

        sid, name = extract_id_and_name(p)
        sid2name[sid], sid2path[sid] = name, p

        # 노트북 로드
        try:
            nb = nbformat.read(p, as_version=4)
        except Exception as e:
            row = [sid, name, p.name, 0.0, "ERROR", "ipynb 파싱 실패", "ERROR", f"노트북 파싱 실패: {e}",0,"",""]
            rows.append(row)
            try:
                if mtime_kst(p).date() == now_kst().date():
                    today_rows_tmp.append(row)
            except Exception:
                pass
            continue

        # 템플릿 유사도(원본/무변경 → 0점)
        fp = _nb_fingerprint(nb)
        ep = _nb_exec_pattern(nb)
        fps[sid],eps[sid], sid2file[sid] = fp,ep, p.name
        from_sim_template = False
        try:
            from_sim_template = (template_fingerprint is not None)
        except Exception:
            pass

        if from_sim_template and template_fingerprint and template_sim_threshold is not None:
            # 템플릿과 유사한 경우 0점 처리
            # (이 조건은 이전 노트북 로직과 동일)
            from .nb_utils import _sim
            if _sim(fp, template_fingerprint) >= template_sim_threshold:
                row = [
                    sid, name, p.name, 0.0, "ZERO",
                    "템플릿과 거의 동일(원본/무변경)", "ZERO",
                    "템플릿과 거의 동일하여 0점 처리되었습니다." ,len(fp or""),fp,ep
                ]
                rows.append(row)
                try:
                    if mtime_kst(p).date() == now_kst().date():
                        today_rows_tmp.append(row)
                except Exception:
                    pass
                continue

        # 라벨 맵
        stu_lmap, ans_lmap = _label_map(nb), _label_map(ans)

        # 채점: 필수/옵션
        req_missing, req_mismatch, opt_missing = [], [], []
        excluded_req, excluded_opt = [], []

        # 1) 필수
        for lab in sorted(req_labels, key=_label_key):
            executed, stu_out, expected_output = _exec_and_out_expected(stu_lmap, ans_lmap, lab)
            if not expected_output:
                excluded_req.append(f"#{lab}")
                continue
            anscell = ans_lmap.get(lab, {}).get("cell")
            ans_out = _cell_output_text(anscell) if anscell else ""
            if not executed:
                req_missing.append(f"#{lab}")
                continue

            _stu_cmp = _maybe_normalize(stu_out)
            _ans_cmp  = _maybe_normalize(ans_out)

            if not outputs_equal(_stu_cmp, _ans_cmp):
                req_mismatch.append(f"#{lab}")

        # 2) 옵션
        for lab in sorted(opt_labels, key=_label_key):
            executed, _stu_out, expected_output = _exec_and_out_expected(stu_lmap, ans_lmap, lab)
            if not expected_output:
                excluded_opt.append(f"#{lab}")
                continue
            if not executed:
                opt_missing.append(f"#{lab}")

        # 점수 계산
        score = (
            BASE_SCORE
            - PENALTY_REQUIRED_MISS * len(req_missing)
            - PENALTY_REQUIRED_MISMATCH * len(req_mismatch)
            - PENALTY_OPTIONAL_MISS * len(opt_missing)
        )

        # 상태/피드백
        status, output_match = decide_status_and_match(req_missing, req_mismatch)
        reason = "" if status == "OK" else "필수 미실행/불일치 존재"

        parts: List[str] = []
        if req_missing:
            parts.append(f"[필수 미실행 {len(req_missing)}개] 셀: {', '.join(req_missing)}")
        if req_mismatch:
            parts.append(f"[필수 출력 불일치 {len(req_mismatch)}개] 셀: {', '.join(req_mismatch)}")
        if opt_missing:
            parts.append(f"[연습 미실행 {len(opt_missing)}개] 셀: {', '.join(opt_missing)}")

        score_line = (
            f"(채점) base={BASE_SCORE}"
            f"{' − ' + str(PENALTY_REQUIRED_MISS)    + '×' + str(len(req_missing))  + '(필수 미실행)' if req_missing else ''}"
            f"{' − ' + str(PENALTY_REQUIRED_MISMATCH)+ '×' + str(len(req_mismatch)) + '(필수 불일치)' if req_mismatch else ''}"
            f"{' − ' + str(PENALTY_OPTIONAL_MISS)    + '×' + str(len(opt_missing))  + '(연습 미실행)' if opt_missing else ''}"
            f" = {score}"
        )

        feedback = ("\n".join(parts) if parts else "정상 제출로 판단되었습니다. 수고했습니다!") + f"\n{score_line}"
        row = [sid, name, p.name, score, status, reason, output_match, feedback.strip(), len(fp or ""), fp, ep]
        rows.append(row)

        try:
            if mtime_kst(p).date() == now_kst().date():
                today_rows_tmp.append(row)
        except Exception:
            pass

        EXCLUDED_REQ_ALL.update(excluded_req)
        EXCLUDED_OPT_ALL.update(excluded_opt)

    summary_df = pd.DataFrame(
        rows,
        columns=["student_id", "student_name", "file", "score", "status", "reasons", "output_match", "feedback", "fp_length", "finger_print","exec_pattern"],
    )

    return (
        summary_df,
        fps,
        eps,
        sid2file,
        sid2name,
        sid2path,
        today_rows_tmp,
        EXCLUDED_REQ_ALL,
        EXCLUDED_OPT_ALL,
    )
