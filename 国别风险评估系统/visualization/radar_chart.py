"""
国别风险评估系统 - 雷达图模块
功能：五维度雷达图（Plotly），含±5置信区间（模拟数据误差）
"""
import plotly.graph_objects as go
from config import DIMENSION_LABELS, RISK_COLORS
from engine.scoring import classify_risk_level


def create_radar_chart(result, country_name):
    """创建五维度风险雷达图（含±5置信区间）。

    Args:
        result:       calculate_total_score() 返回的评分结果字典
        country_name: 国家中文名

    Returns:
        plotly.graph_objects.Figure: 可渲染或导出的雷达图对象
    """
    dim_keys = list(DIMENSION_LABELS.keys())
    categories = [DIMENSION_LABELS[k] for k in dim_keys]
    scores = [result["dimension_scores"].get(k, 0) for k in dim_keys]

    # 置信区间：±5分
    upper = [min(100, s + 5) for s in scores]
    lower = [max(0, s - 5) for s in scores]

    fig = go.Figure()

    # 置信区间带（上界）
    fig.add_trace(go.Scatterpolar(
        r=upper + [upper[0]],
        theta=categories + [categories[0]],
        fill="tonext",
        fillcolor="rgba(180, 180, 180, 0.25)",
        line=dict(color="rgba(180, 180, 180, 0)", width=0),
        name="置信上界 (+5)",
        hoverinfo="skip",
    ))

    # 置信区间带（下界）
    fig.add_trace(go.Scatterpolar(
        r=lower + [lower[0]],
        theta=categories + [categories[0]],
        fill="tonext",
        fillcolor="rgba(255, 255, 255, 1)",
        line=dict(color="rgba(180, 180, 180, 0)", width=0),
        name="置信下界 (-5)",
        hoverinfo="skip",
    ))

    # 主数据线
    fig.add_trace(go.Scatterpolar(
        r=scores + [scores[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(220, 38, 38, 0.15)",
        line=dict(color="#C62828", width=2.5),
        marker=dict(size=6, color="#C62828"),
        name=f"{country_name} 风险评估",
        hovertemplate="<b>%{theta}</b><br>得分: %{r:.1f}<br>置信区间: %{customdata[0]:.1f} ~ %{customdata[1]:.1f}<extra></extra>",
        customdata=[(l, u) for l, u in zip(lower, upper)],
    ))

    # 风险等级环形标注（40/60/80 参考线）
    for level_val, level_name, color in [(40, "低/中", "#F9A825"), (60, "中/高", "#EF6C00"), (80, "高/极高", "#C62828")]:
        fig.add_trace(go.Scatterpolar(
            r=[level_val] * (len(categories) + 1),
            theta=categories + [categories[0]],
            mode="lines",
            line=dict(color=color, width=1, dash="dot"),
            name=f"{level_name}风险阈值({level_val}分)",
            hoverinfo="skip",
            showlegend=False,
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickvals=[0, 20, 40, 60, 80, 100],
                ticktext=["0", "20", "40", "60", "80", "100"],
                gridcolor="#E0E0E0",
                linecolor="#CCC",
            ),
            angularaxis=dict(
                rotation=90,
                direction="clockwise",
                gridcolor="#E0E0E0",
                linecolor="#CCC",
            ),
        ),
        title=dict(
            text=f"<b>{country_name}</b> 五维度风险雷达图",
            x=0.5,
            font=dict(size=16),
        ),
        showlegend=True,
        legend=dict(x=1.05, y=0.5),
        margin=dict(l=60, r=60, t=60, b=40),
        height=500,
    )

    return fig
