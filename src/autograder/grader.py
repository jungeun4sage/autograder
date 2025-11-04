"""
CLI 러너 (선택). 노트북 없이도 실행 가능:
$ python -m autograder.grader --session 9 --env DEV
"""
import argparse
from pathlib import Path
import nbformat, pandas as pd
from autograder.io_utils import now_kst, extract_id_and_name, _mtime_kst_str, _filesize_bytes, load_config
from autograder.nb_utils import (
    _label_map, _nb_fingerprint, _cell_output_text, _indexes_with_labels,
    _label_key_robust
)
from autograder.policy import (
    ScorePolicy, should_grade_label, student_executed_for_grading,
    outputs_equal_loose_text, decide_output_match, __version__ as policy_version
)
from autograder.report import build_stats_block, build_excluded_summary_line

def main(session: int, env: str, toml_path: str):
    cfg = load_config(toml_path, session, env)
    TEMPLATE_PATH = cfg["template_path"]
    SOLUTION_PATH = cfg["solution_path"]
    SUBMIT_DIR    = cfg["submit_dir"]
    OUT_DIR       = cfg["out_dir"]

    RUN_TS = now_kst().strftime("%Y%m%d_%H%M%S")
    OUT = Path(OUT_DIR); OUT.mkdir(parents=True, exist_ok=True)
    EXEC_DIR = OUT / "executed" / RUN_TS
    EXEC_DIR.mkdir(parents=True, exist_ok=True)

    tmpl = nbformat.read(TEMPLATE_PATH, as_version=4)
    sol  = nbformat.read(SOLUTION_PATH, as_version=4)

    # 태그 읽기 (노트북에서 만든 태깅본 없이 운영하려면 여기에 태깅 로직 추가해도 됨)
    req_labels, opt_labels = set(), set()
    for c in tmpl.cells:
        if c.cell_type != "code": 
            continue
        tg = set(c.get("metadata", {}).get("tags", []))
        lab = c.source.splitlines()[0].lstrip("#").strip().split()[0] if c.source else None
        if "required" in tg and lab: req_labels.add(lab)
        if "optional_ex" in tg and lab: opt_labels.add(lab)

    sol_lmap = _label_map(sol)
    base_score = 100.0

    rows=[]
    EXCLUDED_REQ_ALL=set(); EXCLUDED_OPT_ALL=set()

    for p in sorted(Path(SUBMIT_DIR).glob("**/*.ipynb")):
        sid, name = extract_id_and_name(p)
        try:
            nb = nbformat.read(str(p), as_version=4)
        except Exception as e:
            rows.append([sid, name, p.name, 0.0, "ERROR", "ipynb 파싱 실패", "ERROR", f"노트북 파싱 실패: {e}"])
            continue

        stu_lmap = _label_map(nb)

        req_missing=[]; req_mismatch=[]; opt_missing=[]
        excluded_req=[]; excluded_opt=[]

        # 필수
        for lab in sorted(req_labels, key=_label_key_robust):
            solcell = sol_lmap.get(lab, {}).get("cell")
            sol_out = _cell_output_text(solcell) if solcell else ""
            if not should_grade_label(sol_out):
                excluded_req.append(f"#{lab}")
                continue

            sinfo = stu_lmap.get(lab)
            stu_out = _cell_output_text(sinfo["cell"]) if sinfo else ""
            executed = student_executed_for_grading(stu_out)
            if not executed:
                req_missing.append(f"#{lab}"); 
                continue

            if not outputs_equal_loose_text(stu_out, sol_out):
                req_mismatch.append(f"#{lab}")

        # 연습
        for lab in sorted(opt_labels, key=_label_key_robust):
            solcell = sol_lmap.get(lab, {}).get("cell")
            sol_out = _cell_output_text(solcell) if solcell else ""
            if not should_grade_label(sol_out):
                excluded_opt.append(f"#{lab}")
                continue

            sinfo = stu_lmap.get(lab)
            stu_out = _cell_output_text(sinfo["cell"]) if sinfo else ""
            executed = student_executed_for_grading(stu_out)
            if not executed:
                opt_missing.append(f"#{lab}")

        # 점수
        score = base_score \
              - ScorePolicy.REQUIRED_MISSING * len(req_missing) \
              - ScorePolicy.REQUIRED_MISMATCH * len(req_mismatch) \
              - ScorePolicy.OPTIONAL_MISSING * len(opt_missing)
        score = float(max(0.0, min(100.0, round(score, 1))))

        status = "OK" if (not req_missing and not req_mismatch) else "INCOMPLETE"
        output_match = decide_output_match(status, len(req_missing), len(req_mismatch))
        reason = "" if status=="OK" else "필수 미실행/불일치 존재"

        fbl = []
        if req_missing:  fbl.append(f"[필수 미실행 {len(req_missing)}개] 셀: " + ", ".join(req_missing))
        if req_mismatch: fbl.append(f"[필수 출력 불일치 {len(req_mismatch)}개] 셀: " + ", ".join(req_mismatch))
        if opt_missing:  fbl.append(f"[연습문제 미실행 {len(opt_missing)}개] 셀: " + ", ".join(opt_missing))

        from autograder.policy import build_score_line
        score_line = build_score_line(base_score, len(req_missing), len(req_mismatch), len(opt_missing), score)

        feedback = ("\n".join(fbl)) if fbl else "정상 제출로 판단되었습니다. 수고했습니다!"
        feedback = (feedback + ("\n" if feedback else "") + score_line).strip()

        rows.append([sid, name, p.name, score, status, reason, output_match, feedback])

        EXCLUDED_REQ_ALL.update(excluded_req)
        EXCLUDED_OPT_ALL.update(excluded_opt)

    df = pd.DataFrame(rows, columns=["student_id","student_name","file","score","status","reasons","output_match","feedback"])

    # 저장
    summary_latest = Path(OUT_DIR) / "summary_static_with_name_latest.csv"
    df.to_csv(summary_latest, index=False, encoding="utf-8-sig")

    # 통계/로그
    STATS_BLOCK = build_stats_block(df)
    excl_req_str, excl_opt_str = build_excluded_summary_line(EXCLUDED_REQ_ALL, EXCLUDED_OPT_ALL, key=_label_key_robust)

    # 간단 출력
    print(f"Policy version: {policy_version}")
    print("\n".join(["📊 Score & Distribution Summary", *STATS_BLOCK]))
    print(f"채점 제외(정답 출력 없음): 필수=[{excl_req_str}], 연습=[{excl_opt_str}]")
    print("Saved:", summary_latest)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", type=int, required=True)
    ap.add_argument("--env", type=str, choices=["DEV","PROD"], required=True)
    ap.add_argument("--config", type=str, default="autograder/config/sessions.toml")
    args = ap.parse_args()
    main(args.session, args.env, args.config)
