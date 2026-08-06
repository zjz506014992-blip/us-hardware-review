# -*- coding: utf-8 -*-
"""narrative JSON 校验器 — 把历史教训表里的写作坑固化成机器检查。

用法：python3 lint_narrative.py narrative_2026-08-05.json
退出码：0 = 通过（可有 WARN）；1 = 有 FAIL 必须修。

检查项（对应教训）：
  1. JSON 可解析（5/9、5/18 直引号系）
  2. 顶层 keys 合法；earnings_recap 与 news_tiers 平级、未嵌套（7/14）
  3. 字段类型：叙事字段必须是 str，不能是 list/tuple 残留（7/20、7/30 builder 尾逗号）
  4. 语言铁律：叙事字段 grep 英文高频词（8/5）
  5. theme 的每个 sector 在 INDUSTRY_MAP 中存在，且 |cap-w| >= 0.8%（铁律 2）
  6. earnings_recap 的 ah_dp 以 +/- 开头或为中文定性描述（不校验真伪，只校验格式）
  7. 数量：key_stocks 6-10 张、themes 2-5 个
"""
import json
import re
import sys
import glob
import os

REPO = os.path.dirname(os.path.abspath(__file__))

# 语言铁律高频词表（第 4 节对照表左列 + 常见漏网）。仅扫叙事字段。
EN_WORDS = [
    "AH", "BMO", "AMC", "beat", "miss", "guide", "guidance", "rally", "sell-off",
    "sell-the-news", "cap-w", "capex", "mega-cap", "mid-cap", "small-cap",
    "hyperscaler", "momentum", "breadth", "outlier", "priced-in", "rerating",
    "ramp", "backlog", "roadmap", "upgrade", "downgrade", "YoY", "QoQ",
    "record close", "blowout", "supercycle", "pop-then-fade", "mean-reversion",
    "risk-on", "risk-off", "Day 1", "Day 2", "Day 3", "broad",
]
# 允许出现英文的例外模式：ticker、指数、允许的技术术语在词表之外，无需列举。
NARRATIVE_FIELDS_CARD = ["title", "fund", "technical"]
NARRATIVE_FIELDS_THEME = ["theme", "driver", "cross_sector", "duration"]
NARRATIVE_FIELDS_RECAP = ["highlights", "guidance", "call_takeaway", "ah_dp"]
NARRATIVE_FIELDS_NEWS = ["title", "body", "impact"]

fails, warns = [], []


def fail(msg):
    fails.append(msg)


def warn(msg):
    warns.append(msg)


def check_str(val, where):
    if isinstance(val, (list, tuple)):
        fail(f"{where}: 类型是 {type(val).__name__}，应为 str（builder 尾逗号 tuple 坑）")
        return ""
    if not isinstance(val, str):
        fail(f"{where}: 类型是 {type(val).__name__}，应为 str")
        return ""
    return val


def scan_english(text, where):
    for w in EN_WORDS:
        # 词边界匹配，大小写按词表原样（AH/BMO 等大写词不误伤小写单词）
        pat = r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])"
        if re.search(pat, text):
            warn(f"{where}: 含英文词「{w}」，按语言铁律应译为中文（如确为代码/术语可忽略）")


def main(path):
    # 1. 解析
    try:
        d = json.load(open(path, encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"JSON 解析失败：line {e.lineno} col {e.colno} — {e.msg}（大概率是叙事文本里的 ASCII 直引号）")
        return

    # 2. 顶层 keys
    allowed = {"date", "researched_at", "version", "market_structure", "key_stocks",
               "sector_beta", "news_tiers", "earnings_recap", "asia_relay"}
    extra = set(d.keys()) - allowed
    if extra:
        warn(f"顶层出现未知 keys: {sorted(extra)}")
    for k in ("date", "market_structure", "key_stocks", "sector_beta", "news_tiers"):
        if k not in d:
            fail(f"缺少顶层 key: {k}")
    if "news_tiers" in d:
        for tk, tv in d["news_tiers"].items():
            if isinstance(tv, dict) and "verdict" in json.dumps(tv, ensure_ascii=False)[:200]:
                fail(f"news_tiers.{tk} 疑似嵌套了 earnings_recap 内容（7/14 教训：应为平级顶层 key）")

    # 3+4. 卡片
    cards = d.get("key_stocks", [])
    if not (6 <= len(cards) <= 10):
        warn(f"key_stocks 数量 {len(cards)}，规则为 6-10 张")
    for c in cards:
        sym = c.get("sym", "?")
        for f in NARRATIVE_FIELDS_CARD:
            scan_english(check_str(c.get(f, ""), f"card[{sym}].{f}"), f"card[{sym}].{f}")
        for f in ("bull", "bear", "catalysts"):
            v = c.get(f, [])
            if not isinstance(v, list):
                fail(f"card[{sym}].{f}: 应为 list")
            else:
                for i, item in enumerate(v):
                    scan_english(check_str(item, f"card[{sym}].{f}[{i}]"), f"card[{sym}].{f}[{i}]")

    # market_structure / tldr
    scan_english(check_str(d.get("market_structure", {}).get("narrative", ""),
                           "market_structure.narrative"), "market_structure.narrative")
    sb = d.get("sector_beta", {})
    scan_english(check_str(sb.get("tldr", ""), "sector_beta.tldr"), "sector_beta.tldr")

    # 5. themes 阈值
    themes = sb.get("themes", [])
    if not (2 <= len(themes) <= 5):
        warn(f"themes 数量 {len(themes)}，规则为 2-5 个")
    try:
        sys.path.insert(0, REPO)
        from gen import INDUSTRY_MAP
        conf_path = os.path.join(REPO, f"confirmed_{d.get('date')}.json")
        data = json.load(open(conf_path, encoding="utf-8"))["data"] if os.path.exists(conf_path) else None
        if data is None:
            warn(f"未找到 {os.path.basename(conf_path)}，跳过 sector 阈值校验")
    except Exception as e:
        data = None
        warn(f"加载 confirmed/INDUSTRY_MAP 失败，跳过 sector 阈值校验: {e}")
    for t in themes:
        name = t.get("theme", "?")[:20]
        for f in NARRATIVE_FIELDS_THEME:
            scan_english(check_str(t.get(f, ""), f"theme[{name}].{f}"), f"theme[{name}].{f}")
        if t.get("sentiment") not in ("bull", "bear"):
            fail(f"theme[{name}].sentiment 必须是 bull/bear")
        for sec in t.get("sectors", []):
            from gen import INDUSTRY_MAP as IM
            if sec not in IM:
                fail(f"theme[{name}] sector「{sec}」不在 INDUSTRY_MAP（必须逐字照抄子行业名）")
            elif data is not None:
                ss = [data[s] for s in IM[sec] if s in data]
                if ss:
                    cw = sum(v["cap"] * v["dp"] for v in ss) / sum(v["cap"] for v in ss)
                    if abs(cw) < 0.8:
                        fail(f"theme[{name}] sector「{sec}」cap-w {cw:+.2f}% < 0.8%（铁律 2：移出或删主题）")

    # 6. recap
    er = d.get("earnings_recap")
    if er:
        for it in er.get("items", []):
            sym = it.get("sym", "?")
            v = it.get("verdict", "")
            if v not in ("beat", "miss", "mixed", "inline", "—", "-"):
                fail(f"recap[{sym}].verdict「{v}」不合法")
            ah = check_str(it.get("ah_dp", ""), f"recap[{sym}].ah_dp")
            if ah and not (ah[0] in "+-" or re.match(r"^[一-鿿（]", ah)):
                warn(f"recap[{sym}].ah_dp「{ah[:20]}…」既不以 +/- 开头也不是中文定性描述")
            for f in NARRATIVE_FIELDS_RECAP:
                scan_english(check_str(it.get(f, ""), f"recap[{sym}].{f}"), f"recap[{sym}].{f}")

    # asia_relay（可选）
    ar = d.get("asia_relay")
    if ar:
        scan_english(check_str(ar.get("tldr", ""), "asia_relay.tldr"), "asia_relay.tldr")
        for i, it in enumerate(ar.get("items", [])):
            scan_english(check_str(it.get("note", ""), f"asia_relay[{i}].note"), f"asia_relay[{i}].note")
            if not isinstance(it.get("dp"), (int, float)):
                warn(f"asia_relay[{i}].dp 缺失或非数值（chip 无法着色）")

    # news
    for tk, tv in d.get("news_tiers", {}).items():
        for i, it in enumerate(tv.get("items", []) if isinstance(tv, dict) else []):
            for f in NARRATIVE_FIELDS_NEWS:
                scan_english(check_str(it.get(f, ""), f"{tk}[{i}].{f}"), f"{tk}[{i}].{f}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1])
    for m in fails:
        print(f"[FAIL] {m}")
    for m in warns:
        print(f"[WARN] {m}")
    print(f"—— lint 结果：{len(fails)} FAIL / {len(warns)} WARN ——")
    sys.exit(1 if fails else 0)
