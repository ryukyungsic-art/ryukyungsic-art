"""CLI: python -m deal_structurer --profile deal.json [--out report.md]"""

import argparse
import json
import sys

from .engine import DEFAULTS, FIELDS, load_json, recommend
from .report import to_json, to_markdown


def ask_profile():
    """대화형으로 딜 프로파일을 입력받는다. 엔터 시 기본값."""
    profile = {}
    for key, (label, choices) in FIELDS.items():
        default = DEFAULTS[key]
        if choices is None:
            answer = input(f"{label} [{default if default is not None else '생략'}]: ").strip()
            if answer:
                profile[key] = float(answer.replace(",", "")) if key == "deal_size_eok" else answer
            continue
        options = list(choices.items())
        print(f"\n{label}")
        for i, (_, desc) in enumerate(options, 1):
            mark = " (기본)" if options[i - 1][0] == default else ""
            print(f"  {i}. {desc}{mark}")
        while True:
            answer = input("선택 번호: ").strip()
            if not answer:
                break
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                profile[key] = options[int(answer) - 1][0]
                break
            print("  올바른 번호를 입력하세요.")
    return profile


def main(argv=None):
    p = argparse.ArgumentParser(prog="deal_structurer", description="거래 구조 대안 도출·장단점 분석·사례 연계")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--profile", help="딜 프로파일 JSON 파일 경로 ('-'이면 stdin)")
    src.add_argument("--interactive", action="store_true", help="대화형 질문으로 프로파일 입력")
    p.add_argument("--top", type=int, default=3, help="추천할 핵심 구조 수 (기본 3)")
    p.add_argument("--format", choices=["md", "json"], default="md")
    p.add_argument("--title", default="거래 구조 대안 분석 리포트")
    p.add_argument("--out", help="출력 파일 경로 (생략 시 표준출력)")
    p.add_argument("--list-structures", action="store_true", help="구조 카탈로그 목록 출력")
    p.add_argument("--list-cases", action="store_true", help="거래 사례 DB 목록 출력")
    args = p.parse_args(argv)

    if args.list_structures:
        for s in load_json("structures.json")["structures"]:
            print(f"[{s['kind']:7}] {s['id']:20} {s['name']}")
        return 0
    if args.list_cases:
        for c in load_json("cases.json")["cases"]:
            print(f"{c['year']} {c['id']:24} {c['title']} — {', '.join(c['structures'])}")
        return 0

    if args.interactive:
        raw = ask_profile()
    elif args.profile:
        f = sys.stdin if args.profile == "-" else open(args.profile, encoding="utf-8")
        with f:
            raw = json.load(f)
    else:
        p.error("--profile 또는 --interactive 중 하나를 지정하세요")

    try:
        rec = recommend(raw, top=args.top)
    except ValueError as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2

    text = to_json(rec) if args.format == "json" else to_markdown(rec, args.title)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"리포트 저장: {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
