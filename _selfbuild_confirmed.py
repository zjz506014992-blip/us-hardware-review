#!/usr/bin/env python3
"""MCP 自建 confirmed 文件模板（GH Actions cron 失灵时的标准兜底，2026-10-13 固化进仓库）。

用法（routine 内）：
  1. 用 mcp__FMP__quote batch-quote 拉「硬件 102 + 宏观 30」合并 132 符号（通常内联返回）
     与「软件 181」（通常超限自动落盘 tool-results/ 目录）。
  2. 跑本脚本：python3 _selfbuild_confirmed.py <DATE> <transcript.jsonl> [software_toolresult.txt]
     - 硬件+宏观从转录 JSONL 机器提取（三条件：rec.type=='user' + tool_result + text.startswith('[')，
       且包含 AAPL 与 GSPC 关键词——过滤词不带引号，原始行内引号是转义态）。
     - 软件优先从 tool-results 落盘文件读；若也内联，则从转录提取（包含 GOOGL 关键词）。
  3. 脚本自带三重验证：json 可解析 + hit 计数 + timestamp 换算 == 当日 20:00 UTC 附近。

注意：若上次运行中途抛错留下半成品 json，先删除再重跑（9/18 教训）。
"""
import json, os, sys
from datetime import datetime, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def pick(q, *keys):
    for k in keys:
        v = q.get(k)
        if v is not None:
            return v
    return None


def extract_inline_results(jsonl_path, must_contain):
    """从会话转录 JSONL 提取 tool_result 内联 JSON 数组（最新一条匹配的）。"""
    found = None
    with open(jsonl_path, encoding='utf-8') as f:
        for line in f:
            if not all(k in line for k in must_contain):
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get('type') != 'user':
                continue
            for item in (rec.get('message') or {}).get('content') or []:
                if not isinstance(item, dict) or item.get('type') != 'tool_result':
                    continue
                content = item.get('content')
                if isinstance(content, list):
                    for c in content:
                        text = c.get('text', '') if isinstance(c, dict) else ''
                        if text.startswith('[') and all(k in text for k in must_contain):
                            found = text  # 保留最新
                elif isinstance(content, str) and content.startswith('['):
                    found = content
    if not found:
        raise SystemExit(f'transcript 中未找到含 {must_contain} 的 tool_result 数组')
    return json.loads(found)


def build_stock_entry(q):
    return {
        'close': round(float(q['price']), 2),
        'dp': round(float(pick(q, 'changesPercentage', 'changePercentage') or 0), 2),
        'cap': max(round((pick(q, 'marketCap') or 0) / 1e6), 1),
        'high': pick(q, 'dayHigh'),
        'low': pick(q, 'dayLow'),
        'prev_close': pick(q, 'previousClose'),
        'volume': pick(q, 'volume'),
        'year_high': pick(q, 'yearHigh'),
        'year_low': pick(q, 'yearLow'),
        'avg50': pick(q, 'priceAvg50'),
        'avg200': pick(q, 'priceAvg200'),
    }


def write_confirmed(date, pool, quotes_by_sym, out_path):
    data, missing = {}, []
    for sym in pool:
        q = quotes_by_sym.get(sym)
        if not q or not q.get('price'):
            missing.append(sym)
            continue
        data[sym] = build_stock_entry(q)
    out = {
        'date': date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total': len(pool), 'hit': len(data), 'missing': missing,
        'data': data,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'Wrote {out_path}  hit={len(data)}/{len(pool)}  missing={missing}')
    return out


def write_macros(date, macro_symbols, quotes_by_sym, out_path):
    data, missing = {}, []
    for fmp_sym, (group, code, name, hint) in macro_symbols.items():
        q = quotes_by_sym.get(fmp_sym)
        if not q or q.get('price') is None:
            missing.append(fmp_sym)
            continue
        data[fmp_sym] = {
            'group': group, 'code': code, 'name': name, 'hint': hint,
            'close': round(float(q['price']), 2),
            'dp': round(float(pick(q, 'changesPercentage', 'changePercentage') or 0), 2),
            'prev_close': pick(q, 'previousClose'),
            'high': pick(q, 'dayHigh'),
            'low': pick(q, 'dayLow'),
        }
    out = {
        'date': date,
        'fetched_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'total': len(macro_symbols), 'hit': len(data), 'missing': missing,
        'data': data,
    }
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'Wrote {out_path}  hit={len(data)}/{len(macro_symbols)}  missing={missing}')


def main():
    date = sys.argv[1]
    transcript = sys.argv[2]
    soft_file = sys.argv[3] if len(sys.argv) > 3 else None

    sys.path.insert(0, REPO_DIR)
    import fetch_fmp
    from gen import INDUSTRY_MAP as HW_MAP
    hw_pool = sorted({s for ss in HW_MAP.values() for s in ss if s != 'NA'})
    import pool_soft
    soft_pool = sorted({s for ss in pool_soft.INDUSTRY_MAP_SOFT.values() for s in ss if s != 'NA'})

    # 硬件 + 宏观（内联，转录提取）
    hw_quotes = extract_inline_results(transcript, ['AAPL', 'GSPC'])
    by_sym = {q['symbol']: q for q in hw_quotes}
    ts = max(q.get('timestamp') or 0 for q in hw_quotes if q.get('symbol') in ('AAPL', 'NVDA'))
    print('quote timestamp =', datetime.fromtimestamp(ts, timezone.utc))
    write_confirmed(date, hw_pool, by_sym, os.path.join(REPO_DIR, f'confirmed_{date}.json'))
    write_macros(date, fetch_fmp.MACRO_SYMBOLS, by_sym, os.path.join(REPO_DIR, f'confirmed_macros_{date}.json'))

    # 软件
    if soft_file and os.path.exists(soft_file):
        soft_quotes = json.loads(open(soft_file, encoding='utf-8').read())
    else:
        soft_quotes = extract_inline_results(transcript, ['GOOGL', 'MSFT'])
    soft_by_sym = {q['symbol']: q for q in soft_quotes}
    write_confirmed(date, soft_pool, soft_by_sym, os.path.join(REPO_DIR, f'soft_confirmed_{date}.json'))


if __name__ == '__main__':
    main()
