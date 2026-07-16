#!/usr/bin/env python3
"""
Profile Builder - 将 Claude 采集的学生观察数据转化为结构化画像报告。

用途：Claude 在采集完学生信息后运行此脚本，生成结构化画像 JSON + 可读报告。
用法：
  方式一 (JSON 输入):
    python3 scripts/profile-builder.py --json '{"education": {...}, "traits": {...}}'

  方式二 (交互式):
    python3 scripts/profile-builder.py --interactive

输出：结构化画像 JSON + 匹配建议
"""

import json
import sys
import argparse


# ============================================================
# 匹配规则库
# ============================================================

MATCHING_RULES = {
    "tech_roles": {
        "label": "技术类岗位",
        "roles": ["软件开发工程师", "AI/算法工程师", "数据分析师"],
        "required": {
            "coding_ability": ["熟练", "精通"],
            "enjoys_deep_work": True,
        },
        "preferred": {
            "energy_source": "solo",
            "achievement_source": "technical_mastery",
        },
        "contraindicated": {
            "coding_ability": "完全不会",
            "achievement_source": "people_interaction",
        }
    },
    "business_roles": {
        "label": "业务/产品类岗位",
        "roles": ["产品经理", "售前/解决方案", "客户成功", "ToB销售/BD"],
        "required": {},
        "preferred": {
            "energy_source": "social",
            "achievement_source": "business_impact",
        },
        "contraindicated": {
            "energy_source": "highly_solo",
            "conflict_sensitivity": "highly_sensitive",
        }
    },
    "hybrid_roles": {
        "label": "混合类岗位",
        "roles": ["技术型PM", "解决方案架构师", "FDE（工程向）"],
        "required": {
            "coding_ability": ["基础", "熟练"],
        },
        "preferred": {
            "energy_source": "balanced",
            "risk_preference": "flexible",
        }
    },
    "academic_path": {
        "label": "学术路线",
        "paths": ["读博→高校教职", "读博→企业研究院", "读研→跳板就业"],
        "required": {},
        "preferred": {
            "research_enjoyment": "high",
            "long_term_patience": "high",
            "risk_preference": "stable",
            "achievement_source": "discovery",
        },
        "contraindicated": {
            "research_enjoyment": "low",
            "long_term_patience": "low",
            "paper_attitude": "hurry_to_finish",
        }
    },
    "civil_service": {
        "label": "体制内路线",
        "paths": ["考公（国考/省考）", "考编（事业单位）", "定向选调生", "国企/央企"],
        "required": {},
        "preferred": {
            "risk_preference": "stable",
            "structure_acceptance": "high",
            "achievement_source": "stability",
        },
        "contraindicated": {
            "structure_acceptance": "very_low",
            "risk_preference": "adventurous",
            "money_motivation": "very_high",
        }
    },
}


def assess_match(profile: dict, rule_set: dict) -> dict:
    """评估一个画像与一组规则的匹配程度"""
    strengths = []
    warnings = []
    blockers = []

    # 检查必需条件 (required)
    for key, acceptable_values in rule_set.get("required", {}).items():
        user_value = profile.get(key)
        if user_value is None:
            continue
        if isinstance(acceptable_values, list):
            if user_value not in acceptable_values:
                blockers.append(f"缺少必需条件: {key}={user_value} (需要 {acceptable_values})")
        elif isinstance(acceptable_values, bool):
            if user_value != acceptable_values:
                blockers.append(f"条件不满足: {key}")

    # 检查偏好条件 (preferred)
    for key, preferred_value in rule_set.get("preferred", {}).items():
        user_value = profile.get(key)
        if user_value is None:
            continue
        if user_value == preferred_value:
            strengths.append(f"偏好匹配: {key}={user_value}")
        elif preferred_value == "balanced" and user_value in ("solo", "social"):
            strengths.append(f"偏好兼容: {key}={user_value}")

    # 检查禁忌条件 (contraindicated)
    for key, forbidden_value in rule_set.get("contraindicated", {}).items():
        user_value = profile.get(key)
        if user_value is None:
            continue
        if isinstance(forbidden_value, list):
            if user_value in forbidden_value:
                warnings.append(f"⚠️ 画像冲突: {key}={user_value} (此路径可能不适合)")
        else:
            if user_value == forbidden_value:
                warnings.append(f"⚠️ 严重画像冲突: {key}={user_value} (强烈建议重新考虑)")

    return {
        "strengths": strengths,
        "warnings": warnings,
        "blockers": blockers,
        "match_score": max(0, len(strengths) - len(warnings) * 1.5 - len(blockers) * 3),
        "verdict": "强烈推荐" if len(strengths) >= 3 and len(blockers) == 0 and len(warnings) == 0
                   else "推荐" if len(strengths) >= 1 and len(blockers) == 0 and len(warnings) <= 1
                   else "可考虑（有风险）" if len(blockers) == 0
                   else "不推荐"
    }


def build_report(profile: dict) -> dict:
    """生成完整画像报告"""
    matches = {}
    for path_key, rule_set in MATCHING_RULES.items():
        matches[path_key] = assess_match(profile, rule_set)
        matches[path_key]["label"] = rule_set["label"]
        matches[path_key]["roles"] = rule_set.get("roles", rule_set.get("paths", []))

    # 按匹配度排序
    ranked = sorted(matches.items(), key=lambda x: x[1]["match_score"], reverse=True)

    return {
        "profile_summary": profile.get("summary", ""),
        "hard_background": {
            "education": profile.get("education", "未提供"),
            "major": profile.get("major", "未提供"),
            "coding_ability": profile.get("coding_ability", "未提供"),
            "ai_familiarity": profile.get("ai_familiarity", "未提供"),
            "target_cities": profile.get("target_cities", []),
            "salary_floor": profile.get("salary_floor", "未提供"),
            "further_study_interest": profile.get("further_study_interest", "未提供"),
            "civil_service_interest": profile.get("civil_service_interest", "未提供"),
        },
        "soft_traits": {
            "energy_source": profile.get("energy_source", "未采集"),
            "conflict_sensitivity": profile.get("conflict_sensitivity", "未采集"),
            "risk_preference": profile.get("risk_preference", "未采集"),
            "achievement_source": profile.get("achievement_source", "未采集"),
            "travel_tolerance": profile.get("travel_tolerance", "未采集"),
            "research_enjoyment": profile.get("research_enjoyment", "未采集"),
            "long_term_patience": profile.get("long_term_patience", "未采集"),
            "structure_acceptance": profile.get("structure_acceptance", "未采集"),
            "money_motivation": profile.get("money_motivation", "未采集"),
            "paper_attitude": profile.get("paper_attitude", "未采集"),
        },
        "path_recommendations": [
            {
                "path": key,
                "label": val["label"],
                "roles": val["roles"],
                "match_score": val["match_score"],
                "verdict": val["verdict"],
                "strengths": val["strengths"],
                "warnings": val["warnings"],
                "blockers": val["blockers"],
            }
            for key, val in ranked
        ],
        "missing_dimensions": [
            d for d in ["energy_source", "conflict_sensitivity", "risk_preference",
                       "achievement_source", "travel_tolerance", "research_enjoyment",
                       "long_term_patience", "structure_acceptance", "money_motivation",
                       "paper_attitude"]
            if profile.get(d) is None
        ],
        "confidence": "高" if len(profile) >= 12 else "中等" if len(profile) >= 8 else "低（画像不完整）"
    }


def interactive_collect() -> dict:
    """交互式采集学生画像（适用于 Claude 无法直接交互时手动使用）"""
    profile = {}

    print("=== 硬条件采集 ===")
    profile["education"] = input("学历 (本科/硕士/博士): ")
    profile["major"] = input("专业: ")
    profile["coding_ability"] = input("代码水平 (完全不会/基础/熟练/精通): ")
    profile["ai_familiarity"] = input("AI熟悉度 (没用过/用过API/搭过Agent): ")
    profile["target_cities"] = input("目标城市 (逗号分隔): ").split(",")
    profile["salary_floor"] = input("薪资底线 (万/年): ")
    profile["further_study_interest"] = input("深造意愿 (完全不想/不排斥/确定要读): ")
    profile["civil_service_interest"] = input("体制内意愿 (完全不考虑/不排斥/首选): ")

    print("\n=== 软特质采集 ===")
    profile["energy_source"] = input("人际能量来源 (solo/social/balanced): ")
    profile["conflict_sensitivity"] = input("对批评敏感度 (low/medium/highly_sensitive): ")
    profile["risk_preference"] = input("风险偏好 (stable/flexible/adventurous): ")
    profile["achievement_source"] = input("成就感来源 (technical_mastery/business_impact/stability/discovery/people_interaction): ")
    profile["travel_tolerance"] = input("出差容忍度 (none/low/medium/high): ")
    profile["research_enjoyment"] = input("做研究乐趣 (low/medium/high): ")
    profile["long_term_patience"] = input("长期耐心 (low/medium/high): ")
    profile["structure_acceptance"] = input("对形式化事务接受度 (very_low/low/medium/high): ")
    profile["money_motivation"] = input("金钱驱动力 (low/medium/high/very_high): ")
    profile["paper_attitude"] = input("写论文心态 (hurry_to_finish/neutral/enjoy): ")

    profile["summary"] = input("\n一句话总结自己（可选）: ")

    return profile


def main():
    parser = argparse.ArgumentParser(description="学生画像结构化工具")
    parser.add_argument("--json", type=str, help="JSON 格式的画像数据")
    parser.add_argument("--interactive", action="store_true", help="交互式采集")
    parser.add_argument("--template", action="store_true", help="输出画像采集模板（供 Claude 参考）")

    args = parser.parse_args()

    if args.template:
        template = {
            "_instructions": "Claude 在采集完学生信息后，将观察结果填入此模板传给 --json 参数",
            "education": "本科|硕士|博士",
            "major": "专业名称",
            "coding_ability": "完全不会|基础|熟练|精通",
            "ai_familiarity": "没用过|用过API|搭过Agent/Prompt/RAG",
            "target_cities": ["杭州", "苏州"],
            "salary_floor": "xx万/年",
            "further_study_interest": "完全不考虑|不排斥|确定要读",
            "civil_service_interest": "完全不考虑|不排斥|首选",
            "energy_source": "solo(从独处恢复能量)|social(从社交获得能量)|balanced",
            "conflict_sensitivity": "low|medium|highly_sensitive",
            "risk_preference": "stable(风险回避)|flexible|adventurous(风险偏好)",
            "achievement_source": "technical_mastery|business_impact|stability|discovery|people_interaction",
            "travel_tolerance": "none|low|medium|high",
            "research_enjoyment": "low|medium|high",
            "long_term_patience": "low|medium|high",
            "structure_acceptance": "very_low|low|medium|high",
            "money_motivation": "low|medium|high|very_high",
            "paper_attitude": "hurry_to_finish|neutral|enjoy",
            "summary": "一句话总结学生画像（可选）"
        }
        print(json.dumps(template, ensure_ascii=False, indent=2))
        return

    if args.interactive:
        profile = interactive_collect()
        report = build_report(profile)
        print("\n=== 画像报告 ===\n")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.json:
        try:
            profile = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {e}", file=sys.stderr)
            sys.exit(1)

        report = build_report(profile)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    parser.print_help()
    print("\n示例:")
    print('  python3 profile-builder.py --json \'{"education":"硕士","coding_ability":"基础","energy_source":"balanced",...}\'')
    print('  python3 profile-builder.py --interactive')
    print('  python3 profile-builder.py --template')


if __name__ == "__main__":
    main()
