---
name: my-deal-structure
description: 딜 개요(대상회사·거래 목적·매수자/매도자 상황)를 받아 최적 거래 구조 대안을 도출하고, 대안별 장단점·세무/법무 체크포인트·유사 거래 사례를 연계한 구조 제안 리포트를 생성한다. "딜 구조", "거래 구조", "인수 구조", "구조 대안", "deal structure" 요청 시 사용.
---

# /my-deal-structure — 거래 구조 대안 도출

룰 기반 엔진(`deal_structurer/`)으로 1차 스크리닝한 뒤, Claude가 딜 맥락과 최신 사례로 보강해 자문용 리포트를 완성한다.

## 1단계: 딜 프로파일 확정

사용자 설명에서 아래 항목을 추출한다. 비어 있거나 모호한 **핵심 항목**(objective, buyer_type, stake, carve_out, liability_risk, permits_critical)만 AskUserQuestion으로 한 번에 묻고, 나머지는 기본값을 쓰고 리포트에 "가정"으로 명시한다.

| key | 허용값 |
|---|---|
| objective | control(제3자의 경영권 인수) / control_increase(기존 최대주주 지분 확대) / minority(소수지분) / capital_raise(투자유치) / divestiture(매각·엑싯) / restructuring(구조조정) |
| buyer_type | strategic / financial |
| stake | full / majority / minority |
| target_listed, carve_out, permits_critical, seller_stays, target_needs_capital, target_cash_rich | true / false |
| liability_risk, buyer_cash, seller_tax_sensitive, valuation_gap, urgency | low / mid / high |
| industry | 자유 텍스트 (예: "환경(소각)") |
| deal_size_eok | 숫자 (억원) |

환경업(소각·매립·재활용) 딜은 `permits_critical: true`를 기본으로 본다.

기존 최대주주가 지분을 늘려 경영권을 강화하는 딜은 `control` 대신 `control_increase`를 쓴다. 이때 다음 항목은 리서치로 먼저 확인한다.
- 현재 최대주주 지분율과 자기주식 잔량
- 회사 잉여현금(`target_cash_rich`)과 배당가능이익
- 목표 지분율까지 필요한 주식수와 금액(프리미엄별)
- HoldCo 배당 커버리지

## 2단계: 엔진 실행

프로파일을 스크래치패드에 JSON으로 저장한 뒤 실행한다.

```bash
python3 -m deal_structurer --profile <profile.json> --format json   # 점수·사유 확인
python3 -m deal_structurer --profile <profile.json> --out <report.md>  # 기본 리포트
```

## 3단계: 리포트 보강 (Claude 판단)

엔진 결과를 그대로 전달하지 말고 다음을 더한다.

1. **딜 고유 맥락 반영** — 엔진 사유를 실제 당사자·수치로 구체화하고, 엔진이 놓친 구조(예: 분할합병, 회생계획 연계)가 있으면 대안에 추가하며 그 근거를 쓴다.
2. **최신 사례 보강** — WebSearch로 동종 업종·동일 구조의 최근 2~3년 국내 거래를 1~3건 찾아 추가한다. 금액·지분율은 출처(DART 공시, 언론 기사)를 함께 적고, 확인되지 않은 수치는 쓰지 않는다.
3. **추천 결론** — 1순위 구조 + 보완장치 조합을 한 문단으로 제시하고, 이 결론을 뒤집을 수 있는 핵심 변수(예: 실사 결과 우발채무 규모)를 명시한다.
4. **유용한 신규 사례는 `deal_structurer/data/cases.json`에 추가**를 제안한다(사용자 확인 후).

## 출력

- 최종 리포트 마크다운을 작업 디렉터리 `reports/`에 저장하고 요약(1순위 구조, 핵심 사유 3개, 다음 단계)을 채팅으로 전달.
- 리포트 하단 면책 문구(세무·법률 전문가 검토 필요, 사례 수치 근사치)는 삭제하지 않는다.
