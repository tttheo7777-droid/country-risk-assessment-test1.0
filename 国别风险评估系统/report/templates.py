"""
国别风险评估系统 - 报告模板模块
功能：执行摘要、分维度分析、风险传导路径、应对建议的结构化模板
"""
from datetime import date
from config import DIMENSION_LABELS, INDICATOR_META, PRIMARY_WEIGHTS, RISK_LABELS, VERSION
from engine.scoring import classify_risk_level


def generate_executive_summary(country_data, result):
    """生成执行摘要（约300字），自动根据评分结果调整表述。

    Args:
        country_data: 国家完整数据
        result:       calculate_total_score() 输出

    Returns:
        str: 格式化的执行摘要文本
    """
    name = country_data["name_cn"]
    ename = country_data["name_en"]
    region = country_data["region"]
    total = result["total_score"]
    level_label = result["risk_label"]

    # 找出得分最高/最低的维度
    dim_scores = result["dimension_scores"]
    sorted_dims = sorted(dim_scores.items(), key=lambda x: x[1], reverse=True)
    top_dim_key, top_dim_score = sorted_dims[0]
    top_dim_label = DIMENSION_LABELS.get(top_dim_key, top_dim_key)
    low_dim_key, low_dim_score = sorted_dims[-1]
    low_dim_label = DIMENSION_LABELS.get(low_dim_key, low_dim_key)

    # 触发扣分的维度
    penalty_dims = [
        DIMENSION_LABELS.get(dk, dk)
        for dk, notes in result.get("penalty_details", {}).items()
        if notes
    ]

    # 制裁/冲突警告
    flags = country_data.get("flags", {})
    warnings = []
    if flags.get("ofac"):
        warnings.append("该国被列入OFAC SDN制裁清单，存在域外管辖风险，可能导致资产冻结或交易受限")
    if flags.get("conflict"):
        warnings.append("该国正参与区域武装冲突，地缘政治风险显著，对海外投资项目人员安全与资产存续构成直接威胁")
    if flags.get("hostility"):
        warnings.append("该国与主要大国存在外交紧张关系，需关注制裁规避与供应链韧性问题")

    # 风险等级判定术语
    if level_label == "极高风险":
        level_desc = f"综合风险评定为**{level_label}**，不建议在该国进行直接投资，已投项目应制定撤资路径与应急预案"
    elif level_label == "高风险":
        level_desc = f"综合风险评定为**{level_label}**，建议严格限制投资规模，投保海外投资保险，并建立常态化风险监测机制"
    elif level_label == "中风险":
        level_desc = f"综合风险评定为**{level_label}**，建议加强尽职调查，关注{top_dim_label}等重点领域，审慎推进投资决策"
    else:
        level_desc = f"综合风险评定为**{level_label}**，总体投资环境相对稳定，可正常开展经贸活动，仍需定期评估{top_dim_label}等潜在风险"

    penalty_text = ""
    if penalty_dims:
        penalty_text = f"评估过程中，{'、'.join(penalty_dims)}维度触发硬性扣分规则，需重点关注。"

    warning_text = "；".join(warnings) if warnings else "未触发制裁或冲突相关硬性预警。"

    today = date.today().strftime("%Y年%m月%d日")

    summary = (
        f"本报告基于世界银行全球治理指标（WGI）、世界发展指标（WDI）、国际货币基金组织（IMF）"
        f"国际金融统计（IFS）、全球恐怖主义指数（GTI）、全球和平指数（GPI）、乌普萨拉冲突数据"
        f"计划（UCDP）、OFAC制裁清单及OECD外资规制指数等国际权威数据源"
        f"（{country_data.get('data_source_note', '')[:50]}），"
        f"对**{name}（{ename}）**的海外利益安全风险进行了系统性评估。"
        f"\n\n"
        f"评估结果显示，{name}综合风险总分为**{total}/100**分，{level_desc}。"
        f"\n\n"
        f"在五个评估维度中，**{top_dim_label}**得分最高（{top_dim_score}分），"
        f"构成该国海外利益安全的首要风险来源；**{low_dim_label}**得分相对较低（{low_dim_score}分）。"
        f"{penalty_text}"
        f"\n\n"
        f"预警信息：{warning_text}"
        f"\n\n"
        f"本报告评估基准日为{today}，数据基于2022-2024年国际指标模拟值，"
        f"仅供学术研究与风险预判参考，不构成投资建议。"
    )
    return summary


def generate_dimension_analysis(dim_key, country_data, result):
    """生成单个维度的详细分析文本。

    Args:
        dim_key:      维度键名
        country_data: 国家完整数据
        result:       calculate_total_score() 输出

    Returns:
        str: 该维度的详细分析（含子指标得分、数据来源、扣分说明）
    """
    dim_label = DIMENSION_LABELS.get(dim_key, dim_key)
    score = result["dimension_scores"].get(dim_key, 0)
    level = classify_risk_level(score)
    level_label = RISK_LABELS.get(level, "")

    subs = result["sub_scores"].get(dim_key, {})
    meta = INDICATOR_META.get(dim_key, {})
    penalties = result.get("penalty_details", {}).get(dim_key, [])

    lines = [f"### {dim_label}", ""]

    # 总体得分
    lines.append(f"**维度得分**: {score}/100 分（{level_label}）")
    lines.append(f"**全局权重**: {int(PRIMARY_WEIGHTS.get(dim_key, 0) * 100)}%")
    lines.append("")

    # 子指标分析
    lines.append("| 子指标 | 得分 | 国际对标数据源 |")
    lines.append("|--------|------|----------------|")
    for si_key, si_val in subs.items():
        si_meta = meta.get(si_key, {})
        si_name = si_meta.get("name", si_key)
        si_source = si_meta.get("source", "模拟数据")
        lines.append(f"| {si_name} | {si_val} | {si_source} |")
    lines.append("")

    # 扣分说明（含专业表述）
    if penalties:
        lines.append("**扣分项分析**:")
        for i, p in enumerate(penalties, 1):
            lines.append(f"{i}. {p}")
        lines.append("")

    # 风险影响分析（专业术语）
    analysis_texts = {
        "political_stability": (
            "政权更迭与政策连续性风险直接影响海外投资项目的法律稳定性与合同执行保障。"
            "腐败水平高企将增加合规成本与寻租风险，可能触发母国《反海外腐败法》等域外管辖法律的适用。"
        ),
        "economic_financial": (
            "外债高企与汇率剧烈波动可能导致汇兑损失与资产减值，甚至触发资本管制措施。"
            "高通胀环境将侵蚀投资项目实际回报率，增加运营成本的不确定性。"
        ),
        "social_security": (
            "高凶杀率与频繁恐怖袭击直接威胁海外人员生命安全与资产物理安全，"
            "将显著推高安保成本与保险费率，并可能触发紧急撤侨预案。"
        ),
        "geopolitical": (
            "区域冲突参与与大国博弈加剧，可能导致该国成为地缘政治博弈前沿，"
            "增加外资项目被政治化风险与第三方制裁的连带影响。"
        ),
        "legal_compliance": (
            "被列入国际制裁清单将导致交易对手方风险飙升，金融机构可能拒绝提供跨境结算服务。"
            "外资准入限制与域外管辖法律的叠加效应，将显著增加合规成本与法律风险。"
        ),
    }
    lines.append("**风险影响分析**:")
    lines.append(analysis_texts.get(dim_key, "该维度风险需结合具体情况综合评估。"))
    lines.append("")

    return "\n".join(lines)


def generate_risk_pathways(country_data, result):
    """生成风险传导路径分析，识别维度间的风险关联。

    Args:
        country_data: 国家完整数据
        result:       calculate_total_score() 输出

    Returns:
        list[str]: 风险传导路径描述列表
    """
    dim_scores = result["dimension_scores"]
    flags = country_data.get("flags", {})
    pathways = []

    # 检查各维度组合
    political = dim_scores.get("political_stability", 0)
    economic = dim_scores.get("economic_financial", 0)
    social = dim_scores.get("social_security", 0)
    geopolitical = dim_scores.get("geopolitical", 0)
    legal = dim_scores.get("legal_compliance", 0)

    if political > 60 and economic > 60:
        pathways.append(
            f"**政治-经济联动风险**: 政治稳定性（{political}分）与经济金融风险（{economic}分）"
            f"双双处于高位，政权不稳定可能导致财政纪律松弛、资本外逃与汇率贬值，"
            f"形成「政治危机→经济恶化→社会动荡→政权进一步不稳」的恶性循环。"
        )

    if geopolitical > 60 and legal > 50:
        pathways.append(
            f"**地缘政治-法律制裁叠加风险**: 地缘政治风险（{geopolitical}分）与法律合规风险"
            f"（{legal}分）的同向共振，可能导致该国面临多层级制裁（联合国/美国/欧盟），"
            f"域外管辖风险将显著增加第三方合规成本与交易对手方审查力度。"
        )

    if social > 60 and political > 50:
        pathways.append(
            f"**社会安全-政治稳定传导风险**: 社会治安风险（{social}分）持续高企可能"
            f"削弱政权合法性基础，恐怖主义与有组织犯罪的蔓延将侵蚀国家治理能力，"
            f"进而加剧政治不稳定与政策不确定性。"
        )

    if economic > 60 and social > 50:
        pathways.append(
            f"**经济-社会双向传导风险**: 经济金融风险（{economic}分）导致的高通胀与"
            f"失业率上升，可能触发大规模社会抗议与治安恶化（{social}分），"
            f"形成「经济困难→社会不满→治安恶化→投资环境进一步恶化」的负面循环。"
        )

    if flags.get("ofac") and economic > 50:
        pathways.append(
            f"**制裁-金融阻断风险**: 该国因被列入OFAC SDN清单而面临国际金融体系隔离，"
            f"跨境支付渠道受限、代理银行关系中断，叠加经济金融风险（{economic}分），"
            f"将严重阻碍外资企业的正常经营与利润汇回。"
        )

    if flags.get("conflict") and social > 50:
        pathways.append(
            f"**冲突-安全恶化风险**: 区域武装冲突背景叠加社会治安风险（{social}分），"
            f"将显著增加海外项目人员安全保护成本，供应链中断风险与资产损毁概率大幅上升，"
            f"可能触发紧急撤离与不可抗力条款的适用争议。"
        )

    if not pathways:
        pathways.append(
            f"该国当前各维度风险关联程度较低，未检测到显著的风险传导链条。"
            f"但需注意，在全球地缘政治格局加速演变的背景下，各维度风险可能因外部冲击"
            f"（如区域冲突升级、国际制裁政策调整）而形成新的传导路径。"
        )

    return pathways


def generate_recommendations(country_data, result):
    """生成分阶段的应对建议（短期/中期/长期）。

    Args:
        country_data: 国家完整数据
        result:       calculate_total_score() 输出

    Returns:
        dict: {"short_term": str, "medium_term": str, "long_term": str}
    """
    total = result["total_score"]
    level = result["risk_level"]
    dim_scores = result["dimension_scores"]
    flags = country_data.get("flags", {})

    top_dims = sorted(dim_scores.items(), key=lambda x: x[1], reverse=True)
    top2_labels = [DIMENSION_LABELS.get(k, k) for k, v in top_dims[:2]]

    # ---- 短期建议（0-6个月） ----
    short_actions = []
    if level in ("extreme", "high"):
        short_actions.extend([
            f"1. **暂停新增投资决策**：在风险等级降至「中风险」以下前，建议暂停对该国的新增直接投资审批，已批准的尚未执行项目应重新进行风险评估。",
            f"2. **制定应急预案**：针对{top2_labels[0]}等高风险维度，制定包含人员撤离、资产保全、供应链替代在内的分级应急预案，明确触发条件与执行流程。",
            f"3. **投保海外投资保险**：向中国出口信用保险公司（SINOSURE）或国际多边投资担保机构（MIGA）投保，覆盖征收、汇兑限制、战争及政治暴乱等政治风险。",
        ])
    elif level == "medium":
        short_actions.extend([
            f"1. **加强风险监测**：建立对{top2_labels[0]}的月度监测机制，跟踪关键国际指标变化（WGI/WDI/GTI等），设置预警阈值。",
            f"2. **完善尽职调查**：在现有投资项目中嵌入国别风险评估模块，重点关注{'、'.join(top2_labels)}等领域的合规审查。",
            f"3. **分散投资布局**：避免在该国单一项目或行业过度集中，适度向同区域低风险国家倾斜投资组合。",
        ])
    else:
        short_actions.extend([
            f"1. **维持正常经营**：当前风险水平可控，可继续推进正常投资与贸易活动。",
            f"2. **年度风险复审**：建议每年进行一次国别风险复审，关注{'、'.join(top2_labels)}等维度的边际变化趋势。",
            f"3. **把握市场机会**：在风险可控前提下，可利用该国稳定的投资环境拓展市场份额。",
        ])

    if flags.get("ofac"):
        short_actions.append(
            f"4. **立即开展制裁合规审查**：全面排查在当地的业务伙伴、供应链节点与金融通道是否涉及SDN清单实体，必要时寻求OFAC合规法律意见。"
        )
    if flags.get("conflict"):
        short_actions.append(
            f"5. **启动安全警戒升级**：将在当地人员安全保护级别提升至最高级，与驻外使领馆保持密切沟通，储备紧急撤离所需物资与通道。"
        )

    # ---- 中期建议（6-24个月） ----
    medium_actions = []
    if level in ("extreme", "high"):
        medium_actions.extend([
            f"1. **探索替代市场**：系统评估同区域其他国家的投资环境，为可能的产能转移与市场替代做好前期调研与可行性论证。",
            f"2. **法律架构优化**：通过第三国控股公司、国际投资协定保护等法律架构安排，降低域外管辖风险与资产被征收风险。",
            f"3. **本地化策略**：深化与当地政府和社区的合作伙伴关系，通过企业社会责任项目提升社会运营合法性，对冲社会安全风险。",
        ])
    else:
        medium_actions.extend([
            f"1. **深化市场布局**：在现有投资基础上，向产业链上下游延伸，增强市场粘性与退出成本壁垒。",
            f"2. **本地人才培养**：建立本地化管理和技术团队，降低对母国外派人员的依赖，提升运营韧性。",
            f"3. **合规体系完善**：参照OECD《跨国企业指南》等国际标准，完善企业在当地的合规管理体系。",
        ])

    # ---- 长期建议（24个月以上） ----
    long_actions = []
    if level in ("extreme", "high"):
        long_actions.extend([
            f"1. **战略退出路径设计**：制定分阶段撤资方案，包括资产评估、买家遴选、交易架构设计与监管审批路径规划。",
            f"2. **区域供应链重构**：以区域全面经济伙伴关系协定（RCEP）或「一带一路」框架为基础，构建不依赖该国的替代性供应链网络。",
            f"3. **制度性风险对冲**：推动母国与该国签署或升级双边投资协定（BIT），为长期投资提供国际法层面的保护。",
        ])
    else:
        long_actions.extend([
            f"1. **品牌与渠道深耕**：将当地市场培育为区域运营中心，辐射周边国家市场。",
            f"2. **ESG战略融入**：将环境、社会与治理（ESG）标准融入当地投资决策全流程，提升国际融资能力与品牌美誉度。",
            f"3. **持续风险扫描**：将国别风险评估纳入企业年度战略规划流程，确保风险判断与时俱进。",
        ])

    return {
        "short_term": "\n".join(short_actions),
        "medium_term": "\n".join(medium_actions),
        "long_term": "\n".join(long_actions),
    }
