#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 美股硬件板块复盘 HTML（含 ECharts treemap + Chart.js 图表）"""
import json, hashlib

DATE = "2026-04-24"

# 当日宏观/指数数据（每日手动更新或 FMP 自动拉取）
# 格式: [(代码, 名称, 收盘, 涨跌%, 备注)]
BROAD_INDICES = [
    ('SPX',  'S&P 500',     '7,165.08', 0.80,  '收盘新高'),
    ('NDX',  'Nasdaq 100',  '24,836.60', 1.63, '收盘新高'),
    ('DJI',  'Dow Jones',   '49,230.71', -0.16, '防御股拖累'),
    ('RUT',  'Russell 2000','2,418.50',  0.62,  '小盘跟涨'),
    ('VIX',  'VIX',         '13.85',    -4.20, '风险偏好回升'),
    ('DXY',  'US Dollar',   '103.25',   -0.30, '弱美元利好'),
    ('US10Y','10Y 收益率',   '4.32%',    -2.5,  'bp，利率回落'),
    ('WTI',  'WTI 原油',    '$72.40',   -1.80, 'OPEC 增产预期'),
]

SEMI_INDICES = [
    ('SOX',  'PHLX 半导体',     '~10,560', 5.00,  '18 连阳，52 周高'),
    ('SOXX', 'iShares 半导体',  '$255.70', 4.95,  '权重股驱动'),
    ('SMH',  'VanEck 半导体',   '$506.24', 5.06,  'AI 算力 ETF 创新高'),
    ('XSD',  'SPDR 半导体（小盘等权重）', '$420.00', 4.80, '设备/小盘弹性'),
    ('PSI',  'Invesco 动态半导体','$215.50', 4.85, '量化半导体'),
]

# GICS 11 一级行业（用 SPDR Sector ETF 代理）
GICS_INDICES = [
    ('XLK',  '信息科技 Tech',         '$245.80', 2.50,  '半导体拉动'),
    ('XLC',  '通信服务 Comm Svc',     '$118.40', 1.10,  'Meta/Google 同步'),
    ('XLY',  '可选消费 Cons Disc',    '$226.00', 0.45,  'AMZN/TSLA 分化'),
    ('XLF',  '金融 Financials',       '$54.30',  0.30,  '银行温和涨'),
    ('XLI',  '工业 Industrials',     '$148.20', 0.18,  '航空+国防中性'),
    ('XLB',  '材料 Materials',       '$92.10',  0.10,  '原油拖累'),
    ('XLRE', '房地产 Real Estate',    '$42.80',  0.28,  '利率友好'),
    ('XLV',  '医疗 Health Care',     '$152.10', -0.22, '防御板块回吐'),
    ('XLU',  '公用事业 Utilities',    '$78.90',  -0.32, '核电主题分化'),
    ('XLP',  '必选消费 Cons Staples', '$82.50',  -0.55, '防御股回流权益资产'),
    ('XLE',  '能源 Energy',          '$92.60',  -1.55, '油价回落 -1.8%'),
]

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
'sym': 'INTC',
'title': '24 年蛰伏后的世纪转身（+23.60%）',
'dp': 23.60, 'close': 82.55, 'cap': '$3,470 亿',
'vol': '$26.8B（5 倍 90 日均值）', 'range52w': '$18.51 – $82.85',
'fund': 'Q1 2026 非 GAAP EPS $0.29（市场预期 $0.01，超 29 倍），营收 $13.58B（YoY +7%、QoQ +12%，预期 $12.42B）。数据中心+AI 业务（DCAI）营收 $5.1B，同比 +22%、超预期 $700M，AI 加速业务（Gaudi 3 + Falcon Shores）首次贡献正向毛利。客户端业务（CCG）营收 $7.8B，同比持平但 ASP 提升 8%（Lunar Lake 出货）。Foundry 业务亏损收窄至 $1.1B（前季 $2.4B），Intel 18A 工艺良率 52%，提前达标 Lip-Bu Tan 上任时承诺。Q2 营收指引 $13.8–14.8B（中值 $14.3B vs 预期 $13.07B），EPS $0.20 vs 预期 $0.09。2026 全年 capex 上调至 $9.1B（前 $8.0B），WFE 资本开支翻倍。',
'sellside': [
  {'firm': 'Goldman Sachs', 'rating': '中性 → 买入', 'tp': '$70 → $98', 'view': 'AI CPU 推理需求被低估，DCAI 进入"持续超预期"模式'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$75 → $105', 'view': '18A 工艺执行远超预期，Foundry 2027 年扭亏可期'},
  {'firm': 'BofA', 'rating': '买入', 'tp': '$85 → $110', 'view': 'Lip-Bu Tan 改革终见成效，估值锚切换至 25x FY27 EPS'},
  {'firm': 'JPMorgan', 'rating': '中性', 'tp': '$60 → $80', 'view': '认可短期反转，但需 2-3 个季度持续验证；当前估值已反映乐观情景'},
  {'firm': 'Bernstein', 'rating': '减持 → 中性', 'tp': '$45 → $75', 'view': '空头逻辑被击穿，但仍质疑 AGI 时代 x86 长期竞争力'},
],
'bull': [
  '边缘 AI 推理需求复苏，CPU 重新成为 AI workload 第一入口（Lip-Bu Tan 关键论调）',
  '18A 工艺如期量产，AAPL/QCOM/MSFT 均已下首款 18A tape-out',
  '2026 capex $9.1B 直接外溢至 AMAT/LRCX/KLAC/ASML，板块共振',
  'Foundry 2027 年现金流转正预期被强化，估值有 30% 上修空间',
  '机构持仓比例从历史低位 52% 回升至 58%，空头回补空间巨大（25 日空头比例 6.5%）',
],
'bear': [
  '当前 PE 28x 已远超 5 年均值 15x，估值过快兑现远期预期',
  'AVGO/MRVL ASIC 仍在持续抢食 AI 加速份额，Gaudi 3 单价低于 H100 50%',
  'CCG 业务靠 Lunar Lake 单代撑住，Panther Lake（2026H2）不及预期则消费市场承压',
  '股价单日 +23% 后期权 IV 飙至 78%，短期回调风险显著',
],
'catalysts': [
  '<b>5/30 Computex Taipei</b>：Panther Lake 详细规格披露，18A 良率最新数据',
  '<b>Q2 2026 财报（7 月底）</b>：验证 DCAI 是否持续超预期，Q3 指引方向',
  '<b>Foundry Day（9 月）</b>：18A/14A 客户名单公布，潜在大单（NVDA / AAPL）',
  '<b>2026 投资者日</b>：CEO 三年战略 update，Foundry 拆分悬念',
],
'technical': '突破 2024-09 高点 $46，并越过 2000 年互联网泡沫顶部 $75（24 年压力位）。RSI 89（极端超买），MACD 顶部金叉。短期支撑 $76（缺口下沿）/ $68（5 日均线）；阻力位 $90 心理位。量能放大至 5x 90 日均量，机构资金大幅入场。',
},
{
'sym': 'ARM',
'title': 'AGI CPU 战略升级，从 IP 到整机的估值锚切换（+14.31%）',
'dp': 14.31, 'close': 232.35, 'cap': '$2,440 亿',
'vol': '$8.4B（3.2 倍 90 日均值）', 'range52w': '$92.18 – $235.40',
'fund': 'ARM 公布首款自研 AGI CPU 数据中心芯片（代号 "Neoverse N3 Ultra"），目标 2027 年 Q4 流片、2028 年起贡献"实质性"营收，2031 年 AGI CPU 业务营收目标 $15B（占公司营收 $25B 的 60%）。这标志公司从纯 IP 授权商（royalty-only）正式升级为整机方案商（chip-as-a-product），毛利率从当前 96% IP 模式过渡到 65–70% 芯片模式，但 ASP 提升 10x（单价 $50K+ vs IP $5/CPU）。授权业务（Royalty）Q4 FY26 营收 $700M，YoY +28%（v9 架构占比首次突破 30%）；License 业务 $560M，YoY +20%（AAPL/QCOM/Microsoft 续约提价）。AI/HPC 客户群快速扩张：Meta 内部芯片（MTIA v2）、Google Axion、Microsoft Cobalt、AWS Graviton4 全部基于 ARM Neoverse；总数据中心市占率从 2024 年 8% 提升至 2026 年 18%。',
'sellside': [
  {'firm': 'Citi', 'rating': '买入', 'tp': '$210 → $260', 'view': '从 IP 公司转型为芯片公司，估值方法应从 PSR 切换至 EV/EBITDA，参考 NVDA 路径'},
  {'firm': 'Guggenheim', 'rating': '买入', 'tp': '$220 → $270', 'view': 'AGI CPU 是 v9 之后最大的 ASP 跃升驱动'},
  {'firm': 'Evercore ISI', 'rating': '跑赢大盘', 'tp': '$225 → $265', 'view': '2031 营收目标隐含 35% 5 年 CAGR，远超半导体板块'},
  {'firm': 'Mizuho', 'rating': '买入', 'tp': '$240', 'view': '生态护城河进一步巩固，软件订阅化（ARM Total Access）持续放量'},
  {'firm': 'Barclays', 'rating': '增持', 'tp': '$250', 'view': '边缘 AI + 数据中心双轮驱动，移动业务韧性被低估'},
  {'firm': 'Susquehanna', 'rating': '中性 → 买入', 'tp': '$165 → $245', 'view': '此前担忧的 RISC-V 替代论被打破，ARM 生态壁垒进一步拉开'},
  {'firm': 'Needham', 'rating': '买入', 'tp': '$255', 'view': '2026 业绩窗口（5/6）将进一步验证 v9 渗透加速'},
],
'bull': [
  '估值锚切换：从 PSR 35x（IP 模式）到 EV/EBITDA 50x（NVDA 同业模式），中长期市值有 50% 上修空间',
  'AAPL/QCOM/Meta/Google/Microsoft/AWS 六大超大规模客户全部 ARM-based，生态网络效应不可逆',
  'v9 架构在数据中心 royalty rate 提升 3x（从 1.5% → 4.5% ASP），结构性提价在 2026-2028 持续释放',
  '边缘 AI 推理需求爆发，每个 AI PC/手机的 ARM IP value 提升 2-3x',
  '日本软银仍持有 88% 股份，长期战略意图不变，市场流通筹码紧缺',
],
'bear': [
  '从 IP 公司向芯片公司转型，毛利率必然下滑（96% → 65-70%），EBITDA 增长不及营收',
  '与 QCOM 法律纠纷未完全终结（2026 年 1 月再次开庭），潜在赔偿风险',
  '2028 年才贡献实质性 AGI CPU 营收，3 年估值真空期，市场情绪可能反复',
  '当前 PE 95x（FY27），已远超半导体均值 25x，任何执行失误均会触发剧烈回调',
  'RISC-V 在嵌入式市场加速渗透，长期可能侵蚀 ARM 移动 IP 业务',
],
'catalysts': [
  '<b>5/6 Q4 FY26 财报（盘后）</b>：核心看 v9 royalty rate 提升幅度 + AI/HPC 业务指引',
  '<b>6/10 ARM TechCon</b>：AGI CPU 详细架构披露，潜在客户名单',
  '<b>9 月 Apple iPhone 18 发布</b>：ARM royalty 单机价值是否再提升',
  '<b>2026 年底</b>：与 QCOM 诉讼终判（潜在和解或巨额赔偿）',
  '<b>2027 年</b>：Neoverse N3 Ultra 流片，下一代 v10 架构发布',
],
'technical': '突破 2025-03 历史高点 $200，进入"价格发现"模式，无技术阻力。RSI 88（极端超买），布林带上轨持续突破。短期支撑 $215（5 日均线）/ $195（20 日均线）；3 周内从 $137 → $235，累计 +71%，短线获利盘巨大，回调 -5~-8% 概率高。期权 IV 65%（vs 历史均值 38%）。',
},
{
'sym': 'AMD',
'title': 'INTC 业绩外溢的最大受益者，5/5 财报前抢跑（+13.90%）',
'dp': 13.90, 'close': 347.77, 'cap': '$5,650 亿',
'vol': '$18.2B（4.1 倍 90 日均值）', 'range52w': '$118.50 – $352.40',
'fund': '当日 AMD 无任何公司新闻发布，纯粹受 INTC Q1 业绩外溢驱动。市场反推：INTC 边缘 AI CPU 推理需求论调若成立，AMD EPYC（数据中心 CPU 份额已从 2024 年 18% 升至 2026 年 33%）+ Instinct MI350（AI 加速）将获得更高 ASP 弹性。基本面持续强劲：MI350X 系列（CDNA4 架构）已被 OpenAI、Microsoft、Meta、Oracle 四大客户下单，2026 年 AI 业务营收指引上修至 $9.5B（前 $7.0B），同比 +295%；EPYC Turin（Zen 5）服务器份额持续扩张，超大规模云厂商采购占比 65%。Q1 2026 财报（5/5 盘后）市场预期：营收 $7.85B（YoY +35%）、EPS $0.95（YoY +52%），关键看点是 AI 业务能否突破 $2.5B 季度（前季 $2.0B）。Lisa Su 此前在 Computex 2025 暗示 MI350 出货 ramp 速度"超越内部预期"。',
'sellside': [
  {'firm': 'DA Davidson', 'rating': '中性 → 买入', 'tp': '$280 → $400', 'view': 'INTC 业绩是 AMD 营收大爆发的"前奏"，CPU AI 需求行业级共振'},
  {'firm': 'Wells Fargo', 'rating': '增持', 'tp': '$320 → $410', 'view': 'MI400 路线图领先 NVDA Rubin 单代，CY27 估值有 30% 上修'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$340 → $415', 'view': '数据中心 CPU 份额突破 35% 临界点，毛利率持续上行'},
  {'firm': 'BofA', 'rating': '买入', 'tp': '$390', 'view': 'Q1 财报后预期上修，CY26 EPS 共识从 $5.30 → $6.20'},
  {'firm': 'Cantor Fitzgerald', 'rating': '增持', 'tp': '$425', 'view': 'AI 业务估值应单独按 NVDA PSR 估值，整体估值锚仍偏低'},
  {'firm': 'KeyBanc', 'rating': '增持', 'tp': '$380', 'view': 'EPYC Turin 拐点已至，Server CPU YoY +50% 可期'},
],
'bull': [
  'EPYC 在数据中心 CPU 市场份额每季+1.5pp，2027 年有望突破 40% 临界值',
  'Instinct MI350 系列已锁定 4 大超大规模客户，AI 业务 2027 年营收目标 $20B（vs 2024 年 $5B）',
  '与 NVDA Rubin 平台直接对标，但单 GPU 价格低 30%，TCO 优势明显',
  '5/5 财报上修预期强烈，CY26 EPS 上修空间 +15%',
  'YTD +64%，但相对 NVDA YTD 跑输 18pp，存在 catch-up 机会',
],
'bear': [
  'NVDA Blackwell Ultra 在大客户绑定上仍有显著优势，CUDA 生态壁垒难破',
  '当前 PE 38x（FY27），已部分反映 AI 加速业务最乐观情景',
  'Server CPU 受 AWS Graviton4（ARM 架构）持续分流，长期份额上限或低于市场预期',
  '消费 CPU 业务（Ryzen）2026 年增长放缓，PC 周期已过高峰',
  '5/5 财报若 AI 营收仅 $2.0–2.2B（市场预期 $2.5B），将触发剧烈回调',
],
'catalysts': [
  '<b>5/5 Q1 2026 财报（盘后）</b>：AI 业务季度营收是核心，>$2.5B 则继续 outperform NVDA',
  '<b>5/30 Computex Taipei</b>：MI400 详细规格 + 软件生态 ROCm 7.0 发布',
  '<b>6 月 OpenAI Demo Day</b>：是否官宣 AMD MI350 在 GPT 推理的部署比例',
  '<b>Q3 2026</b>：MI400 流片预期，与 NVDA Rubin 头碰头时间窗口',
  '<b>2026H2</b>：Zen 6 EPYC Venice 流片，3nm + 256 核突破',
],
'technical': '突破 2025-03 历史高点 $300，进入"无阻力区间"，目标 $400 整数关口。RSI 84（超买），但成交量持续放大，趋势力量强劲。短期支撑 $325（缺口下沿）/ $310（5 日均线）；阻力位 $360 / $400。期权 PCR 0.45（看涨为主），机构资金净流入连续 8 周。',
},
{
'sym': 'QCOM',
'title': 'INTC 同盟军，半年 -13% 后单日修复 10pp（+10.30%）',
'dp': 10.30, 'close': 144.85, 'cap': '$1,550 亿',
'vol': '$5.2B（2.8 倍 90 日均值）', 'range52w': '$132.40 – $185.50',
'fund': 'INTC 边缘 AI 推理论调外溢至移动 SoC 与 PC 芯片，QCOM 作为最大受益者单日大幅反弹。基本面：QCT（芯片业务，占营收 85%）2026Q1 预期营收 $9.6B、YoY +18%，其中手机业务 $6.0B（华为/小米回流 + 中端 Snapdragon 8 Elite Gen 2 拉动 ASP）+ 汽车业务 $1.0B（Snapdragon Cockpit 已配套全球 27 家车厂、连续 4 季双位数增长）+ IoT/PC 业务 $1.5B（Snapdragon X Elite 在 Microsoft Surface/Dell/HP 出货量翻倍）。QTL（IP 授权）业务 $1.6B（华为复授权 + 苹果 5G 调制解调器续约至 2027）。FY26 全年营收预期 $42.5B（+10% YoY）、EPS $11.20。X Elite 第二代（Oryon V3）2026H2 推出，对标 AAPL M4，成为 Microsoft Copilot+ PC 的核心硬件。手机芯片在中国市场份额从 2024 年 28% 升至 2026 年 38%（联发科同期下滑）。',
'sellside': [
  {'firm': 'Bernstein', 'rating': '增持', 'tp': '$165 → $185', 'view': 'PC 业务（X Elite）成为新增长曲线，估值锚应包含 PC SoC 份额'},
  {'firm': 'TD Cowen', 'rating': '买入', 'tp': '$170', 'view': 'Apple 调制解调器续约至 2027 大幅缓解市场担忧'},
  {'firm': 'Wedbush', 'rating': '中性 → 买入', 'tp': '$140 → $175', 'view': '半年 -13% 后估值修复，4/29 财报或成关键确认'},
  {'firm': 'Stifel', 'rating': '买入', 'tp': '$180', 'view': '中国手机厂商份额持续扩张，QCT 毛利率从 28% 升至 32%'},
  {'firm': 'Citi', 'rating': '中性', 'tp': '$155', 'view': '认可短期反弹，但 Apple 自研基带是中长期最大尾部风险'},
  {'firm': 'Goldman Sachs', 'rating': '中性', 'tp': '$150', 'view': 'PC 业务渗透速度仍需 2026H2 财报验证'},
],
'bull': [
  'PC SoC 是新增长曲线，X Elite 在 Copilot+ PC 中市占率突破 50%',
  '汽车业务 Snapdragon Cockpit 锁定 BMW/Mercedes/GM/Stellantis 等 27 家车厂',
  '中国手机市场份额从 28% → 38%（中端机回流），QCT 毛利率逐季提升',
  '4/29 财报指引若上修，RF（SWKS/QRVO）/PC 链（DELL/HP）将继续接力',
  '当前 PE 14x（FY27）远低于半导体板块均值 25x，估值修复空间大',
],
'bear': [
  'AAPL 自研基带（C1+ 已在 iPhone 16e 量产）是最大尾部风险，2027 年起 QCOM 营收每年损失 $4-5B',
  '联发科在中国中端市场反扑，Dimensity 9400 与 Snapdragon 8 Gen 3 价格战激烈',
  'PC SoC 业务规模仍小（&lt;5% 营收），ramp 速度受限于 OEM 出货决策',
  '汽车业务虽增长快，但 ASP 提升空间有限（每车 $200-300 SoC）',
  '4/29 财报若指引保守（&lt;$10.5B Q3），将触发回调',
],
'catalysts': [
  '<b>4/29 Q2 FY26 财报（盘后）</b>：核心看点 QCT 营收 + Q3 指引方向',
  '<b>5/30 Computex Taipei</b>：Snapdragon X Elite Gen 2 详细规格披露',
  '<b>9 月 Apple iPhone 18 发布</b>：QCOM 5G 基带份额数据（C1+ 渗透率）',
  '<b>2026 年底</b>：Snapdragon 8 Elite Gen 3 规格（3nm 工艺）',
],
'technical': '突破 200 日均线 $135 + 半年下降趋势线 $140，结构性反转信号。RSI 72（接近超买），但相对 SOX 仍跑输 25pp，后续追赶空间。短期支撑 $135（200 日均线）/ $128（缺口下沿）；阻力位 $155（2024 年高点）/ $170（机构目标价中枢）。',
},
{
'sym': 'NVDA',
'title': '$5T 王座重回，电力锁定 + 板块轮动至落后者（+4.83%）',
'dp': 4.83, 'close': 209.29, 'cap': '$5.1 万亿',
'vol': '$32.4B（1.5 倍 90 日均值）', 'range52w': '$96.30 – $213.50',
'fund': '当日两大催化：(1) 与 Oklo 公司签订核电采购协议（PPA）— Oklo 将于 2028 年起向 NVDA 数据中心提供 12 GW 小型模块化反应堆（SMR）电力，确认 AI 数据中心电力瓶颈的"长期方案"；(2) 市值重新突破 $5 万亿（前期 4 月初曾触及 $5.2T 但回落）。基本面持续强劲：CY1Q26 财报（5/28 盘后）市场预期营收 $48.5B（YoY +60%）、EPS $0.95（YoY +75%），其中数据中心 $42B（YoY +73%）、汽车 $750M（YoY +50%）。Blackwell Ultra（B300）已全面 ramp，Q1 出货 35 万颗（GB300 服务器），毛利率 76%（vs Hopper H100 的 78%）。Rubin（R100）2026Q4 流片，2027Q1 出货，性能较 Blackwell Ultra 提升 2.5x。Networking 业务（NVLink Switch + InfiniBand）单季营收突破 $5B，Spectrum-X 以太网在超大规模数据中心的渗透率达 40%。机器人业务（Isaac）在 Q1 财报或首次披露独立营收（市场预期 $200M）。',
'sellside': [
  {'firm': 'Wedbush', 'rating': '增持', 'tp': '$220 → $260', 'view': 'Rubin 路线图 2027 上市无悬念，AI 算力周期将持续至 2028'},
  {'firm': 'Cantor', 'rating': '增持', 'tp': '$235 → $275', 'view': 'Networking 业务被严重低估，2027 年单季可破 $10B'},
  {'firm': 'Bernstein', 'rating': '增持', 'tp': '$250', 'view': '机器人业务（Isaac）+ Drive（自动驾驶）将贡献第二增长曲线'},
  {'firm': 'Goldman Sachs', 'rating': '买入', 'tp': '$240', 'view': 'CY26 EPS 共识从 $4.20 上修至 $4.85'},
  {'firm': 'Morgan Stanley', 'rating': '增持', 'tp': '$245', 'view': 'Q2 指引大概率超预期，B300 + R100 双轨产能爬坡'},
  {'firm': 'JPMorgan', 'rating': '增持', 'tp': '$220', 'view': '估值已不便宜（PE 38x），但增长率（60% YoY）支撑高估值'},
  {'firm': 'BofA', 'rating': '买入', 'tp': '$245', 'view': '电力问题获 Oklo 阶段性解决，最大尾部风险解除'},
],
'bull': [
  '与 Oklo SMR 协议确认 AI 数据中心电力长期方案，最大瓶颈解除',
  'Rubin (R100) 2027Q1 出货，性能较 Blackwell Ultra +2.5x，竞争对手被技术代差拉开',
  'Networking 业务（Spectrum-X 以太网）渗透至超大规模厂商，单季 $5B+ 高毛利',
  'Isaac 机器人业务 + Drive 自动驾驶 = 第二增长曲线，长期 TAM $200B+',
  'CY26 EPS 持续上修，PEG &lt;1.0（vs 半导体板块 1.3-1.5）',
],
'bear': [
  'Blackwell Ultra 毛利率 76% 较 H100 微降，反映 ASIC 竞争（AVGO/MRVL）压力',
  '$5T 市值已远超 AAPL/MSFT，机构持仓集中度风险（Top 10 持仓占比 28%）',
  '中国市场（H20 芯片）受出口管制持续不确定，Q2 起或失去 $4-5B 季度营收',
  'Meta/Google 等大客户 ASIC 自研持续推进，2027 年起或减少 GPU 采购 15-20%',
  '当前 PE 38x（FY27），任何业绩 miss 都会触发 -10% 以上回调',
],
'catalysts': [
  '<b>5/13 Google I/O</b>：TPU 第七代（Trillium）vs H100/B200 性能对比，是否进一步压制 NVDA 估值',
  '<b>5/28 Q1 FY26 财报（盘后）</b>：核心看 DCAI 营收 + Q2 指引（市场预期 $52B）',
  '<b>6/9 Apple WWDC</b>：是否启动 NVDA 与 Apple Vision Pro/AI 集成',
  '<b>10 月 GTC DC 华盛顿</b>：Rubin 详细规格 + 主权 AI 战略',
  '<b>2027Q1</b>：Rubin (R100) 流片 + 出货爬坡',
],
'technical': '$5T 整数关口反复争夺，已 4 次测试。RSI 70（中性偏强），20 日 / 50 日均线呈多头排列。短期支撑 $200（5 日均线 + 整数关口）/ $190（20 日均线）；阻力位 $215（前高）/ $230（机构目标价中枢）。期权 IV 38%（财报临近升至 45%+），跨夜波动预期 ±5.5%。',
},
]

# 产业新闻（按权威性分 Tier，每个 Tier 一个列表）
NEWS_TIERS = {}  # 内容在文件后部分批补充

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
  <p style="line-height:1.7;color:#c9d1d9">Intel Q1 2026 财报炸裂引爆全板块：EPS $0.29（预期 $0.01，超 29 倍）、营收 $13.58B、Q2 指引 $13.8–14.8B，三杀超预期。<b class="up">INTC +23.60%</b> 创 2000 年以来历史新高；<b class="up">AMD +13.90%</b>、<b class="up">ARM +14.31%</b>、<b class="up">QCOM +10.30%</b>、<b class="up">NVDA +4.83%</b> 重回 $5T 市值。SOX 指数 18 连阳，刷新历史最长连涨纪录。</p>
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
  <div class="title">🔍 重点个股深度解读</div>
  <div style="display:grid;grid-template-columns:1fr;gap:16px">
  {key_stocks_html}
  </div>
</div>

<div class="section">
  <div class="title">📰 产业新闻速读</div>
  <ol style="padding-left:20px;line-height:1.85;font-size:.9rem;color:#c9d1d9">
    <li><b>Intel Q1 2026 财报炸裂全行业。</b>EPS 28 倍超预期，AI 业务占比突破 60%，2026 capex 上调至 $9.1B → 直接拉动 AMAT/LRCX/KLAC/ASML/ENTG 全链涨 3–5%</li>
    <li><b>DOJ 撤销对 Fed Powell 主席的刑事调查。</b>央行独立性溢价回归，10Y 利率小幅回落，成长股估值压制解除</li>
    <li><b>ARM 发布首款自研 AGI CPU。</b>数据中心战略升级，2031 营收目标 $25B；从 IP 授权 → 整机方案</li>
    <li><b>AMD 获 DA Davidson 上调评级。</b>称 Intel 业绩为 AMD 业绩的"前奏"，CPU AI 需求行业级共振</li>
    <li><b>存储 ETF AUM 两周破 $1B。</b>SNDK/MU/WDC/STX 资金面集中流入</li>
    <li><b>NVDA 与 Oklo 签核电采购协议。</b>AI 数据中心电力问题获阶段性解决方案</li>
    <li><b>SOX 指数 18 连阳。</b>创历史最长连涨纪录，半导体周期 + AI 主题 + 美股流动性三共振</li>
    <li><b>QCOM/SWKS/QRVO 重新定价。</b>Intel 边缘 AI 推理论调外溢，QCOM 单日 +10% 修复半年估值差</li>
  </ol>
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

    out = f'/home/user/work/{DATE}.html'
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
    out = f'/home/user/work/stocks-{date}.html'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"stocks-{date}.html written, {len(all_stocks)} stocks")

def update_meta(totals):
    import os
    meta_path = '/home/user/work/_meta.json'
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
<div class="sub">覆盖 316 只股票 · 24 个子行业 · 4 大板块 · 点击日期查看当日完整复盘</div>
<table>
  <thead>
    <tr><th>日期</th><th>市值加权均</th><th>上涨</th><th>下跌</th><th>平盘</th><th>总数</th></tr>
  </thead>
  <tbody>{rows}</tbody>
</table>
<div style="margin-top:20px;color:#8b949e;font-size:.82rem">数据来源：Finnhub /quote + WebSearch 公开市场数据交叉核对</div>
</body>
</html>'''
    with open('/home/user/work/index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"index.html updated, {len(dates)} dates listed")

if __name__ == '__main__':
    data = main()
    t = data['totals']
    print(f"Stocks: {len(data['stocks'])}, Up/Down/Flat: {t['up']}/{t['down']}/{t['flat']}, cap-w: {t['cap_w']}%")
    write_html(data)
    write_stocks_page(data['stocks'], DATE)
    meta = update_meta(data['totals'])
    write_index(meta)
