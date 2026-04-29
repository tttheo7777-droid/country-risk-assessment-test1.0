"""
国别风险评估系统 - Streamlit主入口
布局：左侧栏（输入控制） + 中间栏（核心结果） + 右侧栏（风险解读）
模块集成：M1基础界面 + M2评分引擎 + M3可视化 + M4报告生成
"""
import streamlit as st
import pandas as pd
from datetime import date
from ui.sidebar import render_sidebar
from config import (
    DIMENSION_LABELS, INDICATOR_META, RISK_COLORS,
    PRIMARY_WEIGHTS, RISK_LABELS, REGIONS,
)
from engine.scoring import (
    calculate_total_score, classify_risk_level, sensitivity_analysis,
    get_score_breakdown_text,
)
from visualization.radar_chart import create_radar_chart
from visualization.bar_chart import create_bar_chart
from visualization.trend_chart import create_trend_chart
from visualization.heatmap import create_heatmap, create_global_top_heatmap
from report.generator import generate_full_report, export_markdown, export_word, export_pdf


def _render_country_header(country):
    """渲染选中国家的标题信息栏。"""
    st.header(f"{country['name_cn']}（{country['name_en']}）")
    st.caption(f"区域: {country['region']} | ISO代码: {country['iso3']}")
    st.caption(country["data_source_note"])


def _render_score_card(result):
    """渲染综合风险评分卡片。"""
    total = result["total_score"]
    level = result["risk_level"]
    label = result["risk_label"]
    color = RISK_COLORS.get(level, "#666")
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color}22 0%, {color}08 100%);
        border: 2px solid {color}; border-radius: 16px;
        padding: 24px; margin: 8px 0; text-align: center;
    ">
        <div style="font-size: 14px; color: #666; margin-bottom: 4px;">综合风险评分</div>
        <div style="font-size: 64px; font-weight: 700; color: {color}; line-height: 1.1;">{total}</div>
        <div style="font-size: 12px; color: #999;">/ 100</div>
        <div style="
            display: inline-block; background: {color}; color: white;
            padding: 6px 20px; border-radius: 20px;
            font-size: 16px; font-weight: 600; margin-top: 12px;
        ">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_dimension_bars(result):
    """渲染五维度得分HTML柱状条。"""
    st.subheader("分维度得分")
    for dim_key, dim_label in DIMENSION_LABELS.items():
        score = result["dimension_scores"].get(dim_key, 0)
        level = classify_risk_level(score)
        color = RISK_COLORS.get(level, "#666")
        weight = PRIMARY_WEIGHTS.get(dim_key, 0)
        st.markdown(f"""
        <div style="margin: 8px 0;">
            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 2px;">
                <span>{dim_label}</span>
                <span style="color: {color}; font-weight: 600;">{score} 分（权重 {int(weight*100)}%）</span>
            </div>
            <div style="background: #eee; border-radius: 6px; height: 10px;">
                <div style="background: {color}; border-radius: 6px; height: 10px; width: {score}%;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_indicator_table(country):
    """渲染子指标数据表格。"""
    rows = []
    for dim_key, sub_indicators in INDICATOR_META.items():
        dim_label = DIMENSION_LABELS.get(dim_key, dim_key)
        for si_key, si_meta in sub_indicators.items():
            values = country["indicators"].get(dim_key, {}).get(si_key, [])
            rows.append({
                "维度": dim_label,
                "子指标": si_meta["name"],
                "2022": values[0] if len(values) > 0 else "-",
                "2023": values[1] if len(values) > 1 else "-",
                "2024": values[2] if len(values) > 2 else "-",
                "数据来源": si_meta["source"],
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_penalty_details(result):
    """渲染扣分明细展开区。"""
    has_penalties = False
    for notes in result.get("penalty_details", {}).values():
        if notes:
            has_penalties = True
            break
    if not has_penalties:
        st.success("无硬性扣分项触发")
        return
    for dim_key, notes in result.get("penalty_details", {}).items():
        if notes:
            dim_label = DIMENSION_LABELS.get(dim_key, dim_key)
            for note in notes:
                st.warning(f"**{dim_label}**: {note}")


def _render_sensitivity(result, country):
    """渲染敏感性分析区。"""
    st.subheader("敏感性分析（权重 ±5% 影响）")
    sens = sensitivity_analysis(country)
    st.caption(f"当前基准分: **{sens['base_score']}** 分（{sens['base_level']}）")
    if not sens["scenarios"]:
        st.info("无可调整场景")
        return
    rows_sens = []
    for s in sens["scenarios"]:
        rows_sens.append({
            "调整维度": s["dim_label"],
            "权重变化": f"{s['old_weight']*100:.0f}% → {s['new_weight']*100:.0f}%",
            "新总分": s["new_score"],
            "分数变化": f"{s['score_delta']:+.1f}",
            "新等级": s["new_level"],
        })
    st.dataframe(pd.DataFrame(rows_sens), use_container_width=True, hide_index=True)


def _render_right_panel(country, result):
    """渲染右侧风险解读区。"""
    st.header("风险解读")

    if country["flags"].get("ofac"):
        st.error("该国被OFAC列入SDN制裁清单，域外管辖风险可能导致资产冻结，不建议直接投资。")
    if country["flags"].get("conflict"):
        st.error("该国参与区域武装冲突，地缘政治博弈加剧，供应链韧性面临严重挑战。")
    if country["flags"].get("hostility"):
        st.warning("该国与主要大国存在外交摩擦，需关注大国干预风险对外资项目的影响。")

    for dim_key, dim_label in DIMENSION_LABELS.items():
        score = result["dimension_scores"].get(dim_key, 0)
        level = classify_risk_level(score)
        level_label = RISK_LABELS.get(level, level)
        if level == "extreme":
            st.error(f"**{dim_label}**: {score}分（{level_label}）")
        elif level == "high":
            st.warning(f"**{dim_label}**: {score}分（{level_label}）")
        elif level == "medium":
            st.info(f"**{dim_label}**: {score}分（{level_label}）")
        else:
            st.success(f"**{dim_label}**: {score}分（{level_label}）")

    with st.expander("扣分明细"):
        _render_penalty_details(result)

    with st.expander("敏感性分析"):
        _render_sensitivity(result, country)

    with st.expander("风险传导路径与应对建议"):
        from report.templates import generate_risk_pathways, generate_recommendations
        pathways = generate_risk_pathways(country, result)
        for p in pathways:
            st.markdown(p)
        st.divider()
        recs = generate_recommendations(country, result)
        st.caption("**短期建议（0-6个月）**")
        st.markdown(recs["short_term"])
        st.caption("**中期建议（6-24个月）**")
        st.markdown(recs["medium_term"])
        st.caption("**长期建议（24个月以上）**")
        st.markdown(recs["long_term"])


def _render_score_tab(country, result):
    """渲染评分概览标签页：评分卡片 + HTML柱状条 + Plotly雷达图 + Plotly柱状图。"""
    # 第一行：评分卡片 + HTML柱状条
    col_card, col_bars = st.columns([1, 2])
    with col_card:
        _render_score_card(result)
    with col_bars:
        _render_dimension_bars(result)

    st.divider()

    # 第二行：Plotly雷达图 + Plotly柱状图
    col_radar, col_bar = st.columns(2)
    with col_radar:
        fig_radar = create_radar_chart(result, country["name_cn"])
        st.plotly_chart(fig_radar, use_container_width=True, config={
            "toImageButtonOptions": {
                "format": "png", "filename": f"radar_{country['iso3']}",
                "height": 800, "width": 800, "scale": 1,
            }
        })
    with col_bar:
        fig_bar = create_bar_chart(result, country["name_cn"])
        st.plotly_chart(fig_bar, use_container_width=True, config={
            "toImageButtonOptions": {
                "format": "png", "filename": f"bar_{country['iso3']}",
                "height": 600, "width": 800, "scale": 1,
            }
        })


def _render_trend_tab(country):
    """渲染趋势变化标签页：Plotly趋势图 + 维度选择器。"""
    dim_options = list(DIMENSION_LABELS.keys())
    dim_labels = [DIMENSION_LABELS[k] for k in dim_options]
    selected_labels = st.multiselect(
        "选择要显示的维度（留空显示全部）",
        options=dim_labels,
        default=[],
        help="可切换查看特定维度的风险变化趋势",
    )
    selected_keys = [
        dim_options[dim_labels.index(lb)]
        for lb in selected_labels
    ] if selected_labels else None

    fig_trend = create_trend_chart(country, selected_dimensions=selected_keys)
    st.plotly_chart(fig_trend, use_container_width=True, config={
        "toImageButtonOptions": {
            "format": "png", "filename": f"trend_{country['iso3']}",
            "height": 600, "width": 1000, "scale": 1,
        }
    })

    with st.expander("趋势解读"):
        dim_data = country["indicators"]
        for dim_key, dim_label in DIMENSION_LABELS.items():
            dim_vals = dim_data.get(dim_key, {})
            y22 = round(sum(v[0] for v in dim_vals.values()) / 3, 1) if dim_vals else 0
            y24 = round(sum(v[-1] for v in dim_vals.values()) / 3, 1) if dim_vals else 0
            delta = round(y24 - y22, 1)
            direction = "恶化" if delta > 0 else "改善" if delta < 0 else "持平"
            symbol = "" if delta > 2 else "" if delta < -2 else ""
            st.caption(f"{symbol} **{dim_label}**: 2022年{y22}分 → 2024年{y24}分（{direction} {abs(delta)}分）")


def _render_heatmap_tab(country, result):
    """渲染区域对比标签页：同区域国家热力图 + 全球TOP排行。"""
    current_region = country.get("region", "")

    st.subheader(f"{current_region} 区域风险对比")
    fig_region = create_heatmap(current_region)
    if fig_region:
        st.plotly_chart(fig_region, use_container_width=True, config={
            "toImageButtonOptions": {
                "format": "png", "filename": f"heatmap_{current_region}",
                "height": 800, "width": 1000, "scale": 1,
            }
        })
    else:
        st.info(f"暂无{current_region}区域数据")

    st.divider()

    st.subheader("全球最高风险排名 Top 15")
    fig_global = create_global_top_heatmap(top_n=15)
    st.plotly_chart(fig_global, use_container_width=True, config={
        "toImageButtonOptions": {
            "format": "png", "filename": "heatmap_global_top15",
            "height": 800, "width": 1000, "scale": 1,
        }
    })


def _render_mode_score(country, result):
    """评分模式：评分概览 + 指标数据 + 趋势变化。"""
    tab_score, tab_data, tab_trend = st.tabs(["评分概览", "指标数据", "趋势变化"])
    with tab_score:
        _render_score_tab(country, result)
    with tab_data:
        _render_indicator_table(country)
    with tab_trend:
        _render_trend_tab(country)


def _render_mode_visualize(country, result):
    """可视化模式：评分概览 + 雷达/柱状图 + 趋势 + 区域热力图。"""
    tab_score, tab_trend, tab_heatmap = st.tabs(["评分概览与图表", "趋势变化", "区域对比"])
    with tab_score:
        _render_score_tab(country, result)
    with tab_trend:
        _render_trend_tab(country)
    with tab_heatmap:
        _render_heatmap_tab(country, result)


def _render_mode_report(country, result):
    """报告模式：完整评估报告预览 + Markdown/Word 导出下载。"""
    st.subheader("评估报告")

    # 导出按钮
    col_dl1, col_dl2, col_dl3 = st.columns(3)
    report_md = generate_full_report(country, result)

    with col_dl1:
        st.download_button(
            label="下载 Markdown 报告",
            data=report_md,
            file_name=f"风险评估报告_{country['name_cn']}_{date.today().strftime('%Y%m%d')}.md",
            mime="text/markdown",
            help="下载纯文本Markdown格式报告，可直接复制到Word/WPS中使用",
        )

    with col_dl2:
        word_bytes = export_word(country, result)
        if word_bytes:
            st.download_button(
                label="下载 Word 报告",
                data=word_bytes,
                file_name=f"风险评估报告_{country['name_cn']}_{date.today().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                help="下载带格式的Word文档（含表格与专业排版）",
            )
        else:
            st.button("Word 导出不可用", disabled=True,
                      help="请安装 python-docx: pip install python-docx")

    with col_dl3:
        st.button("PDF 导出（待扩展）", disabled=True,
                  help="PDF导出需安装 streamlit-pdf 或 weasyprint")

    st.divider()

    # 报告预览区
    with st.expander("报告全文预览", expanded=True):
        st.markdown(report_md)


def main():
    """主程序入口：配置页面布局，协调三栏渲染。"""
    st.set_page_config(
        page_title="国别风险评估系统",
        page_icon="",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    state = render_sidebar()

    col_center, col_right = st.columns([3, 2])

    if state["selected_country"] is None:
        col_center.warning("请在左侧选择或搜索一个国家开始评估")
        col_right.info("")
        return

    country = state["selected_country"]
    custom_weights = state.get("custom_weights")
    result = calculate_total_score(country, custom_weights)
    mode = state.get("active_mode", "score")

    # ---- 中间栏 ----
    with col_center:
        _render_country_header(country)

        if mode == "score":
            _render_mode_score(country, result)
        elif mode == "visualize":
            _render_mode_visualize(country, result)
        elif mode == "report":
            _render_mode_report(country, result)

    # ---- 右侧栏 ----
    with col_right:
        _render_right_panel(country, result)


if __name__ == "__main__":
    main()
