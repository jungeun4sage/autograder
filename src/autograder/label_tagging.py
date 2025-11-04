import nbformat
import re
import pandas as pd


from autograder.nb_utils import ( LABEL_PATTERN, _normalize_code,_extract_label,
    _label_map, _nb_fingerprint, _cell_output_text, _indexes_with_labels, _sim,
    _label_key_robust
)

STRICT_REQUIRED_FROM_ANSWER = True  # 정답에 코드가 있으면 무조건 필수로 태깅
MIN_CODE_LEN = 5                      # "실코드" 최소 길이 기준

def template_label_tagging(tmpl_path, sol_path, tag_path, audit_path):
    tmpl_nb = nbformat.read(tmpl_path, as_version=4)
    sol_nb  = nbformat.read(sol_path, as_version=4)

    # 1) 라벨 맵
    tmpl_lmap = _label_map(tmpl_nb)
    sol_lmap  = _label_map(sol_nb)

    # 2) '연습문제' 섹션 감지(옵션) — 마크다운 구간 기반
    optional_labels = set()
    in_opt = False
    for i, cell in enumerate(tmpl_nb.cells):
        if cell.cell_type == "markdown":
            tx = cell.source or ""
            if re.search(r"(연습\s*문제|연습문제|Optional|옵션)", tx, re.I):
                in_opt = True
            elif re.match(r"^#{1,6}\s", tx):
                in_opt = False
        elif cell.cell_type == "code":
            lab = _extract_label(cell.source or "")
            if in_opt and lab:
                optional_labels.add(lab)

    # 3) 필수 라벨 결정
    required_labels = set()
    for lab, info in tmpl_lmap.items():
        if lab in optional_labels:
            continue
        tcell = info["cell"]
        scell = sol_lmap.get(lab, {}).get("cell", None)

        tcode = _normalize_code(tcell.source or "")
        scode = _normalize_code(scell.source or "") if scell else ""

        placeholder = bool(re.search(
            r"(TODO|여기에\s*코드|fill\s*in|pass\s*$|\.\.\.|채우세요|작성하시오|구현)",
            tcell.source or "", re.I | re.M
        ))

        if STRICT_REQUIRED_FROM_ANSWER and scell and len(scode) >= MIN_CODE_LEN:
            required_labels.add(lab); continue
        if scell and len(scode) >= MIN_CODE_LEN and (tcode != scode):
            required_labels.add(lab); continue
        if (placeholder or (len(tcode) < MIN_CODE_LEN and len(scode) >= MIN_CODE_LEN)):
            required_labels.add(lab)

    # 4) 태그 메타데이터 쓰기
    for i, cell in enumerate(tmpl_nb.cells):
        if cell.cell_type != "code":
            continue
        lab = _extract_label(cell.source or "")
        tags = set(cell.get("metadata", {}).get("tags", []))
        if lab:
            if lab in required_labels:
                tags.add("required")
            if lab in optional_labels:
                tags.add("optional_ex")
            cell.setdefault("metadata", {})["tags"] = list(tags)
    nbformat.write(tmpl_nb, tag_path)

    # 5) 태깅 감사 리포트 생성 ---
    audit_rows = []
    for lab, info in tmpl_lmap.items():
        tcell = info["cell"]
        scell = sol_lmap.get(lab, {}).get("cell", None)
        tcode = _normalize_code(tcell.source or "")
        scode = _normalize_code(scell.source or "") if scell else ""
        placeholder = bool(re.search(
            r"(TODO|여기에\s*코드|fill\s*in|pass\s*$|\.\.\.|채우세요|작성하시오|구현)",
            tcell.source or "", re.I | re.M
        ))
        optional = ("optional_ex" in (tcell.get("metadata", {}).get("tags", [])))
        required = ("required"     in (tcell.get("metadata", {}).get("tags", [])))
        audit_rows.append({
            "label": lab,
            "in_template": True,
            "in_solution": bool(scell),
            "t_len": len(tcode),
            "s_len": len(scode),
            "equal_code": (tcode == scode) if scell else None,
            "placeholder": placeholder,
            "optional_detected": optional,
            "required_decided": required,
        })
    try:
        audit_df = pd.DataFrame(audit_rows)
        audit_df.to_csv(audit_path, index=False, encoding="utf-8-sig")
    except Exception as e:
        print("⚠️ tag audit save failed:", e)


# tagged file에서 label 분류
def classify_labels(tagged_temp_path):
    tagged_nb = nbformat.read(tagged_temp_path, as_version=4)

    req_labels, opt_labels = set(), set()
    req_idx, opt_idx = set(), set()

    for i, c in enumerate(tagged_nb.cells):
        if c.cell_type != "code":
            continue
        tg = set(c.get("metadata", {}).get("tags", []))
        lab = _extract_label(c.source or "")
        if "required" in tg and lab:
            req_labels.add(lab); req_idx.add(i)
        if "optional_ex" in tg and lab:
            opt_labels.add(lab); opt_idx.add(i)


    template_fp = _nb_fingerprint(tagged_nb)
    return req_labels, opt_labels, req_idx, opt_idx, template_fp
