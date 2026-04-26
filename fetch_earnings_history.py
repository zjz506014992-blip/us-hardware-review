#!/usr/bin/env python3
"""业绩历史拉取 — 维护 earnings_history.json

两个模式：

  默认（增量）: fetch_earnings_history.py
    用 /stable/earnings-calendar?from=today-30d&to=today+180d 拉一次（1 call）,
    过滤到 314 池, upsert 合并进 earnings_history.json.
    适合 GitHub Actions 工作日每天跑.

  全量回填: fetch_earnings_history.py --full
    对池里 313 只 ticker 逐个调 /stable/earnings?symbol=X&limit=120
    覆盖近 25-30 年历史. ~313 次 API 调用, 仅在首次或月度纠错时跑.

  最近重拉: fetch_earnings_history.py --refresh-recent [days]
    重拉过去 N 天 (默认 180) 内有过财报的所有 ticker,
    用于纠正 epsEstimated 后续被订正的情况.

环境变量: FMP_API_KEY (必填)

输出: earnings_history.json
  schema: {"AAPL": [{"date": "2025-10-30", "time": "amc",
                      "eps": 1.65, "epsEstimated": 1.60,
                      "revenue": 94900000000, "revenueEstimated": 94500000000,
                      "fiscalDateEnding": "2025-09-30",
                      "updatedAt": "2026-04-26T..."}, ...], ...}
"""
import os, sys, json, time, argparse
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen import INDUSTRY_MAP

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(REPO_DIR, 'earnings_history.json')
TICKERS = sorted({s for syms in INDUSTRY_MAP.values() for s in syms if s != 'NA'})


def get_api_key():
    k = os.environ.get('FMP_API_KEY', '').strip()
    if not k:
        sys.exit("ERROR: env var FMP_API_KEY not set")
    return k


def http_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = Request(url, headers={'User-Agent': 'us-hardware-review/1.0'})
            with urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except (HTTPError, URLError, json.JSONDecodeError) as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            print(f"    attempt {attempt+1} failed ({e}), retry in {wait}s")
            time.sleep(wait)


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {}
    with open(HISTORY_FILE, encoding='utf-8') as f:
        return json.load(f)


def save_history(history):
    counts = sum(len(v) for v in history.values())
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    size_kb = os.path.getsize(HISTORY_FILE) / 1024
    print(f"Wrote {HISTORY_FILE}: {len(history)} symbols, {counts} earnings records, {size_kb:.1f} KB")


def normalize(rec):
    """裁剪 + 标准化单条记录, 只留我们用得上的字段"""
    return {
        'date': rec.get('date'),
        'time': (rec.get('time') or '').lower() or None,
        'eps': rec.get('eps'),
        'epsEstimated': rec.get('epsEstimated'),
        'revenue': rec.get('revenue'),
        'revenueEstimated': rec.get('revenueEstimated'),
        'fiscalDateEnding': rec.get('fiscalDateEnding'),
        'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    }


def upsert(history, sym, recs):
    """按 (sym, date) upsert, 后到的覆盖先到的"""
    existing = {r['date']: r for r in history.get(sym, []) if r.get('date')}
    for r in recs:
        d = r.get('date')
        if not d:
            continue
        existing[d] = normalize(r)
    history[sym] = sorted(existing.values(), key=lambda x: x['date'], reverse=True)


def mode_full(api_key):
    """逐 ticker 拉历史. 313 calls."""
    print(f"=== FULL backfill: {len(TICKERS)} tickers ===")
    history = load_history()
    failed = []
    sample_logged = False
    for i, sym in enumerate(TICKERS):
        url = f"https://financialmodelingprep.com/stable/earnings?symbol={sym}&limit=120&apikey={api_key}"
        try:
            data = http_get(url)
            if isinstance(data, dict) and ('Error Message' in data or 'error' in data):
                print(f"  [{i+1}/{len(TICKERS)}] {sym}: API error {data}")
                failed.append(sym)
                continue
            if not isinstance(data, list):
                print(f"  [{i+1}/{len(TICKERS)}] {sym}: unexpected payload {str(data)[:100]}")
                failed.append(sym)
                continue
            if not sample_logged and data:
                print(f"\n=== SAMPLE [{sym}] (first record) ===")
                print(json.dumps(data[0], indent=2, ensure_ascii=False, default=str))
                print("=== END SAMPLE ===\n")
                sample_logged = True
            upsert(history, sym, data)
            print(f"  [{i+1}/{len(TICKERS)}] {sym}: {len(data)} records")
        except Exception as e:
            print(f"  [{i+1}/{len(TICKERS)}] {sym}: FAILED {e}")
            failed.append(sym)
        # save every 25 tickers to avoid losing progress on crash
        if (i + 1) % 25 == 0:
            save_history(history)
        time.sleep(0.15)  # ~7 req/s, well under any tier limit
    save_history(history)
    if failed:
        print(f"\nFailed tickers ({len(failed)}): {','.join(failed)}")


def mode_delta(api_key, days_back=30, days_fwd=180):
    """1 call: earnings-calendar 时间窗内全部, 过滤到池, upsert."""
    today = datetime.now(timezone.utc).date()
    frm = (today - timedelta(days=days_back)).isoformat()
    to = (today + timedelta(days=days_fwd)).isoformat()
    print(f"=== DELTA: earnings-calendar {frm} ~ {to} ===")
    history = load_history()
    pool_set = set(TICKERS)
    url = f"https://financialmodelingprep.com/stable/earnings-calendar?from={frm}&to={to}&apikey={api_key}"
    data = http_get(url)
    if isinstance(data, dict) and ('Error Message' in data or 'error' in data):
        sys.exit(f"ERROR: API returned {data}")
    if not isinstance(data, list):
        sys.exit(f"ERROR: unexpected payload {str(data)[:200]}")
    print(f"Calendar returned {len(data)} total records")
    if data:
        print(f"\n=== SAMPLE [{data[0].get('symbol')}] ===")
        print(json.dumps(data[0], indent=2, ensure_ascii=False, default=str))
        print("=== END SAMPLE ===\n")
    by_sym = {}
    for r in data:
        s = r.get('symbol')
        if s and s in pool_set:
            by_sym.setdefault(s, []).append(r)
    print(f"Pool hit: {len(by_sym)} symbols, {sum(len(v) for v in by_sym.values())} records")
    for sym, recs in by_sym.items():
        upsert(history, sym, recs)
    save_history(history)


def mode_refresh_recent(api_key, days=180):
    """重拉过去 N 天有过财报的 ticker, 修正后续订正"""
    today = datetime.now(timezone.utc).date()
    cutoff = (today - timedelta(days=days)).isoformat()
    history = load_history()
    targets = []
    for sym, recs in history.items():
        if any(r.get('date', '') >= cutoff for r in recs):
            targets.append(sym)
    print(f"=== REFRESH-RECENT: {len(targets)} tickers had earnings since {cutoff} ===")
    failed = []
    for i, sym in enumerate(targets):
        url = f"https://financialmodelingprep.com/stable/earnings?symbol={sym}&limit=20&apikey={api_key}"
        try:
            data = http_get(url)
            if isinstance(data, list) and data:
                upsert(history, sym, data)
                print(f"  [{i+1}/{len(targets)}] {sym}: {len(data)} records")
        except Exception as e:
            print(f"  [{i+1}/{len(targets)}] {sym}: FAILED {e}")
            failed.append(sym)
        if (i + 1) % 25 == 0:
            save_history(history)
        time.sleep(0.15)
    save_history(history)
    if failed:
        print(f"\nFailed: {','.join(failed)}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--full', action='store_true', help='Full backfill (313 calls)')
    p.add_argument('--refresh-recent', type=int, nargs='?', const=180, default=None,
                   metavar='DAYS', help='Re-fetch tickers with earnings in last N days')
    args = p.parse_args()
    api_key = get_api_key()
    if args.full:
        mode_full(api_key)
    elif args.refresh_recent is not None:
        mode_refresh_recent(api_key, args.refresh_recent)
    else:
        mode_delta(api_key)


if __name__ == '__main__':
    main()
