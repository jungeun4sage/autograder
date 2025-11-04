"""
리포팅/통계/로그용 문자열 생성
"""

from typing import Iterable, List, Any, Optional, Set
import pandas as pd
from pathlib import Path
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

def load_prev_ids(out_dir: Path) -> Set[str]:
    """OUT_DIR 내 최신 summary_static_with_name_*.csv에서 student_id 집합을 읽어온다.
    없거나 읽기 실패하면 빈 집합 반환."""
    try:
        files = sorted(
            Path(out_dir).glob("summary_static_with_name_*.csv"),
            key=lambda p: p.stat().st_mtime
        )
        if not files:
            return set()
        df = pd.read_csv(files[-1], dtype=str)
        if "student_id" not in df.columns:
            return set()
        return set(df["student_id"].astype(str))
    except Exception:
        return set()

def compute_new_ids(summary_df: pd.DataFrame, prev_ids: Iterable[str]) -> list[str]:
    """이번 런의 summary_df에서 이전에 없던 student_id만 정렬 리스트로 반환."""
    prev = set(str(x) for x in prev_ids) if prev_ids else set()
    curr = set(summary_df["student_id"].astype(str))
    return sorted(curr - prev)

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

def _fmt_n(n): 
    try: return f"{int(n):,}"
    except: return str(n)

def render_run_summary(CONFIG: dict, STATS_BLOCK):
    # STATS_BLOCK이 리스트든 문자열이든 처리
    if isinstance(STATS_BLOCK, (list, tuple)):
        stats_lines = list(STATS_BLOCK)
    else:
        stats_lines = [str(STATS_BLOCK)]
    
    lines = []
    # 헤더
    lines.append(f"✅ 완료: {CONFIG['OUT_DIR']}")
    lines.append(f"🕒 실행시각: {CONFIG['KST_NOW']}  [{CONFIG['TIMEZONE']}]")
    lines.append("")
    
    # 데이터 요약
    lines.append("📦 데이터 요약")
    lines.append(f"  • 전체 채점 학생 수 : {_fmt_n(CONFIG['TOTAL_CNT'])}명")
    lines.append(f"  • 새로 채점한 학생 수 : {_fmt_n(CONFIG['NEW_CNT'])}명")
    lines.append(f"  • 오늘 들어온 파일(KST {CONFIG['TODAY_DATE']}) : {_fmt_n(CONFIG['TODAY_CNT'])}건")
    lines.append("")
    
    # 산출물/경로
    lines.append("🗂 산출물/경로")
    lines.append(f"  • 실행 산출물 폴더 : executed/{CONFIG['RUN_TS']}/")
    lines.append(f"  • 제출 폴더(SUBMIT_DIR) : {CONFIG['SUBMIT_DIR']}")
    lines.append(f"  • OUT_DIR : {CONFIG['OUT_DIR']}")
    lines.append("")
    
    # 최신 파일들 (베이스네임)
    lines.append("🧾 최신 결과 파일")
    lines.append(f"  • 요약(SUMMARY)   : {CONFIG['SUMMARY_FILE_LATEST']}")
    lines.append(f"  • 유사도(SIMILAR) : {CONFIG['SIMILAR_FILE_LATEST']}")
    lines.append(f"  • Today NEW       : {CONFIG['NEWTODAY_FILE_LATEST']}")
    lines.append("")
    
    # 템플릿/정답/태깅본
    lines.append("📑 템플릿/정답/태깅본")
    lines.append(f"  • 템플릿 파일        : {CONFIG['TEMPLATE_FILE']}")
    lines.append(f"  • 정답 파일          : {CONFIG['ANSWER_FILE']}")
    lines.append(f"  • 템플릿 태깅본 파일 : {CONFIG['TAGGED_TEMP_FILE']}")
    lines.append(f"  • 태그 감사 CSV      : {CONFIG['TAG_AUDIT_FILE']}")
    lines.append("")
    
    # 채점 규칙/임계값
    lines.append("⚖️ 채점 규칙 / 임계값")
    lines.append(f"  • SCORE_RULE           : {CONFIG['SCORE_RULE']}")
    lines.append(f"  • SIM_THRESHOLD_TEMPLATE : {CONFIG['SIM_THRESHOLD_TEMPLATE']}")
    lines.append(f"  • SIM_THRESHOLD_PAIR     : {CONFIG['SIM_THRESHOLD_PAIR']}")
    lines.append("")
    
    # 필수/선택 셀 요약
    lines.append("🧩 Required / Optional 셀")
    lines.append(f"  • REQUIRED_CELL_COUNT : {_fmt_n(CONFIG['REQUIRED_CELL_COUNT'])}")
    lines.append(f"  • OPTIONAL_CELL_COUNT : {_fmt_n(CONFIG['OPTIONAL_CELL_COUNT'])}")
    # 제외 목록(있을 때만)
    if CONFIG.get("EXCLUDED_REQ_ALL"):
        lines.append(f"  • 제외된 필수 셀: {CONFIG['EXCLUDED_REQ_ALL']}")
    if CONFIG.get("EXCLUDED_OPT_ALL"):
        lines.append(f"  • 제외된 연습 셀: {CONFIG['EXCLUDED_OPT_ALL']}")
    lines.append("")
    
    # 통계 블록
    lines.append("📊 Score & Distribution Summary")
    lines.extend(stats_lines)
    
    return "\n".join(lines)

def _fmt_seq(seq: Iterable, max_items: int = 12) -> str:
    """리스트/튜플을 한 줄 요약. 길면 앞 n개 + more"""
    try:
        seq = list(seq)
    except TypeError:
        return str(seq)
    n = len(seq)
    if n <= max_items:
        return ", ".join(map(str, seq))
    head = ", ".join(map(str, seq[:max_items]))
    return f"{head} … (+{n - max_items} more)"

def _fmt_map(mp: Mapping, max_items: int = 12) -> str:
    """딕트를 k->v 형태로 한 줄 요약."""
    try:
        items = list(mp.items())
    except Exception:
        # dict가 아니거나 .items()가 없을 때는 json으로 시도
        try:
            return json.dumps(mp, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            return str(mp)
    n = len(items)
    shown = items[:max_items]
    body = ", ".join([f"{k}->{v}" for k, v in shown])
    return body if n <= max_items else f"{body} … (+{n - max_items} more)"

def build_run_log_lines(CONFIG: dict, STATS_BLOCK, new_ids=None) -> list[str]:
    lines: list[str] = []

    # ── Header
    lines.append(f"=== Autograde Run @ {CONFIG['KST_NOW']} ({CONFIG['RUN_TS']}) ===")
    lines.append(f"TIMEZONE: {CONFIG['TIMEZONE']}")
    lines.append("")

    # ── Paths
    lines.append("[Paths]")
    lines.append(f"OUT_DIR: {CONFIG['OUT_DIR']}")
    lines.append(f"EXEC_DIR: {CONFIG['EXEC_DIR']}")
    lines.append(f"SUBMIT_DIR: {CONFIG['SUBMIT_DIR']}")
    lines.append(f"TEMPLATE: {CONFIG['TEMPLATE_PATH']}")
    lines.append(f"ANSWER:   {CONFIG['ANSWER_PATH']}")
    lines.append("")

    # ── Latest Files (basenames)
    lines.append("[Latest Files]")
    lines.append(f"SUMMARY_FILE_LATEST:   {CONFIG['SUMMARY_FILE_LATEST']}")
    lines.append(f"SIMILAR_FILE_LATEST:   {CONFIG['SIMILAR_FILE_LATEST']}")
    lines.append(f"NEWTODAY_FILE_LATEST:  {CONFIG['NEWTODAY_FILE_LATEST']}")
    lines.append(f"TAG_AUDIT_LATEST:      {CONFIG['TAG_AUDIT_FILE']}")
    lines.append("")

    # ── Counts
    lines.append("[Counts]")
    lines.append(f"TOTAL_STUDENTS: {CONFIG['TOTAL_CNT']}")
    lines.append(f"NEWLY_GRADED:   {CONFIG['NEW_CNT']}")
    lines.append(f"TODAY_FILES (KST {CONFIG['TODAY_DATE']}): {CONFIG['TODAY_CNT']}")
    if new_ids and len(new_ids) > 0:
        lines.append(f"NEW_IDS: {_fmt_seq(sorted(new_ids))}")
    lines.append("")

    # ── Cells
    lines.append("[Cells]")
    lines.append(f"REQUIRED_CELLS:  {CONFIG['REQUIRED_CELL_COUNT']}")
    lines.append(f"OPTIONAL_CELLS:  {CONFIG['OPTIONAL_CELL_COUNT']}")
    lines.append(f"REQUIRED_INDEXES: {_fmt_seq(CONFIG['REQUIRED_CELL_INDEXES'])}")
    lines.append(f"OPTIONAL_INDEXES: {_fmt_seq(CONFIG['OPTIONAL_CELL_INDEXES'])}")
    lines.append(f"REQUIRED_CELL_MAP:  {_fmt_map(CONFIG['REQUIRED_CELL_MAP'])}")
    lines.append(f"OPTIONAL_CELL_MAP:  {_fmt_map(CONFIG['OPTIONAL_CELL_MAP'])}")
    lines.append(f"EXCLUDED (no answer print): required=[{CONFIG['EXCLUDED_REQ_ALL']}], optional=[{CONFIG['EXCLUDED_OPT_ALL']}]")
    lines.append("")

    # ── Scoring
    lines.append("[Scoring]")
    lines.append(f"SCORE_RULE: {CONFIG['SCORE_RULE']}")
    lines.append(f"SIM_THRESHOLD_TEMPLATE: {CONFIG['SIM_THRESHOLD_TEMPLATE']}")
    lines.append(f"SIM_THRESHOLD_PAIR:     {CONFIG['SIM_THRESHOLD_PAIR']}")
    lines.append("")

    # ── Stats
    lines.append("[Score & Distribution Summary]")
    if isinstance(STATS_BLOCK, (list, tuple)):
        lines.extend([str(x) for x in STATS_BLOCK])
    else:
        lines.append(str(STATS_BLOCK))

    return lines

@dataclass
@dataclass
class RunConfigInput:
    # time / run (non-default)
    now_str: str
    today_date: date
    timezone: str
    run_ts: str

    # paths (non-default)
    out_dir: Path
    exec_dir: Path
    submit_dir: Path
    template_path: Path
    answer_path: Path
    tagged_temp_path: Path
    tag_audit_path: Path
    summary_latest: Path
    similar_latest: Optional[Path]
    newtoday_latest: Path

    # scoring / thresholds / options (non-default)
    sim_threshold_template: float
    sim_threshold_pair: float
    score_rule: str
    similarity_enabled: bool

    # label info (non-default)
    req_labels_count: int
    opt_labels_count: int
    req_idx: Iterable[int]
    opt_idx: Iterable[int]
    req_map: Mapping[str, Any]
    opt_map: Mapping[str, Any]
    excluded_req_all: str
    excluded_opt_all: str

    # dataset stats (non-default)
    total_cnt: int
    new_cnt: int
    today_cnt: int

    # defaults MUST come last
    run_log_file: str = "autograde_run.log"


def compose_run_config(i: RunConfigInput) -> dict:
    """Create a normalized CONFIG dict for logs/summary rendering."""
    return {
        # ── Run / Time Info ──
        "TODAY_DATE": i.today_date,
        "KST_NOW": i.now_str,
        "TIMEZONE": i.timezone,
        "RUN_TS": i.run_ts,

        # ── Directories (as str) ──
        "OUT_DIR": str(i.out_dir),
        "EXEC_DIR": str(i.exec_dir),
        "SUBMIT_DIR": str(i.submit_dir),

        # ── File basenames ──
        "TEMPLATE_FILE": i.template_path.name,
        "ANSWER_FILE": i.answer_path.name,
        "TAGGED_TEMP_FILE": i.tagged_temp_path.name,
        "TAG_AUDIT_FILE": i.tag_audit_path.name,
        "RUN_LOG_FILE": i.run_log_file,
        "SUMMARY_FILE_LATEST": i.summary_latest.name,
        "SIMILAR_FILE_LATEST": (
            i.similar_latest.name if (i.similar_latest and i.similarity_enabled) else "N/A"
        ),
        "NEWTODAY_FILE_LATEST": i.newtoday_latest.name,

        # ── Full paths (as str) ──
        "TEMPLATE_PATH": str(i.template_path),
        "ANSWER_PATH": str(i.answer_path),
        "TAGGED_TEMP_PATH": str(i.tagged_temp_path),

        # ── Scoring / Thresholds / Options ──
        "SIM_THRESHOLD_TEMPLATE": i.sim_threshold_template,
        "SIM_THRESHOLD_PAIR": i.sim_threshold_pair,
        "SCORE_RULE": i.score_rule,
        "SIMILARITY_ENABLED": i.similarity_enabled,

        # ── Required/Optional cells ──
        "REQUIRED_CELL_COUNT": i.req_labels_count,
        "OPTIONAL_CELL_COUNT": i.opt_labels_count,
        "REQUIRED_CELL_INDEXES": sorted(list(i.req_idx)),
        "OPTIONAL_CELL_INDEXES": sorted(list(i.opt_idx)),
        "REQUIRED_CELL_MAP": i.req_map,
        "OPTIONAL_CELL_MAP": i.opt_map,
        "EXCLUDED_REQ_ALL": i.excluded_req_all or "없음",
        "EXCLUDED_OPT_ALL": i.excluded_opt_all or "없음",

        # ── Dataset stats ──
        "TOTAL_CNT": i.total_cnt,
        "NEW_CNT": i.new_cnt,
        "TODAY_CNT": i.today_cnt,
    }