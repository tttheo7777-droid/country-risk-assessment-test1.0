"""
国别风险评估系统 - 国家名称模糊查询模块
功能：中英文模糊匹配、拼音首字母匹配、ISO代码查询、Levenshtein编辑距离排序
"""
import re
from data.country_data import get_country_list


def levenshtein_distance(s1, s2):
    """计算两个字符串之间的Levenshtein编辑距离（归一化至0-1）。

    Args:
        s1: 字符串1
        s2: 字符串2

    Returns:
        float: 0.0（完全相同）~ 1.0（完全不同）

    Example:
        >>> levenshtein_distance("china", "chine")
        0.2
    """
    if not s1 or not s2:
        return 1.0
    s1, s2 = s1.lower(), s2.lower()
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 1.0
    # 动态规划计算编辑距离
    dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    for i in range(len1 + 1):
        dp[i][0] = i
    for j in range(len2 + 1):
        dp[0][j] = j
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)
    return dp[len1][len2] / max(len1, len2)


def fuzzy_search_countries(query, limit=10, threshold=0.6):
    """对国家列表执行模糊搜索，返回按匹配度排序的结果。

    Args:
        query:     搜索关键词（中文名/英文名/ISO代码/拼音首字母）
        limit:     返回结果数量上限
        threshold: 匹配度阈值（0-1），低于此值的结果被过滤

    Returns:
        list[dict]: 按匹配度降序排列的国家列表，每个元素包含
                    {iso3, name_cn, name_en, region, risk_level, score}

    Example:
        >>> results = fuzzy_search_countries("阿富汗")
        >>> results[0]["name_cn"]
        '阿富汗'
        >>> results = fuzzy_search_countries("afg")
        >>> results[0]["iso3"]
        'AFG'
    """
    if not query or not query.strip():
        return get_country_list()[:limit]

    query = query.strip()
    query_lower = query.lower()
    all_countries = get_country_list()

    scored = []
    for c in all_countries:
        max_score = 0.0
        cn_lower = c["name_cn"].lower()
        en_lower = c["name_en"].lower()
        iso_lower = c["iso3"].lower()

        # 精确匹配
        if query_lower == cn_lower or query_lower == en_lower or query_lower == iso_lower:
            max_score = 1.0
        # 前缀匹配
        elif cn_lower.startswith(query_lower) or en_lower.startswith(query_lower):
            max_score = 0.95
        # 包含匹配
        elif query_lower in cn_lower or query_lower in en_lower:
            max_score = 0.85
        # ISO代码匹配
        elif query_lower == iso_lower:
            max_score = 0.95
        # Python拼音首字母模糊（中文名每个字的拼音首字母）
        elif len(query_lower) <= 4:
            py_initials = _get_pinyin_initials(c["name_cn"])
            if py_initials and query_lower == py_initials.lower():
                max_score = 0.80
        # 编辑距离兜底
        else:
            cn_dist = 1 - levenshtein_distance(query_lower, cn_lower)
            en_dist = 1 - levenshtein_distance(query_lower, en_lower)
            iso_dist = 1 - levenshtein_distance(query_lower, iso_lower)
            max_score = max(cn_dist, en_dist, iso_dist)

        if max_score >= threshold:
            scored.append({**c, "match_score": round(max_score, 3)})

    scored.sort(key=lambda x: x["match_score"], reverse=True)
    return scored[:limit]


def _get_pinyin_initials(chinese_name):
    """获取中文名称的拼音首字母（简化映射，覆盖常用字）。

    Args:
        chinese_name: 中文国家名

    Returns:
        str: 拼音首字母串（如 "阿富汗" → "AFH"）
    """
    _PINYIN_INITIAL_MAP = {
        "阿": "A", "埃": "A", "爱": "A", "安": "A", "澳": "A",
        "巴": "B", "白": "B", "保": "B", "北": "B", "比": "B", "波": "B", "不": "B", "布": "B",
        "朝": "C",
        "大": "D", "丹": "D", "德": "D", "东": "D", "多": "D",
        "俄": "E", "厄": "E",
        "法": "F", "菲": "F", "斐": "F", "芬": "F", "佛": "F",
        "冈": "G", "刚": "G", "哥": "G", "格": "G", "古": "G", "圭": "G",
        "哈": "H", "韩": "H", "荷": "H", "洪": "H",
        "几": "J", "吉": "J", "加": "J", "柬": "J", "捷": "J", "津": "J",
        "喀": "K", "卡": "K", "科": "K", "克": "K", "肯": "K", "库": "K",
        "拉": "L", "莱": "L", "老": "L", "黎": "L", "利": "L", "卢": "L", "罗": "L",
        "马": "M", "毛": "M", "美": "M", "蒙": "M", "孟": "M", "秘": "M", "缅": "M", "摩": "M", "莫": "M", "墨": "M",
        "纳": "N", "南": "N", "尼": "N", "挪": "N",
        "欧": "O",
        "帕": "P", "葡": "P",
        "日": "R", "瑞": "R",
        "萨": "S", "塞": "S", "沙": "S", "斯": "S", "苏": "S", "索": "S",
        "塔": "T", "台": "T", "泰": "T", "坦": "T", "突": "T", "土": "T", "托": "T",
        "瓦": "W", "委": "W", "文": "W", "乌": "W",
        "西": "X", "希": "X", "新": "X", "匈": "X", "叙": "X",
        "牙": "Y", "也": "Y", "伊": "Y", "以": "Y", "意": "Y", "印": "Y", "英": "Y", "约": "Y", "越": "Y",
        "赞": "Z", "乍": "Z", "智": "Z", "中": "Z",
        "香": "X", "澳": "A",
    }
    result = []
    for char in chinese_name:
        if char in _PINYIN_INITIAL_MAP:
            result.append(_PINYIN_INITIAL_MAP[char])
    return "".join(result) if result else None
