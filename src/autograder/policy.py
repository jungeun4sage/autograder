# autograder/policy.py
import re


# === 감점 규칙 ===
BASE_SCORE = 100.0
PENALTY_REQUIRED_MISS = 1.0
PENALTY_REQUIRED_MISMATCH = 0.5
PENALTY_OPTIONAL_MISS = 0.2

#  유사도 임계값 기본값
DEFAULT_TEMPLATE_SIM_THRESHOLD = 0.98
DEFAULT_PAIR_SIM_THRESHOLD     = 0.99

def score_rule_str(
    base: float = BASE_SCORE,
    req_miss: float = PENALTY_REQUIRED_MISS,
    req_mismatch: float = PENALTY_REQUIRED_MISMATCH,
    opt_miss: float = PENALTY_OPTIONAL_MISS,
) -> str:
    """사람이 읽기 쉬운 규칙 문자열 생성 (로그/요약에 쓰기 위함)."""
    return (
        f"base={base}; required: miss -{req_miss}, mismatch -{req_mismatch}; "
        f"optional: miss -{opt_miss}"
    )
# === 출력 비교 정책 ===

def outputs_equal(a: str, b: str) -> bool:
    """숫자는 완전일치, 공백/개행/연속공백은 무시."""
    def strip_space(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "").strip())
    a_s, b_s = strip_space(a), strip_space(b)

    num_pat = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
    a_nums, b_nums = re.findall(num_pat, a_s), re.findall(num_pat, b_s)
    if len(a_nums) != len(b_nums): return False
    if any(x != y for x, y in zip(a_nums, b_nums)): return False

    def remove_nums(s): return re.sub(num_pat, "", s)
    return strip_space(remove_nums(a_s)) == strip_space(remove_nums(b_s))

# === 상태/출력매핑 ===
def decide_status_and_match(req_missing, req_mismatch):
    if not req_missing and not req_mismatch:
        return "OK", "OK"
    # INCOMPLETE
    return "INCOMPLETE", ("MISMATCH" if req_mismatch else "MISSING")