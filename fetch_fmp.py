#!/usr/bin/env python3
"""每日 FMP 数据拉取 — GitHub Actions / Mac mini 入口

读 INDUSTRY_MAP 池子（gen.py 建模池，当前 102 只），调 FMP /quote 批量端点，
落到 confirmed_{TRADING_DATE}.json，供 gen.py 消费。

同时拉取宏观指数 + ETF + 风格因子，落到 confirmed_macros_{TRADING_DATE}.json。

环境变量:
  FMP_API_KEY  必填，从 GitHub Secrets / launchd plist / shell env 注入
  REVIEW_DATE  选填，YYYY-MM-DD，强制覆盖交易日期（默认从 FMP timestamp 推断）
"""
import os, sys, json, time
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# POOL=soft 时 gen 模块自动换成软件池（INDUSTRY_MAP_SOFT），本文件零池子逻辑；
# 输出文件同步带 soft_ 前缀（FILE_PFX），与硬件数据文件互不污染。
from gen import INDUSTRY_MAP, FILE_PFX, IS_SOFT

TICKERS = sorted({s for syms in INDUSTRY_MAP.values() for s in syms})

# === 宏观指数 + ETF + 风格因子（用于 gen.py 自动填 BROAD/SEMI/GICS/STYLE_FACTORS dicts）===
# 格式：fmp_symbol -> (group, display_code, display_name, hint)
# group: 'broad' / 'semi' / 'gics' / 'style'
# 注意：FMP 部分指数符号需带 ^ 前缀（如 ^GSPC = S&P 500）；如果某 symbol fetch 失败会被记入 missing 但不阻塞其他
MACRO_SYMBOLS = {
    # 大盘/宏观
    '^GSPC':    ('broad', 'SPX',   'S&P 500',     '宏观大盘'),
    '^NDX':     ('broad', 'NDX',   'Nasdaq 100',  '科技权重'),
    '^DJI':     ('broad', 'DJI',   'Dow Jones',   '蓝筹工业'),
    '^RUT':     ('broad', 'RUT',   'Russell 2000','小盘'),
    '^VIX':     ('broad', 'VIX',   'VIX',         '波动率'),
    'DX-Y.NYB': ('broad', 'DXY',   'US Dollar',   '美元'),
    '^TNX':     ('broad', 'US10Y', '10Y 收益率',  '利率'),
    'CLUSD':    ('broad', 'WTI',   'WTI 原油',    '油价'),
    # 半导体 ETF
    '^SOX':     ('semi',  'SOX',   'PHLX 半导体',         '半导体官方指数'),
    'SOXX':     ('semi',  'SOXX',  'iShares 半导体',      '权重股 ETF'),
    'SMH':      ('semi',  'SMH',   'VanEck 半导体',       'AI 算力 ETF'),
    'XSD':      ('semi',  'XSD',   'SPDR 半导体（小盘等权重）', '小盘等权'),
    'PSI':      ('semi',  'PSI',   'Invesco 动态半导体',  '量化半导体'),
    # GICS 11 一级行业 ETF
    'XLK':      ('gics',  'XLK',   '信息科技 Tech',         ''),
    'XLC':      ('gics',  'XLC',   '通信服务 Comm Svc',     ''),
    'XLY':      ('gics',  'XLY',   '可选消费 Cons Disc',    ''),
    'XLF':      ('gics',  'XLF',   '金融 Financials',       ''),
    'XLI':      ('gics',  'XLI',   '工业 Industrials',     ''),
    'XLB':      ('gics',  'XLB',   '材料 Materials',       ''),
    'XLRE':     ('gics',  'XLRE',  '房地产 Real Estate',    ''),
    'XLV':      ('gics',  'XLV',   '医疗 Health Care',     ''),
    'XLU':      ('gics',  'XLU',   '公用事业 Utilities',    ''),
    'XLP':      ('gics',  'XLP',   '必选消费 Cons Staples', ''),
    'XLE':      ('gics',  'XLE',   '能源 Energy',          ''),
    # 风格因子
    'IWF':      ('style', 'IWF',   'Russell 1000 Growth',     '成长因子'),
    'IWD':      ('style', 'IWD',   'Russell 1000 Value',      '价值因子'),
    'MTUM':     ('style', 'MTUM',  'iShares Momentum Factor', '动量因子'),
    'SPLV':     ('style', 'SPLV',  'S&P 500 Low Volatility',  '低波因子'),
    'QUAL':     ('style', 'QUAL',  'iShares Quality Factor',  '质量因子'),
    'RSP':      ('style', 'RSP',   'S&P 500 Equal Weight',    '等权基准'),
}


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


def pick(q, *keys):
    """从 q 里按顺序取第一个非 None 的字段（兼容 v3 / stable 字段名差异）"""
    for k in keys:
        v = q.get(k)
        if v is not None:
            return v
    return None


def fetch_macros(trading_date, repo_dir):
    """单独 fetch 宏观指数 + ETF + 风格因子，落到 confirmed_macros_{DATE}.json

    指数符号（^GSPC / ^NDX 等）不一定在 batch-quote 工作，逐个用 /stable/quote 单点 fallback。
    """
    api_key = get_api_key()
    syms = list(MACRO_SYMBOLS.keys())
    print(f"\nFetching FMP macros for {len(syms)} symbols (indices/ETFs/factors)...")

    # 先尝试 batch-quote（ETF 一般支持，指数符号可能不支持）
    batch_quotes = fetch_quote_batch(syms, retries=2)

    out_data = {}
    missing = []
    for fmp_sym, (group, code, name, hint) in MACRO_SYMBOLS.items():
        q = batch_quotes.get(fmp_sym)
        # batch 没拿到则用单 quote 端点兜底（指数符号常见）
        if not q:
            url = f"https://financialmodelingprep.com/stable/quote?symbol={fmp_sym}&apikey={api_key}"
            try:
                req = Request(url, headers={'User-Agent': 'us-hardware-review/1.0'})
                with urlopen(req, timeout=15) as r:
                    data = json.loads(r.read())
                if isinstance(data, list) and data:
                    q = data[0]
                elif isinstance(data, dict):
                    q = data
                time.sleep(0.2)
            except Exception as e:
                print(f"  [macro] {fmp_sym} single-quote failed: {e}")

        if not q:
            missing.append(fmp_sym)
            continue
        price = pick(q, 'price', 'lastSalePrice', 'last')
        dp = pick(q, 'changesPercentage', 'changePercentage', 'changePercent', 'percentageChange') or 0
        if price is None:
            missing.append(fmp_sym)
            continue
        out_data[fmp_sym] = {
            'group': group,
            'code': code,
            'name': name,
            'hint': hint,
            'close': round(float(price), 2),
            'dp': round(float(dp), 2),
            'prev_close': pick(q, 'previousClose', 'prevClose'),
            'high': pick(q, 'dayHigh', 'high'),
            'low': pick(q, 'dayLow', 'low'),
        }

    out = {
        'date': trading_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total': len(syms),
        'hit': len(out_data),
        'missing': missing,
        'data': out_data,
    }
    path = os.path.join(repo_dir, f'confirmed_macros_{trading_date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path}  hit={len(out_data)}/{len(syms)}  missing={len(missing)}")
    if missing:
        print(f"  Missing macros: {','.join(missing)}")


def _fetch_json(url, timeout=20):
    req = Request(url, headers={'User-Agent': 'us-hardware-review/1.0'})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def fetch_aftermarket(repo_dir):
    """盘后收盘价抓取（2026-08-06 新增，独立入口 --aftermarket）

    由 daily.yml 第二个 cron（00:30 UTC = 美东 8:30pm，盘后 session 结束后）触发。
    读最新 confirmed_{DATE}.json 拿常规收盘价，调 /stable/batch-aftermarket-quote
    算盘后涨跌，落 confirmed_ah_{DATE}.json——次日 routine 的 recap 回补直接读文件。
    """
    import glob as _glob
    api_key = get_api_key()
    files = sorted([f for f in _glob.glob(os.path.join(repo_dir, 'confirmed_*.json'))
                    if 'macros' not in os.path.basename(f) and '_ah_' not in os.path.basename(f)
                    and 'ratings' not in os.path.basename(f)], reverse=True)
    if not files:
        sys.exit("ERROR: no confirmed_*.json found, run main fetch first")
    with open(files[0], encoding='utf-8') as f:
        conf = json.load(f)
    trading_date = conf['date']
    closes = {s: v['close'] for s, v in conf['data'].items()}
    syms = sorted(closes)
    print(f"Fetching aftermarket quotes for {len(syms)} tickers (trading date {trading_date})...")

    out_data, missing = {}, []
    chunks = [syms[i:i+100] for i in range(0, len(syms), 100)]
    quotes = {}
    for i, chunk in enumerate(chunks):
        url = f"https://financialmodelingprep.com/stable/batch-aftermarket-quote?symbols={','.join(chunk)}&apikey={api_key}"
        try:
            data = _fetch_json(url, timeout=30)
            if isinstance(data, list):
                for q in data:
                    if q.get('symbol'):
                        quotes[q['symbol']] = q
                print(f"  chunk {i+1}/{len(chunks)}: {len(data)} aftermarket quotes")
            else:
                print(f"  chunk {i+1} unexpected payload: {str(data)[:150]}")
        except Exception as e:
            print(f"  chunk {i+1} aftermarket batch failed: {e}")
        time.sleep(0.3)

    for sym in syms:
        q = quotes.get(sym)
        ah_price = pick(q or {}, 'price', 'lastPrice', 'last', 'askPrice', 'bidPrice')
        if not q or ah_price in (None, 0):
            missing.append(sym)
            continue
        close = closes.get(sym)
        ah_dp = round((float(ah_price) / close - 1) * 100, 2) if close else None
        out_data[sym] = {
            'ah_price': round(float(ah_price), 2),
            'regular_close': close,
            'ah_dp': ah_dp,
            'timestamp': q.get('timestamp'),
        }

    out = {
        'date': trading_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total': len(syms), 'hit': len(out_data), 'missing': missing,
        'data': out_data,
    }
    path = os.path.join(repo_dir, f'confirmed_ah_{trading_date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path}  hit={len(out_data)}/{len(syms)}")
    gho = os.environ.get('GITHUB_OUTPUT')
    if gho:
        with open(gho, 'a') as f:
            f.write(f"date={trading_date}\nhit={len(out_data)}\n")


def fetch_ratings(trading_date, repo_dir):
    """当日池内评级/目标价变动抓取（2026-08-06 新增，非致命）

    逐票调 /stable/grades（评级变动）+ /stable/price-target-news（目标价变动），
    过滤出最近 2 个自然日的记录，落 confirmed_ratings_{DATE}.json。
    个股卡 sellside 字段从此有每日真值清单，不再靠 WebSearch 碰运气。
    端点若不可用（404/schema 变化）静默跳过并计数，不阻塞主流程。
    """
    api_key = get_api_key()
    from datetime import date as _date
    d0 = _date.fromisoformat(trading_date)
    recent = {(d0 - timedelta(days=k)).isoformat() for k in range(0, 2)}

    grades, pt_news = [], []
    g_fail = p_fail = 0
    print(f"\nFetching ratings/PT changes for {len(TICKERS)} tickers (dates {sorted(recent)})...")
    for sym in TICKERS:
        try:
            data = _fetch_json(f"https://financialmodelingprep.com/stable/grades?symbol={sym}&apikey={api_key}", timeout=15)
            if isinstance(data, list):
                for g in data[:10]:
                    gd = str(g.get('date', ''))[:10]
                    if gd in recent:
                        grades.append({'sym': sym, 'date': gd,
                                       'firm': g.get('gradingCompany') or g.get('company'),
                                       'action': g.get('action'),
                                       'prev': g.get('previousGrade'), 'new': g.get('newGrade')})
        except Exception:
            g_fail += 1
        try:
            data = _fetch_json(f"https://financialmodelingprep.com/stable/price-target-news?symbol={sym}&limit=5&apikey={api_key}", timeout=15)
            if isinstance(data, list):
                for p in data:
                    pd_ = str(p.get('publishedDate', p.get('date', '')))[:10]
                    if pd_ in recent:
                        pt_news.append({'sym': sym, 'date': pd_,
                                        'firm': p.get('analystCompany') or p.get('company'),
                                        'analyst': p.get('analystName'),
                                        'pt_prior': p.get('priceTargetPrior'), 'pt_new': p.get('priceTarget'),
                                        'title': (p.get('newsTitle') or '')[:120]})
        except Exception:
            p_fail += 1
        time.sleep(0.12)

    out = {
        'date': trading_date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'grades': grades, 'pt_news': pt_news,
        'endpoint_failures': {'grades': g_fail, 'pt_news': p_fail},
    }
    path = os.path.join(repo_dir, f'{FILE_PFX}confirmed_ratings_{trading_date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path}  grades={len(grades)} pt_news={len(pt_news)} (fail g={g_fail}/p={p_fail})")


def main():
    print(f"Fetching FMP /quote for {len(TICKERS)} tickers...")
    quotes = fetch_quote_batch(TICKERS)
    if not quotes:
        sys.exit("ERROR: no quotes returned from FMP")

    # 诊断：打印第一条响应的所有字段，便于发现新端点的 schema
    sample_sym, sample_q = next(iter(quotes.items()))
    print(f"\n=== SAMPLE RESPONSE [{sample_sym}] ===")
    print(json.dumps(sample_q, indent=2, ensure_ascii=False, default=str))
    print("=== END SAMPLE ===\n")

    trading_date = detect_trading_date(quotes)
    print(f"Trading date: {trading_date}")

    confirmed = {}
    missing = []
    for sym in TICKERS:
        q = quotes.get(sym)
        price = pick(q or {}, 'price', 'lastSalePrice', 'last')
        if not q or price in (None, 0):
            missing.append(sym)
            continue
        cap_raw = pick(q, 'marketCap', 'marketCapitalization') or 0
        dp = pick(q, 'changesPercentage', 'changePercentage', 'changePercent', 'percentageChange') or 0
        confirmed[sym] = {
            'close': round(price, 2),
            'dp': round(dp, 2),
            'cap': max(round(cap_raw / 1e6), 1),
            'high': pick(q, 'dayHigh', 'high'),
            'low': pick(q, 'dayLow', 'low'),
            'prev_close': pick(q, 'previousClose', 'prevClose'),
            'volume': pick(q, 'volume', 'lastSaleVolume'),
            # 2026-08-06 起扩展：52 周高低 + 50/200 日均线（batch-quote 响应自带，零额外调用）
            # 供个股卡 range52w / technical 自动取数，不再依赖 WebSearch/MCP 现查
            'year_high': pick(q, 'yearHigh'),
            'year_low': pick(q, 'yearLow'),
            'avg50': pick(q, 'priceAvg50'),
            'avg200': pick(q, 'priceAvg200'),
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
    path = os.path.join(repo_dir, f'{FILE_PFX}confirmed_{trading_date}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {path}  hit={len(confirmed)}/{len(TICKERS)}  missing={len(missing)}")
    if missing:
        print(f"Missing: {','.join(missing[:30])}{'...' if len(missing)>30 else ''}")

    # 同步拉宏观指数（失败不阻塞主流程）；软件池跑时跳过——共用硬件跑落地的 confirmed_macros
    if not IS_SOFT:
        try:
            fetch_macros(trading_date, repo_dir)
        except Exception as e:
            print(f"WARN: macros fetch failed (non-fatal): {e}")

    # 同步拉当日评级/目标价变动（失败不阻塞主流程）
    try:
        fetch_ratings(trading_date, repo_dir)
    except Exception as e:
        print(f"WARN: ratings fetch failed (non-fatal): {e}")

    gho = os.environ.get('GITHUB_OUTPUT')
    if gho:
        with open(gho, 'a') as f:
            f.write(f"date={trading_date}\nhit={len(confirmed)}\nmissing={len(missing)}\ntotal={len(TICKERS)}\n")


if __name__ == '__main__':
    if '--aftermarket' in sys.argv:
        if IS_SOFT:
            print("aftermarket 仅硬件池使用（软件盘后价由 routine 用 FMP MCP 现查），POOL=soft 跳过")
        else:
            fetch_aftermarket(os.path.dirname(os.path.abspath(__file__)))
    else:
        main()
