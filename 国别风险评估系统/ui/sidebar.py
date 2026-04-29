"""
国别风险评估系统 - 左侧栏输入模块
功能：国家模糊查询（Levenshtein编辑距离）、区域筛选、权重自定义滑块、
      Excel数据导入、功能区切换
"""
import streamlit as st
from data.country_data import get_country_list, get_country_data, get_country_count
from config import (
    PRIMARY_WEIGHTS, DIMENSION_LABELS, REGIONS, RISK_THRESHOLDS,
    PENALTY_RULES, VERSION, AUTHOR,
)
from utils.fuzzy_search import fuzzy_search_countries


def _handle_excel_import():
    """处理Excel文件上传与解析，结果存入session_state。"""
    with st.sidebar.expander("Excel数据导入（WDI格式）"):
        uploaded_file = st.file_uploader(
            "上传Excel文件",
            type=["xlsx", "xls"],
            help="支持世界银行WDI格式表格，自动匹配子指标字段",
        )
        if uploaded_file is not None:
            if st.button("解析导入"):
                with st.spinner("正在解析Excel数据..."):
                    from utils.data_import import import_wdi_excel
                    result = import_wdi_excel(uploaded_file.getvalue())
                    if result["success"]:
                        st.session_state["imported_countries"] = result["countries"]
                        st.success(result["message"])
                        if result["unmatched_columns"]:
                            st.caption(f"未匹配列: {', '.join(result['unmatched_columns'][:5])}")
                    else:
                        st.error(result["message"])

        # 清除导入数据
        if st.session_state.get("imported_countries"):
            if st.button("清除导入数据"):
                st.session_state["imported_countries"] = None
                st.rerun()


def render_sidebar():
    """渲染左侧栏全部输入控件，返回用户选择的状态字典。

    Returns:
        dict: {
            "selected_country": dict | None,
            "custom_weights": dict,
            "active_mode": str,
        }
    """
    st.sidebar.title("国别风险评估系统")
    st.sidebar.caption(f"v{VERSION} | 海外利益安全专业评估工具")

    # ---- Excel 导入 ----
    if "imported_countries" not in st.session_state:
        st.session_state["imported_countries"] = None
    _handle_excel_import()

    # ---- 国家选择区 ----
    st.sidebar.header("选择评估国家")

    selected_region = st.sidebar.selectbox(
        "区域筛选",
        options=REGIONS,
        index=0,
        help="按地理区域筛选国家列表",
    )

    # 获取内置国家列表
    countries = get_country_list(
        region_filter=None if selected_region == "全部" else selected_region
    )

    # 合并导入数据
    imported = st.session_state.get("imported_countries") or []
    for imp in imported:
        exists = any(c["iso3"] == imp["iso3"] for c in countries)
        if not exists:
            countries.append({
                "iso3": imp["iso3"],
                "name_cn": f"[导入] {imp['name_cn']}",
                "name_en": imp["name_en"],
                "region": imp["region"],
                "risk_level": "unknown",
                "_imported": True,
                "_data": imp,
            })

    # 构建查找表
    country_lookup = {}
    for c in countries:
        label = f"{c['name_cn']} ({c['name_en']})"
        country_lookup[label] = c

    # 模糊搜索输入
    search_query = st.sidebar.text_input(
        "国家名称（支持模糊匹配）",
        placeholder="输入中文名/英文名/ISO代码...",
        help=f"数据库覆盖 {get_country_count()} 个国家/地区 | 支持编辑距离模糊匹配",
    )

    if search_query:
        query = search_query.strip()
        # 使用Levenshtein编辑距离模糊搜索
        fuzzy_results = fuzzy_search_countries(
            query, limit=30,
            threshold=0.1 if len(query) <= 2 else 0.3,
        )
        # 按区域过滤
        if selected_region != "全部":
            fuzzy_results = [
                r for r in fuzzy_results
                if r["region"] == selected_region
            ]
        # 转换为显示标签
        filtered_labels = [
            f"{r['name_cn']} ({r['name_en']})"
            for r in fuzzy_results
            if f"{r['name_cn']} ({r['name_en']})" in country_lookup
        ]
        # 合并导入数据的匹配
        for imp in imported:
            imp_label = f"[导入] {imp['name_cn']} ({imp['name_en']})"
            if imp_label in country_lookup:
                if query.lower() in imp_label.lower():
                    filtered_labels.insert(0, imp_label)
        if not filtered_labels:
            filtered_labels = list(country_lookup.keys())[:30]
    else:
        filtered_labels = list(country_lookup.keys())

    selected_label = st.sidebar.selectbox(
        f"匹配结果（{len(filtered_labels)} 个国家）",
        options=filtered_labels if filtered_labels else ["未找到匹配国家"],
        help="选择要评估的国家",
    )

    # 加载选中国家的完整数据
    selected_country = None
    if filtered_labels and selected_label in country_lookup:
        entry = country_lookup[selected_label]
        if entry.get("_imported"):
            selected_country = entry["_data"]
        else:
            selected_country = get_country_data(entry["iso3"])

    # ---- 权重自定义区 ----
    st.sidebar.header("指标权重调整")
    st.sidebar.caption("拖动滑块调整一级维度权重（总和自动归一化为100%）")

    custom_weights = {}
    raw_weights = {}
    for dim_key, default_weight in PRIMARY_WEIGHTS.items():
        label = DIMENSION_LABELS.get(dim_key, dim_key)
        raw_weights[dim_key] = st.sidebar.slider(
            f"{label}",
            min_value=0,
            max_value=100,
            value=int(default_weight * 100),
            step=1,
            format="%d%%",
            help=f"默认权重 {int(default_weight * 100)}%",
        )

    total = sum(raw_weights.values())
    if total > 0:
        for dim_key in raw_weights:
            custom_weights[dim_key] = raw_weights[dim_key] / total
    else:
        custom_weights = PRIMARY_WEIGHTS.copy()

    # ---- 功能区切换 ----
    st.sidebar.header("功能模式")
    active_mode = st.sidebar.radio(
        "选择功能",
        options=["score", "visualize", "report"],
        format_func=lambda x: {"score": "风险评分", "visualize": "可视化分析", "report": "生成报告"}[x],
        help="切换核心功能模块",
    )

    # ---- 风险阈值参考 ----
    with st.sidebar.expander("风险等级参考"):
        st.markdown("""
        | 等级 | 分数 |
        |------|------|
        | 低风险 | 0 - 40 |
        | 中风险 | 41 - 60 |
        | 高风险 | 61 - 80 |
        | 极高风险 | 81 - 100 |
        """)

    # ---- 关于 ----
    with st.sidebar.expander("关于本系统"):
        st.markdown(f"""
        **版本**: {VERSION}
        **作者**: {AUTHOR or '待填写'}
        **数据来源**: 基于世界银行WGI/WDI、IMF IFS、UNODC、
        GTI、GPI、UCDP、OFAC SDN List、OECD FDI
        等国际指标模拟值（2022-2024）
        **技术栈**: Python 3.10+ / Streamlit / Pandas / Plotly
        **扩展功能**: 支持Excel WDI格式数据导入
        """)

    return {
        "selected_country": selected_country,
        "custom_weights": custom_weights,
        "active_mode": active_mode,
    }
