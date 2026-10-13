# M&A/투자유치 자문 자동화

자세한 배경과 스킬 목록은 [PRD.md](PRD.md) 참고.

## deal_structurer — 거래 구조 대안 도출 엔진

딜 프로파일(거래 목적, 매수자 유형, 목표 지분, 우발채무·인허가·세부담·가격갭·회사 잉여현금 등 16개 항목)을 입력하면

1. **핵심 구조 14종**을 룰 기반으로 점수화해 상위 대안을 추천하고, 함께 쓰면 효과가 큰 **결합 구조**도 짚어 주며
   - 경영권 거래: 구주 인수, 제3자배정 유상증자, 구주+신주, 자산양수도, 영업양수도, 합병, 분할 후 매각, 주식교환, 공개매수, JV
   - 최대주주 지분 확대: 자기주식 취득·소각, 최대주주 HoldCo 구조화 매입, 지주회사 전환, 자진 상장폐지
2. 대안별 **이 딜에 맞는 이유 / 우려 사항**, 일반 장단점, 세무·법무 체크포인트, 7개 항목 비교표를 제시하며
3. **보완 장치 8종**(언아웃, 에스크로, W&I 보험, 단계적 인수, LBO, 컨소시엄, 메자닌, PRS·TRS 파생)을 함께 제안하고
4. **국내 거래 사례 DB**(24건)에서 같은 구조·동종 업종 사례를 연결한 마크다운 리포트를 만든다.

외부 패키지 없이 Python 3.9+ 표준 라이브러리만 사용한다.

```bash
# 예시 프로파일로 리포트 생성
python3 -m deal_structurer --profile examples/env_incinerator_buyout.json --out reports/env.md

# 질문에 답하며 입력
python3 -m deal_structurer --interactive

# JSON 결과 (점수·사유) / 카탈로그 조회
python3 -m deal_structurer --profile examples/growth_investment.json --format json
python3 -m deal_structurer --list-structures
python3 -m deal_structurer --list-cases

# 테스트
python3 -m unittest discover -s tests
```

Claude Code에서는 `/my-deal-structure` 스킬이 이 엔진을 실행한 뒤 딜 맥락과 최신 사례 웹 리서치로 리포트를 보강한다.

### 커스터마이징

- `deal_structurer/data/structures.json` — 구조별 장단점·체크포인트와 점수 규칙.
  규칙 예: `{"if": {"liability_risk": ["high"]}, "score": 3, "why": "..."}`. 조건은 AND로 결합되고, `"exclude": true`이면 해당 구조를 후보에서 제외한다. 숫자 항목은 `">=5000"`처럼 비교할 수 있다.
- 구조의 `combos`에 `{"with": "<다른 구조 id>", "name": ..., "note": ...}`를 넣으면 두 구조가 함께 추천될 때 결합 구조로 표시된다.
- `deal_structurer/data/cases.json` — 거래 사례. `structures`에 구조 id를 태그하면 자동 연결되고, `keywords`로 업종을 매칭한다.

> 사례 금액·지분율은 공개 보도 기반 근사치입니다. 실제 자문에 쓰기 전에 DART 공시 원문으로 확인하세요. 추천 결과는 1차 스크리닝용이며 세무·법률 검토를 대신하지 않습니다.
