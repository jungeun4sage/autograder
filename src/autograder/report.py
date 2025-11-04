"""
리포팅/통계/로그용 문자열 생성
"""

from typing import Iterable, List
import pandas as pd

def build_stats_block(df: pd.DataFrame) -> List[str]:
    if df is None or df.empty:
        return ["SCORE STATS:", "- mean=0.0, median=0.0, min=0.0", "STATUS × OUTPUT_MATCH (counts):", "(no data)"]

    score_mean = float(df["score"].astype(float).mean())
    score_median = float(df["score"].astype(float).median())
    score_min = float(df["score"].astype(float).min())

    ct = (
        df.groupby(["status", "output_match"])
          .size()
          .reset_index(name="count")
          .pivot_table(index="status", columns="output_match", values="count", fill_value=0)
          .sort_index()
    )

    ct_lines = []
    if not ct.empty:
        col_order = [c for c in ["ZERO", "ERROR", "MISSING", "MISMATCH", "OK"] if c in ct.columns]
        ct = ct[col_order]
        header = " " * 14 + " | " + " | ".join([f"{c:>8}" for c in col_order])
        sep = "-" * len(header)
        ct_lines.append(header); ct_lines.append(sep)
        for idx, row in ct.iterrows():
            ct_lines.append(f"{str(idx):>14} | " + " | ".join([f"{int(row[c]):8d}" for c in col_order]))
    else:
        ct_lines.append("(no data)")

    return [
        "SCORE STATS:",
        f"- mean={score_mean:.1f}, median={score_median:.1f}, min={score_min:.1f}",
        "STATUS × OUTPUT_MATCH (counts):",
        *ct_lines
    ]

def build_excluded_summary_line(excluded_req_all: Iterable[str], excluded_opt_all: Iterable[str], key=None):
    """
    정답 출력 없음으로 채점 제외된 라벨을 한 줄 요약 문자열로 변환.
    """
    excluded_req_all = set(excluded_req_all or [])
    excluded_opt_all = set(excluded_opt_all or [])

    req_str = ", ".join(sorted(excluded_req_all, key=key)) if excluded_req_all else "없음"
    opt_str = ", ".join(sorted(excluded_opt_all, key=key)) if excluded_opt_all else "없음"
    return req_str, opt_str
