"""
国别风险评估系统 - 全球120+国家模拟基准数据库
包含：国家元数据列表、模拟指标生成器、数据查询接口
数据来源标注：基于世界银行WGI/WDI、IMF IFS、UNODC、GTI、GPI、UCDP、
              OFAC SDN List、OECD FDI等国际指标模拟值（无网络依赖）
"""
import random
import hashlib
import math
from typing import Optional

from config import REGIONS as _CONFIG_REGIONS

# ==================== 120+国家元数据列表 ====================
# 格式：(ISO3, 中文名, 英文名, 所属区域, 风险基准等级)
_COUNTRY_REGISTRY = [
    # --- 东亚 (8) ---
    ("CHN", "中国", "China", "东亚", "low"),
    ("JPN", "日本", "Japan", "东亚", "low"),
    ("KOR", "韩国", "South Korea", "东亚", "low"),
    ("MNG", "蒙古", "Mongolia", "东亚", "medium"),
    ("PRK", "朝鲜", "North Korea", "东亚", "extreme"),
    ("TWN", "中国台湾", "Taiwan", "东亚", "low"),
    ("HKG", "中国香港", "Hong Kong", "东亚", "low"),
    ("MAC", "中国澳门", "Macau", "东亚", "low"),

    # --- 东南亚 (11) ---
    ("SGP", "新加坡", "Singapore", "东南亚", "low"),
    ("MYS", "马来西亚", "Malaysia", "东南亚", "medium"),
    ("THA", "泰国", "Thailand", "东南亚", "medium"),
    ("IDN", "印度尼西亚", "Indonesia", "东南亚", "medium"),
    ("VNM", "越南", "Vietnam", "东南亚", "medium"),
    ("PHL", "菲律宾", "Philippines", "东南亚", "medium"),
    ("MMR", "缅甸", "Myanmar", "东南亚", "extreme"),
    ("KHM", "柬埔寨", "Cambodia", "东南亚", "medium"),
    ("LAO", "老挝", "Laos", "东南亚", "high"),
    ("BRN", "文莱", "Brunei", "东南亚", "low"),
    ("TLS", "东帝汶", "Timor-Leste", "东南亚", "medium"),

    # --- 南亚 (8) ---
    ("IND", "印度", "India", "南亚", "medium"),
    ("PAK", "巴基斯坦", "Pakistan", "南亚", "high"),
    ("BGD", "孟加拉国", "Bangladesh", "南亚", "high"),
    ("LKA", "斯里兰卡", "Sri Lanka", "南亚", "high"),
    ("NPL", "尼泊尔", "Nepal", "南亚", "medium"),
    ("BTN", "不丹", "Bhutan", "南亚", "medium"),
    ("MDV", "马尔代夫", "Maldives", "南亚", "medium"),
    ("AFG", "阿富汗", "Afghanistan", "南亚", "extreme"),

    # --- 中亚 (5) ---
    ("KAZ", "哈萨克斯坦", "Kazakhstan", "中亚", "medium"),
    ("UZB", "乌兹别克斯坦", "Uzbekistan", "中亚", "high"),
    ("TKM", "土库曼斯坦", "Turkmenistan", "中亚", "high"),
    ("KGZ", "吉尔吉斯斯坦", "Kyrgyzstan", "中亚", "high"),
    ("TJK", "塔吉克斯坦", "Tajikistan", "中亚", "high"),

    # --- 中东 (15) ---
    ("SAU", "沙特阿拉伯", "Saudi Arabia", "中东", "medium"),
    ("ARE", "阿联酋", "UAE", "中东", "low"),
    ("QAT", "卡塔尔", "Qatar", "中东", "low"),
    ("KWT", "科威特", "Kuwait", "中东", "medium"),
    ("OMN", "阿曼", "Oman", "中东", "medium"),
    ("BHR", "巴林", "Bahrain", "中东", "medium"),
    ("IRN", "伊朗", "Iran", "中东", "extreme"),
    ("IRQ", "伊拉克", "Iraq", "中东", "extreme"),
    ("SYR", "叙利亚", "Syria", "中东", "extreme"),
    ("YEM", "也门", "Yemen", "中东", "extreme"),
    ("JOR", "约旦", "Jordan", "中东", "medium"),
    ("LBN", "黎巴嫩", "Lebanon", "中东", "high"),
    ("ISR", "以色列", "Israel", "中东", "high"),
    ("PSE", "巴勒斯坦", "Palestine", "中东", "extreme"),
    ("TUR", "土耳其", "Turkey", "中东", "high"),

    # --- 非洲 (35) ---
    ("ZAF", "南非", "South Africa", "非洲", "medium"),
    ("NGA", "尼日利亚", "Nigeria", "非洲", "high"),
    ("EGY", "埃及", "Egypt", "非洲", "high"),
    ("DZA", "阿尔及利亚", "Algeria", "非洲", "high"),
    ("MAR", "摩洛哥", "Morocco", "非洲", "medium"),
    ("TUN", "突尼斯", "Tunisia", "非洲", "medium"),
    ("LBY", "利比亚", "Libya", "非洲", "extreme"),
    ("SDN", "苏丹", "Sudan", "非洲", "extreme"),
    ("SSD", "南苏丹", "South Sudan", "非洲", "extreme"),
    ("ETH", "埃塞俄比亚", "Ethiopia", "非洲", "high"),
    ("KEN", "肯尼亚", "Kenya", "非洲", "high"),
    ("TZA", "坦桑尼亚", "Tanzania", "非洲", "medium"),
    ("UGA", "乌干达", "Uganda", "非洲", "high"),
    ("RWA", "卢旺达", "Rwanda", "非洲", "medium"),
    ("BDI", "布隆迪", "Burundi", "非洲", "high"),
    ("COD", "刚果(金)", "DR Congo", "非洲", "extreme"),
    ("COG", "刚果(布)", "Congo Republic", "非洲", "high"),
    ("AGO", "安哥拉", "Angola", "非洲", "high"),
    ("MOZ", "莫桑比克", "Mozambique", "非洲", "high"),
    ("ZMB", "赞比亚", "Zambia", "非洲", "medium"),
    ("ZWE", "津巴布韦", "Zimbabwe", "非洲", "high"),
    ("BWA", "博茨瓦纳", "Botswana", "非洲", "medium"),
    ("NAM", "纳米比亚", "Namibia", "非洲", "medium"),
    ("GHA", "加纳", "Ghana", "非洲", "medium"),
    ("CIV", "科特迪瓦", "Cote d'Ivoire", "非洲", "medium"),
    ("SEN", "塞内加尔", "Senegal", "非洲", "medium"),
    ("MLI", "马里", "Mali", "非洲", "extreme"),
    ("NER", "尼日尔", "Niger", "非洲", "extreme"),
    ("TCD", "乍得", "Chad", "非洲", "extreme"),
    ("CMR", "喀麦隆", "Cameroon", "非洲", "high"),
    ("GAB", "加蓬", "Gabon", "非洲", "medium"),
    ("GIN", "几内亚", "Guinea", "非洲", "high"),
    ("BFA", "布基纳法索", "Burkina Faso", "非洲", "extreme"),
    ("SOM", "索马里", "Somalia", "非洲", "extreme"),
    ("MDG", "马达加斯加", "Madagascar", "非洲", "medium"),

    # --- 欧洲 (20) ---
    ("GBR", "英国", "United Kingdom", "欧洲", "low"),
    ("FRA", "法国", "France", "欧洲", "low"),
    ("DEU", "德国", "Germany", "欧洲", "low"),
    ("ITA", "意大利", "Italy", "欧洲", "medium"),
    ("ESP", "西班牙", "Spain", "欧洲", "low"),
    ("PRT", "葡萄牙", "Portugal", "欧洲", "medium"),
    ("NLD", "荷兰", "Netherlands", "欧洲", "low"),
    ("BEL", "比利时", "Belgium", "欧洲", "low"),
    ("CHE", "瑞士", "Switzerland", "欧洲", "low"),
    ("SWE", "瑞典", "Sweden", "欧洲", "low"),
    ("NOR", "挪威", "Norway", "欧洲", "low"),
    ("DNK", "丹麦", "Denmark", "欧洲", "low"),
    ("FIN", "芬兰", "Finland", "欧洲", "low"),
    ("POL", "波兰", "Poland", "欧洲", "medium"),
    ("CZE", "捷克", "Czech Republic", "欧洲", "low"),
    ("HUN", "匈牙利", "Hungary", "欧洲", "medium"),
    ("ROU", "罗马尼亚", "Romania", "欧洲", "medium"),
    ("GRC", "希腊", "Greece", "欧洲", "medium"),
    ("UKR", "乌克兰", "Ukraine", "欧洲", "extreme"),
    ("RUS", "俄罗斯", "Russia", "欧洲", "extreme"),

    # --- 北美 (3) ---
    ("USA", "美国", "United States", "北美", "low"),
    ("CAN", "加拿大", "Canada", "北美", "low"),
    ("MEX", "墨西哥", "Mexico", "北美", "high"),

    # --- 南美 (12) ---
    ("BRA", "巴西", "Brazil", "南美", "medium"),
    ("ARG", "阿根廷", "Argentina", "南美", "high"),
    ("CHL", "智利", "Chile", "南美", "medium"),
    ("PER", "秘鲁", "Peru", "南美", "medium"),
    ("COL", "哥伦比亚", "Colombia", "南美", "high"),
    ("VEN", "委内瑞拉", "Venezuela", "南美", "extreme"),
    ("ECU", "厄瓜多尔", "Ecuador", "南美", "medium"),
    ("BOL", "玻利维亚", "Bolivia", "南美", "high"),
    ("PRY", "巴拉圭", "Paraguay", "南美", "medium"),
    ("URY", "乌拉圭", "Uruguay", "南美", "low"),
    ("GUY", "圭亚那", "Guyana", "南美", "medium"),
    ("SUR", "苏里南", "Suriname", "南美", "medium"),

    # --- 大洋洲 (6) ---
    ("AUS", "澳大利亚", "Australia", "大洋洲", "low"),
    ("NZL", "新西兰", "New Zealand", "大洋洲", "low"),
    ("PNG", "巴布亚新几内亚", "Papua New Guinea", "大洋洲", "high"),
    ("FJI", "斐济", "Fiji", "大洋洲", "medium"),
    ("SLB", "所罗门群岛", "Solomon Islands", "大洋洲", "medium"),
    ("VUT", "瓦努阿图", "Vanuatu", "大洋洲", "medium"),
]

# ==================== 风险基准参数（用于模拟数据生成） ====================
# 每个风险等级对应的指标基准范围 (min, max)
_RISK_PROFILE_PARAMS = {
    "low": {
        "regime_change_frequency": (5, 20),
        "policy_continuity": (5, 25),
        "corruption_level": (5, 30),
        "debt_to_gdp": (15, 45),
        "exchange_rate_volatility": (1, 8),
        "inflation_rate": (1, 15),
        "homicide_rate": (1, 10),
        "terrorism_frequency": (0, 2),
        "social_safety_satisfaction": (5, 25),
        "major_power_alliance": (5, 20),
        "regional_conflict_involvement": (0, 15),
        "foreign_policy_orientation": (5, 25),
        "ofac_eu_sanctions_match": (0, 10),
        "anti_extraterritorial_compliance": (5, 20),
        "fdi_restrictiveness": (5, 25),
        "special_flags": {"ofac": False, "conflict": False, "hostility": False},
    },
    "medium": {
        "regime_change_frequency": (20, 45),
        "policy_continuity": (25, 50),
        "corruption_level": (30, 55),
        "debt_to_gdp": (40, 60),
        "exchange_rate_volatility": (8, 15),
        "inflation_rate": (15, 35),
        "homicide_rate": (10, 30),
        "terrorism_frequency": (2, 5),
        "social_safety_satisfaction": (25, 50),
        "major_power_alliance": (25, 50),
        "regional_conflict_involvement": (15, 40),
        "foreign_policy_orientation": (25, 50),
        "ofac_eu_sanctions_match": (10, 30),
        "anti_extraterritorial_compliance": (25, 50),
        "fdi_restrictiveness": (25, 50),
        "special_flags": {"ofac": False, "conflict": False, "hostility": False},
    },
    "high": {
        "regime_change_frequency": (45, 70),
        "policy_continuity": (50, 75),
        "corruption_level": (55, 80),
        "debt_to_gdp": (55, 80),
        "exchange_rate_volatility": (15, 30),
        "inflation_rate": (35, 60),
        "homicide_rate": (30, 55),
        "terrorism_frequency": (5, 10),
        "social_safety_satisfaction": (50, 75),
        "major_power_alliance": (50, 75),
        "regional_conflict_involvement": (35, 65),
        "foreign_policy_orientation": (50, 75),
        "ofac_eu_sanctions_match": (30, 60),
        "anti_extraterritorial_compliance": (55, 75),
        "fdi_restrictiveness": (50, 75),
        "special_flags": {"ofac": False, "conflict": False, "hostility": False},
    },
    "extreme": {
        "regime_change_frequency": (70, 95),
        "policy_continuity": (75, 95),
        "corruption_level": (75, 98),
        "debt_to_gdp": (75, 95),
        "exchange_rate_volatility": (25, 50),
        "inflation_rate": (55, 95),
        "homicide_rate": (50, 85),
        "terrorism_frequency": (8, 20),
        "social_safety_satisfaction": (70, 95),
        "major_power_alliance": (75, 95),
        "regional_conflict_involvement": (60, 95),
        "foreign_policy_orientation": (70, 95),
        "ofac_eu_sanctions_match": (55, 95),
        "anti_extraterritorial_compliance": (75, 95),
        "fdi_restrictiveness": (70, 95),
        "special_flags": {"ofac": False, "conflict": False, "hostility": False},
    },
}

# 特定国家特殊标记覆盖
_COUNTRY_SPECIAL_FLAGS = {
    "PRK": {"ofac": True, "conflict": False, "hostility": True},
    "IRN": {"ofac": True, "conflict": False, "hostility": True},
    "SYR": {"ofac": True, "conflict": True, "hostility": True},
    "RUS": {"ofac": True, "conflict": True, "hostility": True},
    "AFG": {"ofac": False, "conflict": True, "hostility": False},
    "YEM": {"ofac": False, "conflict": True, "hostility": False},
    "MMR": {"ofac": True, "conflict": True, "hostility": False},
    "VEN": {"ofac": True, "conflict": False, "hostility": True},
    "SDN": {"ofac": True, "conflict": True, "hostility": False},
    "SOM": {"ofac": False, "conflict": True, "hostility": False},
    "UKR": {"ofac": False, "conflict": True, "hostility": False},
    "PSE": {"ofac": False, "conflict": True, "hostility": False},
    "IRQ": {"ofac": False, "conflict": True, "hostility": False},
    "LBY": {"ofac": False, "conflict": True, "hostility": False},
    "MLI": {"ofac": False, "conflict": True, "hostility": False},
    "COD": {"ofac": False, "conflict": True, "hostility": False},
}

# 随机种子确保模拟数据一致性
_SEED = 42


def _generate_yearly_values(seed_key, base_min, base_max, years=3, volatility=5):
    """为单个子指标生成3年模拟值（含波动与趋势）。

    Args:
        seed_key: 用于种子的唯一键（如 iso3 + 指标名），确保同一指标每次生成一致
        base_min: 基准下限
        base_max: 基准上限
        years: 年数（默认3）
        volatility: 年际波动幅度

    Returns:
        list[float]: 各年模拟值（0-100）
    """
    seed_val = int(hashlib.md5(seed_key.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed_val)
    midpoint = (base_min + base_max) / 2
    values = []
    for i in range(years):
        trend = -2 + i * 2  # 轻微趋势：前期偏高、后期偏低（模拟改善）
        noise = rng.uniform(-volatility, volatility)
        val = midpoint + trend + noise
        values.append(round(max(0.0, min(100.0, val)), 1))
    return values


def get_country_list(region_filter=None):
    """获取国家列表，可按区域筛选。

    Args:
        region_filter: 区域名称，None或"全部"返回所有国家

    Returns:
        list[dict]: 国家元数据列表 [{"iso3", "name_cn", "name_en", "region"}, ...]
    """
    result = []
    for iso3, name_cn, name_en, region, risk_level in _COUNTRY_REGISTRY:
        if region_filter and region_filter != "全部" and region != region_filter:
            continue
        result.append({
            "iso3": iso3,
            "name_cn": name_cn,
            "name_en": name_en,
            "region": region,
            "risk_level": risk_level,
        })
    return result


def get_country_data(iso3):
    """根据ISO3代码获取单个国家的完整模拟评估数据。

    Args:
        iso3: ISO 3166-1 alpha-3 国家代码（如 "CHN"）

    Returns:
        dict | None: 包含基本信息、5维度×15子指标×3年数据、特殊标记的完整字典
                     若未找到返回 None

    Example:
        >>> data = get_country_data("AFG")
        >>> data["name_cn"]
        '阿富汗'
        >>> data["indicators"]["political_stability"]["regime_change_frequency"]
        [84.2, 82.7, 80.1]
    """
    # 查找国家元数据
    country = None
    risk_level = None
    for c in _COUNTRY_REGISTRY:
        if c[0] == iso3:
            country = c
            risk_level = c[4]
            break
    if not country:
        return None

    params = _RISK_PROFILE_PARAMS[risk_level]
    flags = _COUNTRY_SPECIAL_FLAGS.get(iso3, params["special_flags"].copy())

    # 为每个子指标生成3年模拟值
    indicators = {}
    dimension_map = {
        "political_stability": ["regime_change_frequency", "policy_continuity", "corruption_level"],
        "economic_financial": ["debt_to_gdp", "exchange_rate_volatility", "inflation_rate"],
        "social_security": ["homicide_rate", "terrorism_frequency", "social_safety_satisfaction"],
        "geopolitical": ["major_power_alliance", "regional_conflict_involvement", "foreign_policy_orientation"],
        "legal_compliance": ["ofac_eu_sanctions_match", "anti_extraterritorial_compliance", "fdi_restrictiveness"],
    }

    for dim, sub_indicators in dimension_map.items():
        indicators[dim] = {}
        for si in sub_indicators:
            bmin, bmax = params[si]
            seed_key = f"{iso3}_{dim}_{si}"
            indicators[dim][si] = _generate_yearly_values(seed_key, bmin, bmax)

    return {
        "iso3": country[0],
        "name_cn": country[1],
        "name_en": country[2],
        "region": country[3],
        "risk_level": risk_level,
        "indicators": indicators,
        "flags": flags,
        "data_source_note": "数据基于世界银行WGI/WDI、IMF IFS、UNODC、GTI、GPI、UCDP、OFAC SDN List、OECD FDI 等国际指标模拟值（2022-2024）",
    }


def get_all_regions():
    """获取所有区域列表（不含"全部"选项）。"""
    return [r for r in _CONFIG_REGIONS if r != "全部"]


def get_country_count():
    """返回数据库中国家总数。"""
    return len(_COUNTRY_REGISTRY)
