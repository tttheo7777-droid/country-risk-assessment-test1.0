"""
国别风险评估系统 - 核心评分引擎
功能：AHP加权计算、硬性扣分规则、风险等级判定、敏感性分析
评分函数独立封装，便于后续替换真实数据源
"""
from engine.normalization import get_latest_indicators, validate_indicator_data
from config import (
    PRIMARY_WEIGHTS, SUB_INDICATOR_WEIGHT, RISK_THRESHOLDS,
    PENALTY_RULES, DIMENSION_LABELS, INDICATOR_META,
)


def calculate_dimension_score(dim_key, latest_indicators, country_flags):
    """计算单个维度的风险得分（含硬性扣分规则）。

    Args:
        dim_key:           维度键名（如 "economic_financial"）
        latest_indicators: {dim: {sub_indicator: value}} 最新年份归一化值
        country_flags:     {"ofac": bool, "conflict": bool, "hostility": bool}

    Returns:
        tuple[float, list[str]]: (维度得分(0-100), 扣分说明列表)

    Example:
        >>> indicators = {"economic_financial": {"debt_to_gdp": [65.0], "exchange_rate_volatility": [18.0], "inflation_rate": [30.0]}}
        >>> latest = {"economic_financial": {"debt_to_gdp": 65.0, "exchange_rate_volatility": 18.0, "inflation_rate": 30.0}}
        >>> score, notes = calculate_dimension_score("economic_financial", latest, {})
        >>> "外债/GDP" in notes[0]
        True
    """
    dim_data = latest_indicators.get(dim_key, {})
    if not dim_data:
        return 0.0, ["无数据"]

    # 子指标加权平均（维度内等权）
    sub_scores = []
    sub_keys = list(dim_data.keys())
    for si_key in sub_keys:
        sub_scores.append(dim_data[si_key])

    base_score = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
    penalty_notes = []
    penalty_total = 0.0

    # ---- 经济金融维度专项扣分规则 ----
    if dim_key == "economic_financial":
        debt_val = dim_data.get("debt_to_gdp", 0)
        if debt_val > PENALTY_RULES["debt_to_gdp_threshold"]:
            penalty_total += PENALTY_RULES["debt_to_gdp_penalty"]
            penalty_notes.append(
                f"外债/GDP比率 {debt_val:.1f}% 超过阈值 {PENALTY_RULES['debt_to_gdp_threshold']}%，"
                f"扣除 {PENALTY_RULES['debt_to_gdp_penalty']} 分"
            )

        exchange_val = dim_data.get("exchange_rate_volatility", 0)
        if exchange_val > PENALTY_RULES["exchange_rate_volatility_threshold"]:
            penalty_total += PENALTY_RULES["exchange_rate_volatility_penalty"]
            penalty_notes.append(
                f"汇率年波动率 {exchange_val:.1f}% 超过阈值 {PENALTY_RULES['exchange_rate_volatility_threshold']}%，"
                f"扣除 {PENALTY_RULES['exchange_rate_volatility_penalty']} 分"
            )

    # ---- 社会治安维度恐怖袭击硬性规则 ----
    if dim_key == "social_security":
        terror_val = dim_data.get("terrorism_frequency", 0)
        if terror_val >= PENALTY_RULES["terrorism_extreme_threshold"]:
            # 保底不低于85分
            if base_score < 85.0:
                penalty_notes.append(
                    f"年恐怖袭击 {terror_val:.0f} 次 ≥ {PENALTY_RULES['terrorism_extreme_threshold']} 次，"
                    f"评定为极高风险（保底85分）"
                )
                base_score = max(base_score, 85.0)
        elif terror_val >= PENALTY_RULES["terrorism_high_threshold"]:
            if base_score < 70.0:
                penalty_notes.append(
                    f"年恐怖袭击 {terror_val:.0f} 次 ≥ {PENALTY_RULES['terrorism_high_threshold']} 次，"
                    f"评定为高风险（保底70分）"
                )
                base_score = max(base_score, 70.0)

    # ---- 地缘政治维度专项规则 ----
    if dim_key == "geopolitical":
        conflict_val = dim_data.get("regional_conflict_involvement", 0)
        if country_flags.get("conflict", False):
            if base_score < PENALTY_RULES["conflict_participation_min_score"]:
                penalty_notes.append(
                    f"该国参与区域武装冲突，地缘政治风险保底 {PENALTY_RULES['conflict_participation_min_score']} 分"
                )
                base_score = max(base_score, float(PENALTY_RULES["conflict_participation_min_score"]))

        if country_flags.get("hostility", False):
            penalty_total += PENALTY_RULES["major_power_hostility_penalty"]
            penalty_notes.append(
                f"与主要大国交恶，加扣 {PENALTY_RULES['major_power_hostility_penalty']} 分"
            )

    # ---- 法律合规维度OFAC制裁一票否决 ----
    if dim_key == "legal_compliance":
        if country_flags.get("ofac", False):
            penalty_notes.append(
                f"该国被OFAC列入SDN制裁清单，法律合规风险直接评定为 "
                f"{PENALTY_RULES['ofac_sdn_score']} 分（极高风险）"
            )
            base_score = float(PENALTY_RULES["ofac_sdn_score"])

    final_score = min(100.0, max(0.0, base_score + penalty_total))
    return round(final_score, 1), penalty_notes


def calculate_total_score(country_data, custom_weights=None):
    """计算国别综合风险总分。

    Args:
        country_data:   get_country_data() 返回的完整国家数据
        custom_weights: {dim_key: weight} 可选自定义权重，None则使用默认AHP权重

    Returns:
        dict: {
            "total_score": float,              # 综合风险总分 0-100
            "risk_level": str,                 # "low"/"medium"/"high"/"extreme"
            "risk_label": str,                 # 中文风险等级标签
            "dimension_scores": {dim: float},  # 各维度得分
            "penalty_details": {dim: [str]},   # 各维度扣分说明
            "sub_scores": {dim: {sub: float}}, # 各子指标得分（最新年份）
        }
    """
    is_valid, errors = validate_indicator_data(country_data)
    if not is_valid:
        return {"total_score": 0, "risk_level": "low", "risk_label": "数据异常",
                "dimension_scores": {}, "penalty_details": {}, "sub_scores": {},
                "errors": errors}

    weights = custom_weights if custom_weights else PRIMARY_WEIGHTS.copy()
    latest = get_latest_indicators(country_data)
    flags = country_data.get("flags", {})

    dimension_scores = {}
    all_penalties = {}
    sub_scores = {}

    for dim_key in weights:
        dim_score, penalty_notes = calculate_dimension_score(dim_key, latest, flags)
        dimension_scores[dim_key] = dim_score
        all_penalties[dim_key] = penalty_notes
        sub_scores[dim_key] = latest.get(dim_key, {})

    # 加权求和
    total = 0.0
    for dim_key in weights:
        total += dimension_scores.get(dim_key, 0) * weights[dim_key]

    total = round(total, 1)

    # 风险等级判定
    risk_level = classify_risk_level(total)

    return {
        "total_score": total,
        "risk_level": risk_level,
        "risk_label": _get_risk_label(risk_level),
        "dimension_scores": dimension_scores,
        "penalty_details": all_penalties,
        "sub_scores": sub_scores,
    }


def classify_risk_level(score):
    """根据总分判定风险等级。

    Args:
        score: 综合风险总分 (0-100)

    Returns:
        str: "low" / "medium" / "high" / "extreme"
    """
    if score <= 40:
        return "low"
    elif score <= 60:
        return "medium"
    elif score <= 80:
        return "high"
    else:
        return "extreme"


def _get_risk_label(risk_level):
    """风险等级枚举转中文标签。"""
    from config import RISK_LABELS
    return RISK_LABELS.get(risk_level, risk_level)


def sensitivity_analysis(country_data, vary_dim=None, vary_weight_delta=0.05):
    """敏感性分析：调整维度权重，观察总分变化。

    Args:
        country_data:      国家完整数据
        vary_dim:          要调整的维度键名，None则返回所有维度各±10%的影响
        vary_weight_delta: 权重变化量（默认0.05）

    Returns:
        dict: {
            "base_score": 原始总分,
            "base_weights": 原始权重,
            "scenarios": [{dim_key, new_weight, new_score, score_delta}, ...]
        }
    """
    base_result = calculate_total_score(country_data)
    base_score = base_result["total_score"]
    base_weights = PRIMARY_WEIGHTS.copy()

    scenarios = []
    dims_to_test = [vary_dim] if vary_dim else list(PRIMARY_WEIGHTS.keys())

    for dim_key in dims_to_test:
        if dim_key not in base_weights:
            continue
        # 增加该维度权重（从其他维度均摊扣除）
        for delta in [vary_weight_delta, -vary_weight_delta]:
            new_weights = base_weights.copy()
            old_w = new_weights[dim_key]
            new_w = round(old_w + delta, 4)
            if new_w < 0 or new_w > 1.0:
                continue
            # 将变化量均摊到其他维度
            distribute = -delta / (len(new_weights) - 1)
            for k in new_weights:
                if k == dim_key:
                    continue
                new_weights[k] = round(new_weights[k] + distribute, 4)
            new_weights[dim_key] = new_w

            new_result = calculate_total_score(country_data, new_weights)
            scenarios.append({
                "dim_adjusted": dim_key,
                "dim_label": DIMENSION_LABELS.get(dim_key, dim_key),
                "old_weight": old_w,
                "new_weight": new_w,
                "new_score": new_result["total_score"],
                "score_delta": round(new_result["total_score"] - base_score, 1),
                "new_level": new_result["risk_label"],
            })

    return {
        "base_score": base_score,
        "base_level": base_result["risk_label"],
        "base_weights": {DIMENSION_LABELS.get(k, k): v for k, v in base_weights.items()},
        "scenarios": scenarios,
    }


def get_score_breakdown_text(country_data):
    """生成可读的评分明细文本（供右侧分析面板使用）。

    Args:
        country_data: 国家完整数据

    Returns:
        str: 格式化的评分明细文本
    """
    result = calculate_total_score(country_data)
    if "errors" in result:
        return f"数据异常: {'; '.join(result['errors'])}"

    lines = [
        f"## {country_data['name_cn']}（{country_data['name_en']}）风险评估明细",
        f"**综合风险总分**: {result['total_score']} / 100 分",
        f"**风险等级**: {result['risk_label']}",
        "",
        "### 分维度得分",
    ]

    for dim_key, dim_label in DIMENSION_LABELS.items():
        score = result["dimension_scores"].get(dim_key, 0)
        level = classify_risk_level(score)
        level_label = _get_risk_label(level)
        weight = PRIMARY_WEIGHTS.get(dim_key, 0)
        weighted = round(score * weight, 1)
        lines.append(f"- **{dim_label}**: {score} 分（{level_label}）加权贡献 {weighted} 分")

        # 子指标明细
        subs = result["sub_scores"].get(dim_key, {})
        meta = INDICATOR_META.get(dim_key, {})
        for si_key, si_val in subs.items():
            si_meta = meta.get(si_key, {})
            lines.append(f"  - {si_meta.get('name', si_key)}: {si_val} 分（基于 {si_meta.get('source', '模拟数据')}）")

        # 扣分说明
        penalties = result["penalty_details"].get(dim_key, [])
        for p in penalties:
            lines.append(f"  - 扣分: {p}")

    return "\n".join(lines)
