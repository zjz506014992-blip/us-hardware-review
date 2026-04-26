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
├── gen.py                       # 主生成器（~1300 行），生成所有 HTML
├── fetch_fmp.py                 # FMP 数据拉取，写 confirmed_{DATE}.json
├── calendar.html                # 业绩日历（客户端直连 FMP）
├── index.html                   # 历史存档目录
├── {DATE}.html                  # 当日复盘页（一天一份）
├── stocks-{DATE}.html           # 当日全部 314 只股票表
├── confirmed_{DATE}.json        # FMP 拉取的当日数据（GitHub Actions 自动产出）
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

4. **更新 gen.py 里的 4 块叙事数据**（**只动 dict，别动函数**）：

   | 块 | 行号附近 | 字段 | 数据源 |
   |---|---|---|---|
   | `BROAD_INDICES` | gen.py 第 11 行 | SPX/NDX/DJI/RUT/VIX/DXY/US10Y/WTI 收盘+涨跌 | WebSearch（FMP 没有指数实时） |
   | `SEMI_INDICES` | gen.py 第 23 行 | SOX/SOXX/SMH/XSD/PSI 收盘+涨跌 | WebSearch |
   | `GICS_INDICES` | gen.py 第 32 行 | XLK/XLC/XLY/XLF/XLI/XLB/XLRE/XLV/XLU/XLP/XLE 收盘+涨跌 | WebSearch |
   | `KEY_STOCKS` | gen.py 第 64 行起 | 8 张重点个股深度卡 | 从 FMP JSON 取 dp/close/cap，叙事自己写 |
   | `NEWS_TIERS` | gen.py 接近末尾 | Tier 1（宏观/大盘）/ Tier 2（半导体深度）/ Tier 3（亚洲供应链）/ Tier 4（公司公告/分析师评级） | WebSearch + 你的判断 |

5. **跑生成**：`python gen.py`

6. **检查输出**：
   ```bash
   ls -la {DATE}.html stocks-{DATE}.html
   git status --short
   ```

7. **提交 + 推送**：
   ```bash
   git add gen.py {DATE}.html stocks-{DATE}.html index.html _meta.json
   git commit -m "feat: {DATE} review (cap-w +X.XX%, key takeaway 一句话)"
   git push origin main
   ```

8. **告诉用户**：发布地址 + 关键变化（哪只大涨、哪只大跌、风格切换等）

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

- **Key**：存在 GitHub Secrets `FMP_API_KEY`，也硬编码在 `gen.py` 第 7 行（用于 `calendar.html` 客户端 fetch）
- **端点**：必须用 `/stable/...`（v3 在 2025-08-31 deprecated 返回 403）
  - 批量 quote：`https://financialmodelingprep.com/stable/batch-quote?symbols=AAPL,NVDA&apikey=KEY`
  - 单 quote：`https://financialmodelingprep.com/stable/quote?symbol=AAPL&apikey=KEY`
  - 业绩日历：`https://financialmodelingprep.com/api/v3/earning_calendar?from=YYYY-MM-DD&to=YYYY-MM-DD&apikey=KEY`（注意：日历 API 路径不同，待迁移到 stable）
- **频率限制**：免费版 250 次/天
- **关键字段**：`symbol / price / changesPercentage / marketCap / dayHigh / dayLow / previousClose / volume / timestamp`

## 11. GitHub Actions 工作流

- 文件：`.github/workflows/daily.yml`
- Cron：`30 22 * * 1-5`（UTC 22:30 工作日，= 美东 18:30 EDT / 17:30 EST 收盘后）
- 也支持 `workflow_dispatch` 手动触发，可传 `review_date` 强制覆盖日期
- 自动 commit message 格式：`auto: FMP daily fetch {DATE} (hit {N}/313)`
- **PAT 权限注意**：从 CLI push 工作流文件需要 `workflow` scope，本地 PAT 不一定有 → 修改 `daily.yml` 时优先在 GitHub 网页编辑

## 11.4 Routine push 鉴权（fine-grained PAT 方案，方案 1a）

Anthropic 云端 routine **访问不到 GitHub Secrets**，必须自带 token 才能 push。约定用 **fine-grained PAT**（不要用经典 PAT，泄露面太大）：

### 创建 PAT（一次性，每 90 天轮换）
1. 访问 https://github.com/settings/personal-access-tokens/new
2. 配置：
   - **Token name**：`us-hardware-review-routine-{YYYYMM}`（包含月份方便识别旧 token）
   - **Expiration**：90 天（不要选 No expiration）
   - **Repository access**：Only select repositories → 只选 `zjz506014992-blip/us-hardware-review`
   - **Permissions** → Repository permissions：
     - `Contents`: **Read and write**（必需，用于 push HTML/JSON）
     - `Metadata`: Read-only（自动包含，无需手动勾）
     - 其他全部 No access — 特别**不要**给 `Workflows` / `Actions` / `Secrets` 权限
3. 生成后立刻复制 `github_pat_xxx...`，**写进 routine 配置的环境变量**（见下面 11.5 节），不要落盘

### 轮换流程（每 90 天）
1. 提前 1 周创建新 token（按上面步骤）
2. 在 routine 配置里替换 `GH_TOKEN` 值
3. 跑 routine 一次验证 push 成功
4. 去 https://github.com/settings/personal-access-tokens 把旧 token Revoke
5. 在 CLAUDE.md 这一节末尾记一行轮换日志：`{YYYY-MM-DD} 轮换至 us-hardware-review-routine-{YYYYMM}`

### 泄露应急
- 立刻去 https://github.com/settings/personal-access-tokens Revoke
- 创建新 token，更新 routine 配置
- 检查仓库 Insights → Traffic 看是否有异常 clone

### 轮换日志
- 2026-04-26 初始 token 由 routine 临时使用，**已 Revoke**；正式 token 待用户按上述步骤创建

## 11.5 Claude Code on the Web Routine（云端定时任务）

用户在 Claude Code on the Web 配了一个**每日 routine**，跑在 Anthropic 云端，**不依赖用户开机**。

- **触发时间**：北京 7:00am（UTC 23:00），刻意晚于 GitHub Actions 22:30 UTC 完成
- **第一步永远是 `git pull origin main`**（routine 是新会话，不 pull 会用旧数据）
- **环境变量**：在 Claude Code on the Web routine 配置里加 `GH_TOKEN=github_pat_xxx`（fine-grained PAT，见 11.4 节）
- Routine 提示词（复制到 Claude Code on the Web 的 routine 配置里）：

```text
今天美股硬件板块收盘复盘。

【第一步必做：拉仓库 + 注入 token】
1. 如果 /home/user 没有仓库：
   git clone https://github.com/zjz506014992-blip/us-hardware-review.git /home/user/us-hardware-review
   cd /home/user/us-hardware-review
2. 如果已有：
   cd /home/user/us-hardware-review && git pull origin main
3. 把 push token 注入 remote URL（GH_TOKEN 已由 routine 环境变量提供）：
   git remote set-url origin "https://x-access-token:${GH_TOKEN}@github.com/zjz506014992-blip/us-hardware-review.git"

【按 CLAUDE.md 第 4 节 8 步流程执行】
1. ls -t confirmed_*.json | head -1 → 读最新 JSON（cap 单位是 $M，不是亿）
2. 读 _meta.json 看当日 stats（up/down/flat/cap_w/arith）
3. 用 Python 算出 Top 25 by |dp| 和 Top 25 by |dp|×cap，确定 6-9 只重点解读候选
4. 用 WebSearch 验证当日：
   - 大盘指数（SPX/NDX/DJI/RUT/VIX/DXY/US10Y/WTI）
   - 半导体 ETF（SOX/SOXX/SMH/XSD/PSI）
   - GICS 11 SPDR ETF
   - 当日 Top 5 异动股的真实催化（财报、分析师评级、产品发布）
5. 编辑 gen.py 的 5 个数据 dict（**只动 dict，别动函数体**）：
   - BROAD_INDICES (line ~13)
   - SEMI_INDICES (line ~24)
   - GICS_INDICES (line ~33)
   - KEY_STOCKS (line ~65) — dp/close/cap 必须从 FMP cache 读实数
   - NEWS_TIERS (line ~362) — 4 层 Tier 各 3-5 条
6. python gen.py → 验证："Stocks: 314, Up/Down/Flat: X/Y/Z, cap-w: N.NN%"
7. 提交 + 推送（沙箱 code-sign 服务通常返回 missing source，禁用签名）：
   git add gen.py *.html _meta.json
   git -c commit.gpgsign=false commit -m "feat: {DATE} review (cap-w +X.XX%, 一句话核心叙事)"
   git push origin main

【最后必做：抹掉 token】
git remote set-url origin "https://github.com/zjz506014992-blip/us-hardware-review.git"
（防止 token 落到 .git/config）

【硬规则】
- 颜色：🔴 红涨绿跌（中国习惯，dp_color() 已封装，不要改）
- KEY_STOCKS 必须从 FMP JSON 取 dp/close/cap 实数；卖方评级若 WebSearch 无法验证当日存在，省略 sellside 或写"暂无评级变动"
- 非异动 + 新闻平淡的日子，KEY_STOCKS 可只更新数字、保留长期叙事框架
- KEY_STOCKS 数量动态：默认 6-8 张；当日有 |dp|>30% 的中盘以上异动股（cap > $30亿）必加 1 张
- commit 前 git status --short 确认无意外文件（confirmed_*.json 已由 Actions 提交，不要重复 stage）
- commit 信息中文标题（feat:/fix:/auto: 前缀），简洁说明意图

【发布地址】https://zjz506014992-blip.github.io/us-hardware-review/
```

如果发现 routine 跑出来质量有问题（漏选某只异动股、误填假评级、新闻不准），**直接更新这个 routine 提示词** + 同步更新 CLAUDE.md 第 4 节流程，让两边一致。

## 12. 历史教训（API timeout / 报错的根因）

| 症状 | 根因 | 解决 |
|---|---|---|
| API stream idle timeout | 一次 Edit 太大（>10KB）或 Bash 输出太长 | 小批量、用数据结构而非 inline HTML |
| `Edit string not found` | old_string 包含 typo 或不可见字符 | 用 grep 先确认文件实际内容 |
| HTML 结构错乱 | 用 display:none hack 包裹旧块 | 直接删掉旧块，别藏 |
| GitHub Pages 显示旧版 | CDN 缓存 | 等 1-2 分钟，或加 `?v=N` query param |
| 工作流 push 被拒 | PAT 缺 `workflow` scope | 用 GitHub 网页编辑 yaml |
| FMP 403 Forbidden | 用了 v3 端点 | 切到 `/stable/...` |
| `Stocks: 314, ... Up/Down/Flat: 1/0/313` | FMP 字段名差异，dp 全 0 | `pick()` 函数已加 fallback，看 SAMPLE RESPONSE 日志确认字段名 |

## 13. 用户偏好

- **语言**：中文为主，技术术语英文 OK
- **风格**：直接、简洁、不啰嗦；用表格胜过长段落
- **态度**：敢说"这个想法不好"，提供替代方案；不要无条件附和
- **代码注释**：默认不写。除非"为什么这么做"非显而易见
- **commit 信息**：中文标题（`feat:` / `fix:` / `auto:` 前缀），简洁描述意图
- **重大动作前确认**：force push、删文件、改 CI、跨 PR 操作 → 先问

## 14. 当前未完成 / TODO（更新这里以告知未来 Claude）

- [ ] GICS 11 ETF / VIX / DXY / 10Y / WTI 也接 FMP 自动拉
- [ ] 业绩日历端点从 v3 迁到 stable
- [ ] AI 自动生成新闻摘要（方式 B，把 Anthropic API 接进 GitHub Actions）
- [ ] 业绩日历加 BMO/AMC tooltip 显示历史 EPS surprise

---

**最后**：这份文件是活的。你在干活时发现新约定、新坑、新偏好，**直接编辑这个文件并 commit**，让下一个会话受益。
