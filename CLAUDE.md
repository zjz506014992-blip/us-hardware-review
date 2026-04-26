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

【启动 — 只做这两件事，其他都按 CLAUDE.md】
1. cd /home/user/us-hardware-review && git pull origin main
2. 用 Read 工具完整读取 CLAUDE.md（一次读完，1300+ 行）

【然后严格按 CLAUDE.md 第 4 节执行 8 步工作流，包含 commit + push】

【最高指令】
- 任何业务规则、流程、数据来源、输出格式、颜色约定、避坑、commit 信息格式 — **全部以 CLAUDE.md 为准**
- 本提示词只负责启动，刻意不重复任何业务规则（避免与 CLAUDE.md drift）
- 本提示词与 CLAUDE.md 冲突时，以 CLAUDE.md 为准
- 用户后续维护：只需修改 GitHub 上的 CLAUDE.md，不必动这个提示词

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
