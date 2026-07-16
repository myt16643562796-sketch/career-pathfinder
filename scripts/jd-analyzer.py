#!/usr/bin/env python3
"""
JD Analyzer - 分析岗位 JD 文本，输出结构化分析结果。

用途：Claude 在分析岗位时运行此脚本，辅助检测岗位的真假、类别、红旗信号。
用法：python3 scripts/jd-analyzer.py '<JD_TEXT>'
      python3 scripts/jd-analyzer.py --file <jd.txt>
输出：JSON 格式的结构化分析
"""

import json
import sys
import re
from pathlib import Path


# ============================================================
# 检测规则库
# ============================================================

# 岗位分类关键词
ROLE_CATEGORIES = {
    "研发/工程": {
        "keywords": ["开发工程师", "软件工程师", "后端", "前端", "全栈", "SWE", "SDE",
                     "Java", "Python", "Go", "C++", "React", "Vue", "系统设计",
                     "数据结构", "算法", "编码", "代码", "编程"],
        "weight": 0
    },
    "AI/算法": {
        "keywords": ["算法工程师", "机器学习", "深度学习", "NLP", "CV", "大模型",
                     "LLM", "训练", "推理", "模型部署", "AIGC", "Prompt",
                     "fine-tuning", "RAG", "神经网络", "Transformer"],
        "weight": 0
    },
    "数据分析": {
        "keywords": ["数据分析", "数据科学", "BI", "SQL", "Tableau", "看板",
                     "数据挖掘", "指标体系", "AB测试", "Data Scientist"],
        "weight": 0
    },
    "产品经理": {
        "keywords": ["产品经理", "PM", "PRD", "需求分析", "产品设计", "用户研究",
                     "竞品分析", "产品规划", "产品迭代", "原型设计"],
        "weight": 0
    },
    "售前/解决方案": {
        "keywords": ["售前", "解决方案", "架构师", "方案设计", "技术方案",
                     "客户需求", "方案汇报", "招投标", "PoC", "演示", "demo",
                     "售前工程师", "SA", "解决方案架构师"],
        "weight": 0
    },
    "销售/商务": {
        "keywords": ["销售", "BD", "商务拓展", "客户经理", "大客户", "签单",
                     "业绩", "提成", "KPI", "销售目标", "回款", "陌拜"],
        "weight": 0
    },
    "客户成功": {
        "keywords": ["客户成功", "CSM", "续约", "增购", "健康度", "onboarding",
                     "客户留存", "upsell", "客户关系维护"],
        "weight": 0
    },
    "FDE/交付": {
        "keywords": ["FDE", "Forward Deploy", "前沿部署", "前线部署",
                     "驻场", "交付", "实施", "部署", "客户现场"],
        "weight": 0
    },
    "运营": {
        "keywords": ["运营", "活动运营", "用户运营", "内容运营", "增长",
                     "转化率", "留存", "拉新"],
        "weight": 0
    },
}

# 假 FDE 检测规则
FAKE_FDE_RULES = [
    {
        "signal": "归属非工程序列",
        "patterns": [r"销售.*支持", r"运营", r"销售-", r"Sales Support",
                     r"销售支持"],
        "confidence": 0.8
    },
    {
        "signal": "不要求写代码",
        "patterns": [r"不需要.*程序", r"不需要.*写代码", r"不需要.*编码",
                     r"无代码", r"低代码", r"无.*开发经验"],
        "confidence": 0.9
    },
    {
        "signal": "核心工具是平台内置工具",
        "patterns": [r"多维表格", r"自动化工作流", r"智能助手.*配置",
                     r"飞书.*AI.*工具", r"无代码.*搭建"],
        "confidence": 0.85
    },
    {
        "signal": "JD 重点在演示和文档",
        "patterns": [r"演示.*demo", r"演示模板", r"SOP", r"标准化.*指南",
                     r"培训.*销售", r"培训.*伙伴"],
        "confidence": 0.7
    },
]

# 岗位画饼信号（JD 中常见的美化话术）
RED_FLAGS = {
    "管培生画饼": {
        "patterns": [r"管培生.*轮岗", r"管理培训生"],
        "check": "是否有具体的培养机制描述？是否有往届管培生去向数据？",
        "severity": "medium"
    },
    "AI 热词堆砌": {
        "patterns": [r"AI.*赋能", r"AI.*驱动", r"大模型.*落地", r"AGI",
                     r"智能体.*时代"],
        "check": "JD 中是否提到具体的 AI 工具/框架/工作流？还是只有空洞的 buzzword？",
        "severity": "medium"
    },
    "成长空间大 = 钱少活多": {
        "patterns": [r"成长空间", r"学习机会", r"快速成长", r"扁平化管理"],
        "check": "薪资是否明确？如果画饼不提钱，很可能是工资不够成长来凑",
        "severity": "high"
    },
    "抗压能力强 = 加班/背锅": {
        "patterns": [r"抗压能力", r"高强度", r"快节奏", r"拥抱变化"],
        "check": "是否有 WLB 相关表述？是否有加班费？",
        "severity": "high"
    },
    "弹性工作 = 随时待命": {
        "patterns": [r"弹性工作", r"远程办公", r"不打卡"],
        "check": "弹性是双向还是单向？",
        "severity": "medium"
    },
    "专业不限 = 门槛低/含金量低": {
        "patterns": [r"专业不限"],
        "check": "如果高薪+专业不限=能力至上；如果低薪+专业不限=谁都能干",
        "severity": "low"
    },
}

# 隐含需求（JD 没说但实际需要的）
IMPLICIT_REQUIREMENTS = {
    "能适应长期出差": {
        "triggers": [r"驻场", r"客户现场", r"出差", r"base.*客户"],
        "message": "这个岗位大概率需要频繁出差/驻场。问清楚频率和比例（一周几天？一个月几周？）"
    },
    "需要能自己搞定一切": {
        "triggers": [r"独立", r"自主", r"owner", r"从0到1", r"闭环"],
        "message": "这可能意味着团队小、support 少，你要自己解决大部分问题。适合高自主性的人，不适合需要 mentor 手把手带的人。"
    },
    "可能需要背锅": {
        "triggers": [r"对结果负责", r"结果导向", r"交付结果"],
        "message": "在售前/交付语境下，这可能意味着销售乱承诺你填坑。问清楚：失败了谁负责？"
    },
}


def classify_role(text: str) -> dict:
    """根据 JD 文本分类岗位类别"""
    scores = {}
    for category, config in ROLE_CATEGORIES.items():
        score = 0
        for kw in config["keywords"]:
            if kw.lower() in text.lower():
                score += 1
        scores[category] = score

    # 返回得分最高的 2 个
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0] if ranked[0][1] > 0 else ("无法确定", 0)
    secondary = ranked[1] if len(ranked) > 1 and ranked[1][1] > 0 else ("无", 0)

    return {
        "primary_category": primary[0],
        "primary_score": primary[1],
        "secondary_category": secondary[0],
        "secondary_score": secondary[1],
        "all_scores": {k: v for k, v in scores.items() if v > 0}
    }


def detect_fake_fde(text: str) -> dict:
    """检测是否是假 FDE（销售支持贴牌）"""
    signals = []
    total_confidence = 0

    for rule in FAKE_FDE_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                signals.append({
                    "signal": rule["signal"],
                    "matched": pattern,
                    "confidence": rule["confidence"]
                })
                total_confidence += rule["confidence"]
                break

    # 命中 2 条及以上 → 假 FDE；命中 1 条但置信度 ≥ 0.85 → 假 FDE
    is_fake = False
    if signals:
        avg_conf = total_confidence / len(signals)
        if len(signals) >= 2 and avg_conf > 0.6:
            is_fake = True
        elif len(signals) == 1 and avg_conf >= 0.85:
            is_fake = True

    return {
        "is_fake_fde": is_fake,
        "confidence": round(total_confidence / len(signals), 2) if signals else 0,
        "signals": signals,
        "verdict": "⚠️ 这大概率是销售支持/售前岗位，借'FDE'热词包装。不写代码，不做工程交付。" if is_fake else "无明显假 FDE 信号"
    }


def detect_red_flags(text: str) -> list:
    """检测 JD 中的红旗信号"""
    flags = []
    for name, rule in RED_FLAGS.items():
        for pattern in rule["patterns"]:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append({
                    "flag": name,
                    "matched": pattern,
                    "check_question": rule["check"],
                    "severity": rule["severity"]
                })
                break
    return flags


def detect_implicit_requirements(text: str) -> list:
    """检测 JD 中未明说但实际需要的要求"""
    implicit = []
    for name, rule in IMPLICIT_REQUIREMENTS.items():
        for trigger in rule["triggers"]:
            if re.search(trigger, text, re.IGNORECASE):
                implicit.append({
                    "requirement": name,
                    "trigger_word": trigger,
                    "message": rule["message"]
                })
                break
    return implicit


def extract_basic_info(text: str) -> dict:
    """从 JD 中提取基本信息"""
    info = {}

    # 尝试找公司名
    company_patterns = [r"字节跳动", r"阿里", r"腾讯", r"百度", r"美团",
                        r"京东", r"网易", r"华为", r"小米", r"蚂蚁",
                        r"联想", r"滴滴", r"快手", r"拼多多", r"PDD"]
    companies = []
    for c in company_patterns:
        if c in text:
            companies.append(c)
    info["mentioned_companies"] = companies

    # 尝试找城市
    city_patterns = [r"北京", r"上海", r"深圳", r"广州", r"杭州", r"成都",
                     r"武汉", r"南京", r"苏州", r"西安", r"重庆", r"长沙"]
    cities = []
    for c in city_patterns:
        if re.search(c, text):
            cities.append(c)
    info["mentioned_cities"] = cities

    # 尝试找薪资数字
    salary_patterns = [
        (r"(\d+)[kK]-(\d+)[kK].*月", lambda m: f"{m[0]}-{m[1]}K/月"),
        (r"(\d+)[kK]-(\d+)[kK].*年", lambda m: f"{m[0]}-{m[1]}K/年"),
        (r"(\d+)万.*(\d+)万", lambda m: f"{m[0]}-{m[1]}万/年"),
        (r"月薪.*?(\d+).*?-.*?(\d+).*?[万千]", lambda m: f"{m[0]}-{m[1]}"),
    ]
    for pattern, extractor in salary_patterns:
        m = re.findall(pattern, text)
        # simplified: just note if salary mentioned
        pass

    # 检查是否提到转正/管培
    info["is_internship"] = bool(re.search(r"实习|ByteIntern|Intern", text))
    info["is_management_trainee"] = bool(re.search(r"管培", text))
    info["target_graduate_year"] = None
    year_match = re.search(r"(\d{4})届", text)
    if year_match:
        info["target_graduate_year"] = year_match.group(1)

    return info


def analyze(text: str) -> dict:
    """综合分析 JD"""
    return {
        "basic_info": extract_basic_info(text),
        "role_classification": classify_role(text),
        "fake_fde_check": detect_fake_fde(text),
        "red_flags": detect_red_flags(text),
        "implicit_requirements": detect_implicit_requirements(text),
    }


def main():
    if len(sys.argv) < 2:
        print("用法: python3 jd-analyzer.py '<JD_TEXT>'", file=sys.stderr)
        print("      python3 jd-analyzer.py --file <jd.txt>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "--file":
        text = Path(sys.argv[2]).read_text()
    else:
        text = sys.argv[1]

    result = analyze(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
