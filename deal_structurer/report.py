"""추천 결과를 마크다운 리포트 또는 JSON으로 출력한다."""

import json
from datetime import date

from .engine import FIELDS, load_json


def _label(key, value):
    label, choices = FIELDS[key]
    if value is None or value == "":
        return label, "-"
    if choices is None:
        return label, f"{value:,.0f}" if isinstance(value, float) else str(value)
    return label, choices[value]


def _bullets(items, indent=""):
    return "\n".join(f"{indent}- {item}" for item in items) if items else f"{indent}- (해당 없음)"


def _case_line(case):
    return f"**{case['title']}** ({case['year']}, {case['industry']}, {case['size']}) — {case['summary']} → *시사점:* {case['lesson']}"


def to_markdown(rec, title="거래 구조 대안 분석 리포트"):
    attr_names = load_json("structures.json")["attributes"]
    out = [f"# {title}", "", f"작성일: {date.today().isoformat()}", ""]

    out += ["## 1. 딜 프로파일", "", "| 항목 | 내용 |", "|---|---|"]
    for key in FIELDS:
        label, value = _label(key, rec.profile[key])
        out.append(f"| {label} | {value} |")
    out.append("")

    out += ["## 2. 추천 구조 대안 요약", "", "| 순위 | 구조 | 적합도 | 핵심 적합 사유 | 주요 우려 |", "|---|---|---|---|---|"]
    for i, ev in enumerate(rec.core, 1):
        pro = ev.reasons_for[0] if ev.reasons_for else "-"
        con = ev.reasons_against[0] if ev.reasons_against else f"(일반) {ev.structure['cons'][0]}"
        out.append(f"| {i} | {ev.structure['name']} | {ev.fit}/100 | {pro} | {con} |")
    out.append("")

    if rec.combos:
        out += ["**추천 결합 구조**", ""]
        out += [f"- **{c['name']}** ({' + '.join(c['names'])}): {c['note']}" for c in rec.combos]
        out.append("")

    out += ["## 3. 구조별 비교", ""]
    header = "| 비교 항목 | " + " | ".join(ev.structure["name"] for ev in rec.core) + " |"
    out += [header, "|---" * (len(rec.core) + 1) + "|"]
    for key, name in attr_names.items():
        out.append(f"| {name} | " + " | ".join(ev.structure["attrs"][key] for ev in rec.core) + " |")
    out.append("")

    out += ["## 4. 대안별 상세 분석", ""]
    for i, ev in enumerate(rec.core, 1):
        s = ev.structure
        out += [
            f"### 대안 {i}. {s['name']} (적합도 {ev.fit}/100)", "",
            s["summary"], "",
            "**이 딜에 적합한 이유**", _bullets(ev.reasons_for), "",
            "**이 딜에서의 우려 사항**", _bullets(ev.reasons_against), "",
            "**일반적 장점**", _bullets(s["pros"]), "",
            "**일반적 단점**", _bullets(s["cons"]), "",
            "**세무·법무 체크포인트**", _bullets(s["checkpoints"]), "",
            "**관련 거래 사례**",
            _bullets([_case_line(c) for c in ev.cases]) if ev.cases else "- 공개 사례 DB에 해당 구조 사례 없음 — 추가 리서치 필요",
            "",
        ]

    out += ["## 5. 보완 장치 (구조 오버레이) 제안", ""]
    if rec.overlays:
        for ev in rec.overlays:
            s = ev.structure
            out += [
                f"### {s['name']}", "", s["summary"], "",
                "- **제안 사유:** " + "; ".join(ev.reasons_for),
                "- **장점:** " + "; ".join(s["pros"]),
                "- **유의점:** " + "; ".join(s["cons"]),
                "- **체크포인트:** " + "; ".join(s["checkpoints"]),
            ]
            if ev.cases:
                out.append("- **사례:** " + "; ".join(f"{c['title']} ({c['year']})" for c in ev.cases))
            out.append("")
    else:
        out += ["- 프로파일상 특별히 권장되는 보완 장치 없음", ""]

    if rec.excluded:
        out += ["## 6. 검토 제외 구조", ""]
        out += [f"- **{ev.structure['name']}**: {'; '.join(ev.reasons_against)}" for ev in rec.excluded]
        out.append("")

    out += ["## 7. 동종 업종 거래 사례", ""]
    if rec.industry_cases:
        out += [f"- {_case_line(c)}" for c in rec.industry_cases]
    else:
        out.append("- 사례 DB에 동종 업종 사례 없음 — 업종 키워드로 추가 리서치 권장")
    out.append("")

    out += [
        "## 8. 다음 단계", "",
        "- 상위 대안별 세후 매도자 수령액·매수자 총 취득원가 시뮬레이션",
        "- 재무·세무·법률 실사 범위를 우려 사항 중심으로 확정",
        "- 기업결합신고 및 업종 인허가 승계 요건 사전 확인",
        "- 선택 구조 기준 LOI/Term Sheet 핵심 조건 초안 작성",
        "",
        "---",
        f"> ⚠️ 본 리포트는 룰 기반 1차 스크리닝 결과로, 최종 구조는 세무·법률 전문가 검토를 거쳐 확정해야 합니다. {rec.disclaimer}",
        "",
    ]
    return "\n".join(out)


def to_dict(rec):
    def ev_dict(ev):
        return {
            "id": ev.structure["id"],
            "name": ev.structure["name"],
            "score": ev.score,
            "fit": ev.fit,
            "reasons_for": ev.reasons_for,
            "reasons_against": ev.reasons_against,
            "cases": [c["id"] for c in ev.cases],
        }

    return {
        "profile": rec.profile,
        "core": [ev_dict(e) for e in rec.core],
        "overlays": [ev_dict(e) for e in rec.overlays],
        "excluded": [{"id": e.structure["id"], "reasons": e.reasons_against} for e in rec.excluded],
        "combos": [{"name": c["name"], "ids": c["ids"], "note": c["note"]} for c in rec.combos],
        "industry_cases": [c["id"] for c in rec.industry_cases],
    }


def to_json(rec):
    return json.dumps(to_dict(rec), ensure_ascii=False, indent=2)
