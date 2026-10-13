"""딜 프로파일을 받아 거래 구조 대안을 점수화하고 관련 사례를 매칭한다."""

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

# 프로파일 필드 정의: key -> (한글 라벨, 허용값 -> 한글 설명). 허용값이 None이면 자유 입력.
FIELDS = {
    "objective": ("거래 목적", {
        "control": "경영권 인수",
        "minority": "소수지분 투자",
        "capital_raise": "투자유치 (회사 자금조달)",
        "divestiture": "지분·사업 매각 (엑싯)",
        "restructuring": "구조조정·지배구조 개편",
    }),
    "buyer_type": ("매수자(투자자) 유형", {
        "strategic": "전략적 투자자 (SI)",
        "financial": "재무적 투자자 (FI/PE)",
    }),
    "stake": ("목표 지분", {
        "full": "100%",
        "majority": "과반 (50% 초과)",
        "minority": "소수 (50% 이하)",
    }),
    "target_listed": ("대상회사 상장 여부", {True: "상장", False: "비상장"}),
    "carve_out": ("일부 사업만 거래", {True: "예 (사업부·자산 일부)", False: "아니오 (회사 전체)"}),
    "liability_risk": ("우발채무·부외부채 우려", {"low": "낮음", "mid": "중간", "high": "높음"}),
    "permits_critical": ("인허가·계약 승계 중요도", {True: "핵심 (영업의 전제)", False: "일반"}),
    "buyer_cash": ("매수자 현금 여력", {"low": "부족", "mid": "보통", "high": "충분"}),
    "seller_tax_sensitive": ("매도자 세부담 민감도", {"low": "낮음", "mid": "중간", "high": "높음"}),
    "valuation_gap": ("매도·매수 가격 갭", {"low": "작음", "mid": "보통", "high": "큼"}),
    "seller_stays": ("매도자 잔류·경영 참여 의향", {True: "있음", False: "없음 (완전 엑싯)"}),
    "target_needs_capital": ("대상회사 신규 자금 필요", {True: "필요", False: "불필요"}),
    "urgency": ("일정 긴급도", {"low": "여유", "mid": "보통", "high": "긴급"}),
    "industry": ("업종", None),
    "deal_size_eok": ("예상 거래규모 (억원)", None),
}

DEFAULTS = {
    "objective": "control",
    "buyer_type": "strategic",
    "stake": "majority",
    "target_listed": False,
    "carve_out": False,
    "liability_risk": "mid",
    "permits_critical": False,
    "buyer_cash": "mid",
    "seller_tax_sensitive": "mid",
    "valuation_gap": "mid",
    "seller_stays": False,
    "target_needs_capital": False,
    "urgency": "mid",
    "industry": "",
    "deal_size_eok": None,
}


def load_json(name):
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def normalize_profile(raw):
    """기본값을 채우고 허용값을 검증한다. 잘못된 값이면 ValueError."""
    unknown = set(raw) - set(FIELDS)
    if unknown:
        raise ValueError(f"알 수 없는 프로파일 항목: {', '.join(sorted(unknown))}")
    profile = {**DEFAULTS, **raw}
    for key, (label, choices) in FIELDS.items():
        if choices is not None and profile[key] not in choices:
            allowed = ", ".join(str(c).lower() if isinstance(c, bool) else c for c in choices)
            raise ValueError(f"{label}({key}) 값 '{profile[key]}'이(가) 올바르지 않습니다. 허용값: {allowed}")
    if profile["deal_size_eok"] is not None:
        profile["deal_size_eok"] = float(profile["deal_size_eok"])
    return profile


def _matches(value, expected):
    for exp in expected:
        if isinstance(exp, str) and exp[:2] in (">=", "<="):
            if value is None:
                continue
            threshold = float(exp[2:])
            if (exp[:2] == ">=" and value >= threshold) or (exp[:2] == "<=" and value <= threshold):
                return True
        elif value == exp and type(value) is type(exp):
            return True
    return False


def _rule_applies(rule, profile):
    return all(_matches(profile.get(k), v) for k, v in rule["if"].items())


@dataclass
class Evaluation:
    structure: dict
    score: int = 0
    excluded: bool = False
    reasons_for: list = field(default_factory=list)
    reasons_against: list = field(default_factory=list)
    cases: list = field(default_factory=list)

    @property
    def fit(self):
        """0~100 적합도. 기본 50점에서 규칙 점수 1점당 8점 가감."""
        return max(0, min(100, 50 + self.score * 8))


def evaluate(structure, profile):
    ev = Evaluation(structure)
    for rule in structure["rules"]:
        if not _rule_applies(rule, profile):
            continue
        if rule.get("exclude"):
            ev.excluded = True
            ev.reasons_against.append(rule["why"])
            continue
        ev.score += rule["score"]
        (ev.reasons_for if rule["score"] > 0 else ev.reasons_against).append(rule["why"])
    return ev


def industry_match(case, industry):
    if not industry:
        return False
    text = industry.lower()
    return any(kw.lower() in text or text in kw.lower() for kw in case["keywords"] + [case["industry"]])


def match_cases(structure_id, cases, industry, limit=3):
    """해당 구조를 사용한 사례를 업종 일치 우선, 최신순으로 정렬."""
    hits = [c for c in cases if structure_id in c["structures"]]
    hits.sort(key=lambda c: (industry_match(c, industry), c["year"]), reverse=True)
    return hits[:limit]


@dataclass
class Recommendation:
    profile: dict
    core: list
    overlays: list
    excluded: list
    industry_cases: list
    disclaimer: str


def recommend(raw_profile, top=3, overlay_top=4):
    profile = normalize_profile(raw_profile)
    structures = load_json("structures.json")["structures"]
    case_db = load_json("cases.json")
    cases = case_db["cases"]

    evals = [evaluate(s, profile) for s in structures]
    for ev in evals:
        ev.cases = match_cases(ev.structure["id"], cases, profile["industry"])

    def ranked(kind):
        pool = [e for e in evals if e.structure["kind"] == kind and not e.excluded]
        return sorted(pool, key=lambda e: e.score, reverse=True)

    core = ranked("core")[:top]
    overlays = [e for e in ranked("overlay") if e.score > 0][:overlay_top]
    excluded = [e for e in evals if e.excluded]
    industry_cases = [c for c in cases if industry_match(c, profile["industry"])]
    industry_cases.sort(key=lambda c: c["year"], reverse=True)

    return Recommendation(profile, core, overlays, excluded, industry_cases, case_db["disclaimer"])
