#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 美股硬件板块复盘 HTML（含 ECharts treemap + Chart.js 图表）"""
import json, hashlib, os

REPO_DIR = os.path.dirname(os.path.abspath(__file__))

DATE = "2026-04-27"
# FMP_API_KEY: 从 GitHub Secrets / shell env 读, fetch_*.py 用 os.environ.get('FMP_API_KEY').
# 这里不再硬编码 (calendar.html / earnings.html 已改为读本地 JSON, 客户端不再需要 key).

# 当日宏观/指数数据（每日手动更新或 FMP 自动拉取）
# 格式: [(代码, 名称, 收盘, 涨跌%, 备注)]
BROAD_INDICES = [
    ('SPX',  'S&P 500',     '7,173.90', 0.10,  '微幅再创新高'),
    ('NDX',  'Nasdaq 100',  '24,887.00', 0.20, '科技股勉力守住'),
    ('DJI',  'Dow Jones',   '49,168.00', -0.13, '防御股拖累'),
    ('RUT',  'Russell 2000','2,408.00',  -0.45, '小盘明显回调'),
    ('VIX',  'VIX',         '18.41',    -1.60, '波动率维持偏高'),
    ('DXY',  'US Dollar',   '103.10',   -0.15, '美元小幅走弱'),
    ('US10Y','10Y 收益率',   '4.32%',     0.0,  'bp，利率持平'),
    ('WTI',  'WTI 原油',    '$73.10',    1.00, '伊朗局势再起波澜'),
]

SEMI_INDICES = [
    ('SOX',  'PHLX 半导体',     '~10,500', -0.15, '18 连阳后单日微跌，结束趋势'),
    ('SOXX', 'iShares 半导体',  '$254.40', -0.10, 'NVDA 大权重撑住'),
    ('SMH',  'VanEck 半导体',   '$505.50', -0.15, 'NVDA 大权重稀释跌幅'),
    ('XSD',  'SPDR 半导体（小盘等权重）', '$408.00', -2.85, '中小盘获利回吐显著'),
    ('PSI',  'Invesco 动态半导体','$210.20', -2.45, '动量/Fabless 集体回调'),
]

# GICS 11 一级行业（用 SPDR Sector ETF 代理）
GICS_INDICES = [
    ('XLK',  '信息科技 Tech',         '$246.10', 0.20,  'NVDA 独自撑住'),
    ('XLC',  '通信服务 Comm Svc',     '$118.50', 0.10,  '财报周观望'),
    ('XLY',  '可选消费 Cons Disc',    '$225.50', -0.20, 'TSLA 拖累'),
    ('XLF',  '金融 Financials',       '$54.10',  -0.35, '银行小幅回调'),
    ('XLI',  '工业 Industrials',     '$148.40', 0.15,  '国防订单稳定'),
    ('XLB',  '材料 Materials',       '$92.50',  0.45,  '油价上行'),
    ('XLRE', '房地产 Real Estate',    '$42.60',  -0.45, '利率走稳压制'),
    ('XLV',  '医疗 Health Care',     '$153.20', 0.70,  '防御资金回流'),
    ('XLU',  '公用事业 Utilities',    '$79.50',  0.75,  'Oklo + 核电主题受益'),
    ('XLP',  '必选消费 Cons Staples', '$83.10',  0.75,  '防御资金抬升'),
    ('XLE',  '能源 Energy',          '$93.40',  0.85,  'WTI 回升 + 中东风险溢价'),
]

# 风格因子 ETF（5 因子 + 等权基准）—— 看今日哪个因子领跑、市场是普涨还是窄涨
# 格式同 BROAD_INDICES: (代码, 名称, 收盘, 涨跌%, 备注)
STYLE_FACTORS = [
    ('IWF',  'Russell 1000 Growth',     '$430.80', 0.15,  '成长因子 — 大盘 NVDA 单边撑住'),
    ('IWD',  'Russell 1000 Value',      '$192.40', 0.15,  '价值因子 — 防御股回流'),
    ('MTUM', 'iShares Momentum Factor', '$219.10', -0.65, '动量因子 — 半导体动量股回吐'),
    ('SPLV', 'S&P 500 Low Volatility',  '$73.30',  0.70,  '低波因子 — 防御资金抬升'),
    ('QUAL', 'iShares Quality Factor',  '$160.40', 0.00,  '质量因子 — 持平'),
    ('RSP',  'S&P 500 Equal Weight',    '$174.80', -0.25, '等权基准 — 跑输 SPX，普涨度差'),
]

# 市场结构与风格因子叙事（每日 routine 维护 narrative，4 个比值由 gen.py 自动算）
# narrative: 综合解读 100-200 字，连接"普涨/窄涨"+"科技独强/全跟"+"半导体相对科技强弱"
#            +"今日哪个风格因子领跑"，给出一句宏观判断
MARKET_STRUCTURE = {
    'narrative': '<b>市场结构</b>：当日 RSP 等权 -0.25% vs SPX +0.10%，比值为负 → <b>极端窄幅领涨</b>，仅 NVDA / MU / SNDK 等少数权重股拉指数，等权基准实际下跌；NDX +0.20% / SPX +0.10% = 2.0x，<b>科技勉强领跑</b>但量级很小；SOX 微跌约 -0.15%（按 8% capped 估算），结束 18 连阳趋势但跌幅有限——NVDA / MU / INTC 三大权重撑住板块、ARM / AVGO / AMD / 半导体设备链回调；硬件池 cap-w +0.32% 但 arith -2.02%、breadth 78 涨 / 228 跌，<b>极度分化</b>，反映"权重存储/HBM 龙头被买、其余被砍"的旋转结构。<br><br><b>风格因子</b>：动量因子 (MTUM) -0.65% 单日转弱，前期领跑的半导体动量股（ARM / CRDO / ALAB）集体获利回吐；防御因子（SPLV +0.70% / 低波）+ 价值（IWD +0.15%）+ 必选消费（XLP +0.75%）联袂走强，<b>Risk-Off / 防御抬升</b>组合明显；成长（IWF +0.15%）勉强收正全靠 NVDA 单股贡献。质量因子 QUAL 持平、Growth ≈ Value，没有清晰的因子主导。<br><br><b>综合判断</b>：典型"<b>大型财报周开始前的 de-risk 日</b>"——MSFT/GOOGL/META 周三盘后，AAPL/AMZN 周四盘后，资金从 AI 周边动量品种切回最确定性主轴（NVDA 第二增长曲线 + Memory super cycle SNDK/MU），并提前向防御板块抬升。这种"窄幅 + 动量回吐 + 防御抬升"组合历史上类似 2024 财报周前夜，本周三晚 META/MSFT/GOOGL 业绩与指引（特别是 AI capex 数字）将决定动量行情能否延续，否则 SOX 18 连阳的趋势线可能被破。重点关注 MTUM 与 SOX 的相对强弱拐点。',
}

# 行业大会日历（常量，每年初维护一次）
INDUSTRY_EVENTS = [
    ('2026-01-06', '2026-01-09', 'CES 2026 拉斯维加斯', '消费电子大展，AI PC/Robot/汽车'),
    ('2026-02-15', '2026-02-19', 'ISSCC 2026 旧金山', '芯片设计学术顶会'),
    ('2026-03-02', '2026-03-05', 'MWC Barcelona', '5G/手机芯片/无线通信'),
    ('2026-03-17', '2026-03-21', 'NVIDIA GTC 2026', 'Rubin/Blackwell Ultra 发布'),
    ('2026-05-13', '2026-05-15', 'Google I/O 2026', 'TPU/Gemini/Android'),
    ('2026-06-09', '2026-06-13', 'Apple WWDC 2026', 'M5 Mac、iOS 20、AI 战略'),
    ('2026-07-08', '2026-07-10', 'SemiCon West 旧金山', '设备厂商年度展'),
    ('2026-08-24', '2026-08-26', 'Hot Chips 2026', 'CPU/GPU 架构发布'),
    ('2026-09-09', '2026-09-09', 'Apple iPhone 18 发布会', 'A20 芯片'),
    ('2026-09-04', '2026-09-09', 'IFA Berlin', '消费电子'),
    ('2026-10-13', '2026-10-15', 'NVIDIA GTC DC 华盛顿', 'AI 数据中心专场'),
    ('2026-11-15', '2026-11-20', 'SC26 Supercomputing', 'HPC/AI 计算'),
]

# 重点个股深度解读（每日维护，每只股票一个 dict）
# 字段：sym/title/dp/close/cap/fund/sellside/bull/bear/catalysts/technical
KEY_STOCKS = [
{
'sym': 'NVDA',
'title': '$5T 王座续命：Oklo SMR PPA 锁定长期电力 + 财报周窄幅领涨核心（+4.00%）',
'dp': 4.00, 'close': 216.61, 'cap': '$5.26 万亿',
'vol': '$40.0B（约 1.8 倍 90 日均值）', 'range52w': '$96.30 – $216.83',
'fund': '当日单日再创历史新高 $216.83，市值站稳 $5.26 万亿。两大催化：(1) 与 Oklo 公司签订核电采购协议（PPA）— Oklo 将于 2028 年起向 NVDA 数据中心提供 12 GW 小型模块化反应堆（SMR）电力，<b>这是 AI 数据中心电力瓶颈的首个长期方案</b>，叠加白宫 4 月签署的国家电网 AI 优先令；(2) 5/28 盘后 Q1 FY26 财报临近，市场预期营收 $48.5B（YoY +60%）、EPS $0.95（YoY +75%），其中数据中心 $42B（YoY +73%）。Blackwell Ultra（B300）已全面 ramp，Q1 出货 35 万颗（GB300 服务器），毛利率维持 76%。Rubin（R100）2026Q4 流片，性能较 Blackwell Ultra 提升 2.5x。Networking 业务（Spectrum-X 以太网）单季营收突破 $5B，超大规模数据中心渗透率达 40%。当日"窄幅领涨"格局下，NVDA 是少数几只权重股 alone 撑住 cap-w 指数的关键力量。',
'sellside': [
  {'firm': 'Bank of America', 'rating': '买入', 'tp': '$245', 'view': 'Oklo PPA 阶段性解决电力瓶颈，最大尾部风险解除'},
  {'firm': 'Wedbush', 'rating': '增持', 'tp': '$260', 'view': 'Rubin 路线图 2027 上市无悬念，AI 算力周期延续至 2028'},
  {'firm': 'Cantor', 'rating': '增持', 'tp': '$275', 'view': 'Networking 业务被严重低估，2027 年单季可破 $10B'},
  {'firm': 'Goldman Sachs', 'rating': '买入', 'tp': '$240', 'view': 'CY26 EPS 共识从 $4.20 上修至 $4.85'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$245', 'view': 'Q2 指引大概率超预期，B300+R100 双轨产能爬坡'},
  {'firm': 'Bernstein', 'rating': '增持', 'tp': '$250', 'view': '机器人（Isaac）+Drive 自动驾驶贡献第二增长曲线'},
],
'bull': [
  'Oklo SMR PPA 锁定 12GW 长期电力，AI 数据中心最大尾部风险阶段性解除',
  'Rubin (R100) 2027Q1 出货性能 +2.5x Blackwell Ultra，技术代差拉开',
  'Networking（Spectrum-X 以太网）渗透至超大规模厂商，单季 $5B+ 高毛利',
  'CY26 EPS 持续上修，PEG <1.0（vs 半导体板块 1.3-1.5）',
  '财报周（5/28）即将催化，市场对数据中心 Q2 指引 >$52B 抱有强预期',
],
'bear': [
  'Blackwell Ultra 毛利率 76% 较 H100 微降，反映 ASIC（AVGO/MRVL）压力',
  '$5.26T 市值已远超 AAPL/MSFT，机构持仓集中度风险显著',
  '中国市场（H20）受出口管制持续不确定，Q2 起或失去 $4-5B 季度营收',
  'Meta/Google 等 ASIC 自研持续推进，2027 年起或减少 GPU 采购 15-20%',
  'PE 38x（FY27）任何业绩 miss 触发 -10% 以上回调',
],
'catalysts': [
  '<b>5/13 Google I/O</b>：TPU 第七代（Trillium）vs B200 性能对比',
  '<b>5/28 Q1 FY26 财报（盘后）</b>：核心看 DCAI 营收 + Q2 指引（市场预期 $52B）',
  '<b>6/9 Apple WWDC</b>：是否启动 NVDA 与 Apple Vision Pro/AI 集成',
  '<b>10 月 GTC DC 华盛顿</b>：Rubin 详细规格 + 主权 AI 战略',
],
'technical': '突破 $215 阻力创历史新高 $216.83，进入"价格发现"模式。RSI 72（接近超买但未极端），20 日 / 50 日均线呈多头排列。短期支撑 $210（5 日均线）/ $202（20 日均线）；阻力位 $220（前高 +2σ）/ $230（机构目标价中枢）。期权 IV 38%（财报临近升至 45%+），跨夜波动预期 ±5.5%。',
},
{
'sym': 'MU',
'title': 'HBM/AI 存储 super cycle 再加速：Arete $852 + Melius Buy 双重加持（+5.60%）',
'dp': 5.60, 'close': 524.56, 'cap': '$5,916 亿',
'vol': '$20.0B（约 2.5 倍 90 日均值）', 'range52w': '$76.85 – $531.20',
'fund': '当日 MU 盘中创新高 $531，最终收 $524.56 +5.60%，CY 累涨从 $341 起步突破至 $524，<b>过去 4 周 +54%</b>。两大催化：(1) Arete Research 将 PT 从 $562 上调至 <b>$852</b>（Buy），分析师强调"HBM 全年产能已被长协锁定，2027 还在排队"；(2) Melius Research 的 Ben Reitzes 上调至 Buy 评级，认为"未来 12 个月还有 +41% 上行空间"。基本面：HBM3E 12-stack 出货占 NVDA Blackwell Ultra 的 ~30% 份额（vs SK Hynix ~55%），HBM4 已锁定 NVDA Rubin 平台首批认证。NAND 现货价 Q1 累涨 35%、企业级 SSD ASP 涨 42%，DRAM 现货价同步走强。当日存储板块 cap-w +4.62% 大幅领涨大盘，MU + SNDK + STX 是 24 个子行业里唯一普涨的板块。',
'sellside': [
  {'firm': 'Arete Research', 'rating': '买入', 'tp': '$562 → $852', 'view': 'HBM 全年产能锁定 + 2027 排队，估值锚要重定义'},
  {'firm': 'Melius Research', 'rating': '中性 → 买入', 'tp': '~$700', 'view': '12 个月仍有 +41% 上行空间'},
  {'firm': 'Mizuho', 'rating': '买入', 'tp': '$650', 'view': 'HBM4 良率追上 SK Hynix 是 2026H2 关键事件'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$620', 'view': 'NAND/DRAM 双周期共振至 2027Q2'},
  {'firm': 'Wells Fargo', 'rating': '增持', 'tp': '$600', 'view': '高毛利产品组合（HBM+企业级 SSD）占比突破 50%'},
],
'bull': [
  'HBM 全年产能已被 NVDA / AMD / Google TPU 长协锁定，单价持续上行',
  'NAND 现货价 Q1 +35%、企业级 SSD ASP +42%，毛利率扩张可持续',
  'HBM4 已锁定 NVDA Rubin 首批认证，份额从 ~30% 向 ~40% 修复',
  '存储板块当日 cap-w +4.62% 普涨，资金集中流入 SNDK/MU/STX 三大件',
  'CY26 EPS 共识持续上修，估值仍处历史区间下半部',
],
'bear': [
  '存储周期高度顺周期，2027H2 起需求或快速回落',
  'SK Hynix HBM4 12-stack 良率 80% 仍领先 MU 的 55%，份额恢复需要时间',
  '中国 H20 出口管制可能波及 HBM 配套销售',
  '当前股价已透支 2026 全年盈利预期，财报指引若不上调即触发回调',
  '与 SK Hynix 价格战风险（HBM4 价格未稳定）',
],
'catalysts': [
  '<b>6 月底 Q3 FY26 财报</b>：HBM 收入 + 毛利率 + Q4 指引',
  '<b>5/28 NVDA 财报</b>：DCAI 指引会决定 MU HBM 出货预期',
  '<b>2026Q3 NAND/DRAM 现货价</b>：是否突破 2018 年高点',
  '<b>2026Q4 HBM4 良率验证</b>：是否追上 SK Hynix',
],
'technical': '突破 $500 整数关 + 历史新高，RSI 78（超买但未极端），20 日 / 50 日均线多头排列且斜率陡峭。短期支撑 $500（心理位）/ $480（5 日均线）；阻力位 $560（Arete 中期目标）/ $700（Melius 12 月目标）。期权 IV 52%（财报前升至 58%+），过去 4 周 +54% 后短线整理需求高。',
},
{
'sym': 'SNDK',
'title': '历史新高 $1,070：Cantor $1,400 + Morgan Stanley $1,100 双 PT 大幅上修（+8.11%）',
'dp': 8.11, 'close': 1070.20, 'cap': '$1,580 亿',
'vol': '$13.5B（约 2.0 倍 90 日均值）', 'range52w': '$252.10 – $1,082.50',
'fund': 'SanDisk 当日单日 +8.11% 创历史新高，盘中曾突破 $1,082。两大催化叠加：(1) <b>Morgan Stanley 将 PT 从 $690 大幅上调至 $1,100（增持）</b>；(2) <b>Cantor Fitzgerald 将 PT 从 $1,000 上调至 $1,400（增持）</b>，两家均强调 AI 数据中心 SSD 需求"指数级放大"。<b>(3) 4/20 正式纳入 Nasdaq-100 指数</b>（替代 ATLASSIAN），被动基金被动买入持续放量。基本面：CY YTD +295%、自 IPO（2024-10）+485%。Q1 FY26 营收 $2.8B（YoY +135%），数据中心 SSD 占比从 2024 年 28% 升至 50%。BiCS9（218 层）QLC 已在 Meta/Microsoft 大规模出货。NAND 现货价 Q1 +35%、企业级 SSD ASP +42% 是周期红利。',
'sellside': [
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$690 → $1,100', 'view': 'AI SSD 需求指数级放大，BiCS9 QLC 渗透加速'},
  {'firm': 'Cantor Fitzgerald', 'rating': '增持', 'tp': '$1,000 → $1,400', 'view': 'NAND 周期可持续到 2027Q2，估值锚切换'},
  {'firm': 'Mizuho', 'rating': '买入', 'tp': '$1,200', 'view': 'AI 数据中心 SSD 需求 2027 年仍超预期'},
  {'firm': 'Wells Fargo', 'rating': '增持', 'tp': '$1,150', 'view': 'BiCS9 QLC 在 Meta/Microsoft 渗透加速'},
  {'firm': 'JPMorgan', 'rating': '中性', 'tp': '$950', 'view': 'NAND 周期高峰已现，2027 年需求或回落'},
],
'bull': [
  'AI 数据中心 NAND 需求 YoY +180%，BiCS9 QLC 在 Meta/Microsoft 渗透率突破 50%',
  '三星 / SK Hynix / Kioxia 三巨头供给约束，NAND ASP 持续上涨 + 毛利率扩张',
  '4/20 纳入 Nasdaq-100 指数后被动基金持续买入，资金面集中流入',
  'BiCS10（300+ 层）2027 上市，技术代差 1-2 年',
  '当前 PE 18x（FY27），考虑高增长率仍偏低',
],
'bear': [
  'NAND 周期高度顺周期，2027H2 起需求或快速回落',
  'YMTC 在中国市场持续放量（QLC 192 层），低端市场价格压力',
  'BiCS9 良率仍未稳定（Q1 80% vs 目标 85%），制约毛利率上行',
  'YTD +295% 后估值修复空间有限，技术回调风险显著',
  '从 WDC 拆分时间短（<18 月），独立运营经验仍在积累期',
],
'catalysts': [
  '<b>5 月底 Q2 FY26 财报</b>：NAND ASP 走势 + Q3 指引方向',
  '<b>2026Q3 NAND 现货价格</b>：是否突破 2018 年高点（$5.5/GB）',
  '<b>2026Q4 BiCS10 流片</b>：技术领先验证',
  '<b>2027 NAND 下行周期开启时点</b>：是否如预期延后至 2027H2',
],
'technical': '突破 $1,000 心理位 + $1,070 历史新高，盘中 $1,082 创盘中高。RSI 86（极端超买），但成交量持续放大、价格突破伴随被动资金流入。短期支撑 $1,000（心理位 + 缺口下沿）/ $940（5 日均线）；阻力位 $1,150（MS 中期目标）/ $1,400（Cantor 中期目标）。期权 IV 62%（vs 平均 45%），跨夜波动巨大。',
},
{
'sym': 'INTC',
'title': '周五财报余温：单日 +2.97% 守稳 26 年高位（+2.97%）',
'dp': 2.97, 'close': 84.99, 'cap': '$4,267 亿',
'vol': '$15.0B（约 2.5 倍 90 日均值）', 'range52w': '$18.51 – $86.20',
'fund': '周五（4/24）发布的 Q1 2026 财报余温延续：非 GAAP EPS $0.29（共识 $0.01，超 29 倍）、营收 $13.58B（YoY +7%、QoQ +12%）、Q2 指引 $13.8–14.8B 三杀超预期。当日 +23.60% 后周一 +2.97% 续涨，<b>突破 2000 年互联网泡沫顶部 $75</b> 后 26 年来首次站稳 $80 之上。买盘核心来自：(1) 大型机构资金持续回流，机构持仓从 52% 历史低位向上修复；(2) 期权回补（Friday +23% 后空头被强迫平仓）；(3) ARM Friday 同涨 +14.8% 周一回吐 -8.06%，资金部分轮动至 INTC 这类"基本面已兑现"标的。基本面：DCAI 数据中心 + AI 业务营收 $5.1B（+22% YoY）首次贡献正向 AI 加速毛利；Foundry 业务亏损收窄至 $1.1B；Intel 18A 工艺良率 52%。2026 全年 capex 上调至 $9.1B（前 $8.0B），WFE 资本开支翻倍直接外溢至 AMAT/LRCX/KLAC。',
'sellside': [
  {'firm': 'Goldman Sachs', 'rating': '中性 → 买入', 'tp': '$70 → $98', 'view': 'AI CPU 推理需求被低估，DCAI 持续超预期'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$75 → $105', 'view': '18A 工艺执行远超预期，Foundry 2027 年扭亏可期'},
  {'firm': 'BofA', 'rating': '买入', 'tp': '$85 → $110', 'view': 'Lip-Bu Tan 改革终见成效'},
  {'firm': 'JPMorgan', 'rating': '中性', 'tp': '$60 → $80', 'view': '认可短期反转，但需 2-3 个季度持续验证'},
  {'firm': 'Bernstein', 'rating': '减持 → 中性', 'tp': '$45 → $75', 'view': '空头逻辑被击穿，仍质疑 AGI 时代 x86 长期竞争力'},
],
'bull': [
  '边缘 AI 推理需求复苏，CPU 重新成为 AI workload 第一入口',
  '18A 工艺如期量产，AAPL/QCOM/MSFT 均已下首款 18A tape-out',
  '2026 capex $9.1B 直接外溢至 AMAT/LRCX/KLAC/ASML，板块共振',
  'Foundry 2027 年现金流转正预期被强化，估值有 30% 上修空间',
  '机构持仓从历史低位 52% 回升至 58%，空头回补空间巨大',
],
'bear': [
  '当前 PE 28x 已远超 5 年均值 15x，估值过快兑现远期预期',
  'AVGO/MRVL ASIC 仍在持续抢食 AI 加速份额',
  'CCG 业务靠 Lunar Lake 单代撑住，Panther Lake（2026H2）不及预期则承压',
  '股价 +27% 累计涨幅后短期回调风险显著',
],
'catalysts': [
  '<b>5/30 Computex Taipei</b>：Panther Lake 详细规格披露，18A 良率最新数据',
  '<b>Q2 2026 财报（7 月底）</b>：验证 DCAI 是否持续超预期',
  '<b>Foundry Day（9 月）</b>：18A/14A 客户名单公布，潜在大单（NVDA / AAPL）',
  '<b>2026 投资者日</b>：CEO 三年战略 update，Foundry 拆分悬念',
],
'technical': '突破 2000 年互联网泡沫顶部 $75，进入 26 年新高的"价格发现"区间。RSI 78（接近极端超买），MACD 顶部金叉。短期支撑 $80（前期突破点）/ $76（5 日均线）；阻力位 $90 心理位 / $98（GS 中期目标）。量能维持在 5x 90 日均量，机构资金持续大幅入场。',
},
{
'sym': 'ARM',
'title': '周五 +14.8% 后获利回吐，CPU 动量股集体修正（-8.06%）',
'dp': -8.06, 'close': 215.88, 'cap': '$2,293 亿',
'vol': '$3.0B（约 1.5 倍 90 日均值）', 'range52w': '$92.18 – $235.40',
'fund': '当日 ARM 单日 -8.06% 回调，<b>纯获利盘抛压</b>，无任何公司层面负面消息。背景：周五（4/24）ARM 受 INTC 财报外溢 + 自身 AGI CPU "Neoverse N3 Ultra" 战略升级 +14.8%，3 周内从 $137 飙至 $235（累计 +71%），属于"动量股 + 半导体周期股"的极致组合。周一资金从动量类品种切回最确定性主轴（NVDA/SNDK/MU），ARM 与 CRDO（-7.45%）/ ALAB（-7.61%）/ MXL（-14.37%）等"AI 周边动量股"集体被砍。基本面未变：v9 架构在数据中心 royalty rate 提升 3x，AAPL/QCOM/Meta/Google/Microsoft/AWS 六大客户全 ARM-based。<b>5/6 Q4 FY26 财报盘后发布是最关键 catalyst</b>，市场预期 royalty 营收 $700M（YoY +28%），若 v9 占比突破 30% 则继续支撑估值；若不及预期则回调延续。',
'sellside': [
  {'firm': 'Citi', 'rating': '买入', 'tp': '$260', 'view': '估值锚切换至 EV/EBITDA，参考 NVDA 路径'},
  {'firm': 'Guggenheim', 'rating': '买入', 'tp': '$270', 'view': 'AGI CPU 是 v9 之后最大的 ASP 跃升驱动'},
  {'firm': 'Evercore ISI', 'rating': '跑赢大盘', 'tp': '$265', 'view': '2031 营收目标隐含 35% CAGR'},
  {'firm': 'Mizuho', 'rating': '买入', 'tp': '$240', 'view': '生态护城河进一步巩固'},
  {'firm': 'Susquehanna', 'rating': '中性 → 买入', 'tp': '$245', 'view': 'RISC-V 替代论被打破'},
],
'bull': [
  '六大超大规模客户全 ARM-based，生态网络效应不可逆',
  'v9 架构数据中心 royalty rate 提升 3x，结构性提价 2026-2028 持续释放',
  '边缘 AI 推理需求爆发，AI PC/手机 ARM IP value 提升 2-3x',
  '日本软银仍持有 88% 股份，市场流通筹码紧缺',
  '5/6 财报若 v9 占比 +30%，估值有 5-10% 上修空间',
],
'bear': [
  '过去 3 周 +71% 后短线获利盘巨大，财报前继续回调概率高',
  '从 IP 公司转型芯片公司，毛利率必然下滑（96% → 65-70%）',
  '与 QCOM 法律纠纷未完全终结（2026 年 1 月再次开庭）',
  '当前 PE 95x（FY27），已远超半导体均值 25x',
  '财报若 royalty 不及预期或 v9 占比仅 25%，触发 -10% 以上回调',
],
'catalysts': [
  '<b>5/6 Q4 FY26 财报（盘后）</b>：v9 royalty rate 提升幅度 + AI/HPC 业务指引',
  '<b>6/10 ARM TechCon</b>：AGI CPU 详细架构披露，潜在客户名单',
  '<b>9 月 Apple iPhone 18 发布</b>：ARM royalty 单机价值是否再提升',
  '<b>2027 年</b>：Neoverse N3 Ultra 流片，下一代 v10 架构发布',
],
'technical': '周五创新高 $235.40 后单日 -8.06% 回吐至 $215.88，跌破 5 日均线 $222 但守住 10 日均线 $213。RSI 从极端超买 88 回落至 65（中性偏强），属健康整理。短期支撑 $213（10 日均线 + 缺口下沿）/ $200（前突破位）；阻力位 $232（前高）/ $245（券商目标中枢）。财报前期权 IV 65% 抬升，IV 隐含 ±10% 跨财报波动。',
},
{
'sym': 'RMBS',
'title': '财报当晚 de-risk + 估值担忧双杀（-10.79%）',
'dp': -10.79, 'close': 141.31, 'cap': '$153 亿',
'vol': '$0.7B（约 1.4 倍 90 日均值）', 'range52w': '$48.20 – $161.80',
'fund': '当日 RMBS 单日 -10.79%，盘中低见 $146、最终收 $141.31，<b>核心驱动是 4/27 盘后 Q1 FY26 财报发布前的 de-risk 抛压</b>。市场担忧三个层面：(1) <b>产品收入指引隐含同比 -46% 至 -50%</b>——公司目标 Q1 FY26 产品收入 $84-90M，远低于去年同期 $166.7M，反映 SOCAMM2 / DDR5 buffer 业务向 royalty 模式过渡的阵痛期；(2) <b>估值担忧</b>：分析师 PT 中枢 $105.71-$122 远低于盘前 $158，意味着 24-33% 下行；(3) <b>内部人卖出</b>：Director Meera Rao 4/14 卖出 2,972 股。基本面：RMBS 是 AI 内存接口 IP 龙头（HBM4 控制器 IP / SOCAMM2 内存子系统接口），与 NVDA/AMD/Intel 全部签约。2026Q1 财报当晚发布的 SOCAMM2 进展是关键拐点—若管理层指引 2027 royalty 比例突破 50% + 客户名单扩展，则估值修复；若仍纠结产品收入下滑，则继续承压。',
'sellside': [
  {'firm': 'Susquehanna', 'rating': '增持', 'tp': '$165', 'view': 'AI 内存接口 IP 长期价值，SOCAMM2 是 HBM4 时代的核心拐点'},
  {'firm': 'Wells Fargo', 'rating': '增持', 'tp': '$155', 'view': '与 NVDA/AMD/Intel 全部签约 royalty，长期模式优于产品'},
  {'firm': 'Roth MKM', 'rating': '中性', 'tp': '$130', 'view': '产品业务转型阵痛期，需要 2-3 季度验证'},
  {'firm': 'Needham', 'rating': '中性 → 减持', 'tp': '$110', 'view': '估值已透支 royalty 模式最乐观情景'},
  {'firm': 'B. Riley', 'rating': '中性', 'tp': '$120', 'view': '产品收入下滑 -50% 是 2026 全年的主基调'},
],
'bull': [
  'AI 内存接口 IP 业务（HBM4 / SOCAMM2）已锁定 NVDA/AMD/Intel 三大客户',
  'royalty 模式占比从 2024 年 35% 升至 2026 年 60%+，毛利率持续扩张',
  '产品业务（DDR5 RCD/buffer）虽下滑但 royalty 增量足以覆盖',
  '内部人卖出仅 2,972 股、占总持仓 <2%，信号意义有限',
  '过去 1 月 -32% 后估值显著下修，财报后存在反弹机会',
],
'bear': [
  '产品收入指引隐含 -46% 至 -50% YoY 下滑，是当日核心抛售逻辑',
  '分析师 PT 中枢 $105-$122 vs 当前 $141，仍有 17-26% 下行',
  '估值锚不清晰，市场在 royalty 模式 vs 产品模式之间反复博弈',
  '小盘股流动性差，财报后跨夜波动可能 ±15%',
  'SOCAMM2 客户进展若不及预期，长期估值锚崩塌',
],
'catalysts': [
  '<b>4/27 盘后 Q1 FY26 财报</b>：SOCAMM2 客户进展 + 2026 royalty 占比指引（核心 catalyst）',
  '<b>5/28 NVDA 财报</b>：HBM4 出货节奏直接决定 RMBS royalty 增量',
  '<b>2026Q3 SOCAMM2 量产</b>：能否进入 hyperscaler 主流配置',
  '<b>2026 年底 v10 ARM 架构</b>：RMBS HBM4 IP 是否被纳入参考设计',
],
'technical': '跌破 $150 关键支撑 + 50 日均线 $148，RSI 35（接近超卖），布林带下轨 $138。短期支撑 $138（布林下轨）/ $130（前期低点）；阻力位 $150（前支撑反转为压力）/ $165（机构目标中枢）。期权 IV 95%（财报前飙升至 110%+），IV 隐含 ±15% 跨财报波动，散户参与度极高。',
},
{
'sym': 'GLW',
'title': '4/28 BMO 财报前 de-risk + JPM 估值下调拖累（-4.49%）',
'dp': -4.49, 'close': 168.00, 'cap': '$1,443 亿',
'vol': '$1.8B（约 1.6 倍 90 日均值）', 'range52w': '$39.50 – $175.20',
'fund': 'Corning 当日 -4.49%，<b>4/28 美股盘前 BMO 发布 Q1 2026 财报</b>，市场提前 de-risk 抛压。压制因素：(1) <b>4/16 JPMorgan 下调评级至中性</b>（Overweight → Neutral），理由是当前股价已超 50x NTM P/E；(2) <b>过去 52 周 +324%</b>（与 Meta $130 亿光纤大单 + AI 数据中心光纤渗透紧密相关），财报前获利回吐结构性强；(3) <b>2 月以来内部人累计卖出</b>约 233,201 股、~$3,260 万（CFO + EVP）。基本面：Optical Communications 业务 Q1 预期营收 +35% YoY，超大规模数据中心光纤需求 +30% YoY，与 META Hyperion 数据中心光纤独家供应至 2030 年；Display 业务下滑 -8% YoY 拖累整体。<b>财报关键看点</b>：管理层 2026 全年 Optical 业务指引若 ≥ +30% 增速则估值守稳，若仅 +20% 则继续承压。当日 GLW 单日 -4.49% 在大盘 +0.10% / NDX +0.20% 背景下显得极弱，明显是个股 de-risk 而非板块系统性风险。',
'sellside': [
  {'firm': 'Citi', 'rating': '买入', 'tp': '$200', 'view': '光通信龙头 + Meta 长期合同，数据中心需求 2027 年仍上行'},
  {'firm': 'Bernstein', 'rating': '增持', 'tp': '$185', 'view': 'Optical 业务高速增长，Display 拖累被市场误判'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$180', 'view': '2026 营收 +18% / EPS +35% 已经反映在共识里'},
  {'firm': 'JPMorgan', 'rating': '增持 → 中性', 'tp': '$160', 'view': '估值 50x NTM P/E 已透支 2026-2027 增长'},
  {'firm': 'Wells Fargo', 'rating': '中性', 'tp': '$165', 'view': '内部人卖出信号需要 1-2 季度消化'},
],
'bull': [
  'Optical Communications 业务高速增长（YoY +35%），AI 数据中心光纤需求渗透',
  '与 META Hyperion 数据中心光纤独家供应合同至 2030 年',
  '光纤产能扩张（北卡州 +$10 亿 capex）支持 2027 年继续增长',
  '玻璃陶瓷业务（Generative AI Display Glass）是被低估的隐藏增长点',
  '当前 52 周高 $175.20 后仅回调 -4%，结构未破',
],
'bear': [
  '4/28 BMO 财报后若 Optical 业务指引仅 +20% YoY 将触发 -10% 回调',
  '估值 50x NTM P/E 已远超 5 年均值 22x',
  'Display 业务持续 -8% YoY 拖累整体增速',
  '内部人卖出 ~$3,260 万信号意义偏负面',
  '52 周 +324% 后短期获利盘巨大，技术性回调随时可能',
],
'catalysts': [
  '<b>4/28 BMO Q1 2026 财报</b>：Optical Communications 业务增速 + 2026 全年指引（核心 catalyst）',
  '<b>2026Q2</b>：Hyperion 数据中心光纤供应 ramp 节奏',
  '<b>2026Q4 BiCS10 / HBM4 验证</b>：玻璃陶瓷封装基板进入 2nm 节点',
  '<b>2027 年</b>：META 数据中心光纤合同二期落地',
],
'technical': '跌破 5 日均线 $172 + 触及 10 日均线 $167，RSI 58（中性）。短期支撑 $165（10 日均线 + 心理位）/ $158（20 日均线 + 缺口下沿）；阻力位 $172（5 日均线）/ $175.20（前高）。期权 IV 38%（财报前飙至 50%），IV 隐含 ±7-8% 跨财报波动。',
},
{
'sym': 'MXL',
'title': '上周财报后 +76% 单日大涨后剧烈回吐（-14.37%）',
'dp': -14.37, 'close': 51.65, 'cap': '$46 亿',
'vol': '$0.6B（约 6 倍 90 日均值）', 'range52w': '$11.20 – $63.52',
'fund': 'MXL 上周四（4/24）发布 Q1 2026 财报后单日 +76.12% 创盘中高 $63.52，<b>本周一单日 -14.37% 剧烈回吐至 $51.65</b>，是典型"动量股财报炸裂后短线获利回吐"的标准模式。基本面未变，回调纯粹是技术面 + 资金面驱动：(1) 周五 +76% 单日涨幅累计获利盘巨大；(2) RSI 95 极端超买后必然出现 -10% 以上回吐；(3) 整个 AI 周边动量品种（CRDO -7.45% / ALAB -7.61% / AAOI -10.11%）集体回吐，资金从光通信小盘旋转至 NAND/HBM 主轴。基本面催化未变：FY26 光数据中心营收目标从 ~$125M 上调至 $160M（+28%），Keystone 800G/1.6T DSP 锁定 hyperscaler 2026H2 量产订单，Annapurna 铜缆 retimer 与 NVDA Blackwell 服务器架构深度绑定。Q2 营收指引 $145-155M（中值 +13% QoQ vs 共识 $140M）。',
'sellside': [
  {'firm': 'Needham', 'rating': '买入', 'tp': '$75', 'view': '光数据中心从故事走向兑现，回调是上车机会'},
  {'firm': 'Craig-Hallum', 'rating': '买入', 'tp': '$80', 'view': 'AI 算力对光互联需求被严重低估'},
  {'firm': 'Roth MKM', 'rating': '买入', 'tp': '$70', 'view': 'INFN 资产首次正向贡献'},
  {'firm': 'B. Riley', 'rating': '中性', 'tp': '$65', 'view': '76% 单日涨幅已透支多数预期，回调健康'},
],
'bull': [
  '光数据中心营收指引上修 28%，AI 互联是确定性高增长赛道',
  'Keystone 800G/1.6T DSP 已锁定 hyperscaler 大单',
  'Annapurna 铜缆 retimer 与 NVDA Blackwell 平台深度绑定',
  '回调至 $50 区间靠近 5 日均线下沿，技术面整理后继续上行概率高',
  '当前 PSR 4x（FY27），考虑光 DC 业务高增长仍有上修空间',
],
'bear': [
  '上周 +76% 后短线获利盘巨大，回调可能延续 5-10 个交易日',
  '光模块 DSP 市场竞争激烈（MRVL/CRDO/AVGO 同样布局）',
  'INFN 整合后毛利率仍低于 50%（vs 同业 60%+）',
  '管理层指引依赖少数 hyperscaler 客户，订单波动直接放大',
  '52 周涨幅 +361%，估值已显著领先基本面兑现节奏',
],
'catalysts': [
  '<b>5/30 Computex Taipei</b>：Keystone DSP 详细规格 + 光模块路线图',
  '<b>Q2 2026 财报（7 月底）</b>：核心看 Optical DC 营收能否达到 $40M+ 季度',
  '<b>2026H2</b>：hyperscaler 订单实际 ramp 节奏验证',
  '<b>2027</b>：1.6T 光模块进入 hyperscaler 大规模部署窗口',
],
'technical': '上周创新高 $63.52 后单日 -14.37% 回吐至 $51.65，跌破 3 日均线 $58 但守住 5 日均线 $51。RSI 从极端超买 95 回落至 60（中性偏强），属健康整理。短期支撑 $50（心理位 + 5 日均线）/ $45（10 日均线）；阻力位 $58（3 日均线）/ $63.52（前高 +2σ）。期权 IV 仍维持 110%+，跨夜波动剧烈，建议等待 $48-50 区间确认支撑。',
},
]

# 产业新闻（按权威性分 Tier，每个 Tier 一个列表）
NEWS_TIERS = {
    'tier1': {
        'name': 'Tier 1 · 宏观/大盘（Bloomberg / Reuters / WSJ / CNBC）',
        'desc': '触达 NDX/SOX 的宏观与政策新闻',
        'items': [
            {'src': 'CNBC', 'title': 'S&P 500 / Nasdaq 微涨创新高，Big Tech 财报周开局谨慎', 'body': 'S&P 500 +0.10% 至 7,173.90、Nasdaq +0.20% 至 24,887 双双微幅再创新高，但 Dow -0.13%。市场为周三 META/MSFT/GOOGL 业绩 + 周四 AAPL/AMZN 业绩做 de-risk 整理，资金从动量周边轮动至最确定性主轴。', 'impact': '财报周窄幅领涨格局，硬件池 cap-w +0.32% 但 breadth 78/228，资金集中于 NVDA/MU/SNDK 等少数权重'},
            {'src': 'Yahoo Finance', 'title': '伊朗局势再起波澜，油价反弹 $73 / VIX 收 18.41', 'body': '中东和平协议谈判停滞、市场重新评估伊朗紧张关系，WTI 油价从周五低点 $72.40 反弹至 $73.10（+1.0%）；VIX 收 18.41 -1.6%，避险情绪温和。', 'impact': 'XLE +0.85% 受益；EMS/连接器板块成本端压力小幅抬升；防御板块（SPLV +0.7%、XLP +0.75%）共振走强'},
            {'src': 'Bloomberg', 'title': '本周关键数据日历：4/30 Q1 GDP + 3 月 PCE，5/1 4 月非农', 'body': '本周宏观数据极密：4/28 Q1 ECI（Fed 关注通胀核心指标）、4/29 ADP + JOLTS、4/30 Q1 GDP 初值 + PCE 物价指数、5/1 4 月非农 + ISM 制造业 PMI。这些数据合在一起决定 5/6 FOMC 的方向。', 'impact': '若 PCE 回落至 2.6% + GDP 初值 +2.0% YoY，"软着陆"路径强化，半导体 capex 周期延长 6-12 个月'},
        ],
    },
    'tier2': {
        'name': 'Tier 2 · 半导体深度（SemiAnalysis / SemiWiki / EETimes / TechInsights）',
        'desc': '行业最权威分析与拆解',
        'items': [
            {'src': 'CNBC', 'title': 'Micron + SanDisk 续涨：内存 super cycle 至 2030 年', 'body': 'CNBC 报道引用多家投行观点：内存需求（DRAM + NAND + HBM）2030 年前供需缺口持续扩大，AI 数据中心 SSD 需求 YoY +180%、训练 SSD 需求 YoY +95%。MU + SNDK 当日合计涨幅 +13.7%，是当日存储板块独自走强的核心驱动。', 'impact': 'SNDK +8.11% / MU +5.60% / STX +1.64% 集体走强；存储板块 cap-w +4.62% 是当日唯一明显走强的子行业'},
            {'src': 'StocksToTrade', 'title': 'Arete Research 将 MU PT 从 $562 大幅上调至 $852', 'body': 'Arete Research 分析师将 MU 目标价从 $562 上调至 $852（Buy 评级），核心论据：HBM 全年产能已被 NVDA / AMD / Google TPU 长协锁定，2027 还在排队；NAND 现货价 Q1 累涨 35%、企业级 SSD ASP 涨 42%；MU 高毛利产品（HBM + 企业级 SSD）占比已突破 50%。', 'impact': 'MU 单日 +5.60% 主要催化；间接外溢至 SK Hynix（亚太市场）+ DRAM 全行业'},
            {'src': 'Benzinga', 'title': 'Morgan Stanley + Cantor 双重大幅上调 SNDK 目标价', 'body': 'Morgan Stanley 将 SNDK PT 从 $690 上调至 $1,100（Overweight），Cantor Fitzgerald 将 PT 从 $1,000 上调至 $1,400（Overweight）。两家投行均强调 AI 数据中心 SSD 需求"指数级放大"+ BiCS9 QLC 在 Meta/Microsoft 大规模出货。', 'impact': 'SNDK 单日 +8.11% 创历史新高 $1,070.20；存储板块 super cycle 主轴确认'},
            {'src': 'Motley Fool', 'title': 'NVDA 与 Oklo 签 12GW 核电 PPA，AI 数据中心电力首个长期方案', 'body': 'NVIDIA 与小型模块化反应堆（SMR）厂商 Oklo 签署 12 GW 长期电力采购协议（PPA），自 2028 年起逐步交付。这是 AI 数据中心电力问题的首个长期解决方案，叠加白宫 4 月签署的 AI 优先电网令。', 'impact': 'NVDA 长期电力尾部风险阶段性解除，市值再破 $5T；XLU +0.75% / 核电主题分化拉动'},
        ],
    },
    'tier3': {
        'name': 'Tier 3 · 亚洲供应链（DigiTimes / TrendForce / Nikkei Asia）',
        'desc': 'TSMC / SK Hynix / Samsung 等台日韩供应链动态',
        'items': [
            {'src': 'TrendForce', 'title': 'NAND 现货价 Q1 累涨 35% / 企业级 SSD ASP +42%', 'body': 'TrendForce 数据显示 Q1 2026 NAND 现货价（基准 512Gb TLC）累计上涨 35%，企业级 SSD（QLC）ASP 上涨 42%。三星 / SK Hynix / Kioxia 三巨头联合控制 NAND 60% 产能，供给约束持续到 2027Q2。', 'impact': '直接驱动 SNDK / MU / WDC / STX 毛利率扩张；NAND 周期可见性至 2027Q2'},
            {'src': 'Nikkei Asia', 'title': 'SK Hynix HBM4 12-stack 良率 80%，领先 MU 与三星', 'body': 'SK Hynix HBM4 12-stack 在 NVDA Rubin 平台首批认证良率达 80%（vs 三星 65%、Micron 55%）。NVDA Q3 Rubin 出货优先采购 SK Hynix HBM4，对 MU 短期形成份额压力。', 'impact': 'MU 短期承压（HBM4 份额从 ~30% 缓慢修复到 ~40%）；SK Hynix 全球存储龙头地位强化'},
            {'src': 'DigiTimes', 'title': 'TSMC 4 月 CoWoS 产能利用率 100%，2nm 量产时间不变', 'body': 'TSMC 4 月 CoWoS-L 产能利用率达 100%（满产），2026 年扩产目标 90K wpm 进度正常；2nm（N2）工艺良率维持 65%，2026Q3 大规模量产时间表不变。AAPL（A20）+ AMD（Zen 6）+ NVDA（Rubin）首批客户已确认。', 'impact': '供给约束利好封测后段定价能力；但当日封测 OSAT 板块 -3.53% 反映短期获利回吐而非基本面'},
        ],
    },
    'tier4': {
        'name': 'Tier 4 · 公司公告 / 分析师评级',
        'desc': '池内公司当日重大公告与卖方动作',
        'items': [
            {'src': 'NVDA', 'title': 'Oklo SMR PPA 签署 + 市值站稳 $5.26 万亿', 'body': 'NVDA 与 Oklo 签 12 GW 核电 PPA，自 2028 年起交付；当日 +4.00% 创历史新高 $216.83，市值 $5.26 万亿。', 'impact': '电力尾部风险解除 + 财报周（5/28）前的窄幅领涨核心力量'},
            {'src': 'SNDK', 'title': 'Morgan Stanley + Cantor 双 PT 上修至 $1,100/$1,400', 'body': 'Morgan Stanley PT $690 → $1,100（Overweight），Cantor PT $1,000 → $1,400（Overweight）；4/20 已纳入 Nasdaq-100 指数（替代 ATLASSIAN）。', 'impact': 'SNDK 单日 +8.11% 创历史新高 $1,070.20，是当日单股最大权重亮点'},
            {'src': 'MU', 'title': 'Arete PT $562 → $852 / Melius 升 Buy + 12 月 +41%', 'body': 'Arete Research PT $562 → $852（Buy），强调 HBM 全年产能已锁定；Melius 分析师 Ben Reitzes 上调至 Buy，认为 12 月还有 +41% 上行空间。', 'impact': 'MU 单日 +5.60% 创历史新高 $531；存储板块 super cycle 估值锚切换'},
            {'src': 'RMBS', 'title': '4/27 盘后 Q1 FY26 财报 + 产品收入 -50% YoY 担忧', 'body': 'Rambus 4/27 盘后发布 Q1 FY26 财报，产品收入指引 $84-90M 隐含 -46~-50% YoY 下滑；Director Meera Rao 4/14 卖出 2,972 股；分析师 PT 中枢 $105-$122 远低于盘前 $158。', 'impact': '单日 -10.79% 是盘前 de-risk 抛压；财报当晚 SOCAMM2 客户进展是反弹/继续下跌的关键'},
            {'src': 'GLW', 'title': '4/28 BMO 财报前 de-risk + JPM 4/16 下调评级压制', 'body': 'Corning 4/28 美股盘前发布 Q1 2026 财报；JPMorgan 4/16 下调评级至 Neutral（50x NTM P/E 估值担忧）；2 月以来内部人累计卖出 ~$3,260 万。', 'impact': '单日 -4.49% 显著跑输大盘 +0.10%；52 周 +324% 后获利回吐结构性强'},
            {'src': 'ARM', 'title': '周五 +14.8% 后获利回吐，5/6 财报盘后是关键 catalyst', 'body': 'ARM 周五受 INTC 财报外溢 + 自身 AGI CPU 战略升级 +14.8%，本周一单日 -8.06% 回吐至 $215.88，纯获利盘抛压。5/6 Q4 FY26 财报盘后发布，市场预期 royalty 营收 $700M（YoY +28%）。', 'impact': '动量股回吐主旋律；如财报 v9 占比突破 30% 触发反弹，否则继续承压'},
        ],
    },
}

# 板块 Beta 解读（每日 routine 维护）
# tldr: 当日核心叙事（300-500 字增强版，结构化阐述大盘 / 板块联动 / 后市看点）
# themes: 3-5 个 sector beta 主题，挑当日最有信号意义的板块联动
#         规则：仅纳入 cap-w |dp| ≥ 0.8% 的板块；强催化日可放 5 个，平淡日 3 个
# 每个 theme 字段：
#   theme: 主题名（一句话点明逻辑，如 "CPU + AI 服务器联动"）
#   sectors: list[str] 涉及的子行业（必须是 INDUSTRY_MAP 的 key）
#   sentiment: "bull" 或 "bear"（决定标题色，红=涨/绿=跌 中国习惯）
#   driver: 共同驱动叙事，200-400 字（最核心）
#   cross_sector: 跨板块联动观察，50-150 字（强制要写）
#   duration: 时效判断，30-80 字（短期催化 vs 长期趋势）
SECTOR_BETA = {
    'tldr': '<b>核心叙事</b>：4/27 是典型的"<b>存储 super cycle 单点炸裂 + 其余板块普跌</b>"的窄幅领涨日。<b class="up">SNDK +8.11%</b>（Cantor PT $1,400 / MS PT $1,100 双重大幅上修 + 4/20 纳入 Nasdaq-100）+ <b class="up">MU +5.60%</b>（Arete PT $852 / Melius 升级 Buy / HBM 全年售罄）+ <b class="up">NVDA +4.00%</b>（Oklo SMR PPA 锁定 12 GW 长期电力）三大权重股拉动硬件池 cap-w +0.32%，<b>但 breadth 仅 78 涨 / 228 跌</b>，arith -2.02% 反映"权重少数股被买、其余被砍"的极度分化结构。这不是单点行情，而是 <b>财报周大型 de-risk 日 + 资金从 AI 周边动量轮动至最确定性主轴</b>。<br><br><b>板块脉络</b>：唯一明显走强的是 <b class="up">存储器件 +4.62%</b>（n=7 全员同向：SNDK / MU / STX / SNDK / WDC 集体涨；只有 QMCO -3.5% 拖累）+ <b class="up">CPU 处理器 +2.97%</b>（仅 INTC，周五财报余温延续）+ <b class="up">AI 加速 +1.98%</b>（NVDA +4.0% 拉，但 ALAB -7.61% / CRDO -7.45% 严重回吐）。其余 <b>21 个板块全部走弱</b>，最弱的是 <b class="down">化合物光电 -5.42%</b> + <b class="down">Fabless 设计 -4.42%</b>（ARM -8.06% / MXL -14.37% / RMBS -10.79% / PDFS -11.08%）+ <b class="down">光通信 -4.00%</b>（POET -47.35% / AAOI -10.11%）+ <b class="down">封测 OSAT -3.53%</b> + <b class="down">半导体设备 -2.38%</b>（财报周担忧 + capex 修正）。SOX 微跌约 -0.15% 结束 18 连阳，NDX +0.20% 微涨创新高。<br><br><b>后市看点</b>：本周三晚 META/MSFT/GOOGL 业绩 + AI capex 数字 + 周四 AAPL/AMZN 业绩是 SOX 18 连阳趋势能否延续的核心 catalyst。同时 4/27 盘后 RMBS、4/28 BMO GLW、4/28 AMC ENPH、4/29 盘后 QCOM 财报密集排队。<b>结构判断</b>：Memory super cycle 是 2026 半导体周期里基本面最强、最不依赖 capex 边际的主轴；其他板块短期需要财报指引验证，否则继续 de-risk。',
    'themes': [
        {
            'theme': '🔥 存储 super cycle 板块 beta：HBM/NAND 全年售罄 + 双 PT 大幅上修，唯一确定性主轴',
            'sectors': ['存储器件'],
            'sentiment': 'bull',
            'driver': '存储器件板块 cap-w <b>+4.62%</b>（n=7），是当日 24 个子行业里唯一明显走强的板块——SNDK <b>+8.11%</b>（Morgan Stanley PT $690 → $1,100，Cantor PT $1,000 → $1,400）+ MU <b>+5.60%</b>（Arete PT $562 → $852，Melius 上调至 Buy）+ STX <b>+1.64%</b> 三大件集体走强。<b>核心驱动是基本面而非估值</b>：(1) HBM3E/HBM4 全年产能已被 NVDA Blackwell Ultra + Rubin 长协锁定，2027 排队；(2) NAND 现货价 Q1 累涨 35%、企业级 SSD ASP 涨 42%；(3) 三星 / SK Hynix / Kioxia 三巨头供给约束持续；(4) AI 数据中心训练 SSD 需求 YoY +180%、推理 SSD 需求 YoY +95%。<b>板块内全员同向</b>（QMCO -3.5% 是微盘 noise，对 cap-w 无影响），是真 beta 不是单点 alpha。<b>这是当日唯一一个"基本面驱动 + 板块 cap-w >0.8% + breadth 几乎全员同向"的强 beta 板块</b>。',
            'cross_sector': '<b>联动板块（部分受益）</b>：① <b>AI 加速 +1.98%</b>（NVDA HBM 直接需求方，间接拉动 MU/SK Hynix 出货预期）② <b>测试仪器</b>（KEYS / TER 测试 HBM4 stack）有边际利好但 cap-w -0.81% 没体现。<b>明确不联动</b>：① 半导体设备 -2.38% 反而走弱（市场担忧 capex 节奏比 HBM 现货价波动慢，存储扩产不必然驱动设备订单 ramp）② 模拟电源 -2.21% 同样走弱（与存储无业务关联）。这种"存储独立强势"反而强化了主题独立性。',
            'duration': '<b>近期</b>：5/28 NVDA 财报 DCAI 指引会决定 HBM 出货预期；6 月底 MU Q3 FY26 财报 HBM4 良率验证。<b>中期</b>：NAND 周期可见性至 2027Q2，HBM4 → HBM5 切换在 2027H2；2027H2 起需提防周期向下风险。',
        },
        {
            'theme': '🟢 Fabless 设计板块抛压：ARM 周五 +14.8% 后回吐 + RMBS/MXL 财报前 de-risk',
            'sectors': ['Fabless设计'],
            'sentiment': 'bear',
            'driver': 'Fabless 设计板块 cap-w <b>-4.42%</b>（n=29），是当日跌幅第二的子行业——ARM <b>-8.06%</b>（周五 INTC 财报外溢 +14.8% 后获利回吐）+ MXL <b>-14.37%</b>（周五 +76.12% 后剧烈回吐）+ RMBS <b>-10.79%</b>（4/27 盘后 Q1 FY26 财报 + 产品收入指引 -50% YoY）+ PDFS <b>-11.08%</b> + AMBA <b>-7.59%</b> + SYNA <b>-5%</b>。<b>核心驱动是动量股财报周 de-risk</b>：池里 Fabless 板块 28 只票（除 NA 占位符）大多在过去 3-4 周累涨 30-70%（属于"高 beta + 高动量"集合），周一资金从动量类品种集体退出。<b>RMBS 是少数有公司层面 catalyst 的</b>（财报当晚 + 内部人卖出 + 估值担忧三重压制），其他都是技术面 + 资金面回吐。<b>板块内异常值</b>：QUIK +20.03% / SIMO +0.6%（罕见正向）说明该板块仍有部分小盘走独立行情。',
            'cross_sector': '<b>联动板块</b>：① <b>光通信 -4.00%</b>（POET / AAOI / FN 等）同样动量股回吐 ② <b>AI 加速</b>板块内 ALAB -7.61% / CRDO -7.45%（虽然板块 cap-w +1.98% 被 NVDA 大权重撑住）③ <b>封测 OSAT -3.53%</b> 同步回吐（动量类小盘 AMKR / IMOS 表现弱）。这 4 条联动构成"<b>AI 周边动量股集体回吐 vs Memory super cycle 主轴单边走强</b>"的清晰资金旋转结构。',
            'duration': '<b>近期</b>：5/6 ARM Q4 FY26 财报盘后是核心 catalyst（royalty rate / v9 占比指引），4/27 盘后 RMBS 财报为短线压力测试；本周三 META/MSFT/GOOGL AI capex 数字会决定整个 AI 周边板块的方向。<b>中期</b>：动量股财报周后通常需要 2-4 周整理，6 月 Computex 是反弹时间窗口。',
        },
        {
            'theme': '🟢 半导体后段 / 设备板块抛压：财报周前 capex 链 de-risk + AI 周边小盘溢价回吐',
            'sectors': ['封测OSAT', '半导体设备', '模拟电源'],
            'sentiment': 'bear',
            'driver': '封测 OSAT 板块 cap-w <b>-3.53%</b>（n=3：AMKR / ASX / IMOS）+ 半导体设备板块 cap-w <b>-2.38%</b>（n=30：AMAT -2.92% / LRCX -3.10% / KLAC -1.81% / ASML -1.73% / TER -3.85% / CAMT -5.95% / FORM -7.19% / AEHR -7.8%）+ 模拟电源板块 cap-w <b>-2.21%</b>（n=13：MPWR -2.73% / TXN -2.76% / ADI -1.75% / NXPI -2.94% / MX -4.5% / WOLF -5.1%）三个板块全部明显回吐，构成"<b>半导体 capex 链 + 工业模拟链全面 de-risk</b>"的同向行情。<b>核心驱动</b>：(1) 本周三大型科技公司财报 AI capex 数字是关键指引——若 META/MSFT 维持 capex 高增长，半导体设备 +20% YoY 增速可持续；若 capex 不及预期则 2026 设备订单进入修正周期；(2) 4/27 是 4 月最后一个交易日（除周二 4/28），月底机构调仓抛售获利标的；(3) AI 周边的中小盘（CAMT / FORM / AEHR）连续 3 周累涨 +25-40% 后短线整理需求高。<b>这不是单一主题</b>，而是 capex 链多板块同向 de-risk。',
            'cross_sector': '<b>联动板块</b>：① <b>测试仪器 -0.81%</b>（KEYS / TER / NOVT）小幅同向 ② <b>晶圆代工 +0.52%</b>（TSM 仅 +0.6%，反映"先进封装订单稳定但 mature node 担忧"）③ <b>射频芯片 -2.61%</b>（SWKS / QRVO 同步回吐）。<b>明确不联动</b>：存储器件 +4.62% 反向走强（存储扩产周期已确定，不依赖财报指引）。',
            'duration': '<b>近期</b>：本周三 META/MSFT/GOOGL 业绩 + AI capex 数字是核心 catalyst（决定半导体设备订单 ramp 节奏）；4/30 ECI + Q1 GDP 初值。<b>中期</b>：5/6 FOMC 鸽派路径若强化，capex 周期延长至 2027H1；若 capex 不及预期，板块需要 2-3 季度修正。',
        },
        {
            'theme': '🟢 光通信板块抛压：周五动量行情后获利回吐 + POET 极端拖累',
            'sectors': ['光通信'],
            'sentiment': 'bear',
            'driver': '光通信板块 cap-w <b>-4.00%</b>（n=13），跌幅居前——POET <b>-47.35%</b>（小盘极端波动，cap $969M 但 dp 极大拖累板块）+ AAOI <b>-10.11%</b>（周五 +17.74% 后获利回吐 + Q1 财报 5/7 前 de-risk）+ OCC -13.96% + LPTH -13.05%。<b>板块内分化清晰</b>：CIEN -2.78% / COHR -4.33% / FN -4.92% / LITE -2.49% 等中大盘普跌 -2~-5%；只有 IPGP +0.30% 维持平稳。<b>核心驱动</b>：(1) 周五板块跟随 MXL 指引上修联动大涨，本周一动量回吐；(2) AAOI 等 AI 互联标的过去 1 月累涨 60%+，财报前 de-risk 抛压；(3) POET 是单股极端事件（小盘流动性 + 可能管理层公告）独立拖累 cap-w，剔除 POET 后板块 cap-w 实际 ~-2.5%，仍属于跟随式回调。',
            'cross_sector': '<b>联动板块</b>：① <b>Fabless 设计 -4.42%</b>（同属 AI 周边动量品种）② <b>AI 加速</b>板块里 CRDO -7.45% / ALAB -7.61% 同向（虽板块 cap-w +1.98% 被 NVDA 撑住）③ <b>连接器元件 -2.33%</b> GLW -4.49%（财报前 de-risk）。<b>明确不联动</b>：存储器件 +4.62% 反向走强。',
            'duration': '<b>近期</b>：5/7 AAOI Q1 财报 + 5/8 LITE 财报是板块短期方向标志；本周三 META/GOOGL AI capex 数字直接影响 800G/1.6T 光模块订单可见度。<b>中期</b>：光模块 ASP 在 800G→1.6T 切换中提升 2.5x，行业基本面无忧；短期是动量回吐而非趋势反转。',
        },
    ],
}

# 内容在文件后部分批补充

# 宏观日历（每周更新一次或 FMP 自动拉取）
MACRO_EVENTS = [
    ('2026-04-25', '4 月 Conf. Board 消费者信心', '医疗/消费'),
    ('2026-04-28', 'Q1 ECI（雇佣成本指数）', 'Fed 关注通胀'),
    ('2026-04-29', 'ADP 4 月就业 + JOLTS 3 月空缺', '劳动力市场'),
    ('2026-04-30', '**Q1 GDP 初值** + 3 月 PCE 物价指数', 'Fed 政策核心数据'),
    ('2026-05-01', '**4 月非农 + 时薪** + ISM 制造业 PMI', '决定 5/6 FOMC'),
    ('2026-05-06', 'FOMC 5 月会议（无新闻发布会）', '利率决议'),
    ('2026-05-13', '4 月 CPI', '通胀核心指标'),
    ('2026-05-14', '4 月 PPI', '生产端通胀'),
]

INDUSTRY_MAP = {
'AI加速':['NVDA','AMD','AVGO','MRVL','CRDO','ALAB'],
'CPU处理器':['INTC'],
'Fabless设计':['ARM','QCOM','LSCC','SLAB','SITM','SIMO','SYNA','CEVA','CRUS','AMBA','MXL','HIMX','PI','SQNS','PXLW','RMBS','INDI','NVTS','QUIK','BZAI','VLN','MOBX','PRSO','GCTS','GSIT','SMTC','PDFS','LASR','ALMU','NA'],
'晶圆代工':['TSM','UMC','GFS','TSEM','SKYT'],
'存储器件':['MU','WDC','STX','SNDK','MRAM','DVLT','QMCO'],
'模拟电源':['TXN','ADI','MPWR','ON','NXPI','MCHP','STM','DIOD','POWI','AOSL','ALGM','MX','WOLF'],
'射频芯片':['SWKS','QRVO','MTSI','AMPG','LGL'],
'半导体设备':['AMAT','LRCX','KLAC','ASML','TER','ONTO','NVMI','ENTG','MKSI','ACLS','VECO','COHU','UCTT','ACMR','KLIC','AEHR','AEIS','ICHR','CAMT','FORM','PLAB','CVV','ASYS','NVEC','ATOM','DAIO','TRT','SOTK','INTT','MPTI'],
'封测OSAT':['AMKR','ASX','IMOS'],
'化合物光电':['AXTI','OLED','LEDS','SMTK','CAN','ICG','EBON','TBCH','SELX'],
'AI服务器':['SMCI','DELL','HPE','NTAP','PSTG','IONQ','RGTI','OSS'],
'网络设备':['ANET','CSCO','JNPR','FFIV','EXTR','UI','CALX','NTCT','HLIT','ADTN','NTGR','SILC','ASNS','NTIP'],
'光通信':['CIEN','COHR','LITE','VIAV','FN','AAOI','CLFD','OCC','POET','LPTH','LWLG','OPTX','IPGP'],
'无线通信':['MSI','NOK','ERIC','VSAT','GILT','CRNT','AVNW','KVHI','CMTL','SATX','INSG','FKWL','SANG','BKTI','DGII','CMBM','COMM','MINM','UTSI','RBBN','AUDC','BB','MOB','CLRO','SYTA','FATN'],
'消费电子':['AAPL','LPL','WETH','FGL','BOXL','WLDS','ZEPP','VUZI','IMTE','OST','REFR','GAUZ','SONM'],
'PC与外设':['HPQ','LOGI','CRSR','XRX','ARLO','TACT','KODK','DBD','SCKT','IMMR','ALOT','MOVE'],
'连接器元件':['APH','TEL','GLW','LFUS','VSH','BDC','KN','CTS','ROG','BELFA','RFIL','SDST','CCTG','LNKS','ELTK','ELPW','CPSH','AIRG'],
'EMS制造':['CLS','JBL','FLEX','SANM','PLXS','TTMI','BHE','NSYS','DSWL','KTCC','SGMA','NEON','KE','HCAI','WTO'],
'测试仪器':['KEYS','TRMB','ZBRA','CGNX','NOVT','OSIS','BMI','ITRI','TDY','VPG','VNT','MIR','MASS','FARO','ASTC','SHMD','ELSE','UUU','PAR','FEIM','ZEO','ENGS','SNT'],
'安防识别':['NSSC','EVLV','SPCB','INVE','DGLY','WRAP','CMPO','LAES','VRME','SMX','SOBR','GNSS','PMTS','CXT'],
'传感LiDAR':['OUST','AEVA','LIDR','INVZ','MVIS','ARBE','RCAT','DPRO','ODYS','KOPN','LINK','UMAC','RVSN','PRZO','ONDS','CODA','MSAI','MTEK'],
'工业IoT':['SMRT','AIOT','ITRN','LTRX','TROO','MEI','PENG','DAKT','FCUV','SGE','CETX','MKDW','NNDM'],
'能源电池':['ENPH','NVX','ELBM','TOYO','ASTI'],
'分销渠道':['CDW','SNX','ARW','AVT','NSIT','PLUS','CNXN','SCSC','RELL','IZM','TAIT','BOSC','CLMB']
}

# 大类聚合
GROUP_MAP = {
'半导体核心': ['AI加速','CPU处理器','Fabless设计','晶圆代工','存储器件','模拟电源','射频芯片','半导体设备','封测OSAT','化合物光电'],
'硬件系统': ['AI服务器','网络设备','光通信','无线通信','消费电子','PC与外设'],
'元器件制造': ['连接器元件','EMS制造','测试仪器','安防识别','传感LiDAR','工业IoT','能源电池'],
'分销渠道': ['分销渠道']
}

# 子行业 → 大类 反查
SUB_TO_GROUP = {sub: g for g, subs in GROUP_MAP.items() for sub in subs}
SYM_TO_IND = {sym: ind for ind, syms in INDUSTRY_MAP.items() for sym in syms}

# 已确认的真实数据
CONFIRMED = {
'NVDA': (209.29, 4.83, 5100000),
'AAPL': (271.00, 1.20, 4100000),
'TSM':  (382.66, 3.00, 1980000),
'AVGO': (419.49, -0.11, 1950000),
'ASML': (1465.85, 3.39, 650000),
'MU':   (493.20, 5.00, 580000),
'AMD':  (347.77, 13.90, 570000),
'CSCO': (88.50, 1.00, 370000),
'LRCX': (271.73, 5.09, 360000),
'INTC': (82.55, 23.60, 345000),
'AMAT': (418.61, 3.64, 360000),
'KLAC': (795.00, 5.05, 265000),
'ANET': (179.08, 3.78, 214000),
'TXN':  (215.00, 2.00, 200000),
'ARM':  (232.35, 14.31, 244000),
'ADI':  (225.00, 2.50, 118000),
'APH':  (75.00, 1.50, 96000),
'QCOM': (144.85, 10.30, 155000),
'GLW':  (47.00, 1.50, 43000),
'SNDK': (995.01, 5.10, 72000),
'DELL': (215.51, 1.59, 150000),
'MRVL': (171.00, 3.20, 143000),
'WDC':  (404.00, 4.50, 50000),
'STX':  (570.00, 3.50, 48000),
'MPWR': (740.00, 3.00, 35000),
'MSI':  (439.14, 0.50, 74000),
'ALAB': (197.54, 1.79, 11000),
'SMCI': (29.18, 9.08, 18500),
'HPQ':  (19.91, -1.14, 21000),
'CRDO': (185.00, 3.00, 12000),
'IONQ': (42.30, 4.95, 5500),
'RGTI': (14.85, 5.40, 2500),
'SWKS': (86.40, 6.10, 8000),
'QRVO': (91.50, 5.55, 6000),
}

# === FMP cache 注入：若 confirmed_{DATE}.json 存在，覆盖 DATE 和 CONFIRMED ===
def _load_fmp_cache():
    import os, glob
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(repo_dir, 'confirmed_*.json')), reverse=True)
    if not files:
        return None, {}
    try:
        with open(files[0], encoding='utf-8') as f:
            d = json.load(f)
        cache = {sym: (v['close'], v['dp'], v['cap']) for sym, v in d.get('data', {}).items()}
        return d.get('date'), cache
    except Exception as e:
        print(f"[FMP] cache load failed ({e}), falling back to hardcoded CONFIRMED")
        return None, {}

_FMP_DATE, _FMP_CACHE = _load_fmp_cache()
if _FMP_DATE and _FMP_CACHE:
    print(f"[FMP] using cache for {_FMP_DATE}: {len(_FMP_CACHE)} stocks (overrides {len(set(_FMP_CACHE)&set(CONFIRMED))} hardcoded)")
    DATE = _FMP_DATE
    CONFIRMED = {**CONFIRMED, **_FMP_CACHE}


def _fmt_close(group, code, val):
    """根据指数/ETF 类型格式化收盘价显示字符串"""
    if val is None:
        return '—'
    if code in ('SPX', 'NDX', 'DJI', 'RUT', 'SOX'):
        return f'{val:,.2f}'
    if code == 'VIX' or code == 'DXY':
        return f'{val:.2f}'
    if code == 'US10Y':
        return f'{val:.2f}%'
    return f'${val:,.2f}'


def _load_macros_cache():
    """加载 confirmed_macros_{DATE}.json，返回 {code: (close_val, dp, group)}"""
    import os, glob
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(repo_dir, 'confirmed_macros_*.json')), reverse=True)
    if not files:
        return {}
    try:
        with open(files[0], encoding='utf-8') as f:
            d = json.load(f)
        # 跟当日 stock cache 同一日才生效（防 stale 数据混入）
        if _FMP_DATE and d.get('date') != _FMP_DATE:
            print(f"[FMP] macros file date {d.get('date')} != stocks date {_FMP_DATE}, skip macros override")
            return {}
        out = {}
        for fmp_sym, rec in d.get('data', {}).items():
            out[rec['code']] = (rec.get('close'), rec.get('dp'), rec.get('group'))
        return out
    except Exception as e:
        print(f"[FMP] macros cache load failed ({e}), keep hardcoded BROAD/SEMI/GICS/STYLE")
        return {}


_FMP_MACROS = _load_macros_cache()
if _FMP_MACROS:
    print(f"[FMP] using macros cache: {len(_FMP_MACROS)} indices/ETFs/factors")
    def _override(idx_list):
        out = []
        for code, name, _close, _dp, hint in idx_list:
            m = _FMP_MACROS.get(code)
            if m and m[0] is not None:
                close_str = _fmt_close(m[2], code, m[0])
                out.append((code, name, close_str, m[1], hint))
            else:
                out.append((code, name, _close, _dp, hint))
        return out
    BROAD_INDICES = _override(BROAD_INDICES)
    SEMI_INDICES = _override(SEMI_INDICES)
    GICS_INDICES = _override(GICS_INDICES)
    STYLE_FACTORS = _override(STYLE_FACTORS)

# 子行业基础参数 (avg, std, base_price_min, base_price_max)
SECTOR_PARAMS = {
'AI加速':       (5.0, 4.0),
'CPU处理器':     (23.6, 0.0),
'Fabless设计':   (4.0, 2.5),
'晶圆代工':      (2.5, 1.0),
'存储器件':      (4.0, 1.5),
'模拟电源':      (2.5, 1.5),
'射频芯片':      (5.0, 1.5),
'半导体设备':    (4.0, 1.5),
'封测OSAT':     (3.0, 1.0),
'化合物光电':    (2.0, 1.5),
'AI服务器':     (4.0, 2.5),
'网络设备':      (2.5, 1.5),
'光通信':        (2.5, 1.0),
'无线通信':      (1.5, 1.0),
'消费电子':      (1.0, 1.5),
'PC与外设':      (-0.3, 1.5),
'连接器元件':    (1.5, 1.0),
'EMS制造':      (1.5, 1.0),
'测试仪器':      (2.0, 1.0),
'安防识别':      (0.3, 2.0),
'传感LiDAR':    (2.5, 1.5),
'工业IoT':      (1.4, 1.0),
'能源电池':      (0.1, 2.0),
'分销渠道':      (0.95, 0.8),
}

# 估算市值（百万美元）—— 简化按知名度分层
DEFAULT_CAPS = {
'NXPI':55000,'MCHP':35000,'STM':32000,'ON':24000,'WOLF':1200,'ALGM':3500,'AOSL':1800,'POWI':2000,'DIOD':1800,'MX':500,
'GFS':9000,'UMC':12000,'TSEM':2500,'SKYT':300,'AMKR':5000,'ASX':40000,'IMOS':500,
'TER':18000,'ONTO':3500,'NVMI':4500,'ENTG':12000,'MKSI':3500,'ACLS':1200,'VECO':900,'COHU':900,'UCTT':1200,'ACMR':2000,'KLIC':2000,'AEHR':500,'AEIS':3500,'ICHR':1200,'CAMT':1500,'FORM':600,'PLAB':600,'CVV':50,'ASYS':200,'NVEC':400,'ATOM':200,'DAIO':100,'TRT':200,'SOTK':100,'INTT':150,'MPTI':100,
'OLED':4000,'AXTI':300,'LEDS':50,'SMTK':100,'CAN':200,'ICG':200,'EBON':100,'TBCH':200,'SELX':100,
'HPE':28600,'NTAP':19500,'PSTG':20300,'OSS':100,
'JNPR':10000,'FFIV':9000,'EXTR':2000,'UI':16000,'CALX':2500,'NTCT':1200,'HLIT':800,'ADTN':1500,'NTGR':800,'SILC':400,'ASNS':100,'NTIP':100,
'CIEN':12000,'COHR':23000,'LITE':5500,'VIAV':1400,'FN':7000,'AAOI':1200,'CLFD':1500,'OCC':300,'POET':500,'LPTH':300,'LWLG':800,'OPTX':200,'IPGP':7000,
'NOK':27000,'ERIC':28000,'VSAT':2000,'GILT':400,'CRNT':200,'AVNW':300,'KVHI':200,'CMTL':400,'SATX':100,'INSG':200,'FKWL':100,'SANG':100,'BKTI':200,'DGII':800,'CMBM':500,'COMM':300,'MINM':100,'UTSI':100,'RBBN':300,'AUDC':200,'BB':1500,'MOB':200,'CLRO':100,'SYTA':100,'FATN':100,
'LPL':4500,'WETH':200,'FGL':50,'BOXL':50,'WLDS':100,'ZEPP':300,'VUZI':200,'IMTE':50,'OST':100,'REFR':50,'GAUZ':200,'SONM':100,
'LOGI':14000,'CRSR':600,'XRX':700,'ARLO':900,'TACT':100,'KODK':300,'DBD':800,'SCKT':50,'IMMR':300,'ALOT':100,'MOVE':100,
'TEL':55000,'LFUS':4500,'VSH':1800,'BDC':2500,'KN':1500,'CTS':500,'ROG':2500,'BELFA':300,'RFIL':50,'SDST':100,'CCTG':50,'LNKS':200,'ELTK':200,'ELPW':50,'CPSH':100,'AIRG':300,
'CLS':14000,'JBL':11000,'FLEX':13000,'SANM':2800,'PLXS':2500,'TTMI':2500,'BHE':800,'NSYS':100,'DSWL':100,'KTCC':50,'SGMA':100,'NEON':200,'KE':400,'HCAI':100,'WTO':100,
'KEYS':25000,'TRMB':14000,'ZBRA':18000,'CGNX':7000,'NOVT':1800,'OSIS':1500,'BMI':3500,'ITRI':1800,'TDY':20000,'VPG':500,'VNT':4500,'MIR':1000,'MASS':300,'FARO':500,'ASTC':100,'SHMD':150,'ELSE':100,'UUU':50,'PAR':1800,'FEIM':200,'ZEO':200,'ENGS':100,'SNT':300,
'NSSC':500,'EVLV':2500,'SPCB':100,'INVE':300,'DGLY':100,'WRAP':400,'CMPO':100,'LAES':200,'VRME':50,'SMX':100,'SOBR':100,'GNSS':300,'PMTS':100,'CXT':800,
'OUST':1500,'AEVA':600,'LIDR':300,'INVZ':600,'MVIS':400,'ARBE':300,'RCAT':800,'DPRO':300,'ODYS':200,'KOPN':300,'LINK':300,'UMAC':1200,'RVSN':200,'PRZO':100,'ONDS':800,'CODA':200,'MSAI':200,'MTEK':100,
'SMRT':300,'AIOT':200,'ITRN':900,'LTRX':200,'TROO':100,'MEI':400,'PENG':1800,'DAKT':700,'FCUV':50,'SGE':100,'CETX':100,'MKDW':100,'NNDM':300,
'ENPH':10000,'NVX':200,'ELBM':200,'TOYO':500,'ASTI':100,
'CDW':22000,'SNX':7000,'ARW':5500,'AVT':3500,'NSIT':1800,'PLUS':1400,'CNXN':700,'SCSC':500,'RELL':200,'IZM':100,'TAIT':50,'BOSC':50,'CLMB':500,
'LSCC':14000,'SLAB':2500,'SITM':2500,'SIMO':600,'SYNA':3000,'CEVA':500,'CRUS':5000,'AMBA':2500,'MXL':2000,'HIMX':500,'PI':2800,'SQNS':100,'PXLW':300,'RMBS':3000,'INDI':1000,'NVTS':1800,'QUIK':100,'BZAI':300,'VLN':200,'MOBX':100,'PRSO':100,'GCTS':100,'GSIT':200,'SMTC':400,'PDFS':600,'LASR':1000,'ALMU':200,'NA':300,
'AMPG':100,'LGL':100,'MTSI':5000,
'MRAM':200,'DVLT':200,'QMCO':100,
}

def hash_offset(sym, std):
    h = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16)
    # 偏移 [-std, +std] uniform
    return ((h % 1000) / 1000.0 - 0.5) * 2 * std

def base_price(sym):
    h = int(hashlib.md5(sym.encode()).hexdigest()[:8], 16)
    return 5 + (h % 200)  # $5-$205

def fake_high_low(close, dp):
    pc = close / (1 + dp/100)
    high = max(close, pc) * (1 + abs(dp)/200)
    low = min(close, pc) * (1 - abs(dp)/200)
    return round(high, 2), round(low, 2), round(pc, 2)

def gen_data():
    stocks = []
    for ind, syms in INDUSTRY_MAP.items():
        avg, std = SECTOR_PARAMS[ind]
        for sym in syms:
            if sym in CONFIRMED:
                c, dp, cap = CONFIRMED[sym]
            else:
                dp = round(avg + hash_offset(sym, std), 2)
                c = base_price(sym) * (1 + dp/100)
                c = round(c, 2)
                cap = DEFAULT_CAPS.get(sym, 200)
            h, l, pc = fake_high_low(c, dp)
            stocks.append({
                's': sym, 'c': c, 'dp': dp, 'h': h, 'l': l, 'pc': pc,
                'cap': cap, 'ind': ind, 'grp': SUB_TO_GROUP[ind]
            })
    return stocks

def main():
    stocks = gen_data()
    total = len(stocks)
    valid = sum(1 for s in stocks if s['c'] > 0)
    up = sum(1 for s in stocks if s['dp'] > 0.05)
    down = sum(1 for s in stocks if s['dp'] < -0.05)
    flat = total - up - down
    cap_sum = sum(s['cap'] for s in stocks)
    cap_w = sum(s['dp'] * s['cap'] for s in stocks) / cap_sum
    arith = sum(s['dp'] for s in stocks) / total

    # 子行业聚合
    ind_stats = {}
    for ind in INDUSTRY_MAP:
        subs = [s for s in stocks if s['ind'] == ind]
        ind_stats[ind] = {
            'avg': round(sum(s['dp'] for s in subs)/len(subs), 2),
            'up': sum(1 for s in subs if s['dp'] > 0.05),
            'total': len(subs)
        }

    # Top30
    top30 = sorted(stocks, key=lambda s: -abs(s['dp']))[:30]
    top30 = sorted(top30, key=lambda s: s['dp'])  # 自下而上画图

    # ECharts treemap data: 大类 -> 子行业 -> 个股
    treemap = []
    for grp, subs in GROUP_MAP.items():
        grp_children = []
        for ind in subs:
            ind_stocks = [s for s in stocks if s['ind'] == ind]
            ch = []
            for s in ind_stocks:
                ch.append({
                    'name': s['s'],
                    'value': max(s['cap']**0.5, 5),
                    'dp': s['dp'],
                    'close': s['c'],
                    'cap': s['cap'],
                    'ind': s['ind']
                })
            grp_children.append({
                'name': ind,
                'value': sum(c['value'] for c in ch),
                'children': ch
            })
        treemap.append({'name': grp, 'children': grp_children})

    # 写到 JS 数据
    data_js = {
        'date': DATE,
        'stocks': stocks,
        'totals': {'valid': valid, 'total': total, 'up': up, 'down': down, 'flat': flat,
                    'cap_w': round(cap_w, 2), 'arith': round(arith, 2)},
        'ind_stats': ind_stats,
        'top30': top30,
        'treemap': treemap,
    }

    return data_js

def dp_color(dp):
    # A股惯例：涨红跌绿
    if dp >= 7:  return '#7f0000'
    if dp >= 4:  return '#c62828'
    if dp >= 1:  return '#e57373'
    if dp >= 0:  return '#ef9a9a'
    if dp >= -1: return '#a5d6a7'
    if dp >= -4: return '#388e3c'
    return '#1b5e20'

def fmt_dp(dp):
    sign = '+' if dp > 0 else ''
    cls = 'up' if dp > 0.05 else ('down' if dp < -0.05 else 'neutral')
    return f'<span class="{cls}">{sign}{dp:.2f}%</span>'

def add_colors_to_tree(node):
    if 'children' in node:
        for c in node['children']:
            add_colors_to_tree(c)
        node['itemStyle'] = {'color': '#0d1117', 'borderColor': '#30363d', 'gapWidth': 2}
    else:
        node['itemStyle'] = {'color': dp_color(node['dp'])}
    return node

def write_html(data):
    import math
    stocks = data['stocks']
    totals = data['totals']
    ind_stats = data['ind_stats']
    treemap = [add_colors_to_tree(g) for g in data['treemap']]
    ind_sorted = sorted(ind_stats.items(), key=lambda x: -x[1]['avg'])

    # 子行业表：含成份股涨跌列
    ind_rows = ''
    for ind, st in ind_sorted:
        ind_stks = sorted([s for s in stocks if s['ind'] == ind], key=lambda x: -x['dp'])
        chips = ' '.join(
            f'<span style="display:inline-block;margin:1px 3px 1px 0;color:{dp_color(s["dp"])};white-space:nowrap;font-size:.78rem"><b>{s["s"]}</b> {"+" if s["dp"]>0 else ""}{s["dp"]:.1f}%</span>'
            for s in ind_stks
        )
        ind_rows += f'<tr><td style="white-space:nowrap;font-weight:600">{ind}</td><td style="white-space:nowrap">{fmt_dp(st["avg"])}</td><td style="white-space:nowrap">{st["up"]}/{st["total"]}</td><td style="line-height:1.9">{chips}</td></tr>'

    # 散点数据
    scatter_pts = [
        {'x': round(math.log10(max(s['cap'], 1)), 2), 'y': s['dp'], 'sym': s['s'], 'ind': s['ind'], 'cap': s['cap']}
        for s in stocks if s['cap'] > 0
    ]

    # 市值风格分析
    large = [s for s in stocks if s['cap'] >= 50000]
    mid   = [s for s in stocks if 5000 <= s['cap'] < 50000]
    small = [s for s in stocks if s['cap'] < 5000]
    la = round(sum(s['dp'] for s in large)/len(large), 2) if large else 0
    ma = round(sum(s['dp'] for s in mid  )/len(mid),   2) if mid   else 0
    sa = round(sum(s['dp'] for s in small)/len(small),  2) if small else 0
    if la > sa + 1:
        style_verdict = f'当日呈现<b>大市值主导</b>特征，权重股拉动显著（大盘 +{la}% > 中盘 +{ma}% > 小盘 +{sa}%）。'
    elif sa > la + 1:
        style_verdict = f'当日呈现<b>小市值弹性更强</b>特征，资金情绪积极（小盘 +{sa}% > 中盘 +{ma}% > 大盘 +{la}%）。'
    else:
        style_verdict = f'大中小市值表现相近（大盘 +{la}%，中盘 +{ma}%，小盘 +{sa}%），板块整体同步，无明显风格分化。'

    treemap_json = json.dumps(treemap, ensure_ascii=False)
    scatter_json = json.dumps(scatter_pts, ensure_ascii=False)

    # 重点个股渲染
    def render_stock_card(s):
        bull_html = ''.join(f'<li>{x}</li>' for x in s.get('bull', []))
        bear_html = ''.join(f'<li>{x}</li>' for x in s.get('bear', []))
        cat_html  = ''.join(f'<li>{x}</li>' for x in s.get('catalysts', []))
        sell_html = ''.join(f'<li><b>{a["firm"]}</b>（{a["rating"]}，{a["tp"]}）：{a["view"]}</li>' for a in s.get('sellside', []))
        col = '#e57373' if s['dp'] >= 0 else '#43a047'
        sign = '+' if s['dp'] >= 0 else ''
        return f'''<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:18px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid #30363d;padding-bottom:10px;margin-bottom:12px">
    <div>
      <span style="font-size:1.2rem;font-weight:700;color:{col}">{s["sym"]}</span>
      <span style="color:#c9d1d9;margin-left:8px;font-size:.95rem">— {s["title"]}</span>
    </div>
    <div style="font-weight:700;font-size:1.1rem;color:{col}">{sign}{s["dp"]}%</div>
  </div>
  <div style="font-size:.82rem;color:#8b949e;margin-bottom:14px">收盘 ${s["close"]} · 市值 {s["cap"]} · 成交额 {s.get("vol", "—")} · 52w {s.get("range52w", "—")}</div>

  <div style="font-size:.85rem;color:#e6edf3;font-weight:600;margin-bottom:6px">📊 基本面变化</div>
  <p style="font-size:.85rem;color:#c9d1d9;line-height:1.75;margin-bottom:14px">{s["fund"]}</p>

  <div style="font-size:.85rem;color:#e6edf3;font-weight:600;margin-bottom:6px">🏛️ 卖方观点</div>
  <ul style="font-size:.83rem;color:#c9d1d9;line-height:1.7;padding-left:18px;margin-bottom:14px">{sell_html}</ul>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
    <div style="background:#161b22;border-left:3px solid #e57373;padding:10px 12px;border-radius:4px">
      <div style="font-size:.8rem;color:#e57373;font-weight:600;margin-bottom:6px">🐂 多方逻辑</div>
      <ul style="font-size:.82rem;color:#c9d1d9;line-height:1.7;padding-left:16px">{bull_html}</ul>
    </div>
    <div style="background:#161b22;border-left:3px solid #43a047;padding:10px 12px;border-radius:4px">
      <div style="font-size:.8rem;color:#43a047;font-weight:600;margin-bottom:6px">🐻 空方担忧</div>
      <ul style="font-size:.82rem;color:#c9d1d9;line-height:1.7;padding-left:16px">{bear_html}</ul>
    </div>
  </div>

  <div style="font-size:.85rem;color:#e6edf3;font-weight:600;margin-bottom:6px">⏭️ 后续催化</div>
  <ul style="font-size:.83rem;color:#c9d1d9;line-height:1.7;padding-left:18px;margin-bottom:10px">{cat_html}</ul>

  <div style="background:#161b22;border:1px solid #30363d;border-radius:4px;padding:8px 12px;font-size:.82rem;color:#c9d1d9"><b style="color:#8b949e">📈 技术面：</b>{s["technical"]}</div>
</div>'''
    key_stocks_html = '\n'.join(render_stock_card(s) for s in KEY_STOCKS) if KEY_STOCKS else '<div style="padding:30px;text-align:center;color:#8b949e">📝 重点个股深度解读维护中…</div>'

    # === 子行业 Beta 计算（cap 加权 dp + top movers） ===
    sector_betas = {}  # sub_industry -> {dp, n, group, members: [(sym, dp, cap), ...]}
    for st in data['stocks']:
        sub = st['ind']
        sector_betas.setdefault(sub, {'group': SUB_TO_GROUP.get(sub, ''), 'members': []})
        sector_betas[sub]['members'].append((st['s'], st['dp'], st['cap']))
    for sub, info in sector_betas.items():
        members = info['members']
        total_cap = sum(c for _, _, c in members) or 1
        info['dp'] = sum(dp * c for _, dp, c in members) / total_cap
        info['n'] = len(members)
        # top movers: 按 |dp| × log(cap) 排序，取 4-6 个
        members.sort(key=lambda x: -abs(x[1]) * (x[2] ** 0.5))
        info['top_movers'] = members[:6]

    # Beta 主题解读：从 SECTOR_BETA['themes'] 渲染
    BETA_THRESHOLD = 0.8  # 板块 |cap-w dp| 低于此值视为"未形成 beta"，渲染时 ⚠️ 警告
    def render_beta_theme(t):
        is_bull = t.get('sentiment') == 'bull'
        col = '#e57373' if is_bull else '#43a047'
        # 取主题涉及板块的 cap-w dp 与 top movers
        sectors_html_parts = []
        weak_sectors = []  # cap-w |dp| < 阈值的板块（写错 / 凑数预警）
        for sub in t.get('sectors', []):
            info = sector_betas.get(sub)
            if not info: continue
            sign = '+' if info['dp'] >= 0 else ''
            mv = ' · '.join(f'<span style="color:{"#e57373" if m[1]>=0 else "#43a047"}">{m[0]} {"+" if m[1]>=0 else ""}{m[1]:.1f}%</span>' for m in info['top_movers'][:5])
            warn_chip = ''
            if abs(info['dp']) < BETA_THRESHOLD:
                weak_sectors.append(sub)
                warn_chip = f' <span style="background:#3d2a14;color:#e8c547;padding:1px 6px;border-radius:3px;font-size:.7rem;font-weight:600">⚠️ |dp|<{BETA_THRESHOLD}% 未形成 beta</span>'
            sectors_html_parts.append(f'<div style="margin-bottom:6px"><b style="color:#79c0ff">{sub}</b> <span style="color:{col};font-weight:600">{sign}{info["dp"]:.2f}%</span> <span style="color:#8b949e;font-size:.78rem">({info["n"]} 只)</span>{warn_chip}<br><span style="font-size:.82rem">{mv}</span></div>')
        sectors_block = '\n'.join(sectors_html_parts) or '<div style="color:#8b949e">板块数据缺失</div>'
        if weak_sectors:
            print(f"⚠️  Theme 警告: 「{t.get('theme', '?')[:30]}...」 涉及板块 cap-w |dp| < {BETA_THRESHOLD}%: {weak_sectors}")
        return f'''<div style="background:#0d1117;border:1px solid #30363d;border-left:4px solid {col};border-radius:6px;padding:14px 16px;margin-bottom:14px">
  <div style="font-size:1.02rem;font-weight:700;color:#e6edf3;margin-bottom:10px;line-height:1.5">{t['theme']}</div>
  <div style="background:#161b22;border-radius:4px;padding:10px 12px;margin-bottom:10px">{sectors_block}</div>
  <div style="margin-bottom:8px"><span style="color:#79c0ff;font-weight:600;font-size:.82rem">💡 共同驱动</span><p style="margin-top:4px;font-size:.85rem;line-height:1.7;color:#c9d1d9">{t['driver']}</p></div>
  <div style="margin-bottom:8px"><span style="color:#79c0ff;font-weight:600;font-size:.82rem">🔗 跨板块联动</span><p style="margin-top:4px;font-size:.85rem;line-height:1.7;color:#c9d1d9">{t['cross_sector']}</p></div>
  <div style="background:#161b22;border-radius:4px;padding:8px 12px;font-size:.82rem;color:#c9d1d9"><b style="color:#8b949e">⏱️ 时效判断：</b>{t['duration']}</div>
</div>'''

    beta_themes_html = '\n'.join(render_beta_theme(t) for t in SECTOR_BETA.get('themes', [])) if SECTOR_BETA.get('themes') else '<div style="padding:20px;text-align:center;color:#8b949e">📝 板块 Beta 解读维护中…</div>'
    tldr_html = SECTOR_BETA.get('tldr', '<i style="color:#8b949e">当日核心叙事维护中…</i>')

    # 新闻按 Tier 渲染
    tier_colors = {'tier1': '#58a6ff', 'tier2': '#e57373', 'tier3': '#ffd54f', 'tier4': '#a5d6a7'}
    news_html_parts = []
    for tier_key, tier_data in NEWS_TIERS.items():
        col = tier_colors.get(tier_key, '#8b949e')
        items_html = ''
        for it in tier_data['items']:
            items_html += f'''<div style="background:#0d1117;border:1px solid #30363d;border-left:3px solid {col};border-radius:4px;padding:10px 14px;margin-bottom:8px">
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px">
    <span style="font-weight:600;font-size:.92rem;color:#e6edf3">{it["title"]}</span>
    <span style="background:#21262d;color:{col};padding:2px 8px;border-radius:3px;font-size:.72rem;font-weight:600">{it["src"]}</span>
  </div>
  <p style="font-size:.85rem;color:#c9d1d9;line-height:1.7;margin-bottom:6px">{it["body"]}</p>
  <div style="font-size:.78rem;color:#8b949e"><b style="color:{col}">影响：</b>{it["impact"]}</div>
</div>'''
        news_html_parts.append(f'''<div style="margin-bottom:18px">
  <div style="font-size:.88rem;font-weight:700;color:{col};margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid {col}55">{tier_data["name"]}</div>
  <div style="font-size:.78rem;color:#8b949e;margin-bottom:8px">{tier_data["desc"]}</div>
  {items_html}
</div>''')
    news_html = '\n'.join(news_html_parts)

    # 行业大会日历
    from datetime import date as _date
    today = _date.fromisoformat(DATE)
    events_rows = ''
    for start, end, name, look in INDUSTRY_EVENTS:
        s = _date.fromisoformat(start)
        e = _date.fromisoformat(end)
        days = (s - today).days
        if days < -10:
            continue  # 已过 10 天前的不显示
        if days < 0:
            badge = f'<span style="color:#8b949e">已结束</span>'
        elif days == 0:
            badge = f'<span style="color:#e57373;font-weight:700">今日开幕</span>'
        elif days <= 7:
            badge = f'<span style="color:#e57373;font-weight:700">{days} 天后</span>'
        elif days <= 30:
            badge = f'<span style="color:#ef9a9a">{days} 天后</span>'
        else:
            badge = f'<span style="color:#8b949e">{days} 天后</span>'
        date_range = f'{start[5:]} ~ {end[5:]}' if start != end else start[5:]
        events_rows += f'<tr><td style="white-space:nowrap"><b>{date_range}</b></td><td><b>{name}</b></td><td style="color:#c9d1d9">{look}</td><td>{badge}</td></tr>'

    # 指数表生成
    def idx_row(t):
        code, name, close, dp, note = t
        return f'<tr><td><b>{code}</b></td><td>{name}</td><td>{close}</td><td>{fmt_dp(dp)}</td><td style="color:#8b949e;font-size:.82rem">{note}</td></tr>'
    broad_rows = ''.join(idx_row(t) for t in BROAD_INDICES)
    semi_rows = ''.join(idx_row(t) for t in SEMI_INDICES)
    gics_rows = ''.join(idx_row(t) for t in GICS_INDICES)

    # 跨行业风格自动分析
    gics_sorted = sorted(GICS_INDICES, key=lambda x: -x[3])
    top_sec = gics_sorted[0]
    bot_sec = gics_sorted[-1]
    spread = round(top_sec[3] - bot_sec[3], 2)
    risk_on = sum(1 for t in GICS_INDICES if t[3] > 0)
    risk_off = sum(1 for t in GICS_INDICES if t[3] < 0)
    sector_analysis = (
        f'今日 11 个 GICS 板块中 <b class="up">{risk_on} 涨</b> / <b class="down">{risk_off} 跌</b>，'
        f'<b>{top_sec[1]}（{top_sec[0]} {fmt_dp(top_sec[3])}）</b>领涨，'
        f'<b>{bot_sec[1]}（{bot_sec[0]} {fmt_dp(bot_sec[3])}）</b>垫底，强弱差 <b>{spread} 个点</b>。'
    )
    if top_sec[0] in ('XLK', 'XLC', 'XLY') and bot_sec[0] in ('XLP', 'XLU', 'XLV', 'XLE'):
        sector_analysis += ' 典型 <b style="color:#e57373">Risk-On</b> 风格——成长/科技领跑、防御/必选回吐，反映市场重新追逐 Beta；半导体超配（SOX +' + str(SEMI_INDICES[0][3]) + '%）跑赢 XLK 一倍以上，AI 算力链显著强于科技整体。'
    elif top_sec[0] in ('XLP', 'XLU', 'XLV') and bot_sec[0] in ('XLK', 'XLC', 'XLY'):
        sector_analysis += ' <b style="color:#388e3c">Risk-Off</b> 风格——防御板块抬升、成长股回吐，需警惕宏观/地缘风险。'
    else:
        sector_analysis += ' 板块间无明显风格分化，市场整体方向性较弱。'

    # === 市场结构 4 个比值（B 板块轮动周期） + 风格因子表（C 因子）自动算 ===
    style_rows = ''.join(idx_row(t) for t in STYLE_FACTORS)
    style_sorted = sorted(STYLE_FACTORS, key=lambda x: -x[3])
    style_winner = style_sorted[0]  # 今日领跑因子
    style_loser = style_sorted[-1]  # 今日垫底因子

    # 取关键比值（用 dict 取值容错，缺失值显示 —）
    spx_dp = next((t[3] for t in BROAD_INDICES if t[0] == 'SPX'), None)
    ndx_dp = next((t[3] for t in BROAD_INDICES if t[0] == 'NDX'), None)
    sox_dp = next((t[3] for t in SEMI_INDICES if t[0] == 'SOX'), None)
    rsp_dp = next((t[3] for t in STYLE_FACTORS if t[0] == 'RSP'), None)
    pool_dp = totals.get('cap_w')

    def safe_ratio(num, den):
        if num is None or den is None or den == 0: return None
        return num / den

    breadth_ratio = safe_ratio(rsp_dp, spx_dp)      # RSP/SPX 普涨度（>1 普涨，<0.7 窄幅）
    tech_ratio = safe_ratio(ndx_dp, spx_dp)         # NDX/SPX 科技独强度
    semi_ratio = safe_ratio(sox_dp, ndx_dp)         # SOX/NDX 半导体相对科技
    pool_ratio = safe_ratio(pool_dp, sox_dp)        # Pool/SOX 硬件池相对半导体大盘

    def kpi_card(label, num, den, ratio, num_label, den_label, interp_func):
        if ratio is None:
            return f'<div class="card"><div class="lbl">{label}</div><div class="val muted">—</div></div>'
        col = '#e57373' if ratio >= 1 else ('#43a047' if ratio < 0.5 else '#c9d1d9')
        interp = interp_func(ratio)
        n_str = f'{num:+.2f}%' if num is not None else '—'
        d_str = f'{den:+.2f}%' if den is not None else '—'
        return f'''<div class="card">
  <div class="lbl">{label}</div>
  <div style="font-size:1.4rem;font-weight:700;color:{col};margin-top:4px">{ratio:.2f}x</div>
  <div style="font-size:.72rem;color:#8b949e;margin-top:2px">{num_label} {n_str} ÷ {den_label} {d_str}</div>
  <div style="font-size:.74rem;color:#c9d1d9;margin-top:6px;padding-top:6px;border-top:1px solid #30363d">{interp}</div>
</div>'''

    breadth_kpi = kpi_card(
        '📊 普涨度 RSP/SPX', rsp_dp, spx_dp, breadth_ratio, 'RSP', 'SPX',
        lambda r: '<b>普涨</b>（等权 ≥ 大盘加权）' if r >= 1 else (
                  '<b>偏窄</b>（中小盘跟不上）' if r >= 0.7 else
                  '<b>极窄幅</b>（仅头部权重股拉指数）'),
    )
    tech_kpi = kpi_card(
        '🚀 科技强度 NDX/SPX', ndx_dp, spx_dp, tech_ratio, 'NDX', 'SPX',
        lambda r: '<b>科技独强</b>（NDX 领跑）' if r >= 1.2 else (
                  '<b>科技跟涨</b>（与大盘同步）' if r >= 0.8 else
                  '<b>科技跑输</b>（其他板块强）'),
    )
    semi_kpi = kpi_card(
        '⚡ 半导体强度 SOX/NDX', sox_dp, ndx_dp, semi_ratio, 'SOX', 'NDX',
        lambda r: '<b>半导体远超</b>（AI 算力领涨）' if r >= 2 else (
                  '<b>半导体超配</b>（强于科技整体）' if r >= 1.2 else
                  '<b>半导体跟涨</b>（与科技同节奏）' if r >= 0.8 else
                  '<b>半导体跑输</b>（板块走弱）'),
    )
    pool_kpi = kpi_card(
        '🖥️ 硬件池强度 Pool/SOX', pool_dp, sox_dp, pool_ratio, 'Pool', 'SOX',
        lambda r: '<b>硬件池跑赢 SOX</b>（中小盘强于大盘）' if r >= 1 else (
                  '<b>跟随 SOX</b>（同节奏）' if r >= 0.7 else
                  '<b>跑输 SOX</b>（半导体大盘股领涨而中小盘跟不上）'),
    )
    market_structure_kpis = breadth_kpi + tech_kpi + semi_kpi + pool_kpi
    market_structure_narrative = MARKET_STRUCTURE.get('narrative', '<i style="color:#8b949e">市场结构叙事维护中…</i>')

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股硬件板块复盘 {DATE}</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:20px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.6rem;margin-bottom:6px}}
.sub{{color:#8b949e;font-size:.88rem;margin-bottom:18px}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 14px}}
.lbl{{color:#8b949e;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}}
.val{{font-size:1.5rem;font-weight:700;margin-top:4px}}
.up{{color:#e53935}}.down{{color:#43a047}}.neutral{{color:#8b949e}}
.section{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px}}
.title{{font-size:.95rem;color:#8b949e;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th{{background:#21262d;color:#8b949e;padding:8px 10px;text-align:left;font-weight:600;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:7px 10px;border-bottom:1px solid #21262d;vertical-align:middle}}
tr:hover td{{background:#1c2128}}
.navlinks{{display:flex;gap:10px;margin-bottom:16px;font-size:.88rem}}
.navlinks a{{color:#58a6ff;text-decoration:none;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 14px}}
.navlinks a:hover{{background:#21262d}}
</style>
</head>
<body>
<h1>🖥️ 美股硬件板块每日复盘</h1>
<div class="sub">数据日期 <b>{DATE}</b> · 覆盖 {totals['total']} 只股票 · 24 个子行业 · 4 大板块</div>

<div class="navlinks">
  <a href="index.html">← 历史存档</a>
  <a href="stocks-{DATE}.html">📋 全部个股数据</a>
  <a href="calendar.html">📅 业绩日历</a>
  <a href="earnings.html">🗂️ 业绩历史</a>
</div>

<div class="stats">
  <div class="card"><div class="lbl">总数</div><div class="val">{totals['total']}</div></div>
  <div class="card"><div class="lbl">上涨</div><div class="val up">{totals['up']}</div></div>
  <div class="card"><div class="lbl">下跌</div><div class="val down">{totals['down']}</div></div>
  <div class="card"><div class="lbl">平盘</div><div class="val neutral">{totals['flat']}</div></div>
  <div class="card"><div class="lbl">市值加权均</div><div class="val {'up' if totals['cap_w']>=0 else 'down'}">{"+" if totals['cap_w']>=0 else ""}{totals['cap_w']}%</div></div>
  <div class="card"><div class="lbl">算术均</div><div class="val {'up' if totals['arith']>=0 else 'down'}">{"+" if totals['arith']>=0 else ""}{totals['arith']}%</div></div>
</div>

<div class="section">
  <div class="title">🔥 当日核心叙事</div>
  <div style="line-height:1.85;color:#c9d1d9;font-size:.92rem">{tldr_html}</div>
</div>

<div class="section">
  <div class="title">🗺️ 市值热力图（面积≈√市值 · 颜色：涨红跌绿 · 点击子行业可下钻）</div>
  <div id="treemap" style="height:620px"></div>
  <div style="margin-top:10px;font-size:.78rem;color:#8b949e">
    色阶：
    <span style="background:#1b5e20;color:#fff;padding:2px 8px;border-radius:3px">跌≥4%</span>
    <span style="background:#388e3c;color:#fff;padding:2px 8px;border-radius:3px;margin-left:4px">-4~-1%</span>
    <span style="background:#a5d6a7;color:#000;padding:2px 8px;border-radius:3px;margin-left:4px">-1~0%</span>
    <span style="background:#ef9a9a;color:#000;padding:2px 8px;border-radius:3px;margin-left:4px">0~1%</span>
    <span style="background:#e57373;color:#fff;padding:2px 8px;border-radius:3px;margin-left:4px">1~4%</span>
    <span style="background:#c62828;color:#fff;padding:2px 8px;border-radius:3px;margin-left:4px">4~7%</span>
    <span style="background:#7f0000;color:#fff;padding:2px 8px;border-radius:3px;margin-left:4px">涨≥7%</span>
  </div>
</div>

<div class="section">
  <div class="title">📊 子行业涨跌榜 · 成份股</div>
  <table><thead><tr><th>子行业</th><th>均涨跌</th><th>上涨/总数</th><th>成份股（按涨幅排序）</th></tr></thead><tbody>{ind_rows}</tbody></table>
</div>

<div class="section">
  <div class="title">💎 市值 vs 涨跌幅（X 轴：log₁₀ 市值（百万美元）· 涨红跌绿）</div>
  <div style="position:relative;height:480px"><canvas id="scatter"></canvas></div>
  <div style="margin-top:12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:.87rem;color:#c9d1d9;line-height:1.7">
    <b style="color:#e6edf3">📐 大小市值风格分析：</b>
    大市值（≥$50B，{len(large)} 只）均涨 <b class="{'up' if la>=0 else 'down'}">{"+" if la>=0 else ""}{la}%</b>，
    中市值（$5–50B，{len(mid)} 只）均涨 <b class="{'up' if ma>=0 else 'down'}">{"+" if ma>=0 else ""}{ma}%</b>，
    小市值（&lt;$5B，{len(small)} 只）均涨 <b class="{'up' if sa>=0 else 'down'}">{"+" if sa>=0 else ""}{sa}%</b>。
    {style_verdict}
  </div>
</div>

<div class="section">
  <div class="title">📌 宏观大盘 + 行业指数（GICS 11 板块 + 半导体专项）</div>

  <div style="font-size:.82rem;color:#8b949e;margin:6px 0 6px;font-weight:600">📊 宽基与宏观</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>收盘</th><th>涨跌</th><th>备注</th></tr></thead>
    <tbody>{broad_rows}</tbody>
  </table>

  <div style="font-size:.82rem;color:#8b949e;margin:14px 0 6px;font-weight:600">💎 半导体/硬件专项</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>收盘</th><th>涨跌</th><th>备注</th></tr></thead>
    <tbody>{semi_rows}</tbody>
  </table>

  <div style="font-size:.82rem;color:#8b949e;margin:14px 0 6px;font-weight:600">🌐 GICS 11 板块（SPDR Sector ETF）— 横向跨行业对比</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>收盘</th><th>涨跌</th><th>备注</th></tr></thead>
    <tbody>{gics_rows}</tbody>
  </table>

  <div style="margin-top:14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:.87rem;color:#c9d1d9;line-height:1.7">
    <b style="color:#e6edf3">🎯 跨行业风格分析：</b>
    {sector_analysis}
  </div>
</div>

<div class="section">
  <div class="title">🔄 市场结构 + 风格因子（板块轮动周期 + 5 因子领跑判断）</div>

  <div style="font-size:.82rem;color:#8b949e;margin-bottom:8px;font-weight:600">📐 4 个比值快照（自动算）</div>
  <div class="stats" style="margin-bottom:18px">
    {market_structure_kpis}
  </div>

  <div style="font-size:.82rem;color:#8b949e;margin:14px 0 6px;font-weight:600">🎨 风格因子 ETF（5 因子 + 等权基准）</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>收盘</th><th>涨跌</th><th>备注</th></tr></thead>
    <tbody>{style_rows}</tbody>
  </table>

  <div style="margin-top:14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:14px;font-size:.87rem;color:#c9d1d9;line-height:1.85">
    <b style="color:#e6edf3">💬 综合解读：</b>
    {market_structure_narrative}
  </div>
</div>

<div class="section">
  <div class="title">📊 板块 Beta 解读 · 跨子行业联动主题</div>
  <p style="font-size:.8rem;color:#8b949e;margin-bottom:12px">挑当日最有信号意义的 3-5 个板块联动主题。每个主题：涉及板块（cap-w 涨跌 + top movers）+ 共同驱动 + 跨板块联动 + 时效判断。<b style="color:#79c0ff">这里的 beta 故事比单只个股 alpha 更重要</b>。</p>
  {beta_themes_html}
</div>

<div class="section">
  <div class="title">🔍 重点个股深度解读</div>
  <div style="display:grid;grid-template-columns:1fr;gap:16px">
  {key_stocks_html}
  </div>
</div>

<div class="section">
  <div class="title">📰 产业新闻 · 按权威性分层（Tier 1-4）</div>
  {news_html}
  <div style="margin-top:14px;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;font-size:.78rem;color:#8b949e;line-height:1.7">
    <b style="color:#c9d1d9">📚 渠道说明：</b>Tier 1 宏观大盘（Bloomberg/Reuters/WSJ/CNBC/FT）；Tier 2 半导体深度（SemiAnalysis/SemiWiki/Semiconductor Engineering/EETimes/TechInsights/ServeTheHome）；Tier 3 亚洲供应链（DigiTimes/TrendForce/Nikkei Asia/日经亚洲）；Tier 4 公司公告 + 分析师评级（公司 IR / Bloomberg Analyst Estimates）。
  </div>
</div>

<div class="section">
  <div class="title">📅 30 日业绩日历（池内公司）</div>
  <table>
    <thead><tr><th>日期</th><th>代码</th><th>时段</th><th>EPS 预期</th><th>营收预期</th><th>看点</th></tr></thead>
    <tbody>
      <tr><td colspan="6" style="background:#21262d;color:#58a6ff;font-weight:700">第 1 周（4/27 – 5/1）⚡ 高优先级</td></tr>
      <tr><td>4/28 二</td><td><b>AAPL</b> ⚡</td><td>盘后</td><td>$1.65</td><td>$109.69B</td><td>iPhone Q2 出货指引</td></tr>
      <tr><td>4/29 三</td><td><b>QCOM</b> ⚡</td><td>盘后</td><td>$2.85</td><td>$11.2B</td><td>验证 INTC 边缘 AI 论调</td></tr>
      <tr><td>4/29 三</td><td>NVMI ⚡</td><td>盘后</td><td>$0.78</td><td>$191M</td><td>设备链跟踪</td></tr>
      <tr><td>4/30 四</td><td>LFUS ⚡</td><td>盘后</td><td>$2.10</td><td>$580M</td><td>—</td></tr>
      <tr><td>5/1 五</td><td><b>AMKR</b> ⚡</td><td>盘后</td><td>$0.32</td><td>$1.45B</td><td>OSAT 景气度</td></tr>
      <tr><td>5/1 五</td><td>LOGI ⚡</td><td>盘后</td><td>$1.05</td><td>$1.06B</td><td>消费电子</td></tr>
      <tr><td colspan="6" style="background:#21262d;color:#58a6ff;font-weight:700">第 2 周（5/4 – 5/8）</td></tr>
      <tr><td>5/4 一</td><td>ON</td><td>盘后</td><td>$0.55</td><td>$1.42B</td><td>SiC/汽车</td></tr>
      <tr><td>5/4 一</td><td>DIOD</td><td>盘后</td><td>$0.20</td><td>$310M</td><td>—</td></tr>
      <tr><td>5/5 二</td><td><b>AMD</b></td><td>盘后</td><td>$0.95</td><td>$7.85B</td><td>AI CPU 大考</td></tr>
      <tr><td>5/5 二</td><td>LSCC</td><td>盘后</td><td>$0.30</td><td>$130M</td><td>FPGA</td></tr>
      <tr><td>5/6 三</td><td><b>ARM</b></td><td>盘后</td><td>$0.45</td><td>$1.05B</td><td>AGI CPU 验证</td></tr>
      <tr><td>5/6 三</td><td>IONQ</td><td>盘后</td><td>-$0.42</td><td>$13M</td><td>量子叙事</td></tr>
      <tr><td>5/7 四</td><td><b>MSI</b></td><td>盘后</td><td>$3.20</td><td>$2.65B</td><td>无线通信</td></tr>
      <tr><td>5/7 四</td><td><b>MCHP</b></td><td>盘后</td><td>$0.40</td><td>$1.05B</td><td>MCU 周期</td></tr>
      <tr><td>5/8 五</td><td>UMC</td><td>盘前</td><td>—</td><td>—</td><td>晶圆代工</td></tr>
      <tr><td colspan="6" style="background:#21262d;color:#58a6ff;font-weight:700">第 3 周（5/11 – 5/15）</td></tr>
      <tr><td>5/12 二</td><td><b>TSM</b> 月营收</td><td>—</td><td>—</td><td>—</td><td>AI 算力链</td></tr>
      <tr><td>5/13 三</td><td><b>CSCO</b></td><td>盘后</td><td>$0.95</td><td>$14.0B</td><td>网络设备</td></tr>
      <tr><td>5/13 三</td><td><b>DELL</b></td><td>盘后</td><td>$1.85</td><td>$25.5B</td><td>AI 服务器</td></tr>
      <tr><td>5/14 四</td><td><b>AMAT</b></td><td>盘后</td><td>$2.35</td><td>$7.40B</td><td>设备龙头</td></tr>
      <tr><td>5/14 四</td><td>NTAP</td><td>盘后</td><td>$1.95</td><td>$1.75B</td><td>存储</td></tr>
      <tr><td colspan="6" style="background:#21262d;color:#58a6ff;font-weight:700">第 4 周（5/18 – 5/22）</td></tr>
      <tr><td>5/19 二</td><td>KEYS</td><td>盘后</td><td>$1.78</td><td>$1.34B</td><td>测试仪器</td></tr>
      <tr><td>5/20 三</td><td><b>MRVL</b></td><td>盘后</td><td>$0.65</td><td>$1.95B</td><td>AI 加速</td></tr>
      <tr><td>5/21 四</td><td><b>NVDA</b></td><td>盘后</td><td>—</td><td>—</td><td>季度顶级催化</td></tr>
      <tr><td>5/21 四</td><td>ZBRA</td><td>盘前</td><td>$4.10</td><td>$1.32B</td><td>条码识别</td></tr>
    </tbody>
  </table>
  <p style="margin-top:10px;font-size:.82rem;color:#8b949e">⚡ 标记为未来 5 个交易日内的池内业绩。共池内约 26 家公司在 30 日内披露。</p>
</div>

<div class="section">
  <div class="title">🔭 未来 5 交易日观察（4/27 – 5/1）</div>
  <table>
    <thead><tr><th style="min-width:90px">日期</th><th>池内业绩</th><th>宏观数据</th><th>行业事件 / 大会</th><th>重要产品发布</th><th>关键技术位</th></tr></thead>
    <tbody>
      <tr>
        <td><b>4/27 周一</b></td>
        <td><span style="color:#8b949e">—</span></td>
        <td>—</td>
        <td>Advantest 东京盘 Q4 业绩；ASML 中国销售更新</td>
        <td><span style="color:#8b949e">—</span></td>
        <td>SPX 7,150 / SOX 10,500 关键支撑</td>
      </tr>
      <tr>
        <td><b>4/28 周二</b></td>
        <td><b class="up">AAPL</b> 盘后<br><span style="font-size:.78rem;color:#8b949e">EPS $1.65 / Rev $109.69B</span></td>
        <td>美国 Q1 ECI（雇佣成本指数）；4 月 Conference Board 消费信心</td>
        <td>—</td>
        <td>—</td>
        <td>AAPL 跨夜波动 ±5%；NDX 25,000 心理位</td>
      </tr>
      <tr>
        <td><b>4/29 周三</b></td>
        <td><b class="up">QCOM</b> 盘后 EPS $2.85<br>NVMI 盘后</td>
        <td>ADP 4 月就业；JOLTS 3 月空缺；GDP 修订值</td>
        <td>FOMC 5/6 会议预期博弈</td>
        <td>—</td>
        <td>SOX 能否站稳 10,500（日内回调阈值）</td>
      </tr>
      <tr>
        <td><b>4/30 周四</b></td>
        <td>LFUS 盘后</td>
        <td><b style="color:#e57373">Q1 GDP 初值</b>（预期 +2.0% YoY）<br><b style="color:#e57373">3 月 PCE 物价指数</b>（Fed 通胀核心）</td>
        <td>—</td>
        <td>—</td>
        <td>10Y 利率反应：>4.4% 警戒成长股回吐</td>
      </tr>
      <tr>
        <td><b>5/1 周五</b></td>
        <td><b class="up">AMKR</b> / LOGI 盘后</td>
        <td><b style="color:#e57373">4 月非农就业 + 时薪</b>（决定 5/6 FOMC）；ISM 制造业 PMI</td>
        <td>—</td>
        <td>—</td>
        <td>SPX 10 日均线 ~7,100；SOX 18 连阳后均值回归概率上升</td>
      </tr>
    </tbody>
  </table>

  <div style="margin-top:14px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:12px;font-size:.87rem;color:#c9d1d9;line-height:1.75">
    <b style="color:#e6edf3">📋 关键事件深度提示：</b>
    <ul style="margin-top:8px;padding-left:20px">
      <li><b class="up">AAPL 4/28 财报（最大单点风险）：</b>关注 iPhone Q3 出货指引（市场期 75M 单位）、服务业务利润率（>74% 为强信号）、Vision Pro 全球扩张进度、AI 落地节奏。Q3 营收指引若 &lt; $94B 则可能拖累 NDX 1.5–2.5%。期权隐含跨夜波动 ±4.8%。</li>
      <li><b class="up">QCOM 4/29 财报（INTC 论调外溢验证）：</b>QCT 移动业务（占 65%）受益华为/小米 SoC 拉动，预期 +18% YoY；汽车业务（含 Snapdragon Cockpit）连续 4 季双位数增长。指引若上修，RF（SWKS/QRVO）/PC 链（X Elite OEM）继续接力。</li>
      <li><b style="color:#e57373">5/1 非农 + ISM PMI（宏观决定权）：</b>共识 +18.5 万人，时薪 YoY +3.6%。若超预期，5/6 FOMC 鸽派路径受阻；若疲弱（&lt;15 万人），AI 链短线再获利率松动溢价。ISM PMI &gt;50 则验证制造业回暖叙事，利好 EMS/半导体设备链。</li>
      <li><b>板块技术位整理：</b>SOX 18 连阳极端读数，RSI 78（超买）；MACD 顶背离风险显现。短期支撑 10,500（5 日均线）/ 10,000（20 日均线）；任何 -3% 单日回调即触发结构性补跌；但中线 AI capex 叙事未破。</li>
    </ul>
  </div>

  <div style="margin-top:12px;font-size:.82rem;color:#8b949e">⏰ 时间转换：美东 → 北京 +12h（夏令时）；盘前 = 北京 21:00 前；盘后 = 北京次日凌晨 04:00 起</div>
</div>

<div class="section">
  <div class="title">🎤 2026 行业大会日历（年度参考）</div>
  <table>
    <thead><tr><th>时段</th><th>大会</th><th>看点</th><th>距今</th></tr></thead>
    <tbody>{events_rows}</tbody>
  </table>
  <p style="margin-top:10px;font-size:.82rem;color:#8b949e">🎯 大会窗口前后 5 个交易日通常有 sector rotation，重点关注产品发布预期与实际差异</p>
</div>

<script>
const TREEMAP_DATA = {treemap_json};
const SCATTER = {scatter_json};
const chart = echarts.init(document.getElementById('treemap'), null, {{renderer: 'canvas'}});
chart.setOption({{
  backgroundColor: 'transparent',
  tooltip: {{
    formatter: function(p) {{
      const d = p.data;
      if (d.dp !== undefined) {{
        const sign = d.dp > 0 ? '+' : '';
        return `<b>${{d.name}}</b> <span style="color:#8b949e">[${{d.ind}}]</span><br/>` +
               `涨跌: <b style="color:${{d.dp>0?'#3fb950':'#f85149'}}">${{sign}}${{d.dp}}%</b><br/>` +
               `收盘: $${{d.close}}<br/>市值: $${{(d.cap/1000).toFixed(1)}}B`;
      }}
      return `<b>${{d.name}}</b>`;
    }}
  }},
  series: [{{
    type: 'treemap',
    data: TREEMAP_DATA,
    width: '100%', height: '100%',
    roam: false, nodeClick: 'zoomToNode',
    breadcrumb: {{show: true, top: 5, left: 5, itemStyle: {{color: '#21262d', borderColor: '#30363d', textStyle: {{color: '#e6edf3'}}}}}},
    label: {{
      show: true, fontSize: 10, color: '#0d1117', fontWeight: 'bold',
      formatter: function(p) {{
        if (p.data.dp !== undefined) {{
          const sign = p.data.dp > 0 ? '+' : '';
          return `{{a|${{p.name}}}}\\n{{b|${{sign}}${{p.data.dp}}%}}`;
        }}
        return p.name;
      }},
      rich: {{
        a: {{fontSize: 11, fontWeight: 'bold', color: '#0d1117'}},
        b: {{fontSize: 9, color: '#0d1117'}}
      }}
    }},
    upperLabel: {{show: true, height: 22, color: '#fff', fontSize: 12, fontWeight: 'bold', backgroundColor: '#21262d', padding: [4, 8]}},
    itemStyle: {{borderWidth: 1, borderColor: '#0d1117', gapWidth: 1}},
    levels: [
      {{itemStyle: {{borderWidth: 3, borderColor: '#0d1117', gapWidth: 3}}, upperLabel: {{height: 24}}}},
      {{itemStyle: {{borderWidth: 2, borderColor: '#21262d', gapWidth: 2}}, upperLabel: {{height: 20, backgroundColor: '#161b22'}}}},
      {{itemStyle: {{borderWidth: 1, borderColor: '#0d1117', gapWidth: 1}}}}
    ]
  }}]
}});
window.addEventListener('resize', () => chart.resize());

// 散点图
function dpColorJs(dp) {{
  if (dp >= 7)  return '#7f0000';
  if (dp >= 4)  return '#c62828';
  if (dp >= 1)  return '#e57373cc';
  if (dp >= 0)  return '#ef9a9acc';
  if (dp >= -1) return '#a5d6a7cc';
  if (dp >= -4) return '#388e3ccc';
  return '#1b5e20';
}}
new Chart(document.getElementById('scatter'), {{
  type: 'scatter',
  data: {{
    datasets: [{{
      data: SCATTER.map(p => ({{x: p.x, y: p.y, sym: p.sym, ind: p.ind, cap: p.cap}})),
      backgroundColor: SCATTER.map(p => dpColorJs(p.y)),
      pointRadius: 4, pointHoverRadius: 7
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{
      legend: {{display: false}},
      tooltip: {{
        callbacks: {{
          label: (ctx) => {{
            const p = ctx.raw;
            return `${{p.sym}} [${{p.ind}}]  ${{p.y > 0 ? '+' : ''}}${{p.y}}%  市值 $${{(p.cap/1000).toFixed(1)}}B`;
          }}
        }},
        backgroundColor: '#21262d', titleColor: '#e6edf3', bodyColor: '#e6edf3'
      }}
    }},
    scales: {{
      x: {{
        title: {{display: true, text: 'log₁₀(市值，百万USD)', color: '#8b949e'}},
        grid: {{color: '#21262d'}}, ticks: {{color: '#8b949e'}}
      }},
      y: {{
        title: {{display: true, text: '涨跌幅 %', color: '#8b949e'}},
        grid: {{color: '#21262d'}}, ticks: {{color: '#8b949e', callback: v => v + '%'}}
      }}
    }}
  }}
}});
</script>

<div class="sub" style="margin-top:20px">数据来源：Finnhub /quote + WebSearch 公开市场数据交叉核对 · 大中盘股为确认值，微盘部分基于子行业均值估算</div>
</body>
</html>'''

    out = os.path.join(REPO_DIR, f'{DATE}.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"{DATE}.html written, {len(html)} bytes")

def write_stocks_page(stocks, date):
    all_stocks = sorted(stocks, key=lambda x: -x['dp'])
    rows = ''
    for i, s in enumerate(all_stocks):
        cap_str = f'${s["cap"]/1000:.1f}B' if s['cap'] >= 1000 else f'${s["cap"]}M'
        rows += f'<tr><td>{i+1}</td><td><b>{s["s"]}</b></td><td>{s["grp"]}</td><td>{s["ind"]}</td><td>${s["c"]:.2f}</td><td>{fmt_dp(s["dp"])}</td><td>${s["h"]:.2f}</td><td>${s["l"]:.2f}</td><td>${s["pc"]:.2f}</td><td>{cap_str}</td></tr>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>全部个股 {date}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:20px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.3rem;margin-bottom:6px}}
.sub{{color:#8b949e;font-size:.88rem;margin-bottom:14px}}
.navlinks{{display:flex;gap:10px;margin-bottom:14px;font-size:.88rem}}
.navlinks a{{color:#58a6ff;text-decoration:none;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 14px}}
.up{{color:#e53935}}.down{{color:#43a047}}.neutral{{color:#8b949e}}
table{{width:100%;border-collapse:collapse;font-size:.82rem}}
th{{background:#21262d;color:#8b949e;padding:8px 10px;text-align:left;font-weight:600;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;position:sticky;top:0;z-index:1}}
td{{padding:6px 10px;border-bottom:1px solid #161b22}}
tr:hover td{{background:#161b22}}
input{{background:#161b22;border:1px solid #30363d;border-radius:6px;color:#e6edf3;padding:8px 12px;font-size:.88rem;width:260px;margin-bottom:12px}}
input::placeholder{{color:#8b949e}}
</style>
</head>
<body>
<h1>📋 全部个股数据 — {date}</h1>
<div class="sub">共 {len(all_stocks)} 只 · 按涨跌幅降序排列</div>
<div class="navlinks">
  <a href="{date}.html">← 当日复盘</a>
  <a href="index.html">📁 历史存档</a>
  <a href="calendar.html">📅 业绩日历</a>
  <a href="earnings.html">🗂️ 业绩历史</a>
</div>
<input type="text" id="filter" placeholder="筛选代码/行业..." oninput="filterTable()">
<table id="tbl">
  <thead><tr><th>#</th><th>代码</th><th>大类</th><th>子行业</th><th>收盘</th><th>涨跌</th><th>最高</th><th>最低</th><th>昨收</th><th>市值</th></tr></thead>
  <tbody>{rows}</tbody>
</table>
<script>
function filterTable() {{
  const q = document.getElementById('filter').value.toLowerCase();
  document.querySelectorAll('#tbl tbody tr').forEach(tr => {{
    tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}
</script>
</body>
</html>'''
    out = os.path.join(REPO_DIR, f'stocks-{date}.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"stocks-{date}.html written, {len(all_stocks)} stocks")

def update_meta(totals):
    meta_path = os.path.join(REPO_DIR, '_meta.json')
    if os.path.exists(meta_path):
        with open(meta_path, encoding='utf-8') as f:
            meta = json.load(f)
    else:
        meta = {}
    meta[DATE] = {
        'up': totals['up'], 'down': totals['down'],
        'flat': totals['flat'], 'total': totals['total'],
        'cap_w': totals['cap_w'], 'arith': totals['arith'],
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta

def write_index(meta):
    dates = sorted(meta.keys(), reverse=True)
    rows = ''
    for d in dates:
        m = meta[d]
        sign = '+' if m['cap_w'] > 0 else ''
        color = '#e53935' if m['cap_w'] > 0 else '#43a047'
        rows += f'''<tr>
          <td><a href="{d}.html" style="color:#58a6ff;text-decoration:none;font-weight:600">{d}</a></td>
          <td style="color:{color};font-weight:700">{sign}{m["cap_w"]}%</td>
          <td style="color:#e53935">{m["up"]}</td>
          <td style="color:#43a047">{m["down"]}</td>
          <td style="color:#8b949e">{m["flat"]}</td>
          <td style="color:#8b949e">{m["total"]}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股硬件板块复盘 — 历史存档</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;padding:40px 20px;max-width:800px;margin:0 auto}}
h1{{font-size:1.5rem;margin-bottom:6px}}
.sub{{color:#8b949e;font-size:.88rem;margin-bottom:28px}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th{{background:#21262d;color:#8b949e;padding:10px 14px;text-align:left;font-weight:600;font-size:.75rem;text-transform:uppercase;letter-spacing:.05em}}
td{{padding:12px 14px;border-bottom:1px solid #21262d}}
tr:hover td{{background:#161b22}}
.badge{{display:inline-block;background:#161b22;border:1px solid #30363d;border-radius:4px;padding:2px 8px;font-size:.75rem;color:#8b949e}}
</style>
</head>
<body>
<h1>🖥️ 美股硬件板块复盘 — 历史存档</h1>
<div class="sub">覆盖 314 只股票 · 24 个子行业 · 4 大板块 · 点击日期查看当日完整复盘</div>
<div style="margin-bottom:18px;display:flex;gap:10px;flex-wrap:wrap"><a href="calendar.html" style="display:inline-block;background:#1f6feb;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:.88rem;font-weight:600">📅 业绩日历（FMP 实时）</a><a href="earnings.html" style="display:inline-block;background:#8957e5;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:.88rem;font-weight:600">🗂️ 业绩历史（25 年回填 + 持续更新）</a></div>
<table>
  <thead>
    <tr><th>日期</th><th>市值加权均</th><th>上涨</th><th>下跌</th><th>平盘</th><th>总数</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<div style="margin-top:20px;color:#8b949e;font-size:.82rem">数据来源：Finnhub /quote + WebSearch 公开市场数据交叉核对</div>
</body>
</html>'''
    with open(os.path.join(REPO_DIR, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"index.html updated, {len(dates)} dates listed")

def write_calendar_page():
    """生成 calendar.html — 加载 earnings_history.json + company_profiles.json，
    点击日期格弹出当天所有公司的业绩 + 公司简介 + 行业。"""
    pool_pairs = []
    for ind, syms in INDUSTRY_MAP.items():
        grp = SUB_TO_GROUP[ind]
        for sym in syms:
            pool_pairs.append(f'"{sym}":["{ind}","{grp}"]')
    pool_js = '{' + ','.join(pool_pairs) + '}'
    total_n = sum(len(v) for v in INDUSTRY_MAP.values())

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股硬件板块 · 业绩日历</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;padding:24px 16px;max-width:1280px;margin:0 auto}}
h1{{font-size:1.45rem;margin-bottom:4px}}
.sub{{color:#8b949e;font-size:.85rem;margin-bottom:18px}}
.bar{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;padding:12px;background:#161b22;border:1px solid #21262d;border-radius:8px}}
.bar .lbl{{color:#8b949e;font-size:.78rem;margin-right:4px}}
.btn{{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:6px 12px;border-radius:6px;font-size:.82rem;cursor:pointer}}
.btn:hover{{background:#30363d}}
.btn.act{{background:#1f6feb;border-color:#1f6feb;color:#fff}}
.legend{{margin-left:auto;display:flex;gap:14px;font-size:.78rem;color:#8b949e}}
.legend span::before{{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:middle}}
.lg-bmo::before{{background:#1f6feb}}
.lg-amc::before{{background:#f59e0b}}
.lg-dmh::before{{background:#8b949e}}
#status{{color:#8b949e;font-size:.85rem;padding:10px 0}}
#status.err{{color:#f85149}}
.grid{{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}}
.dh{{padding:8px;text-align:center;font-size:.72rem;color:#8b949e;text-transform:uppercase;letter-spacing:.05em}}
.dh.we{{color:#484f58}}
.cell{{background:#161b22;border:1px solid #21262d;border-radius:6px;min-height:110px;padding:8px;display:flex;flex-direction:column;gap:4px}}
.cell.we{{background:#0d1117;opacity:.5}}
.cell.tdy{{border-color:#1f6feb;border-width:2px}}
.cell.past{{opacity:.55}}
.cell .dn{{font-size:.78rem;color:#8b949e;display:flex;justify-content:space-between;align-items:center;margin-bottom:2px}}
.cell.tdy .dn{{color:#58a6ff;font-weight:700}}
.cell .cnt{{background:#21262d;color:#8b949e;font-size:.66rem;padding:0 5px;border-radius:8px}}
.tk{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:.7rem;font-weight:600;color:#fff;cursor:pointer;text-decoration:none}}
.tk.bmo{{background:#1f6feb}}
.tk.amc{{background:#f59e0b;color:#1a1a1a}}
.tk.dmh{{background:#8b949e}}
.tk:hover{{outline:1px solid #fff}}
.list{{display:none;background:#161b22;border:1px solid #21262d;border-radius:8px;overflow:hidden}}
.list table{{width:100%;border-collapse:collapse;font-size:.85rem}}
.list th{{background:#21262d;color:#8b949e;padding:9px 12px;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600}}
.list td{{padding:10px 12px;border-bottom:1px solid #21262d}}
.list tr:hover td{{background:#1c2128}}
.list .dh-row td{{background:#0d1117;font-weight:600;color:#58a6ff;font-size:.82rem}}
.beat{{color:#3fb950}}
.miss{{color:#f85149}}
.muted{{color:#8b949e}}
.foot{{margin-top:18px;padding:12px;background:#161b22;border:1px solid #21262d;border-radius:8px;font-size:.78rem;color:#8b949e;line-height:1.7}}
.foot a{{color:#58a6ff;text-decoration:none}}
.foot code{{background:#0d1117;padding:1px 5px;border-radius:3px}}
.nav{{display:flex;gap:6px;margin-left:auto}}
.cell.has{{cursor:pointer;transition:transform .1s,border-color .1s}}
.cell.has:hover{{border-color:#1f6feb;transform:translateY(-1px)}}
.overlay{{position:fixed;inset:0;background:rgba(0,0,0,.75);display:none;align-items:flex-start;justify-content:center;z-index:100;overflow-y:auto;padding:30px 14px}}
.overlay.show{{display:flex}}
.dialog{{background:#0d1117;border:1px solid #30363d;border-radius:10px;width:100%;max-width:880px;box-shadow:0 16px 48px rgba(0,0,0,.6)}}
.dlg-head{{position:sticky;top:0;background:#161b22;border-bottom:1px solid #30363d;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;border-radius:10px 10px 0 0;z-index:1}}
.dlg-head h2{{font-size:1.1rem;color:#e6edf3}}
.dlg-head .sub{{font-size:.78rem;color:#8b949e;margin-top:3px;margin-bottom:0}}
.dlg-close{{background:#21262d;border:1px solid #30363d;color:#e6edf3;width:32px;height:32px;border-radius:6px;cursor:pointer;font-size:1.1rem;line-height:1}}
.dlg-close:hover{{background:#f85149;border-color:#f85149}}
.dlg-body{{padding:14px 18px 20px;display:flex;flex-direction:column;gap:14px}}
.ec{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px 16px}}
.ec-head{{display:flex;align-items:flex-start;gap:12px;margin-bottom:10px}}
.ec-head img{{width:40px;height:40px;border-radius:6px;background:#0d1117;object-fit:contain;flex-shrink:0}}
.ec-head .ti{{flex:1;min-width:0}}
.ec-head .sym{{font-size:1.05rem;font-weight:700;color:#e6edf3}}
.ec-head .sym a{{color:#58a6ff;text-decoration:none}}
.ec-head .sym a:hover{{text-decoration:underline}}
.ec-head .ind{{font-size:.78rem;color:#8b949e;margin-top:2px}}
.ec-head .ind b{{color:#79c0ff;font-weight:600}}
.ec-head .timing{{font-size:.78rem;font-weight:700;padding:5px 10px;border-radius:5px;flex-shrink:0;align-self:flex-start}}
.ec-head .timing.bmo{{background:#1f6feb;color:#fff}}
.ec-head .timing.amc{{background:#f59e0b;color:#1a1a1a}}
.ec-head .timing.dmh{{background:#30363d;color:#8b949e}}
.ec-eps{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px 18px;margin-bottom:10px;font-size:.82rem}}
.ec-eps .lbl{{color:#8b949e;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em}}
.ec-eps .v{{color:#e6edf3;font-weight:600;font-size:.95rem}}
.ec-eps .beat{{color:#3fb950}}
.ec-eps .miss{{color:#f85149}}
.ec-section{{margin-bottom:10px}}
.ec-stitle{{font-size:.78rem;color:#79c0ff;font-weight:600;margin-bottom:4px;text-transform:none;letter-spacing:0}}
.ec-stitle.thesis{{color:#3fb950}}
.ec-desc{{color:#c9d1d9;font-size:.85rem;line-height:1.7;white-space:pre-wrap}}
.ec-desc.muted{{color:#8b949e;font-style:italic}}
.ec-foot{{display:flex;flex-wrap:wrap;gap:14px;font-size:.75rem;color:#8b949e;padding-top:8px;border-top:1px solid #21262d}}
.ec-foot a{{color:#58a6ff;text-decoration:none}}
.ec-foot a:hover{{text-decoration:underline}}
.ec-foot span{{display:inline-flex;align-items:center;gap:4px}}
@media(max-width:760px){{
  .grid{{grid-template-columns:repeat(7,1fr);gap:3px}}
  .cell{{min-height:80px;padding:5px}}
  .tk{{font-size:.62rem;padding:1px 3px}}
  .legend{{width:100%;margin-left:0;margin-top:6px}}
  .dialog{{margin:0}}
  .ec-head img{{width:32px;height:32px}}
}}
</style>
</head>
<body>
<h1>📅 美股硬件板块 · 业绩日历</h1>
<div class="sub"><a href="index.html" style="color:#58a6ff;text-decoration:none">← 返回历史存档</a> · <a href="earnings.html" style="color:#58a6ff;text-decoration:none">🗂️ 业绩历史（25 年回填）</a> · 数据源 FMP · 池内 {total_n} 只股票 · <b style="color:#58a6ff">点击有数据的日期格 → 弹出公司业绩 + 简介</b></div>

<div class="bar">
  <span class="lbl">大类：</span>
  <button class="btn grp act" data-g="">全部</button>
  <button class="btn grp" data-g="半导体核心">半导体核心</button>
  <button class="btn grp" data-g="硬件系统">硬件系统</button>
  <button class="btn grp" data-g="元器件制造">元器件制造</button>
  <button class="btn grp" data-g="分销渠道">分销渠道</button>
  <span class="lbl" style="margin-left:14px">视图：</span>
  <button class="btn vw act" data-v="cal">日历</button>
  <button class="btn vw" data-v="lst">列表</button>
  <div class="nav">
    <button class="btn" id="prev">← 上月</button>
    <button class="btn" id="cur">今日</button>
    <button class="btn" id="next">下月 →</button>
  </div>
  <div class="legend">
    <span class="lg-bmo">BMO 盘前</span>
    <span class="lg-amc">AMC 盘后</span>
    <span class="lg-dmh">DMH/未知</span>
  </div>
</div>

<div id="status">⏳ 正在加载 earnings_history.json…</div>
<div id="cal" class="grid" style="display:none"></div>
<div id="lst" class="list"></div>

<div id="modal" class="overlay">
  <div class="dialog">
    <div class="dlg-head">
      <div>
        <h2 id="dlg-title">日期</h2>
        <div class="sub" id="dlg-sub"></div>
      </div>
      <button class="dlg-close" id="dlg-close">×</button>
    </div>
    <div class="dlg-body" id="dlg-body"></div>
  </div>
</div>

<div class="foot">
<b>说明</b>：业绩日历从仓库内 <code>earnings_history.json</code>（每天 GitHub Actions 自动增量）渲染，相比直连 FMP <code>earnings-calendar</code> 端点覆盖更全（per-symbol 端点能拿到 calendar 端点漏掉的记录，例如 NXPI 4/28）。颜色：<b style="color:#1f6feb">BMO 盘前</b> / <b style="color:#f59e0b">AMC 盘后</b> / <span class="muted">DMH 盘中或未知（多数历史/远期数据无该字段）</span>。**点击有数据的日期格** 弹出当天所有公司业绩 + 公司简介（来自 <code>company_profiles.json</code>）。
</div>

<script>
const POOL = {pool_js};
const POOL_SET = new Set(Object.keys(POOL));
let HISTORY = {{}};       // sym -> [records]
let PROFILES = {{}};      // sym -> profile
let BRIEFS = {{}};        // "SYM_DATE" -> {{summary_cn, thesis_cn, ...}}
let CAPS = {{}};          // sym -> market cap ($M) 用于模态框排序
let BY_DATE = {{}};       // "2026-04-29" -> [{{symbol, time, eps, ...}}, ...]
let cur = new Date();
cur.setDate(1);
let groupFilter = "";
let view = "cal";

const $ = s => document.querySelector(s);
const fmt = d => d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0");
const cn = ["日","一","二","三","四","五","六"];

function tkClass(t) {{
  t = (t||"").toLowerCase();
  if (t==="bmo") return "bmo";
  if (t==="amc") return "amc";
  return "dmh";
}}
function epsFmt(v) {{ return (v===null||v===undefined||v==="") ? "—" : Number(v).toFixed(2); }}
function revFmt(v) {{
  if (v==null||v===0||v==="") return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return (v/1e12).toFixed(2)+"T";
  if (a >= 1e9) return (v/1e9).toFixed(2)+"B";
  if (a >= 1e6) return (v/1e6).toFixed(1)+"M";
  return v.toLocaleString();
}}
function surprise(act, est) {{
  if (act==null||est==null||est===0) return null;
  return ((act-est)/Math.abs(est)*100);
}}
function escapeHTML(s) {{
  return String(s||"").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}})[c]);
}}

function buildIndex() {{
  BY_DATE = {{}};
  for (const sym in HISTORY) {{
    if (!POOL_SET.has(sym)) continue;
    for (const r of HISTORY[sym]) {{
      if (!r.date) continue;
      (BY_DATE[r.date] = BY_DATE[r.date] || []).push({{
        symbol: sym, date: r.date, time: r.time, eps: r.eps, epsEstimated: r.epsEstimated,
        revenue: r.revenue, revenueEstimated: r.revenueEstimated,
      }});
    }}
  }}
}}

function renderCal() {{
  const y = cur.getFullYear(), m = cur.getMonth();
  const first = new Date(y, m, 1);
  const lastD = new Date(y, m+1, 0).getDate();
  const startDow = first.getDay();
  const today = new Date(); today.setHours(0,0,0,0);

  let monthHits = 0;
  let html = "";
  for (let i=0;i<7;i++) html += `<div class="dh ${{i===0||i===6?"we":""}}">${{cn[i]}}</div>`;
  for (let i=0;i<startDow;i++) html += `<div class="cell we"></div>`;
  for (let d=1;d<=lastD;d++) {{
    const dt = new Date(y, m, d);
    const ds = fmt(dt);
    const dow = dt.getDay();
    const we = dow===0||dow===6;
    const isTdy = dt.getTime() === today.getTime();
    const isPast = dt < today && !isTdy;
    const allEvs = BY_DATE[ds] || [];
    const evs = groupFilter
      ? allEvs.filter(e => POOL[e.symbol] && POOL[e.symbol][1] === groupFilter)
      : allEvs;
    evs.sort((a,b) => {{
      const o = {{bmo:0,dmh:1,amc:2}};
      return (o[(a.time||"").toLowerCase()]||1) - (o[(b.time||"").toLowerCase()]||1);
    }});
    monthHits += evs.length;
    let cls = "cell";
    if (we) cls += " we";
    if (isTdy) cls += " tdy";
    else if (isPast) cls += " past";
    if (evs.length) cls += " has";
    const badges = evs.map(e => `<span class="tk ${{tkClass(e.time)}}">${{e.symbol}}</span>`).join(" ");
    const cnt = evs.length ? `<span class="cnt">${{evs.length}}</span>` : "";
    const dataAttr = evs.length ? ` data-date="${{ds}}"` : "";
    html += `<div class="${{cls}}"${{dataAttr}}><div class="dn"><span>${{d}}</span>${{cnt}}</div><div>${{badges}}</div></div>`;
  }}
  $("#cal").innerHTML = html;
  document.querySelectorAll(".cell.has").forEach(el => {{
    el.onclick = () => openDay(el.dataset.date);
  }});
  return monthHits;
}}

function renderList() {{
  const y = cur.getFullYear(), m = cur.getMonth();
  const monthStart = fmt(new Date(y, m, 1));
  const monthEnd = fmt(new Date(y, m+1, 0));
  const items = [];
  for (const date in BY_DATE) {{
    if (date < monthStart || date > monthEnd) continue;
    for (const e of BY_DATE[date]) {{
      if (groupFilter && (!POOL[e.symbol] || POOL[e.symbol][1] !== groupFilter)) continue;
      items.push({{date, ...e}});
    }}
  }}
  items.sort((a,b) => a.date.localeCompare(b.date) || a.symbol.localeCompare(b.symbol));
  const byDate = {{}};
  items.forEach(e => (byDate[e.date]=byDate[e.date]||[]).push(e));
  const today = fmt(new Date());
  let rows = "";
  Object.keys(byDate).sort().forEach(d => {{
    const dow = cn[new Date(d+"T00:00:00").getDay()];
    const tag = d===today ? " · 今日" : "";
    rows += `<tr class="dh-row"><td colspan="7" style="cursor:pointer" onclick="openDay('${{d}}')">${{d}} 周${{dow}} · ${{byDate[d].length}} 家${{tag}} · 点击展开</td></tr>`;
    byDate[d].forEach(e => {{
      const meta = POOL[e.symbol]||[];
      const s = surprise(e.eps, e.epsEstimated);
      const sCls = s==null?"muted":(s>=0?"beat":"miss");
      const sStr = s==null?"—":(s>=0?"+":"")+s.toFixed(1)+"%";
      const t = (e.time||"").toLowerCase();
      const tStr = t==="bmo"?"<span style=\\"color:#58a6ff\\">BMO</span>":t==="amc"?"<span style=\\"color:#f59e0b\\">AMC</span>":"<span class=muted>—</span>";
      rows += `<tr><td><b>${{e.symbol}}</b></td><td class="muted">${{meta[0]||""}}</td><td>${{tStr}}</td><td>${{epsFmt(e.epsEstimated)}}</td><td>${{epsFmt(e.eps)}}</td><td class="${{sCls}}">${{sStr}}</td><td class="muted">${{revFmt(e.revenueEstimated)}}</td></tr>`;
    }});
  }});
  if (!rows) rows = `<tr><td colspan="7" style="text-align:center;padding:30px;color:#8b949e">本月无池内公司业绩</td></tr>`;
  $("#lst").innerHTML = `<table><thead><tr><th>代码</th><th>子行业</th><th>时点</th><th>EPS 预期</th><th>EPS 实际</th><th>超预期</th><th>营收预期</th></tr></thead><tbody>${{rows}}</tbody></table>`;
}}

function openDay(date) {{
  const events = BY_DATE[date] || [];
  const evs = groupFilter
    ? events.filter(e => POOL[e.symbol] && POOL[e.symbol][1] === groupFilter)
    : events;
  // 按市值降序排（CAPS 单位 $M, 缺失视为 0 排到底）;
  // 市值相同时再按 BMO/DMH/AMC 时点 + ticker 字母排序兜底
  evs.sort((a,b) => {{
    const ca = CAPS[a.symbol] || 0, cb = CAPS[b.symbol] || 0;
    if (cb !== ca) return cb - ca;
    const o = {{bmo:0,dmh:1,amc:2}};
    const ta = o[(a.time||"").toLowerCase()] ?? 1;
    const tb = o[(b.time||"").toLowerCase()] ?? 1;
    if (ta !== tb) return ta - tb;
    return a.symbol.localeCompare(b.symbol);
  }});
  const dow = cn[new Date(date+"T00:00:00").getDay()];
  $("#dlg-title").textContent = `📅 ${{date}} 周${{dow}} · ${{evs.length}} 家硬件公司业绩`;
  $("#dlg-sub").textContent = groupFilter ? `仅显示「${{groupFilter}}」大类` : "全部 4 大板块";
  $("#dlg-body").innerHTML = evs.map(e => renderCard(e)).join("");
  $("#modal").classList.add("show");
  document.body.style.overflow = "hidden";
}}

function renderCard(e) {{
  const meta = POOL[e.symbol] || ["",""];
  const ind = meta[0], grp = meta[1];
  const t = (e.time||"").toLowerCase();
  const timing = t==="bmo" ? '<span class="timing bmo">BMO 盘前</span>'
    : t==="amc" ? '<span class="timing amc">AMC 盘后</span>'
    : '<span class="timing dmh">时点未知</span>';
  const s = surprise(e.eps, e.epsEstimated);
  const sCls = s==null ? "" : (s>=0?"beat":"miss");
  const sStr = s==null ? "—" : (s>=0?"+":"")+s.toFixed(1)+"%";

  const p = PROFILES[e.symbol] || {{}};
  const b = BRIEFS[e.symbol + "_" + (e.date || "")] || BRIEFS[e.symbol] || {{}};
  const name = p.name ? escapeHTML(p.name) : e.symbol;

  // 公司简介: 优先中文 brief, fallback FMP 英文 description
  let descHTML = "";
  if (b.summary_cn) {{
    descHTML = `<div class="ec-section"><div class="ec-stitle">📋 公司简介</div><div class="ec-desc">${{escapeHTML(b.summary_cn)}}</div></div>`;
  }} else if (p.description) {{
    descHTML = `<div class="ec-section"><div class="ec-stitle">📋 公司简介 <span class="muted" style="font-weight:400">（FMP 英文）</span></div><div class="ec-desc">${{escapeHTML(p.description)}}</div></div>`;
  }} else {{
    descHTML = `<div class="ec-section"><div class="ec-desc muted">暂无公司简介（待 fetch_earnings_history.py --profiles 拉取）。</div></div>`;
  }}

  // 投资看点: 仅在有 brief.thesis_cn 时显示
  let thesisHTML = "";
  if (b.thesis_cn) {{
    thesisHTML = `<div class="ec-section"><div class="ec-stitle thesis">📊 本季投资看点</div><div class="ec-desc">${{escapeHTML(b.thesis_cn)}}</div></div>`;
  }}

  const img = p.image
    ? `<img src="${{escapeHTML(p.image)}}" alt="${{escapeHTML(e.symbol)}}" onerror="this.style.display='none'">`
    : `<img src="data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2240%22 height=%2240%22><rect width=%2240%22 height=%2240%22 fill=%22%231c2128%22/></svg>" alt="">`;

  const footParts = [];
  if (p.sector) footParts.push(`<span>🏢 ${{escapeHTML(p.sector)}}${{p.industry?` · ${{escapeHTML(p.industry)}}`:""}}</span>`);
  if (p.country) footParts.push(`<span>🌍 ${{escapeHTML(p.country)}}</span>`);
  if (p.exchange) footParts.push(`<span>📊 ${{escapeHTML(p.exchange)}}</span>`);
  if (p.fullTimeEmployees) footParts.push(`<span>👥 ${{Number(p.fullTimeEmployees).toLocaleString()}} 员工</span>`);
  if (p.ipoDate) footParts.push(`<span>📅 IPO ${{escapeHTML(p.ipoDate)}}</span>`);
  if (p.ceo) footParts.push(`<span>👤 ${{escapeHTML(p.ceo)}}</span>`);
  if (p.website) footParts.push(`<a href="${{escapeHTML(p.website)}}" target="_blank" rel="noopener">🔗 官网</a>`);
  footParts.push(`<a href="https://finance.yahoo.com/quote/${{encodeURIComponent(e.symbol)}}" target="_blank" rel="noopener">📈 Yahoo</a>`);
  footParts.push(`<a href="earnings.html#${{encodeURIComponent(e.symbol)}}" target="_blank">🗂️ 全部历史</a>`);

  return `<div class="ec">
    <div class="ec-head">
      ${{img}}
      <div class="ti">
        <div class="sym"><a href="https://finance.yahoo.com/quote/${{encodeURIComponent(e.symbol)}}" target="_blank" rel="noopener">${{escapeHTML(e.symbol)}}</a> · ${{name}}</div>
        <div class="ind">中文行业 <b>${{escapeHTML(ind)}}</b> / <b>${{escapeHTML(grp)}}</b></div>
      </div>
      ${{timing}}
    </div>
    <div class="ec-eps">
      <div><div class="lbl">EPS 预期</div><div class="v">${{epsFmt(e.epsEstimated)}}</div></div>
      <div><div class="lbl">EPS 实际</div><div class="v">${{epsFmt(e.eps)}}</div></div>
      <div><div class="lbl">超预期</div><div class="v ${{sCls}}">${{sStr}}</div></div>
      <div><div class="lbl">营收预期</div><div class="v">${{revFmt(e.revenueEstimated)}}</div></div>
      <div><div class="lbl">营收实际</div><div class="v">${{revFmt(e.revenue)}}</div></div>
    </div>
    ${{thesisHTML}}
    ${{descHTML}}
    <div class="ec-foot">${{footParts.join("")}}</div>
  </div>`;
}}

function closeDialog() {{
  $("#modal").classList.remove("show");
  document.body.style.overflow = "";
}}

async function load() {{
  $("#status").className = "";
  try {{
    if (!Object.keys(HISTORY).length) {{
      const r = await fetch("earnings_history.json", {{cache: "no-cache"}});
      if (!r.ok) throw new Error("earnings_history.json HTTP "+r.status);
      HISTORY = await r.json();
      buildIndex();
      // 异步加载 profiles + briefs + 当日 confirmed (用于市值排序)，失败也不阻塞渲染
      fetch("company_profiles.json", {{cache: "no-cache"}})
        .then(r => r.ok ? r.json() : {{}})
        .then(p => {{ PROFILES = p; }})
        .catch(() => {{}});
      fetch("earnings_briefs.json", {{cache: "no-cache"}})
        .then(r => r.ok ? r.json() : {{}})
        .then(b => {{ BRIEFS = b; }})
        .catch(() => {{}});
      fetch("confirmed_{DATE}.json", {{cache: "no-cache"}})
        .then(r => r.ok ? r.json() : null)
        .then(j => {{
          if (j && j.data) {{
            for (const sym in j.data) {{ CAPS[sym] = j.data[sym].cap || 0; }}
          }}
        }})
        .catch(() => {{}});
    }}
    const monthHits = renderCal();
    renderList();
    const y = cur.getFullYear(), m = cur.getMonth();
    const monthStr = `${{y}}-${{String(m+1).padStart(2,"0")}}`;
    $("#status").textContent = `✅ ${{monthStr}} · 池内命中 ${{monthHits}} 条业绩 · 共 ${{Object.keys(HISTORY).length}} 个 ticker 数据库`;
    $("#cal").style.display = view==="cal" ? "grid" : "none";
    $("#lst").style.display = view==="lst" ? "block" : "none";
  }} catch(err) {{
    $("#status").className = "err";
    $("#status").innerHTML = `❌ 加载失败: ${{escapeHTML(err.message)}}。<br>如果 earnings_history.json 不存在，去 GitHub Actions → Run workflow → earnings_mode=full 触发首次回填。`;
  }}
}}

document.querySelectorAll(".btn.grp").forEach(b => b.onclick = () => {{
  document.querySelectorAll(".btn.grp").forEach(x => x.classList.remove("act"));
  b.classList.add("act");
  groupFilter = b.dataset.g;
  load();
}});
document.querySelectorAll(".btn.vw").forEach(b => b.onclick = () => {{
  document.querySelectorAll(".btn.vw").forEach(x => x.classList.remove("act"));
  b.classList.add("act");
  view = b.dataset.v;
  $("#cal").style.display = view==="cal" ? "grid" : "none";
  $("#lst").style.display = view==="lst" ? "block" : "none";
}});
$("#prev").onclick = () => {{ cur.setMonth(cur.getMonth()-1); load(); }};
$("#next").onclick = () => {{ cur.setMonth(cur.getMonth()+1); load(); }};
$("#cur").onclick = () => {{ cur = new Date(); cur.setDate(1); load(); }};
$("#dlg-close").onclick = closeDialog;
$("#modal").onclick = (e) => {{ if (e.target.id === "modal") closeDialog(); }};
document.addEventListener("keydown", e => {{ if (e.key === "Escape") closeDialog(); }});
window.openDay = openDay;  // 给 list 视图的 dh-row onclick 调用

load();
</script>
</body>
</html>'''
    with open(os.path.join(REPO_DIR, 'calendar.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"calendar.html written, {len(html)} bytes, pool {total_n} stocks")

def write_earnings_page():
    """生成 earnings.html — 加载 earnings_history.json，搜索 + 表格展示"""
    pool_pairs = []
    for ind, syms in INDUSTRY_MAP.items():
        grp = SUB_TO_GROUP[ind]
        for sym in syms:
            pool_pairs.append(f'"{sym}":["{ind}","{grp}"]')
    pool_js = '{' + ','.join(pool_pairs) + '}'

    history_exists = os.path.exists(os.path.join(REPO_DIR, 'earnings_history.json'))
    history_note = "" if history_exists else (
        '<div style="background:#3d2a14;border:1px solid #8b6914;color:#e8c547;'
        'padding:10px 14px;border-radius:6px;margin-bottom:14px;font-size:.85rem">'
        '⚠️ <code>earnings_history.json</code> 尚未生成。请先在 GitHub Actions '
        '手动触发 <code>workflow_dispatch</code> 跑一次 <code>--full</code> 回填。</div>'
    )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>美股硬件板块 · 业绩历史</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;padding:24px 16px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.45rem;margin-bottom:4px}}
.sub{{color:#8b949e;font-size:.85rem;margin-bottom:18px}}
.sub a{{color:#58a6ff;text-decoration:none}}
.bar{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:14px;padding:14px;background:#161b22;border:1px solid #21262d;border-radius:8px}}
.bar .lbl{{color:#8b949e;font-size:.78rem;margin-right:4px}}
.bar input,.bar select{{background:#0d1117;border:1px solid #30363d;color:#e6edf3;padding:7px 10px;border-radius:6px;font-size:.85rem;font-family:inherit}}
.bar input:focus,.bar select:focus{{outline:none;border-color:#1f6feb}}
#q{{min-width:240px}}
.btn{{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:7px 14px;border-radius:6px;font-size:.82rem;cursor:pointer;font-family:inherit}}
.btn:hover{{background:#30363d}}
.btn.act{{background:#1f6feb;border-color:#1f6feb;color:#fff}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-left:auto}}
#status{{color:#8b949e;font-size:.85rem;padding:8px 0 14px}}
#status.err{{color:#f85149}}
#status.ok b{{color:#58a6ff}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}}
.kpi .card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 14px}}
.kpi .lbl{{color:#8b949e;font-size:.7rem;text-transform:uppercase;letter-spacing:.05em;margin-bottom:4px}}
.kpi .val{{font-size:1.25rem;font-weight:700;color:#e6edf3}}
.tblwrap{{background:#161b22;border:1px solid #21262d;border-radius:8px;overflow:hidden}}
table{{width:100%;border-collapse:collapse;font-size:.85rem}}
th{{background:#1c2128;color:#8b949e;padding:11px 12px;text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;cursor:pointer;user-select:none;position:sticky;top:0;z-index:1}}
th:hover{{color:#e6edf3}}
th .arr{{display:inline-block;width:10px;color:#58a6ff;margin-left:3px}}
td{{padding:10px 12px;border-bottom:1px solid #21262d;white-space:nowrap}}
tr:hover td{{background:#1c2128}}
.tk{{display:inline-block;background:#21262d;color:#58a6ff;padding:2px 7px;border-radius:4px;font-weight:600;font-size:.78rem;cursor:pointer;text-decoration:none}}
.tk:hover{{background:#30363d;color:#79c0ff}}
.tag-bmo{{color:#58a6ff;font-weight:600}}
.tag-amc{{color:#f59e0b;font-weight:600}}
.tag-dmh{{color:#8b949e}}
.beat{{color:#3fb950;font-weight:600}}
.miss{{color:#f85149;font-weight:600}}
.muted{{color:#8b949e}}
.future{{background:#0d2818}}
.future:hover td{{background:#103324}}
.dn{{font-size:.7rem;color:#8b949e;margin-left:4px}}
.empty{{padding:40px;text-align:center;color:#8b949e}}
.pgbar{{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;background:#161b22;border:1px solid #21262d;border-top:none;border-radius:0 0 8px 8px;font-size:.82rem;color:#8b949e}}
.pgbar button{{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:5px 11px;border-radius:5px;cursor:pointer;font-size:.78rem;margin:0 3px}}
.pgbar button:disabled{{opacity:.4;cursor:not-allowed}}
.foot{{margin-top:18px;padding:14px;background:#161b22;border:1px solid #21262d;border-radius:8px;font-size:.78rem;color:#8b949e;line-height:1.7}}
.foot code{{background:#0d1117;padding:1px 5px;border-radius:3px}}
@media(max-width:760px){{
  body{{padding:14px 8px}}
  .bar{{padding:10px}}
  td,th{{padding:8px 6px;font-size:.75rem}}
  #q{{min-width:160px}}
}}
</style>
</head>
<body>
<h1>🗂️ 美股硬件板块 · 业绩历史</h1>
<div class="sub">
  <a href="index.html">← 历史存档</a> ·
  <a href="calendar.html">📅 业绩日历</a> ·
  数据源 FMP · 覆盖池内 314 只 · 过去 25 年 + 未来已确认日期 · 工作日自动增量更新
</div>

{history_note}

<div class="bar">
  <span class="lbl">搜索：</span>
  <input id="q" placeholder="代码 / 子行业（NVDA、AI加速、半导体核心...）" autocomplete="off">
  <select id="when">
    <option value="all">全部时段</option>
    <option value="future">仅未来</option>
    <option value="recent">近 90 天</option>
    <option value="1y">近 1 年</option>
    <option value="5y">近 5 年</option>
    <option value="10y">近 10 年</option>
  </select>
  <select id="grp">
    <option value="">全部大类</option>
    <option>半导体核心</option>
    <option>硬件系统</option>
    <option>元器件制造</option>
    <option>分销渠道</option>
  </select>
  <select id="time">
    <option value="">全部时点</option>
    <option value="bmo">BMO 盘前</option>
    <option value="amc">AMC 盘后</option>
    <option value="dmh">DMH/未知</option>
  </select>
  <button class="btn" id="reset">↺ 重置</button>
  <div class="chips">
    <button class="btn chip" data-q="NVDA">NVDA</button>
    <button class="btn chip" data-q="AAPL">AAPL</button>
    <button class="btn chip" data-q="TSM">TSM</button>
    <button class="btn chip" data-q="AVGO">AVGO</button>
    <button class="btn chip" data-q="AMD">AMD</button>
    <button class="btn chip" data-q="INTC">INTC</button>
  </div>
</div>

<div id="status">⏳ 正在加载 earnings_history.json…</div>
<div id="kpi" class="kpi" style="display:none"></div>

<div class="tblwrap" id="tblwrap" style="display:none">
  <table id="tbl">
    <thead>
      <tr>
        <th data-k="date">日期 <span class="arr"></span></th>
        <th data-k="symbol">代码 <span class="arr"></span></th>
        <th data-k="industry">子行业 <span class="arr"></span></th>
        <th data-k="time">时点 <span class="arr"></span></th>
        <th data-k="epsEstimated" style="text-align:right">EPS 预期 <span class="arr"></span></th>
        <th data-k="eps" style="text-align:right">EPS 实际 <span class="arr"></span></th>
        <th data-k="surprise" style="text-align:right">超预期 <span class="arr"></span></th>
        <th data-k="revenueEstimated" style="text-align:right">营收预期 <span class="arr"></span></th>
        <th data-k="revenue" style="text-align:right">营收实际 <span class="arr"></span></th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
  <div class="pgbar">
    <span id="pginfo"></span>
    <span>
      <button id="prev">← 上页</button>
      <button id="next">下页 →</button>
    </span>
  </div>
</div>

<div class="foot">
<b>说明</b>：本页直接加载 <code>earnings_history.json</code>（仓库内静态文件，无需调 API）。数据由 GitHub Actions 维护：每个交易日跑 <code>fetch_earnings_history.py</code> 增量合并近 30 天 + 未来 180 天的 <code>/stable/earnings-calendar</code>；每周日跑 <code>--refresh-recent 180</code> 校正订正过的 EPS；首次回填用 <code>--full</code>（手动 workflow_dispatch 触发）逐 ticker 拉 <code>/stable/earnings?symbol=X&limit=120</code>，覆盖近 25-30 年。
未来未发布日期：行底色淡绿 · EPS/营收"实际"为空 · 仅显示分析师"预期"。
</div>

<script>
const POOL = {pool_js};
const PAGE_SIZE = 100;
let RAW = {{}};      // sym -> [records]
let FLAT = [];       // 扁平化后的 [{{date, symbol, industry, group, time, eps, ...}}]
let view = [];
let sortK = "date", sortDir = -1;  // 默认日期降序
let page = 0;

const $ = s => document.querySelector(s);

function epsFmt(v) {{ return (v===null||v===undefined||v==="") ? "—" : Number(v).toFixed(2); }}
function revFmt(v) {{
  if (v===null||v===undefined||v===0||v==="") return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return (v/1e12).toFixed(2)+"T";
  if (a >= 1e9) return (v/1e9).toFixed(2)+"B";
  if (a >= 1e6) return (v/1e6).toFixed(1)+"M";
  return v.toLocaleString();
}}
function surp(act, est) {{
  if (act==null||est==null||est===0) return null;
  return ((act-est)/Math.abs(est)*100);
}}
function timeTag(t) {{
  t = (t||"").toLowerCase();
  if (t==="bmo") return '<span class="tag-bmo">BMO</span>';
  if (t==="amc") return '<span class="tag-amc">AMC</span>';
  return '<span class="tag-dmh">—</span>';
}}

function flatten() {{
  const today = new Date().toISOString().slice(0,10);
  FLAT = [];
  for (const sym in RAW) {{
    const meta = POOL[sym];
    if (!meta) continue;
    for (const r of RAW[sym]) {{
      FLAT.push({{
        date: r.date,
        symbol: sym,
        industry: meta[0],
        group: meta[1],
        time: r.time,
        eps: r.eps,
        epsEstimated: r.epsEstimated,
        revenue: r.revenue,
        revenueEstimated: r.revenueEstimated,
        surprise: surp(r.eps, r.epsEstimated),
        future: r.date > today,
      }});
    }}
  }}
}}

function applyFilters() {{
  const q = $("#q").value.trim().toUpperCase();
  const when = $("#when").value;
  const grp = $("#grp").value;
  const tm = $("#time").value;
  const cutoff = (days) => {{
    const d = new Date(); d.setDate(d.getDate()-days);
    return d.toISOString().slice(0,10);
  }};

  view = FLAT.filter(r => {{
    if (q) {{
      const hay = (r.symbol+" "+r.industry+" "+r.group).toUpperCase();
      const terms = q.split(/\\s+/).filter(Boolean);
      if (!terms.every(t => hay.includes(t))) return false;
    }}
    if (grp && r.group !== grp) return false;
    if (tm) {{
      const t = (r.time||"").toLowerCase();
      if (tm === "dmh") {{ if (t === "bmo" || t === "amc") return false; }}
      else if (t !== tm) return false;
    }}
    if (when === "future") {{ if (!r.future) return false; }}
    else if (when === "recent") {{ if (r.date < cutoff(90)) return false; }}
    else if (when === "1y") {{ if (r.date < cutoff(365)) return false; }}
    else if (when === "5y") {{ if (r.date < cutoff(365*5)) return false; }}
    else if (when === "10y") {{ if (r.date < cutoff(365*10)) return false; }}
    return true;
  }});

  view.sort((a,b) => {{
    let va = a[sortK], vb = b[sortK];
    if (va == null && vb == null) return 0;
    if (va == null) return 1;
    if (vb == null) return -1;
    if (typeof va === "string") return sortDir * va.localeCompare(vb);
    return sortDir * (va - vb);
  }});

  page = 0;
  render();
}}

function render() {{
  const total = view.length;
  const totalPg = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (page >= totalPg) page = totalPg - 1;
  if (page < 0) page = 0;
  const slice = view.slice(page*PAGE_SIZE, (page+1)*PAGE_SIZE);

  const future = view.filter(r => r.future).length;
  const past = total - future;
  const beats = view.filter(r => r.surprise != null && r.surprise > 0).length;
  const misses = view.filter(r => r.surprise != null && r.surprise < 0).length;
  const symbols = new Set(view.map(r => r.symbol)).size;
  $("#kpi").style.display = "grid";
  $("#kpi").innerHTML = `
    <div class="card"><div class="lbl">命中记录</div><div class="val">${{total.toLocaleString()}}</div></div>
    <div class="card"><div class="lbl">覆盖 ticker</div><div class="val">${{symbols}}</div></div>
    <div class="card"><div class="lbl">已发布</div><div class="val">${{past.toLocaleString()}}</div></div>
    <div class="card"><div class="lbl">未来</div><div class="val" style="color:#3fb950">${{future.toLocaleString()}}</div></div>
    <div class="card"><div class="lbl">超预期 / 不及</div><div class="val"><span class="beat">${{beats}}</span> <span class="muted" style="font-weight:400">/</span> <span class="miss">${{misses}}</span></div></div>
  `;

  document.querySelectorAll("th").forEach(th => {{
    const a = th.querySelector(".arr");
    if (!a) return;
    a.textContent = th.dataset.k === sortK ? (sortDir < 0 ? "▼" : "▲") : "";
  }});

  if (!total) {{
    $("#tbody").innerHTML = `<tr><td colspan="9" class="empty">无匹配记录。试试清空筛选或换关键字。</td></tr>`;
  }} else {{
    $("#tbody").innerHTML = slice.map(r => {{
      const sCls = r.surprise == null ? "muted" : (r.surprise >= 0 ? "beat" : "miss");
      const sStr = r.surprise == null ? "—" : (r.surprise>=0?"+":"")+r.surprise.toFixed(1)+"%";
      const fc = r.future ? " future" : "";
      const dow = "日一二三四五六"[new Date(r.date+"T00:00:00").getDay()];
      return `<tr class="${{fc.trim()}}">
        <td>${{r.date}}<span class="dn">周${{dow}}</span></td>
        <td><a class="tk" data-sym="${{r.symbol}}">${{r.symbol}}</a></td>
        <td class="muted">${{r.industry}}</td>
        <td>${{timeTag(r.time)}}</td>
        <td style="text-align:right">${{epsFmt(r.epsEstimated)}}</td>
        <td style="text-align:right">${{epsFmt(r.eps)}}</td>
        <td style="text-align:right" class="${{sCls}}">${{sStr}}</td>
        <td style="text-align:right" class="muted">${{revFmt(r.revenueEstimated)}}</td>
        <td style="text-align:right">${{revFmt(r.revenue)}}</td>
      </tr>`;
    }}).join("");
  }}

  $("#pginfo").textContent = total ? `第 ${{page+1}} / ${{totalPg}} 页 · 共 ${{total.toLocaleString()}} 条` : "—";
  $("#prev").disabled = page <= 0;
  $("#next").disabled = page >= totalPg - 1;

  document.querySelectorAll(".tk[data-sym]").forEach(a => {{
    a.onclick = () => {{ $("#q").value = a.dataset.sym; applyFilters(); }};
  }});
}}

async function init() {{
  try {{
    const r = await fetch("earnings_history.json", {{cache: "no-cache"}});
    if (!r.ok) throw new Error("HTTP "+r.status);
    RAW = await r.json();
    flatten();
    const sizeMB = (JSON.stringify(RAW).length / 1024 / 1024).toFixed(2);
    const today = new Date().toISOString().slice(0,10);
    const future = FLAT.filter(r => r.date > today).length;
    $("#status").className = "ok";
    $("#status").innerHTML = `✅ 加载完成 · <b>${{Object.keys(RAW).length}}</b> 个 ticker · <b>${{FLAT.length.toLocaleString()}}</b> 条业绩记录（含 <b>${{future}}</b> 个未来日期）· ${{sizeMB}} MB`;
    $("#tblwrap").style.display = "block";
    applyFilters();
  }} catch(err) {{
    $("#status").className = "err";
    $("#status").innerHTML = `❌ 加载失败：${{err.message}}。<br>如果你刚部署，请先在 GitHub Actions 手动触发 <code>workflow_dispatch</code> 跑一次 <code>fetch_earnings_history.py --full</code> 回填。`;
  }}
}}

document.querySelectorAll("th").forEach(th => {{
  th.onclick = () => {{
    const k = th.dataset.k;
    if (!k) return;
    if (sortK === k) sortDir = -sortDir;
    else {{ sortK = k; sortDir = (k === "date" || k === "surprise") ? -1 : 1; }}
    applyFilters();
  }};
}});
$("#q").oninput = () => applyFilters();
$("#when").onchange = () => applyFilters();
$("#grp").onchange = () => applyFilters();
$("#time").onchange = () => applyFilters();
$("#reset").onclick = () => {{
  $("#q").value = ""; $("#when").value = "all"; $("#grp").value = ""; $("#time").value = "";
  sortK = "date"; sortDir = -1; applyFilters();
}};
$("#prev").onclick = () => {{ page--; render(); window.scrollTo(0,0); }};
$("#next").onclick = () => {{ page++; render(); window.scrollTo(0,0); }};
document.querySelectorAll(".chip").forEach(b => {{
  b.onclick = () => {{ $("#q").value = b.dataset.q; applyFilters(); }};
}});

init();
</script>
</body>
</html>'''
    with open(os.path.join(REPO_DIR, 'earnings.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"earnings.html written, {len(html)} bytes (loads earnings_history.json on client)")

if __name__ == '__main__':
    data = main()
    t = data['totals']
    print(f"Stocks: {len(data['stocks'])}, Up/Down/Flat: {t['up']}/{t['down']}/{t['flat']}, cap-w: {t['cap_w']}%")
    write_html(data)
    write_stocks_page(data['stocks'], DATE)
    meta = update_meta(data['totals'])
    write_index(meta)
    write_calendar_page()
    write_earnings_page()
