"""
国别风险评估系统 - 柱状图模块
功能：五维度得分柱状图（Plotly），含风险阈值线、颜色映射、数值标注
"""
import plotly.graph_objects as go
from config import DIMENSION_LABELS, RISK_COLORS
from engine.scoring import classify_risk_level


def create_bar_chart(result, country_name):
    """创建五维度得分柱状图（叠加风险阈值线）。

    Args:
        result:       calculate_total_score() 返回的评分结果字典
        country_name: 国家中文名

    Returns:
        plotly.graph_objects.Figure: 可渲染或导出的柱状图对象
    """
    dim_keys = list(DIMENSION_LABELS.keys())
    categories = [DIMENSION_LABELS[k] for k in dim_keys]
    scores = [result["dimension_scores"].get(k, 0) for k in dim_keys]

    # 根据风险等级分配颜色
    bar_colors = []
    for s in scores:
        level = classify_risk_level(s)
        bar_colors.append(RISK_COLORS.get(level, "#666"))

    # 柱状图
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=categories,
        y=scores,
        marker=dict(
            color=bar_colors,
            line=dict(color=[_darken(c) for c in bar_colors], width=1),
        ),
        text=[f"{s:.1f}" for s in scores],
        textposition="outside",
        textfont=dict(size=13, color="#333"),
        name="维度得分",
        hovertemplate="<b>%{x}</b><br>得分: %{y:.1f} / 100<extra></extra>",
    ))

    # 风险阈值线（使用 add_shape 避免 add_hline + annotation 的 xref 冲突）
    thresholds = [
        (40, "#F9A825", "低/中风险 (40分)"),
        (60, "#EF6C00", "中/高风险 (60分)"),
        (80, "#C62828", "高/极高风险 (80分)"),
    ]
    for thresh_val, color, label in thresholds:
        fig.add_shape(
            type="line",
            x0=-0.45, x1=4.45,
            y0=thresh_val, y1=thresh_val,
            line=dict(color=color, width=1.5, dash="dash"),
            layer="above",
        )
        fig.add_annotation(
            x=4.6, y=thresh_val,
            text=label,
            showarrow=False,
            font=dict(size=10, color=color),
            xanchor="left",
        )

    # 风险区域背景色带
    zone_colors = [
        (0, 40, "rgba(46,125,50,0.08)"),    # 低风险绿
        (40, 60, "rgba(249,168,37,0.08)"),    # 中风险黄
        (60, 80, "rgba(239,108,0,0.08)"),     # 高风险橙
        (80, 100, "rgba(198,40,40,0.12)"),    # 极高风险红
    ]
    for y0, y1, color in zone_colors:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color,
            layer="below",
            line=dict(width=0),
            name="",
            showlegend=False,
        )

    fig.update_layout(
        title=dict(
            text=f"<b>{country_name}</b> 五维度风险得分对比",
            x=0.5,
            font=dict(size=16),
        ),
        xaxis=dict(
            title="",
            tickangle=-15,
            tickfont=dict(size=11),
        ),
        yaxis=dict(
            title="风险得分 (0-100)",
            range=[0, 110],
            tickvals=[0, 20, 40, 60, 80, 100],
            gridcolor="#E0E0E0",
        ),
        showlegend=False,
        height=450,
        margin=dict(l=60, r=20, t=60, b=80),
    )

    return fig


def _darken(hex_color, factor=0.8):
    """将十六进制颜色加深指定倍率。"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r, g, b = int(r * factor), int(g * factor), int(b * factor)
    return f"#{r:02x}{g:02x}{b:02x}"
