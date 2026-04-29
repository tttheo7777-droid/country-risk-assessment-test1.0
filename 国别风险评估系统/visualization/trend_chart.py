"""
国别风险评估系统 - 趋势图模块
功能：近3年（2022-2024）五维度风险变化曲线，支持维度切换
"""
import plotly.graph_objects as go
from config import DIMENSION_LABELS


def create_trend_chart(country_data, selected_dimensions=None):
    """创建3年风险变化趋势曲线（Plotly）。

    Args:
        country_data:        get_country_data() 返回的完整国家数据
        selected_dimensions: 要显示的维度键名列表，None=显示全部

    Returns:
        plotly.graph_objects.Figure: 趋势图对象
    """
    years = [2022, 2023, 2024]
    dim_keys = selected_dimensions if selected_dimensions else list(DIMENSION_LABELS.keys())

    # 颜色方案（Plotly默认色板）
    colors = ["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099"]

    fig = go.Figure()

    # 风险区域背景
    zone_configs = [
        (0, 40, "rgba(46,125,50,0.06)", "低风险区"),
        (40, 60, "rgba(249,168,37,0.06)", "中风险区"),
        (60, 80, "rgba(239,108,0,0.06)", "高风险区"),
        (80, 100, "rgba(198,40,40,0.08)", "极高风险区"),
    ]
    for y0, y1, color, name in zone_configs:
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=color, layer="below", line=dict(width=0),
            name=name, showlegend=False,
        )

    for idx, dim_key in enumerate(dim_keys):
        dim_data = country_data["indicators"].get(dim_key, {})
        color = colors[idx % len(colors)]
        # 计算每年3个子指标的平均分
        avg_scores = []
        for year_idx in range(3):
            year_vals = []
            for si_values in dim_data.values():
                if len(si_values) > year_idx:
                    year_vals.append(si_values[year_idx])
            avg = sum(year_vals) / len(year_vals) if year_vals else 0
            avg_scores.append(round(avg, 1))

        dim_label = DIMENSION_LABELS.get(dim_key, dim_key)

        fig.add_trace(go.Scatter(
            x=years,
            y=avg_scores,
            mode="lines+markers",
            name=dim_label,
            line=dict(color=color, width=2.5),
            marker=dict(size=8, color=color, line=dict(width=1, color="white")),
            hovertemplate=(
                f"<b>{dim_label}</b><br>"
                f"%{{x}}: %{{y:.1f}} 分<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(
            text=f"<b>{country_data['name_cn']}</b> 近3年风险趋势变化",
            x=0.5,
            font=dict(size=16),
        ),
        xaxis=dict(
            title="",
            tickmode="array",
            tickvals=years,
            ticktext=[str(y) for y in years],
            dtick=1,
            gridcolor="#E0E0E0",
        ),
        yaxis=dict(
            title="风险得分 (0-100)",
            range=[0, 105],
            tickvals=[0, 20, 40, 60, 80, 100],
            gridcolor="#E0E0E0",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=11),
        ),
        hovermode="x unified",
        height=450,
        margin=dict(l=60, r=20, t=60, b=80),
    )

    return fig


def create_trend_chart_all_dimensions(country_data):
    """快捷函数：显示全部5个维度的趋势图。"""
    return create_trend_chart(country_data, selected_dimensions=None)
