# src/autograder/similarity.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pandas as pd
from autograder.io_utils import _mtime_kst_str, _filesize_bytes

def compute_similarity_pairs(
    fps: Dict[str, Any],
    sid2file: Dict[str, str],
    sid2path: Dict[str, Path],
    sid2name: Dict[str, str],
    sim_func,
    threshold: float = 0.99
) -> Tuple[List[list], pd.DataFrame]:
    """
    학생 제출물 간 코드 유사도(pairwise) 계산.

    Args:
        fps: {student_id: fingerprint_object}
        sid2file, sid2path, sid2name: 학생 id → 정보 매핑
        sim_func: 유사도 계산 함수, ex) lambda a,b: _sim(a,b)
        threshold: 유사도로 필터할 기준값

    Returns:
        pairs (list of lists), df_sim (DataFrame)
    """
    sids = list(fps.keys())
    pairs = []

    for i, a in enumerate(sids):
        for b in sids[i + 1:]:
            sab = sim_func(fps[a], fps[b])
            if sab >= threshold:
                file_a, file_b = sid2file.get(a, ""), sid2file.get(b, "")
                path_a, path_b = sid2path.get(a, ""), sid2path.get(b, "")
                name_a, name_b = sid2name.get(a, ""), sid2name.get(b, "")

                try:
                    mtime_a = _mtime_kst_str(path_a) if path_a else ""
                    mtime_b = _mtime_kst_str(path_b) if path_b else ""
                    size_a = _filesize_bytes(path_a) if path_a else -1
                    size_b = _filesize_bytes(path_b) if path_b else -1
                except Exception:
                    mtime_a, mtime_b, size_a, size_b = "", "", -1, -1

                pairs.append([
                    a, name_a, file_a, mtime_a, size_a,
                    b, name_b, file_b, mtime_b, size_b,
                    f"{sab:.3f}"
                ])

    df_sim = pd.DataFrame(
        pairs,
        columns=[
            "student_a", "name_a", "file_a", "mtime_a_kst", "size_a_bytes",
            "student_b", "name_b", "file_b", "mtime_b_kst", "size_b_bytes",
            "similarity"
        ]
    )

    return pairs, df_sim
