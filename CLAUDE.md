# 美股硬件板块每日复盘 — Claude 工作手册

> 这是给 **未来 Claude 会话** 看的"使命说明书"。每次新会话启动会自动读这份文件，所以以下内容必须 **自包含、可执行、无歧义**。

---

## 1. 项目一句话

每日产出 **美股硬件板块** 收盘复盘网页，发布到 GitHub Pages：
<https://zjz506014992-blip.github.io/us-hardware-review/>

覆盖 **314 只股票 / 24 个子行业 / 4 大板块**，含 ECharts treemap、Chart.js scatter、个股深度卡、新闻 Tier 分层、业绩日历等。

## 2. 仓库结构

```
us-hardware-review/
├── gen.py                       # 主生成器（~1900 行），生成所有 HTML
├── fetch_fmp.py                 # 每日 FMP 行情，写 confirmed_{DATE}.json
├── fetch_earnings_history.py    # 业绩历史 + 公司 profile 维护（delta / refresh-recent / full / profiles）
├── calendar.html                # 业绩日历（加载 earnings_history.json + company_profiles.json，点格弹框）
├── earnings.html                # 业绩历史搜索表（客户端加载 earnings_history.json）
├── earnings_history.json        # 314 池近 25-30 年业绩（首次 --full 回填，之后日增量）
├── company_profiles.json        # 314 公司 profile（name/desc/industry/website/image，每周日刷新）
├── index.html                   # 历史存档目录
├── {DATE}.html                  # 当日复盘页（一天一份）
├── stocks-{DATE}.html           # 当日全部 314 只股票表
├── confirmed_{DATE}.json        # FMP 当日行情（GitHub Actions 自动产出）
├── _meta.json                   # 累计每日统计（cap_w / up / down / flat / total）
├── .github/workflows/daily.yml  # GitHub Actions 定时任务（cron 22:30 UTC 工作日）
└── CLAUDE.md                    # 你正在读的这个文件
```

**Git 仓库**：<https://github.com/zjz506014992-blip/us-hardware-review>

## 3. 数据流（自动 + 手动两层）

### 3.1 自动层（GitHub Actions，每个交易日跑）
- 美东 22:30（北京 6:30am）触发 `.github/workflows/daily.yml`
- 跑 `python fetch_fmp.py` → 调 `https://financialmodelingprep.com/stable/batch-quote` 拉 313 只 ticker（'NA' 是占位符跳过）
- 落到 `confirmed_{DATE}.json`，schema：
  ```json
  {
    "date": "2026-04-24",
    "fetched_at": "2026-04-24T22:30:15+00:00",
    "total": 313, "hit": 313, "missing": [],
    "data": {
      "NVDA": {"close": 208.27, "dp": 4.32, "cap": 5062000,
               "high": 215, "low": 200, "prev_close": 199.64, "volume": 12345}
    }
  }
  ```
  注意：`cap` 单位是 **$M（百万美元）**，不是亿、不是 $B。
- 跑 `python gen.py` → 自动检测最新 JSON、覆盖 `DATE` 和 `CONFIRMED`、重新生成所有 HTML
- Git auto commit & push

### 3.2 手动层（你 = Claude，每个交易日早上跑）
**叙事部分** FMP 不提供，必须由你写。每天早上用户起床后，会让你做这件事。

## 4. 你每日要做的事（核心工作流）

当用户说"**今天复盘**"或类似话时，按顺序执行：

1. **拉取最新代码**：`git pull origin main`（确保 GitHub Actions 跑出来的新数据已经到本地）

2. **找最新 FMP 数据**：
   ```bash
   ls -t confirmed_*.json | head -1
   ```
   读这个 JSON。

3. **看当日 stats**：读 `_meta.json` 最新一条，确认 cap_w / up / down 数字。

4. **更新 gen.py 里的 5 块叙事数据**（**只动 dict，别动函数**）：

   | 块 | 行号附近 | 字段 | 数据源 |
   |---|---|---|---|
   | `BROAD_INDICES` | gen.py 第 11 行 | SPX/NDX/DJI/RUT/VIX/DXY/US10Y/WTI 收盘+涨跌 | WebSearch（FMP 没有指数实时） |
   | `SEMI_INDICES` | gen.py 第 23 行 | SOX/SOXX/SMH/XSD/PSI 收盘+涨跌 | WebSearch |
   | `GICS_INDICES` | gen.py 第 32 行 | XLK/XLC/XLY/XLF/XLI/XLB/XLRE/XLV/XLU/XLP/XLE 收盘+涨跌 | WebSearch |
   | **`STYLE_FACTORS`** | gen.py 第 48 行起 | **IWF/IWD/MTUM/SPLV/QUAL/RSP 6 个因子 ETF 收盘+涨跌** | **WebSearch** |
   | **`MARKET_STRUCTURE`** | gen.py 第 60 行起 | **`narrative` 字段：市场结构 + 风格因子综合解读 100-300 字** | **基于 4 个自动算的比值（普涨度 RSP/SPX、科技强度 NDX/SPX、半导体强度 SOX/NDX、硬件池强度 Pool/SOX）+ 风格因子领跑情况，自己写** |
   | `KEY_STOCKS` | gen.py 第 64 行起 | 8 张重点个股深度卡 | 从 FMP JSON 取 dp/close/cap，叙事自己写 |
   | **`SECTOR_BETA`** | gen.py 第 437 行起 | **当日核心叙事 (`tldr`) + 3-5 个板块联动主题 (`themes`)** | **从 FMP JSON 算子行业 cap-w 涨跌，叙事自己写。详见下方 schema** |
   | `NEWS_TIERS` | gen.py 接近末尾 | Tier 1（宏观/大盘）/ Tier 2（半导体深度）/ Tier 3（亚洲供应链）/ Tier 4（公司公告/分析师评级） | WebSearch + 你的判断 |

### `SECTOR_BETA` 写作要点（最重要的叙事块）

`tldr`（当日核心叙事）：300-500 字，用 `<br><br>` 分 3 段：
1. **核心叙事**：今日最大事件 + 引爆点；强调"是 board beta 而非个股 alpha"
2. **板块脉络**：强势板块 + 弱势板块 + 大盘 / SOX / NDX 数字
3. **后市看点**：本周 / 本月关键数据 + 财报节点

`themes`（3-5 个）：每天挑当日最有信号意义的板块联动。

#### 5 条 Theme 写作铁律（必须遵守）

1. **数据真实性硬规则** — `driver` / `cross_sector` 里的所有 ticker 涨幅必须从当日 `confirmed_*.json` 取实数。**写完前必须 grep 一遍** `confirmed_{DATE}.json` 验证：
   ```bash
   python -c "import json; d=json.load(open('confirmed_{DATE}.json')); [print(s, d['data'][s]['dp']) for s in ['INTC','APH','GLW']]"
   ```
   过去翻车案例：把 APH 写成 +2.9% 实际 -0.31%、CIEN 写成 +4.1% 实际 +0.96% — 这种错数据让整个主题立不住。

2. **板块 cap-w 阈值硬规则** — `sectors` 字段里的每个板块，**cap-w |dp| 必须 ≥ 0.8%**。如果板块只有 1 只票动而其他没动，不算 beta。`gen.py` 已加 sanity check：板块 |cap-w| < 0.8% 时渲染会显示 ⚠️ "未形成 beta" warning chip，stdout 也会打印警告 — 看到警告就**回头删掉那个板块或者整个主题重新选**。

3. **不凑数原则** — 宁可写 single-sector theme（只一个板块），也不要硬拉一个 cap-w 不动的板块凑成"X+Y 联动"。**反例：** "光通信 + 连接器 beta"——光通信 +2.89% 是真 beta，连接器板块 +1.10% 跑输大盘 +3.26%、龙头 APH/TEL 还在跌，把连接器拉进来就是凑数，主题立不住。**正例：** "光通信板块 beta" 单板块即可，连接器在 cross_sector 里写明"明确不联动"。

4. **跨标签真实经济概念** — 当一个真实经济概念跨越 INDUSTRY_MAP 多个标签（典型如 "CPU 设计"：INTC 在"CPU处理器"、ARM/QCOM 在"Fabless设计"、AMD 在"AI加速"），`sectors` 字段写全所有相关标签，**driver 必须明确说明"为什么这些标签放一起"**——不要写 "CPU + Fabless 板块 beta" 这种把 INDUSTRY_MAP 标签当主题名的偷懒写法，要写 "CPU 设计板块 beta" + driver 里点出"池里这些公司分布在 X/Y/Z 三个标签下，但本质是同一组 CPU/SoC 设计公司"。

5. **特例点名（INDUSTRY_MAP 归类粗糙的票）** — 池子里有些票（典型 GLW 归"连接器元件"但 Corning 业务跨光纤/玻璃/陶瓷、AMD 归"AI 加速"但同时是 CPU 设计公司）当天驱动可能跨主题，driver 里要明确标注："虽然池里我们归类 X 子行业（因为 业务 Y），但当天 +N% 的实际驱动来自 Z 业务，**实质属于本主题**"。这种点名比例每天不超过 1-2 个，超过说明 INDUSTRY_MAP 该重新切了。

#### 必填字段

- `theme`: 标题，一句话点明唯一逻辑（**避免 "X+Y 板块联动" 模糊式标题，要 "XX 板块 beta：一句话点逻辑"**）
- `sectors`: list[str]，涉及子行业（INDUSTRY_MAP 的 key，每个必须满足铁律 2 的阈值）
- `sentiment`: "bull" 或 "bear"
- `driver`: 共同驱动叙事，**200-400 字**，最核心
- `cross_sector`: 跨板块联动，**50-150 字**，强制要写（包括"明确不联动"的负面观察）
- `duration`: 时效判断，30-80 字（短期催化 vs 长期趋势）

#### 主题数量规则

- 强催化日（财报潮 / SOX ±2%+）：5 个主题
- 平淡日：3 个主题

#### 写作风格

- 用具体数字（共识 EPS / 营收 / cap-w dp / top movers ±%）
- 用具体公司动作（"X 公司 Q1 财报营收 $XB +X% YoY，引爆 Y 板块"）
- 不写空话（避免"持续观察、关注后续"等模糊用语）

### `MARKET_STRUCTURE` 写作要点

`narrative` 字段（100-300 字，分 3 段）：

**第 1 段：市场结构**（用 4 个比值，gen.py 自动算并显示在 KPI 卡里，narrative 里要把比值含义讲清）：
- 普涨度 RSP/SPX：≥ 1 普涨；0.7-1 偏窄；< 0.7 极窄幅（仅头部权重股拉指数）
- 科技强度 NDX/SPX：≥ 1.2 科技独强；0.8-1.2 跟涨；< 0.8 科技跑输
- 半导体强度 SOX/NDX：≥ 2 远超；1.2-2 超配；0.8-1.2 跟涨；< 0.8 跑输
- 硬件池强度 Pool/SOX：≥ 1 硬件池跑赢 SOX（中小盘强）；< 0.7 跑输（仅大盘股拉动）

**第 2 段：风格因子**：哪个因子领跑（`STYLE_FACTORS` 排序后取最高），Growth vs Value 比值，今日是 Risk-On / Risk-Off / 防御抬升 哪种结构。常见组合：
- 动量 + 成长 + 低波下行 → 典型 Risk-On
- 价值 + 低波 + 质量上行 → Risk-Off / 防御
- 动量 + 质量 + 价值同向 → 普涨基本面 rally

**第 3 段：综合判断**：用一句话给出"今日属于哪一类历史模式"+ 后市风险点（如"窄幅领涨脆弱性，关注 MTUM 与 SOX 拐点"）

5. **跑生成**：`python gen.py`

6. **检查输出**：
   ```bash
   ls -la {DATE}.html stocks-{DATE}.html
   git status --short
   ```

7. **更新 `earnings_briefs.json`（增量补全未来 7 天的中文 brief）**：
   ```bash
   # 找未来 7 天的池内业绩 + 已有 brief 的覆盖率
   python <<'PY'
   import json
   from datetime import datetime, timedelta
   today = datetime.now().date()
   end = today + timedelta(days=7)
   with open('earnings_history.json') as f: hist = json.load(f)
   with open('earnings_briefs.json') as f: briefs = json.load(f)
   missing = []
   for sym, recs in hist.items():
       for r in recs:
           d = r.get('date', '')
           if today.isoformat() <= d <= end.isoformat():
               key = f"{sym}_{d}"
               if key not in briefs:
                   missing.append((d, sym, r.get('epsEstimated'), r.get('revenueEstimated')))
   missing.sort(key=lambda x: (x[0], -(x[3] or 0)))
   print(f"未来 7 天缺 brief 的: {len(missing)} 家")
   for d, s, e, rev in missing[:30]:
       rev_s = f"${rev/1e9:.1f}B" if rev and rev>=1e9 else (f"${rev/1e6:.0f}M" if rev else "—")
       print(f"  {d}  {s:6s}  EPS_est={e}  rev_est={rev_s}")
   PY
   ```
   - 对每只缺失的 ticker，写一份中文 brief（schema 见下面"earnings_briefs.json schema"）
   - 大盘股（rev > $1B）写详细版（thesis 6 条看点），中小盘短一些（3-4 条）
   - 必要时 WebSearch 当季 earnings preview 验证关键数字

8. **提交 + 推送**：
   ```bash
   git add gen.py {DATE}.html stocks-{DATE}.html index.html _meta.json earnings_briefs.json
   git commit -m "feat: {DATE} review (cap-w +X.XX%, key takeaway 一句话)"
   git push origin main
   ```

9. **告诉用户**：发布地址 + 关键变化（哪只大涨、哪只大跌、风格切换等）+ 本次新补了几家 brief

---

### `earnings_briefs.json` schema

按 `{symbol}_{date}` 键，例如 `"AAPL_2026-04-30"`：

```json
{
  "summary_cn": "中文公司简介，3-5 句，业务模式 / 客户结构 / 竞争格局 / 中国敞口。150-300 字。",
  "thesis_cn": "本季 (季度标识) 关键看点：\n1) 营收/EPS 共识 — $X.XB、EPS $X.XX\n2) 关键催化 1 —— ...\n3) 关键催化 2 —— ...\n4) 风险点 —— ...\n5) ...\n6) ...",
  "researched_at": "YYYY-MM-DD",
  "version": 1
}
```

写作要点：
- 中文为主，技术术语英文保留 (PCIe / HBM / CoWoS / ODM / EMS / OSAT 等)
- thesis 第一条永远是 "营收/EPS 共识"，不要瞎编投行评级或目标价
- 数字必须用 FMP `earnings_history.json` 的实数，绝不造数据
- 微盘股 (无 EPS 共识) 写"分析师覆盖少 + 关注业务进展"即可

## 5. KEY_STOCKS 卡片 schema（每只股票一个 dict）

```python
{
'sym': 'INTC',
'title': '24 年蛰伏后的世纪转身（+23.60%）',
'dp': 23.60, 'close': 82.55, 'cap': '$3,470 亿',
'vol': '$26.8B（5 倍 90 日均值）', 'range52w': '$18.51 – $82.85',
'fund': '基本面段：财报数据、业绩超预期、指引、capex 等。300-500 字。',
'sellside': [
  {'firm': 'Goldman Sachs', 'rating': '中性 → 买入', 'tp': '$70 → $98', 'view': '观点摘要'},
  # 5-6 家投行
],
'bull': ['看多论据 1', '看多论据 2', ...],   # 4-5 条
'bear': ['看空论据 1', ...],                  # 3-4 条
'catalysts': ['<b>5/30 Computex Taipei</b>: ...', ...],  # 3-4 个未来事件
'technical': '技术面段：突破点位、RSI、MACD、支撑/阻力。100-150 字。',
}
```

每天选 **当日涨跌幅最大 / 最具叙事价值的 6-8 只**，可以跨子行业。

### 5.1 卡片数量动态规则
- 默认 **6-8 张**
- 当日有 `|dp| > 30%` 的中盘以上异动股（`cap > $30 亿` = 3000 $M）→ **必加 1 张**
- 总卡片数硬上限 **10 张**（防止单日稿件失控）
- 候选挑选算法：FMP JSON 算 Top 25 by `|dp|` 和 Top 25 by `|dp| × cap`，两个榜单交集优先；小市值（<$30亿）仅在 `|dp| > 10%` + 有可验证催化时纳入

### 5.2 内容更新策略（按当日新闻浓度）
| 当日类型 | 判断 | 更新颗粒 |
|---|---|---|
| 强催化日 | 池内有财报 / 大型行业事件 / 大单 / 评级变动潮 / SOX ±2% 以上 | 完整重写 fund / sellside / bull / bear / catalysts / technical |
| 介于两者 | 大盘 ±0.5–2% 普通波动 | 更新 dp/close/cap + fund 第一段（点出当日驱动）+ technical |
| 平淡日 | 大盘 ±0.5% 内 + 无明显催化 | 只更新 dp/close/cap 数字 + technical，保留长期叙事框架 |

### 5.3 数据真实性硬规则
- `dp` / `close` / `cap` **必须从 FMP JSON 取实数**，不造数据、不四舍五入掩盖
- `cap` 单位是 $M，显示亿美元用 `cap / 100`（例：cap=4144 → "$4,144 亿"；cap=50620 → "$5.06 万亿"）
- 卖方评级（`sellside`）若 WebSearch 无法验证当日确实发生：
  - 要么 **省略整个 sellside 字段**
  - 要么写一条："暂无评级变动 / 当日卖方静默"
  - **绝对不要编造**目标价或评级动作

## 6. NEWS_TIERS 4 层 schema

```python
NEWS_TIERS = {
'tier1': {
  'name': 'Tier 1·宏观/大盘',
  'desc': 'Bloomberg / Reuters / WSJ / FT 等一线财经媒体',
  'items': [{'src': 'WSJ', 'title': '...', 'body': '正文 80-150 字', 'impact': '对硬件板块影响一句话'}, ...]
},
'tier2': {
  'name': 'Tier 2·半导体深度',
  'desc': 'SemiAnalysis / EETimes / TechInsights / IC Insights 行业垂媒',
  'items': [...]
},
'tier3': {
  'name': 'Tier 3·亚洲供应链',
  'desc': 'DigiTimes / TrendForce / Nikkei Asia / 日经新闻',
  'items': [...]
},
'tier4': {
  'name': 'Tier 4·公司公告/分析师评级',
  'desc': '8-K / 评级变动 / 大单 / 高管变动',
  'items': [...]
},
}
```

每层 3-5 条，挑对硬件板块**最有信息量**的新闻。

## 7. 池子定义（INDUSTRY_MAP, gen.py 第 414 行）

24 个子行业：
- **半导体核心 (10)**：AI加速 / CPU处理器 / Fabless设计 / 晶圆代工 / 存储器件 / 模拟电源 / 射频芯片 / 半导体设备 / 封测OSAT / 化合物光电
- **硬件系统 (6)**：AI服务器 / 网络设备 / 光通信 / 无线通信 / 消费电子 / PC与外设
- **元器件制造 (7)**：连接器元件 / EMS制造 / 测试仪器 / 安防识别 / 传感LiDAR / 工业IoT / 能源电池
- **分销渠道 (1)**：分销渠道

合计 **314 只**。`'NA'` 是 Fabless 子行业里的 placeholder（不是真 ticker），FMP 拉不到，gen.py 用 hash-fake 数据兜底。

## 8. 颜色约定（中国股市习惯，与西方相反）

- 🔴 **红色 = 上涨**
- 🟢 **绿色 = 下跌**

`gen.py` 第 ~660 行 `dp_color()` 函数已封装，**改 dp 数值时不要改色卡**。

## 9. 重要规则（避坑）

| ❌ 别这么做 | ✅ 应该这么做 |
|---|---|
| 写绝对路径 `/home/user/work/...` | 用 `os.path.join(REPO_DIR, ...)`（gen.py 第 6 行已定义 REPO_DIR） |
| 一次 Edit 改 >5KB | 拆分成多次小 Edit，避免 API stream timeout |
| 大块 HTML 直接拼字符串 | 数据放 Python 数据结构（dict / list），用 loop 渲染 |
| 任意 ticker 直接当 narrative 主角 | 必须当日涨跌幅 ≥ 显著（绝对值 > 5%）或有重大新闻 |
| 给代码加 emoji | 除非已有，不要新加。文档/对话可以 |
| 改 `dp_color()` 颜色 | 中国习惯红涨绿跌，不要"修正"成西方习惯 |
| `git push` 用 `--force` | **永远不要**。除非用户明确要求 |
| `--no-verify` 跳过 hooks | **永远不要** |
| 在 gen.py 里调 FMP | 沙箱出站 allowlist 拦截 financialmodelingprep.com，调不到。只能读 GitHub Actions 已落地的 JSON |

## 10. FMP API 详情

- **Key**：存在 GitHub Secrets `FMP_API_KEY`，也硬编码在 `gen.py` 第 9 行（**注意**：当前 calendar.html / earnings.html 都改成读本地 JSON 不再客户端调 FMP，但 gen.py 模板里的 KEY 常量保留以备未来需要）
- **端点**：必须用 `/stable/...`（v3 在 2025-08-31 deprecated 返回 403）
  - 批量 quote：`https://financialmodelingprep.com/stable/batch-quote?symbols=AAPL,NVDA&apikey=KEY`
  - 单 quote：`https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=KEY`
  - 业绩日历：`https://financialmodelingprep.com/stable/earnings-calendar?from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=KEY`（响应 schema：symbol / date / eps / epsEstimated / time / revenue / revenueEstimated；time 取值 bmo/amc/null）⚠️ **此端点会漏数据**（实测 2026-04-28 池内 14 家全漏），需要用下面的 per-symbol 端点兜底
  - 单股历史业绩：`https://financialmodelingprep.com/stable/earnings?symbol=AAPL&limit=120&apikey=KEY`（同上 schema 但 **time 字段总是 null**；`limit=120` ≈ 30 年季报）—— 这是 calendar 漏数据时的兜底，per-symbol 调用更全
  - 公司 profile：`https://financialmodelingprep.com/stable/profile-symbol?symbol=AAPL&apikey=KEY`（返回 companyName / description / industry / sector / country / website / image / exchange / ipoDate / ceo / fullTimeEmployees / marketCap）
- **频率限制**：付费 tier 已开通，免费版 250 次/天（兜底）
- **关键字段**：`symbol / price / changesPercentage / marketCap / dayHigh / dayLow / previousClose / volume / timestamp`

## 11. GitHub Actions 工作流

- 文件：`.github/workflows/daily.yml`
- Cron：`30 22 * * 1-5`（UTC 22:30 工作日，= 美东 18:30 EDT / 17:30 EST 收盘后）
- 步骤：`fetch_fmp.py`（行情）→ `fetch_earnings_history.py`（业绩历史增量；周日额外跑 refresh-recent + profiles）→ `fetch_earnings_history.py --profiles`（公司简介，仅周日 / 缺失 / 强制时跑）→ `gen.py`（重生成全部 HTML）→ commit & push
- 手动触发输入：
  - `review_date`：强制指定交易日 YYYY-MM-DD
  - `earnings_mode`：`delta`（默认）/ `refresh-recent`（重拉近 180 天纠错）/ `full`（**首次回填**，313 calls，仅手动触发）
  - `fetch_profiles`：勾选则强制刷新 `company_profiles.json`（313 calls，平时只在周日 / 文件缺失时自动跑）
- 自动 commit message 格式：`auto: FMP daily fetch {DATE} (hit {N}/313)`
- **PAT 权限注意**：从 CLI push 工作流文件需要 `workflow` scope，本地 PAT 不一定有 → 修改 `daily.yml` 时优先在 GitHub 网页编辑

## 11.4 Routine push 鉴权（OAuth 代理 — 当前生产方案）

**当前方案**：在 Claude Code on the Web 的 routine 配置里 **"Select a repository" → 选 `us-hardware-review`**。

绑定后 routine 启动时：
- 仓库**自动 clone** 到工作目录（约定 `/home/user/us-hardware-review`）
- git remote 已配置走 **OAuth 代理**，`git push origin main` 直接能用，**无需 PAT、无需任何 env var**
- push 受限于"当前工作分支"（即从 main 拉就只能 push 回 main，安全）

### 一次性接入步骤（已完成 ✅）
1. 在 GitHub 装 Claude GitHub App：https://github.com/apps/claude → Configure → 仅授权 `us-hardware-review` 一个仓库
2. 在 Claude Code on the Web routine 编辑页 → "Select a repository" → 选这个仓库 → Save

### 故障兜底：fine-grained PAT 备用方案

万一某天 OAuth 代理出问题（symptom：`git push` 报 403 / Authentication failed），临时切换到 PAT 路线：

1. 创建 fine-grained PAT（https://github.com/settings/personal-access-tokens/new）：
   - **Token name**：`us-hardware-review-routine-{YYYYMM}`
   - **Expiration**：90 天
   - **Repository access**：Only select repositories → `us-hardware-review`
   - **Permissions** → Repository → `Contents`: Read and write（其他全 No access）
2. 在 routine 提示词第一步加：`export GH_TOKEN=github_pat_xxx`
3. push 前：`git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/zjz506014992-blip/us-hardware-review.git"`
4. push 后：`git remote set-url origin "https://github.com/zjz506014992-blip/us-hardware-review.git"`（抹 token）
5. OAuth 修好后：revoke PAT，把上面三行从 routine 删掉

### 历史日志
- 2026-04-26 上线 OAuth 代理方案；初始测试 PAT (`claude-routine-push-temp` 经典 PAT 和 `us-hardware-review-routine-202604` fine-grained PAT) 全部 revoke 完毕

## 11.5 Claude Code on the Web Routine（云端定时任务）

用户在 Claude Code on the Web 配了一个**每日 routine**，跑在 Anthropic 云端，**不依赖用户开机**。

- **触发时间**：北京 7:00am（UTC 23:00），刻意晚于 GitHub Actions 22:30 UTC 完成
- **绑定仓库**：routine 配置里 "Select a repository" 选 `us-hardware-review`（OAuth 代理，无需 token）
- **工作目录**：routine 启动时仓库已自动 clone 到 `/home/user/us-hardware-review`，第一步直接 `cd` + `git pull`
- Routine 提示词（复制到 Claude Code on the Web 的 routine 配置里）：

```text
今天美股硬件板块收盘复盘。

【启动 — 按顺序做以下 4 件事，其他都按 CLAUDE.md】
1. cd /home/user/us-hardware-review && git pull origin main
2. 用 Read 工具完整读取 CLAUDE.md（一次读完，1300+ 行）
3. 【幂等检查】查最新 confirmed_*.json 对应日期 X，再查 git log 是否已有 "feat: X" 的 commit。
   - 若已有 → routine 已成功跑过，**直接退出**（避免重复 commit）
   - 若没有 → 继续第 4 步
4. 严格按 CLAUDE.md 第 4 节执行 8 步工作流，包含 commit + push

【失败重启策略 — 若 mid-session 被 API error 中断】
- routine 是幂等的：下次定时触发时，第 3 步会重新检查 commit 状态
  · 已 commit 过 → 退出
  · 没 commit / commit 不全 → 在已有进度上续做（git status 查 staged/modified files 决定从哪步续）
- 兜底 routine：在 Claude Code on the Web 多配一个 routine，触发时间 +1.5 小时（北京 8:30am），
  跑同一个提示词，靠幂等检查决定退出还是补跑

【遇到 API error 处理】
- 不要 panic。把错误本身（错误类型、上一步在做什么、文件大致改到哪）记到 CLAUDE.md 第 12 节"历史教训"末尾
- 然后退出 routine（不是修复后再继续）—— 让幂等检查 + 兜底 routine 来补救
- 这样错误经验积累，下次遇到能用 CLAUDE.md 的避坑表预防

【最高指令】
- 任何业务规则、流程、数据来源、输出格式、颜色约定、避坑、commit 信息格式 — **全部以 CLAUDE.md 为准**
- 本提示词只负责启动 + 幂等 + 错误记录策略，业务规则一概不重复（避免与 CLAUDE.md drift）
- 本提示词与 CLAUDE.md 冲突时，以 CLAUDE.md 为准
- 用户后续维护：只需修改 GitHub 上的 CLAUDE.md，不必动这个提示词

【发布地址】https://zjz506014992-blip.github.io/us-hardware-review/
```

如果发现 routine 跑出来质量有问题（漏选某只异动股、误填假评级、新闻不准），**直接更新这个 routine 提示词** + 同步更新 CLAUDE.md 第 4 节流程，让两边一致。

### 11.5.1 兜底 routine（防 API error 中断）

主 routine 北京 7:00am 跑；**配第二个兜底 routine 北京 8:30am 跑**，提示词完全相同。靠**幂等检查**避免重复工作：
- 主 routine 成功完成 → 8:30 兜底 routine 第 3 步发现 commit 已存在，**直接退出**（无成本）
- 主 routine 中途 API error → 8:30 兜底 routine 接着跑，最终页面在 9:00 前更新

如果 API error 频繁，可以再加第三个兜底（如 10:00am）。每次成功只需要一次跑通。

## 12. 历史教训（API timeout / 报错的根因）

> **怎么记**：每次 routine 遇到 API error 就在表格末尾加一行：日期 + 症状 + 根因 + 解决。
> 这张表是给未来 Claude 看的"避坑指南"，记得越多下次撞同样问题概率越低。

| 日期 | 症状 | 根因 | 解决 |
|---|---|---|---|
| 持续 | API stream idle timeout | 一次 Edit 太大（>10KB）或 Bash 输出太长 | 小批量、用数据结构而非 inline HTML |
| 持续 | `Edit string not found` | old_string 包含 typo 或不可见字符 | 用 grep 先确认文件实际内容 |
| 持续 | HTML 结构错乱 | 用 display:none hack 包裹旧块 | 直接删掉旧块，别藏 |
| 持续 | GitHub Pages 显示旧版 | CDN 缓存 | 等 1-2 分钟，或加 `?v=N` query param、或浏览器强刷 Cmd/Ctrl+Shift+R |
| 持续 | 工作流 push 被拒 | PAT 缺 `workflow` scope | 用 GitHub 网页编辑 yaml |
| 持续 | FMP 403 Forbidden | 用了 v3 端点 | 切到 `/stable/...` |
| 持续 | `Stocks: 314, ... Up/Down/Flat: 1/0/313` | FMP 字段名差异，dp 全 0 | `pick()` 函数已加 fallback，看 SAMPLE RESPONSE 日志确认字段名 |
| 2026-04-28 | routine 中断后页面"叙事是 4/24 / 数字是 4/27" | mid-session API error 让 routine 没 commit；GH Actions auto 只覆盖数字、不更新 narrative | (1) 增加幂等检查 + 兜底 routine（11.5.1）(2) 接 FMP 自动拉指数/ETF/风格因子，减少手动维护点 |
| 2026-04-28 | KEY_STOCKS 卡片 8 张连续 Edit 接近 30KB 总输出 | 单次 Edit 单卡 ~3KB 安全，但 8 张连续大 Edit 增加超时概率 | 中间穿插简短 Read/Bash 操作，避免连续 8 个大 Edit；或用 Write 一次性替换整段 list 反而更稳 |
| 2026-04-28 | 写新一天 narrative 时不小心把 24 号的 KEY_STOCKS 整段 dict 留着 | 复制粘贴脏数据；Edit 没匹配到旧 sym 块就漏改 | 改完后 `grep "'sym': '"` 数一下 sym 是否符合预期数量（默认 6-8 个，不应有当日不该有的票） |

## 13. 用户偏好

- **语言**：中文为主，技术术语英文 OK
- **风格**：直接、简洁、不啰嗦；用表格胜过长段落
- **态度**：敢说"这个想法不好"，提供替代方案；不要无条件附和
- **代码注释**：默认不写。除非"为什么这么做"非显而易见
- **commit 信息**：中文标题（`feat:` / `fix:` / `auto:` 前缀），简洁描述意图
- **重大动作前确认**：force push、删文件、改 CI、跨 PR 操作 → 先问

## 14. 当前未完成 / TODO（更新这里以告知未来 Claude）

- [x] GICS 11 ETF / VIX / DXY / 10Y / WTI 也接 FMP 自动拉（2026-04-28 完成；`fetch_fmp.py` 加 `MACRO_SYMBOLS` 字典 + `fetch_macros()` 函数；写 `confirmed_macros_{DATE}.json`；`gen.py` 加 `_load_macros_cache()` 自动覆盖 BROAD/SEMI/GICS/STYLE_FACTORS dicts。**首次生效**：下次 GitHub Actions 跑 `fetch_fmp.py` 后 macros 文件出现，gen.py 自动接管。指数符号 `^GSPC/^NDX/^DJI/^RUT/^VIX/^TNX/^SOX` + 商品 `CLUSD/DX-Y.NYB`，部分指数若 FMP 不支持会落到 missing list 但不阻塞）
- [x] 业绩日历端点从 v3 迁到 stable（2026-04-26 完成，calendar.html 切到 `/stable/earnings-calendar`）
- [x] 业绩历史可搜索表（2026-04-26 完成；`earnings.html` + `fetch_earnings_history.py` + `earnings_history.json`；首次需手动 `workflow_dispatch` → `earnings_mode=full` 触发回填，之后日增量）
- [x] calendar.html 改读本地 `earnings_history.json`，修复 calendar 端点漏数据问题（2026-04-26 完成；同时点击日期格弹出当天所有公司业绩 + `company_profiles.json` 公司简介）
- [x] 兜底 routine 设计 + 幂等检查（2026-04-28 完成；详见 11.5.1）
- [ ] 验证 FMP 是否支持所有 MACRO_SYMBOLS（首次跑 fetch_macros 后看 `missing` 列表，把不支持的 symbol 替换成 ETF proxy，比如 `^TNX` 不行就用 `IEF` 10Y 国债 ETF 代理）
- [ ] AI 自动生成新闻摘要（方式 B，把 Anthropic API 接进 GitHub Actions）

---

**最后**：这份文件是活的。你在干活时发现新约定、新坑、新偏好，**直接编辑这个文件并 commit**，让下一个会话受益。
