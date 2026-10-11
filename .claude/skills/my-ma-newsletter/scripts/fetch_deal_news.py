#!/usr/bin/env python3
"""딜 뉴스 후보 수집기: 더벨·인베스트조선 목록 + Google 뉴스 RSS.
사용법: python3 fetch_deal_news.py --since "2026-10-09 07:00"   (KST, 생략 시 직전 영업일 07:00 자동)
출력: 수집 기간 안의 후보 기사 목록(날짜·매체·제목·URL), 제목 기준 중복 제거.
"""
import argparse, html, re, subprocess, sys, urllib.parse
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

THEBELL = {"0103": "M&A", "0303": "PEF/VC", "0304": "연기금", "0301": "IB"}
GNEWS_QUERIES = [
    "경영권 인수", "경영권 매각", "우선협상대상자 인수", "주식매매계약 SPA", "매각 본입찰 OR 예비입찰",
    "매각 주관사 선정", "사모펀드 인수", "PEF 인수", "프리IPO 투자 유치", "시리즈 투자 유치 억원",
    "지분 투자 유치", "블라인드펀드 결성", "출자사업 위탁운용사 선정", "펀드 결성 클로징",
    "site:dealsite.co.kr 인수 OR 매각 OR 투자 OR 펀드", "site:edaily.co.kr 마켓인 인수 OR 매각 OR 투자유치 OR 펀드",
    "site:investchosun.com", "site:thebell.co.kr", "site:sedaily.com 시그널 인수 OR 매각 OR 출자",
    "site:bloter.net 인수 OR 투자 OR 펀드", "site:hankyung.com 인수 OR 매각 OR 사모펀드",
]
DEAL = re.compile(r"인수|매각|M&A|우협|우선협상|SPA|본입찰|예비입찰|투자\s?유치|시리즈\s?[A-Z]|프리\s?IPO|Pre-?IPO|"
                  r"펀드|출자|운용사|GP|LP|PEF|사모|지분|경영권|매물|클로징|원매자|실사|밸류|CB|RCPS|메자닌|합병|투자")
NOISE = re.compile(r"블로그|Blog|카지노|슬롯|맞고|Roughnecks|포토|\[사진\]|운세|날씨")


def get(url):
    r = subprocess.run(["curl", "-sSL", "-m", "20", "-A", UA, url], capture_output=True)
    return r.stdout.decode("utf-8", "ignore")


def clean(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t))).strip()


def thebell():
    for code, sect in THEBELL.items():
        s = get(f"https://www.thebell.co.kr/front/NewsList.asp?Code={code}")
        for key, title in re.findall(r'newsview\.asp\?[^"]*key=(\d{14})\d*[^"]*"[^>]*>(.*?)</a>', s, re.S):
            title = clean(title)
            if len(title) < 8 or title.endswith("기자"):
                continue
            dt = datetime.strptime(key, "%Y%m%d%H%M%S").replace(tzinfo=KST)
            # 목록 링크 안에 제목+리드가 붙어 오는 경우 앞부분만 제목으로 사용
            yield dt, f"더벨({sect})", title[:120], f"https://www.thebell.co.kr/front/newsview.asp?code=00&key={key}"


def investchosun():
    for url in ["https://www.investchosun.com/", "https://www.investchosun.com/svc/news/list.html?catid=2"]:
        s = get(url)
        for path, d, title in re.findall(r'href="(https://www\.investchosun\.com/site/data/html_dir/(\d{4}/\d\d/\d\d)/\d+\.html)"[^>]*>([^<]{8,})<', s):
            title = clean(title)
            if len(title) > 90 or not DEAL.search(title):  # 리드 문단 링크·비딜 기사 건너뜀
                continue
            dt = datetime.strptime(d, "%Y/%m/%d").replace(hour=12, tzinfo=KST)  # 시각 미상 → 정오로 간주
            yield dt, "인베스트조선", title, path


def gnews(days):
    for q in GNEWS_QUERIES:
        enc = urllib.parse.quote(f"{q} when:{days}d")
        s = get(f"https://news.google.com/rss/search?q={enc}&hl=ko&gl=KR&ceid=KR:ko")
        for title, link, pub, src in re.findall(
                r"<item><title>(.*?)</title><link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?<source[^>]*>(.*?)</source>", s, re.S):
            title = clean(title)
            src = clean(src)
            title = re.sub(rf"\s*-\s*{re.escape(src)}(\s*-\s*{re.escape(src)})?$", "", title)
            if NOISE.search(title + src) or not DEAL.search(title):
                continue
            yield parsedate_to_datetime(pub).astimezone(KST), src, title, link


def last_business_day_7am(now):
    d = now.date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return datetime(d.year, d.month, d.day, 7, tzinfo=KST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help='KST "YYYY-MM-DD HH:MM"')
    a = ap.parse_args()
    now = datetime.now(KST)
    since = datetime.strptime(a.since, "%Y-%m-%d %H:%M").replace(tzinfo=KST) if a.since else last_business_day_7am(now)
    days = max(1, (now - since).days + 1)
    seen, rows = set(), []
    for src_fn in (thebell, investchosun, lambda: gnews(days)):
        try:
            for dt, media, title, url in src_fn():
                key = re.sub(r"[^가-힣A-Za-z0-9]", "", title)[:30]
                if key in seen:
                    continue
                # 인베스트조선은 날짜만 있으므로 날짜 단위로 비교
                ok = dt.date() >= since.date() if media == "인베스트조선" else dt >= since
                if ok and dt <= now:
                    seen.add(key)
                    rows.append((dt, media, title, url))
        except Exception as e:  # 한 소스가 실패해도 나머지는 계속
            print(f"[warn] {src_fn}: {e}", file=sys.stderr)
    rows.sort(key=lambda r: r[0], reverse=True)
    print(f"# 수집 기간 {since:%Y-%m-%d %H:%M} ~ {now:%Y-%m-%d %H:%M} KST · 후보 {len(rows)}건")
    for dt, media, title, url in rows:
        print(f"{dt:%m-%d %H:%M} | {media} | {title} | {url}")


if __name__ == "__main__":
    main()
