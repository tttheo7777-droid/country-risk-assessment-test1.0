"""
国别风险评估系统 - Excel数据导入模块
功能：读取世界银行WDI格式Excel表格，自动匹配子指标字段，
     校验清洗后返回与评分引擎兼容的数据结构
"""
import io
from typing import Optional
from config import INDICATOR_META, DIMENSION_LABELS
from engine.normalization import handle_missing_values, validate_indicator_data


# WDI字段名与系统子指标键名的映射表（支持模糊匹配）
_WDI_FIELD_MAPPING = {
    # 政治稳定性
    "political stability": "regime_change_frequency",
    "government effectiveness": "policy_continuity",
    "corruption perception": "corruption_level",
    "cpi": "corruption_level",
    "wgi political": "regime_change_frequency",
    "wgi government": "policy_continuity",
    "wgi corruption": "corruption_level",
    # 经济金融
    "external debt": "debt_to_gdp",
    "debt to gdp": "debt_to_gdp",
    "debt/gdp": "debt_to_gdp",
    "exchange rate": "exchange_rate_volatility",
    "currency volatility": "exchange_rate_volatility",
    "inflation": "inflation_rate",
    "cpi inflation": "inflation_rate",
    # 社会治安
    "homicide": "homicide_rate",
    "intentional homicide": "homicide_rate",
    "terrorism": "terrorism_frequency",
    "terrorist": "terrorism_frequency",
    "gti": "terrorism_frequency",
    "peace index": "social_safety_satisfaction",
    "gpi": "social_safety_satisfaction",
    "safety satisfaction": "social_safety_satisfaction",
    # 地缘政治
    "alliance": "major_power_alliance",
    "major power": "major_power_alliance",
    "strategic assessment": "major_power_alliance",
    "conflict": "regional_conflict_involvement",
    "ucdp": "regional_conflict_involvement",
    "foreign policy": "foreign_policy_orientation",
    "diplomatic": "foreign_policy_orientation",
    # 法律合规
    "ofac": "ofac_eu_sanctions_match",
    "sanctions": "ofac_eu_sanctions_match",
    "sdn": "ofac_eu_sanctions_match",
    "extraterritorial": "anti_extraterritorial_compliance",
    "anti foreign": "anti_extraterritorial_compliance",
    "fdi restrict": "fdi_restrictiveness",
    "oecd fdi": "fdi_restrictiveness",
    "investment restrict": "fdi_restrictiveness",
}


def _match_field_to_indicator(column_name):
    """将Excel列名匹配到系统子指标键名。

    Args:
        column_name: Excel表头列名

    Returns:
        str | None: 匹配到的子指标键名，或None
    """
    col_lower = column_name.lower().strip()
    # 精确匹配
    if col_lower in _WDI_FIELD_MAPPING:
        return _WDI_FIELD_MAPPING[col_lower]
    # 部分匹配
    for pattern, indicator_key in _WDI_FIELD_MAPPING.items():
        if pattern in col_lower:
            return indicator_key
    return None


def import_wdi_excel(file_bytes_or_path, sheet_name=0):
    """导入世界银行WDI格式Excel文件，自动解析为国家评估数据结构。

    Args:
        file_bytes_or_path: Excel文件的字节内容或文件路径
        sheet_name:         工作表名称或索引（默认第一个sheet）

    Returns:
        dict: {
            "success": bool,
            "message": str,
            "countries": [  # 成功解析的国家列表
                {
                    "iso3": str,
                    "name_cn": str,
                    "name_en": str,
                    "region": str,
                    "indicators": {dim: {sub_indicator: [year_values]}},
                    "flags": {ofac: bool, conflict: bool, hostility: bool},
                }
            ],
            "field_mapping": {excel_col: indicator_key},  # 字段匹配日志
            "unmatched_columns": [str],                     # 未匹配的列
        }

    Example:
        >>> result = import_wdi_excel("world_bank_data.xlsx")
        >>> result["success"]
        True
        >>> len(result["countries"]) > 0
        True
    """
    try:
        import pandas as pd
    except ImportError:
        return {"success": False, "message": "需要安装 pandas 和 openpyxl: pip install pandas openpyxl"}

    try:
        if isinstance(file_bytes_or_path, bytes):
            df = pd.read_excel(io.BytesIO(file_bytes_or_path), sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_bytes_or_path, sheet_name=sheet_name)
    except Exception as e:
        return {"success": False, "message": f"Excel读取失败: {str(e)}"}

    if df.empty:
        return {"success": False, "message": "Excel文件为空"}

    # 识别国家标识列
    country_col = None
    iso_col = None
    year_col = None
    for col in df.columns:
        col_lower = str(col).lower().strip()
        if col_lower in ("country", "country name", "economy", "国家", "国家名称"):
            country_col = col
        elif col_lower in ("iso3", "iso", "country code", "iso code", "代码"):
            iso_col = col
        elif col_lower in ("year", "年份", "date"):
            year_col = col

    if country_col is None and iso_col is None:
        # 尝试将第一列当作国家名
        country_col = df.columns[0]

    # 匹配指标列
    indicator_columns = {}
    unmatched = []
    for col in df.columns:
        if col in (country_col, iso_col, year_col):
            continue
        matched = _match_field_to_indicator(str(col))
        if matched:
            indicator_columns[col] = matched
        else:
            unmatched.append(str(col))

    if not indicator_columns:
        return {
            "success": False,
            "message": f"未找到可匹配的指标列。表格列名: {list(df.columns)}。请确保列名包含WDI标准字段名。",
            "unmatched_columns": unmatched,
        }

    # 将指标列映射到五维度结构
    _INDICATOR_TO_DIM = {}
    for dim_key, sub_dict in INDICATOR_META.items():
        for si_key in sub_dict:
            _INDICATOR_TO_DIM[si_key] = dim_key

    countries = []
    # 按国家分组
    group_col = iso_col if iso_col else country_col
    for group_key, group_df in df.groupby(group_col):
        country_name = group_key
        iso3 = group_key[:3] if len(str(group_key)) >= 3 else str(group_key)

        # 初始化维度结构
        indicators = {}
        for dim_key in DIMENSION_LABELS:
            indicators[dim_key] = {}
            for si_key in INDICATOR_META.get(dim_key, {}):
                indicators[dim_key][si_key] = []

        # 提取指示器值
        for excel_col, si_key in indicator_columns.items():
            dim_key = _INDICATOR_TO_DIM.get(si_key)
            if dim_key is None:
                continue
            values = group_df[excel_col].dropna().tolist()
            values = [float(v) for v in values if v is not None]
            values = handle_missing_values(values, strategy="nearest")
            if len(values) < 3:
                # 补齐至3年
                while len(values) < 3:
                    values.append(values[-1] if values else 50.0)
            values = values[:3]
            indicators[dim_key][si_key] = values

        # 缺失子指标补默认值
        for dim_key in DIMENSION_LABELS:
            for si_key in INDICATOR_META.get(dim_key, {}):
                if not indicators[dim_key].get(si_key):
                    indicators[dim_key][si_key] = [50.0, 50.0, 50.0]

        country_data = {
            "iso3": iso3,
            "name_cn": str(country_name),
            "name_en": str(country_name),
            "region": "导入数据",
            "indicators": indicators,
            "flags": {"ofac": False, "conflict": False, "hostility": False},
            "data_source_note": "用户导入Excel数据（WDI格式）",
        }

        valid, errors = validate_indicator_data(country_data)
        if not valid:
            continue

        countries.append(country_data)

    return {
        "success": True,
        "message": f"成功导入 {len(countries)} 个国家/地区的评估数据，匹配 {len(indicator_columns)} 个指标字段",
        "countries": countries,
        "field_mapping": {str(k): v for k, v in indicator_columns.items()},
        "unmatched_columns": unmatched,
        "total_rows": len(df),
    }
