# src/autograder/paths.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

# 모든 산출물 파일명 포맷을 한 곳에서 정의
SUMMARY_TS_FMT   = "summary_static_with_name_{run_ts}.csv"
SIMILAR_TS_FMT   = "similar_pairs_{run_ts}.csv"
NEWTODAY_TS_FMT  = "new_today_{run_ts}.csv"
RUN_LOG_NAME     = "autograde_run.log"

SUMMARY_LATEST   = "summary_static_with_name_latest.csv"
SIMILAR_LATEST   = "similar_pairs_latest.csv"
NEWTODAY_LATEST  = "new_today_latest.csv"

@dataclass(frozen=True)
class OutputLayout:
    """RUN_TS만 알면 산출물 모든 경로를 반환."""
    out_dir: Path
    exec_dir: Path
    run_ts: str

    @property
    def summary_ts(self) -> Path:
        return self.exec_dir / SUMMARY_TS_FMT.format(run_ts=self.run_ts)

    @property
    def similar_ts(self) -> Path:
        return self.exec_dir / SIMILAR_TS_FMT.format(run_ts=self.run_ts)

    @property
    def newtoday_ts(self) -> Path:
        return self.exec_dir / NEWTODAY_TS_FMT.format(run_ts=self.run_ts)

    @property
    def summary_latest(self) -> Path:
        return self.out_dir / SUMMARY_LATEST

    @property
    def similar_latest(self) -> Path:
        return self.out_dir / SIMILAR_LATEST

    @property
    def newtoday_latest(self) -> Path:
        return self.out_dir / NEWTODAY_LATEST

    @property
    def run_log(self) -> Path:
        return self.out_dir / RUN_LOG_NAME

    def ensure_dirs(self) -> "OutputLayout":
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.exec_dir.mkdir(parents=True, exist_ok=True)
        return self  # chaining

def build_output_layout(out_dir: Path, exec_dir: Path, run_ts: str) -> OutputLayout:
    """편의 함수."""
    return OutputLayout(out_dir=Path(out_dir), exec_dir=Path(exec_dir), run_ts=run_ts).ensure_dirs()
