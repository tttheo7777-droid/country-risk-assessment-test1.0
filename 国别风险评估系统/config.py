"""
国别风险评估系统 - 全局配置模块
包含：权重配置、风险阈值、扣分规则、指标元数据、版本信息
"""

# ==================== 版本与个人信息（预留填写） ====================
VERSION = "1.0.0"
AUTHOR = ""
COURSE = ""

# ==================== 一级维度权重（AHP层次分析法，总和=1.0） ====================
PRIMARY_WEIGHTS = {
    "political_stability": 0.30,
    "economic_financial": 0.25,
    "social_security": 0.15,
    "geopolitical": 0.15,
    "legal_compliance": 0.15,
}

# 维度中英文映射
DIMENSION_LABELS = {
    "political_stability": "政治稳定性与政权更迭风险",
    "economic_financial": "经济金融与债务汇率风险",
    "social_security": "社会治安与恐怖主义风险",
    "geopolitical": "地缘政治与大国干预风险",
    "legal_compliance": "法律合规、域外管辖与制裁风险",
}

# 二级子指标权重（维度内等权）
SUB_INDICATOR_WEIGHT = 1.0 / 3.0

# ==================== 风险等级阈值 ====================
RISK_THRESHOLDS = {
    "low": (0, 40),
    "medium": (41, 60),
    "high": (61, 80),
    "extreme": (81, 100),
}

RISK_LABELS = {
    "low": "低风险",
    "medium": "中风险",
    "high": "高风险",
    "extreme": "极高风险",
}

RISK_COLORS = {
    "low": "#2E7D32",
    "medium": "#F9A825",
    "high": "#EF6C00",
    "extreme": "#C62828",
}

# ==================== 硬性扣分规则 ====================
PENALTY_RULES = {
    "debt_to_gdp_threshold": 60.0,
    "debt_to_gdp_penalty": 30,
    "exchange_rate_volatility_threshold": 15.0,
    "exchange_rate_volatility_penalty": 20,
    "terrorism_high_threshold": 5,
    "terrorism_extreme_threshold": 10,
    "conflict_participation_min_score": 70,
    "major_power_hostility_penalty": 15,
    "ofac_sdn_score": 90,
}

# ==================== 子指标元数据（对标国际标准） ====================
INDICATOR_META = {
    "political_stability": {
        "regime_change_frequency": {"name": "政权更迭频率", "source": "WGI Political Stability & Absence of Violence"},
        "policy_continuity": {"name": "政策连续性", "source": "WGI Government Effectiveness"},
        "corruption_level": {"name": "腐败水平", "source": "TI Corruption Perceptions Index (CPI)"},
    },
    "economic_financial": {
        "debt_to_gdp": {"name": "外债/GDP比率", "source": "World Bank WDI"},
        "exchange_rate_volatility": {"name": "汇率波动率", "source": "IMF IFS"},
        "inflation_rate": {"name": "通胀率", "source": "IMF Global Financial Stability Report"},
    },
    "social_security": {
        "homicide_rate": {"name": "凶杀率", "source": "UNODC"},
        "terrorism_frequency": {"name": "恐怖袭击频次", "source": "GTI Global Terrorism Index"},
        "social_safety_satisfaction": {"name": "社会治安满意度", "source": "GPI Global Peace Index"},
    },
    "geopolitical": {
        "major_power_alliance": {"name": "大国盟友关系", "source": "CSP Global Strategic Assessment"},
        "regional_conflict_involvement": {"name": "区域冲突参与度", "source": "UCDP Conflict Data Program"},
        "foreign_policy_orientation": {"name": "外交政策倾向性", "source": "综合评估"},
    },
    "legal_compliance": {
        "ofac_eu_sanctions_match": {"name": "OFAC/欧盟制裁清单匹配度", "source": "OFAC SDN List / EU Sanctions"},
        "anti_extraterritorial_compliance": {"name": "反不当域外管辖条例适配性", "source": "中国《反外国不当域外管辖条例》"},
        "fdi_restrictiveness": {"name": "外资准入限制", "source": "OECD FDI Regulatory Restrictiveness Index"},
    },
}

# ==================== 区域列表 ====================
REGIONS = ["全部", "东亚", "东南亚", "南亚", "中亚", "中东", "非洲", "欧洲", "北美", "南美", "大洋洲"]
