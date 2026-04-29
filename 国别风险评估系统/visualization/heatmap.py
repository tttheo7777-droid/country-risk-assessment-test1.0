"""
国别风险评估系统 - 热力图模块
功能：区域内多国风险对比热力图，按维度着色，支持排名
"""
import plotly.graph_objects as go
from config import DIMENSION_LABELS, RISK_COLORS
from engine.scoring import calculate_total_score, classify_risk_level
from data.country_data import get_country_list, get_country_data


def create_heatmap(region, top_n=None):
    """创建区域风险对比热力图。

    Args:
        region: 区域名称（如 "东南亚"、"非洲"）
        top_n:  仅显示前N个国家（按总分排序），None=显示全部

    Returns:
        plotly.graph_objects.Figure | None: 热力图对象，区域无国家时返回None
    """
    # 获取区域内所有国家
    countries = get_country_list(region_filter=region)
    if not countries:
        return None

    # 为每个国家计算评分
    scored = []
    for c in countries:
        data = get_country_data(c["iso3"])
        if data is None:
            continue
        result = calculate_total_score(data)
        scored.append({
            "name_cn": c["name_cn"],
            "iso3": c["iso3"],
            "total_score": result["total_score"],
            "risk_level": result["risk_level"],
            "dimension_scores": result["dimension_scores"],
        })

    if not scored:
        return None

    # 按总分降序排列（高风险在前）
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    if top_n:
        scored = scored[:top_n]

    country_names = [s["name_cn"] for s in scored]
    dim_keys = list(DIMENSION_LABELS.keys())
    dim_labels = [DIMENSION_LABELS[k] for k in dim_keys]

    # 构建热力图数据矩阵
    z_data = []
    hover_texts = []
    for s in scored:
        row = []
        row_hover = []
        for dk in dim_keys:
            val = s["dimension_scores"].get(dk, 0)
            row.append(val)
            level = classify_risk_level(val)
            row_hover.append(
                f"<b>{s['name_cn']}</b><br>"
                f"维度: {DIMENSION_LABELS[dk]}<br>"
                f"得分: {val:.1f}<br>"
                f"等级: {level}"
            )
        z_data.append(row)
        hover_texts.append(row_hover)

    # 自定义色阶：绿→黄→橙→红
    custom_colorscale = [
        [0.0, "#2E7D32"],      # 0分 绿
        [0.4, "#F9A825"],      # 40分 黄
        [0.6, "#EF6C00"],      # 60分 橙
        [0.8, "#C62828"],      # 80分 红
        [1.0, "#8B0000"],      # 100分 深红
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=dim_labels,
        y=country_names,
        colorscale=custom_colorscale,
        zmin=0,
        zmax=100,
        text=[[f"{v:.0f}" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        customdata=hover_texts,
        hovertemplate="%{customdata}<extra></extra>",
        colorbar=dict(
            title=dict(text="风险分", font=dict(size=11)),
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0 低", "20", "40 中", "60", "80 高", "100 极高"],
            len=0.8,
            outlinewidth=1,
        ),
    ))

    # 总分标注（右侧）
    annotations = []
    for i, s in enumerate(scored):
        level_color = RISK_COLORS.get(s["risk_level"], "#666")
        annotations.append(dict(
            x=len(dim_labels) - 0.3,
            y=i,
            text=f"<b>{s['total_score']:.0f}</b>",
            showarrow=False,
            font=dict(size=12, color=level_color),
            xanchor="left",
        ))

    fig.update_layout(
        title=dict(
            text=f"<b>{region}</b> 区域风险对比热力图（{len(scored)} 国）",
            x=0.5,
            font=dict(size=16),
        ),
        xaxis=dict(
            title="",
            tickangle=-20,
            tickfont=dict(size=10),
            side="top",
        ),
        yaxis=dict(
            title="",
            tickfont=dict(size=11),
            autorange="reversed",
        ),
        annotations=annotations,
        height=max(400, 35 * len(scored) + 120),
        margin=dict(l=60, r=60, t=60, b=40),
    )

    return fig


def create_global_top_heatmap(top_n=15):
    """创建全球最高风险国家热力图。

    Args:
        top_n: 显示前N个最高风险国家

    Returns:
        plotly.graph_objects.Figure
    """
    all_countries = get_country_list()
    scored = []
    for c in all_countries:
        data = get_country_data(c["iso3"])
        if data is None:
            continue
        result = calculate_total_score(data)
        scored.append({
            "name_cn": c["name_cn"],
            "total_score": result["total_score"],
            "risk_level": result["risk_level"],
            "dimension_scores": result["dimension_scores"],
        })

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    top = scored[:top_n]

    dim_keys = list(DIMENSION_LABELS.keys())
    dim_labels = [DIMENSION_LABELS[k] for k in dim_keys]
    z_data = [[s["dimension_scores"].get(dk, 0) for dk in dim_keys] for s in top]

    custom_colorscale = [
        [0.0, "#2E7D32"], [0.4, "#F9A825"], [0.6, "#EF6C00"],
        [0.8, "#C62828"], [1.0, "#8B0000"],
    ]

    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=dim_labels,
        y=[s["name_cn"] for s in top],
        colorscale=custom_colorscale,
        zmin=0, zmax=100,
        text=[[f"{v:.0f}" for v in row] for row in z_data],
        texttemplate="%{text}",
        textfont=dict(size=11, color="white"),
        hovertemplate="<b>%{y}</b><br>%{x}: %{z:.1f}<extra></extra>",
        colorbar=dict(
            title=dict(text="风险分", font=dict(size=11)),
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0", "20", "40", "60", "80", "100"],
            len=0.8,
        ),
    ))

    fig.update_layout(
        title=dict(text=f"<b>全球最高风险 Top {top_n}</b> 国家热力图", x=0.5, font=dict(size=16)),
        xaxis=dict(title="", tickangle=-20, tickfont=dict(size=10), side="top"),
        yaxis=dict(title="", tickfont=dict(size=11), autorange="reversed"),
        height=550,
        margin=dict(l=60, r=40, t=60, b=30),
    )

    return fig
