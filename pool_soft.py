# -*- coding: utf-8 -*-
"""软件建模池 v1（2026-08-12 由用户 Excel「建模池」Sheet 生成，181 只 / 21 子行业 / 6 大板块，核心 96 + 跟踪 85）

来源决策（用户 2026-08-12 拍板）：
- 181 家建模池全量入池，不瘦身；退市/微盘/「需确认」名单全部不进
- SpaceX（SPCX）从「航天/星链」归入「AI算力/数据中心」，与 CoreWeave 同组
- Wind 代码 .O/.N 后缀已剥离为 FMP 符号，2026-08-12 经 FMP batch-quote 验证 181/181 全部命中
"""

INDUSTRY_MAP_SOFT = {
    '云与互联网巨头': ['GOOGL', 'MSFT', 'AMZN', 'META'],  # 4 只
    '企业应用软件': ['ORCL', 'SAP', 'CRM', 'NOW', 'INTU', 'WDAY', 'HUBS', 'NICE', 'OTEX', 'PEGA', 'WK', 'FRSH', 'AVPT', 'APPN', 'VERX', 'BL', 'DCBO'],  # 17 只
    '创意与内容软件': ['ADBE', 'U'],  # 2 只
    'EDA与工程软件': ['CDNS', 'SNPS', 'ADSK', 'PTC', 'BSY', 'AIP'],  # 6 只
    '数据基础设施': ['SNOW', 'MDB', 'NTNX', 'ESTC', 'TDC'],  # 5 只
    'AI应用与数据智能': ['PLTR', 'PATH', 'SOUN', 'AI', 'BBAI', 'CRNC'],  # 6 只
    '网络安全': ['PANW', 'CRWD', 'FTNT', 'ZS', 'OKTA', 'RBRK', 'CHKP', 'SAIL', 'S', 'GEN', 'YOU', 'QLYS', 'CVLT', 'VRNS', 'TENB', 'CLBT', 'ATEN', 'RPD'],  # 18 只
    '开发运维与DevOps': ['DDOG', 'TEAM', 'DT', 'FROG', 'GTLB', 'PRGS', 'PD'],  # 7 只
    '协同办公与通信': ['TWLO', 'ZM', 'DOCU', 'MNDY', 'DBX', 'RNG', 'BOX', 'FIVN', 'ASAN'],  # 9 只
    '营销与广告科技': ['APP', 'ZETA', 'TTD', 'KVYO', 'BRZE', 'RAMP', 'DV', 'CXM', 'AMPL', 'SMWB', 'SPT'],  # 11 只
    '金融科技与支付': ['V', 'MA', 'PYPL', 'FICO', 'BILL', 'ACIW', 'WAY', 'QTWO', 'DAVE', 'NYAX', 'NCNO', 'ALKT', 'PGY'],  # 13 只
    '垂直行业SaaS': ['ROP', 'IOT', 'GWRE', 'TYL', 'MANH', 'PCOR', 'TTAN', 'APPF', 'DSGX', 'AGYS', 'INTA', 'ALRM', 'SPSC', 'BLKB', 'KARO', 'EVCM', 'LSPD'],  # 17 只
    '互联网基础设施': ['NET', 'VRSN', 'AKAM', 'GDDY', 'DOCN', 'WIX', 'FSLY'],  # 7 只
    'AI算力/数据中心': ['NBIS', 'CRWV', 'IREN', 'APLD', 'WULF', 'CIFR', 'CORZ', 'GDS', 'VNET', 'SPCX'],  # 10 只
    '加密矿企与数字资产财库': ['MSTR', 'RIOT', 'MARA', 'CLSK', 'BTDR', 'HIVE', 'BTBT'],  # 7 只
    '消费互联网平台': ['NFLX', 'SHOP', 'BKNG', 'UBER', 'CVNA', 'SE', 'EBAY', 'RDDT', 'GRAB', 'LIF', 'OPRA'],  # 11 只
    '中概/亚洲互联网': ['NTES', 'BIDU', 'BZ', 'BILI', 'JOYY', 'KC', 'ATHM', 'WB', 'IQ', 'MOMO', 'API', 'ZH'],  # 12 只
    'IT服务与咨询': ['IBM', 'ACN', 'INFY', 'CTSH', 'WIT', 'GIB', 'ULS', 'IT', 'DOX', 'EPAM', 'KD', 'GLOB'],  # 12 只
    '自动驾驶与AI出行': ['AUR', 'PONY'],  # 2 只
    '量子计算': ['QBTS', 'QUBT'],  # 2 只
    'IP授权与内容技术': ['IDCC', 'DLB', 'ADEA'],  # 3 只
}

# 跟踪票（正常参与 cap-w，KEY_STOCKS 选卡仅在 |dp|>10% + 可验证催化时纳入）
TRACK_TIER_SOFT = {'ACIW', 'ADEA', 'AGYS', 'AIP', 'ALKT', 'ALRM', 'AMPL', 'API', 'APPN', 'ASAN', 'ATEN', 'ATHM', 'AVPT', 'BBAI', 'BL', 'BLKB', 'BOX', 'BRZE', 'BTBT', 'BTDR', 'CLBT', 'CRNC', 'CVLT', 'CXM', 'DAVE', 'DBX', 'DCBO', 'DLB', 'DOCN', 'DOX', 'DV', 'EPAM', 'EVCM', 'FIVN', 'FRSH', 'FSLY', 'GDS', 'GEN', 'GIB', 'GLOB', 'GRAB', 'HIVE', 'IDCC', 'INTA', 'IQ', 'IT', 'JOYY', 'KARO', 'KC', 'KD', 'LIF', 'LSPD', 'MOMO', 'NCNO', 'NICE', 'NYAX', 'OPRA', 'OTEX', 'PD', 'PEGA', 'PGY', 'PRGS', 'QBTS', 'QLYS', 'QTWO', 'QUBT', 'RAMP', 'RNG', 'RPD', 'SMWB', 'SPSC', 'SPT', 'TDC', 'TENB', 'ULS', 'VERX', 'VNET', 'VRNS', 'WAY', 'WB', 'WIT', 'WIX', 'WK', 'YOU', 'ZH'}

GROUP_MAP_SOFT = {
    '平台与互联网': ['云与互联网巨头', '消费互联网平台', '中概/亚洲互联网'],
    '企业软件': ['企业应用软件', '垂直行业SaaS', '创意与内容软件', 'EDA与工程软件', '协同办公与通信', '开发运维与DevOps'],
    '基础软件与安全': ['数据基础设施', '网络安全', '互联网基础设施'],
    'AI与算力': ['AI应用与数据智能', 'AI算力/数据中心', '量子计算', '自动驾驶与AI出行'],
    '金融与数字资产': ['金融科技与支付', '加密矿企与数字资产财库'],
    '服务与IP': ['IT服务与咨询', '营销与广告科技', 'IP授权与内容技术'],
}
