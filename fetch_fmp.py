#!/usr/bin/env python3
"""每日 FMP 数据拉取 — GitHub Actions / Mac mini 入口

读 INDUSTRY_MAP 池子（314 只），调 FMP /quote 批量端点，
落到 confirmed_{TRADING_DATE}.json，供 gen.py 消费。

环境变量:
  FMP_API_KEY  必填，从 GitHub Secrets / launchd plist / shell env 注入
  REVIEW_DATE  选填，YYYY-MM-DD，强制覆盖交易日期（默认从 FMP timestamp 推断）
"""
import os, sys, json, time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import INDUSTRY_MAP

# 'NA' 是占位符不是真 ticker，FMP 上不存在
TICKERS = sorted({s for syms in INDUSTRY_MAP.values() for s in syms if s != 'NA'})


def get_api_key():
    k = os.environ.get('FMP_API_KEY', '').strip()
    if not k:
        sys.exit("ERROR: env var FMP_API_KEY not set")
    return k


def fetch_quote_batch(syms, retries=3):
    """FMP /stable/batch-quote 端点（v3 已于 2025-08-31 deprecated），分块 100/批"""
    api_key = get_api_key()
    quotes = {}
    chunks = [syms[i:i+100] for i in range(0, len(syms), 100)]
    for i, chunk in enumerate(chunks):
        url = f"https://financialmodelingprep.com/stable/batch-quote?symbols={','.join(chunk)}&apikey={api_key}"
        for attempt in range(retries):
            try:
                req = Request(url, headers={'User-Agent': 'us-hardware-review/1.0'})
                with urlopen(req, timeout=30) as r:
                    data = json.loads(r.read())
                if isinstance(data, dict) and ('Error Message' in data or 'error' in data):
                    raise RuntimeError(f"FMP error: {data}")
                if not isinstance(data, list):
                    raise RuntimeError(f"unexpected payload: {str(data)[:200]}")
                for q in data:
                    if q.get('symbol'):
                        quotes[q['symbol']] = q
                print(f"  chunk {i+1}/{len(chunks)}: {len(data)} quotes")
                break
            except (HTTPError, URLError, RuntimeError, json.JSONDecodeError) as e:
                if attempt == retries - 1:
                    print(f"  chunk {i+1} FAILED after {retries} retries: {e}")
                else:
                    wait = 2 ** attempt
                    print(f"  chunk {i+1} attempt {attempt+1} failed ({e}), retry in {wait}s")
                    time.sleep(wait)
        time.sleep(0.3)
    return quotes


def detect_trading_date(quotes):
    """从 FMP 返回的 timestamp 推断交易日（美东时区）"""
    forced = os.environ.get('REVIEW_DATE', '').strip()
    if forced:
        print(f"  (REVIEW_DATE forced -> {forced})")
        return forced
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo('America/New_York')
    except ImportError:
        et = timezone(timedelta(hours=-4))
    timestamps = [q.get('timestamp') for q in quotes.values() if q.get('timestamp')]
    if not timestamps:
        return datetime.now(et).strftime('%Y-%m-%d')
    return datetime.fromtimestamp(max(timestamps), tz=et).strftime('%Y-%m-%d')


def main():
    print(f"Fetching FMP /quote for {len(TICKERS)} tickers...")
    quotes = fetch_quote_batch(TICKERS)
    if not quotes:
        sys.exit("ERROR: no quotes returned from FMP")

    trading_date = detect_trading_date(quotes)
    print(f"Trading date: {trading_date}")

    confirmed = {}
    missing = []
    for sym in TICKERS:
        q = quotes.get(sym)
        if not q or q.get('price') in (None, 0):
            missing.append(sym)
            continue
        cap_raw = q.get('marketCap') or 0
        confirmed[sym] = {
            'close': round(q['price'], 2),
            'dp': round(q.get('changesPercentage') or 0, 2),
            'cap': max(round(cap_raw / 1e6), 1),  # $M, 至少 1 防 sqrt 崩溃
            'high': q.get('dayHigh'),
            'low': q.get('dayLow'),
            'prev_close': q.get('previousClose'),
            'volume': q.get('volume'),
        }

    out = {
        'date': trading_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total': len(TICKERS),
        'hit': len(confirmed),
        'missing': missing,
        'data': confirmed,
    }

    repo_dir = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(repo_dir, f'confirmed_{trading_date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path}  hit={len(confirmed)}/{len(TICKERS)}  missing={len(missing)}")
    if missing:
        print(f"Missing: {','.join(missing[:30])}{'...' if len(missing)>30 else ''}")

    gho = os.environ.get('GITHUB_OUTPUT')
    if gho:
        with open(gho, 'a') as f:
            f.write(f"date={trading_date}\nhit={len(confirmed)}\nmissing={len(missing)}\n")


if __name__ == '__main__':
    main()
