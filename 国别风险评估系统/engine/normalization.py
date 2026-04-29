"""
国别风险评估系统 - 指标归一化模块
功能：Min-Max标准化、缺失值处理、数据校验
所有原始指标统一映射至 0-100 风险分（数值越高=风险越大）
"""
from typing import Optional


def min_max_normalize(value, min_bound, max_bound, invert=False):
    """Min-Max标准化：将原始指标值映射至0-100风险分。

    Args:
        value:   原始指标值
        min_bound: 指标合理下限（低于此值截断）
        max_bound: 指标合理上限（高于此值截断）
        invert:  True=低值高风险（如和平指数），False=高值高风险（如通胀率）

    Returns:
        float: 0-100 归一化风险分

    Example:
        >>> min_max_normalize(65, 0, 100)
        65.0
        >>> min_max_normalize(3.2, 0, 10, invert=True)
        68.0
    """
    if max_bound == min_bound:
        return 50.0
    clamped = max(min_bound, min(max_bound, value))
    normalized = (clamped - min_bound) / (max_bound - min_bound) * 100
    return round(100.0 - normalized if invert else normalized, 1)


def normalize_indicator_set(indicator_values, bounds):
    """对一组子指标值执行批量归一化。

    Args:
        indicator_values: {indicator_key: raw_value}  原始值字典
        bounds:           {indicator_key: (min, max, invert)}  归一化参数

    Returns:
        dict: {indicator_key: normalized_score (0-100)}
    """
    result = {}
    for key, raw_value in indicator_values.items():
        if key not in bounds:
            result[key] = raw_value  # 无参数时保持原值
            continue
        bmin, bmax, invert = bounds[key]
        result[key] = min_max_normalize(raw_value, bmin, bmax, invert)
    return result


def handle_missing_values(values, strategy="nearest", fill_value=None):
    """处理指标序列中的缺失值（None/NaN）。

    Args:
        values:   数值列表，可能含 None
        strategy: "nearest"=前向填充, "mean"=均值填充, "fixed"=固定值填充
        fill_value: strategy="fixed"时的填充值

    Returns:
        list: 缺失值已填充的列表

    Example:
        >>> handle_missing_values([10.0, None, 30.0])
        [10.0, 10.0, 30.0]
        >>> handle_missing_values([None, 20.0], strategy="fixed", fill_value=50.0)
        [50.0, 20.0]
    """
    if strategy == "fixed" and fill_value is not None:
        return [fill_value if v is None else v for v in values]
    if strategy == "mean":
        valid = [v for v in values if v is not None]
        mean_val = sum(valid) / len(valid) if valid else 50.0
        return [mean_val if v is None else v for v in values]
    # "nearest" — 前向填充，无前值则后向填充
    result = list(values)
    for i in range(len(result)):
        if result[i] is None:
            # 前向查找
            found = None
            for j in range(i - 1, -1, -1):
                if result[j] is not None:
                    found = result[j]
                    break
            # 后向查找
            if found is None:
                for j in range(i + 1, len(result)):
                    if result[j] is not None:
                        found = result[j]
                        break
            result[i] = found if found is not None else 50.0
    return result


def validate_indicator_data(country_data):
    """校验国家数据结构的完整性。

    Args:
        country_data: get_country_data() 返回的国家数据字典

    Returns:
        tuple[bool, list[str]]: (是否有效, 错误信息列表)
    """
    errors = []
    required_keys = ["iso3", "name_cn", "name_en", "region", "indicators", "flags"]
    for k in required_keys:
        if k not in country_data:
            errors.append(f"缺少必要字段: {k}")

    if "indicators" not in country_data:
        return False, errors

    expected_dims = [
        "political_stability", "economic_financial",
        "social_security", "geopolitical", "legal_compliance",
    ]
    expected_sub_count = 3
    expected_year_count = 3

    for dim in expected_dims:
        if dim not in country_data["indicators"]:
            errors.append(f"缺少维度: {dim}")
            continue
        dim_data = country_data["indicators"][dim]
        if len(dim_data) != expected_sub_count:
            errors.append(f"维度 {dim} 子指标数异常: 期望{expected_sub_count}, 实际{len(dim_data)}")
        for si_key, si_values in dim_data.items():
            cleaned = handle_missing_values(si_values)
            if len(cleaned) != expected_year_count:
                errors.append(f"{dim}.{si_key} 年份数异常: 期望{expected_year_count}, 实际{len(cleaned)}")
            for i, v in enumerate(cleaned):
                if not (0.0 <= v <= 100.0):
                    errors.append(f"{dim}.{si_key} 年份{i} 值越界: {v}")

    return len(errors) == 0, errors


def get_latest_indicators(country_data):
    """从国家数据中提取最新年份（2024）的子指标值。

    Args:
        country_data: 国家完整数据字典

    Returns:
        dict: {dimension_key: {sub_indicator_key: latest_value}}
    """
    result = {}
    for dim_key, dim_data in country_data["indicators"].items():
        result[dim_key] = {}
        for si_key, si_values in dim_data.items():
            cleaned = handle_missing_values(si_values)
            result[dim_key][si_key] = cleaned[-1]  # 最新年份
    return result
