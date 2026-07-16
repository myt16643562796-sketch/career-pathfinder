#!/usr/bin/env python3
"""
Career Timeline Simulator - 模拟职业发展路径和薪资曲线（1-20 年）。

用途：根据岗位和城市，生成从入职到 20 年的职业发展预测。
用法：
  python3 scripts/career-timeline.py --role "产品经理" --city "杭州" --start-age 25
  python3 scripts/career-timeline.py --compare "FDE（真·工程向）" "售前/解决方案" --city "北京"

输出：JSON 格式的时间线数据 + 关键节点（35 岁/40 岁/45 岁）评估
"""

import json
import sys
import argparse

# ============================================================
# 岗位发展曲线参数
# 每个岗位定义：起始薪资基数、各阶段增长因子、35 岁风险系数
# ============================================================

CAREER_CURVES = {
    "软件开发工程师": {
        "base_salary": {"tier1": 22, "tier2": 18, "tier3": 14},  # 校招年薪（万）
        "growth_model": "steep_then_flat",  # 前陡后平
        "growth_factors": {
            "1-3年": 1.3,    # 涨幅 30%
            "3-5年": 1.5,    # 累计涨幅 50%
            "5-8年": 1.8,    # 累计涨幅 80%
            "8-12年": 2.0,   # 到天花板
            "12-20年": 2.0,  # 持平（通胀调整可能微涨但实质不涨）
        },
        "age_35_risk": "medium",
        "age_35_note": "纯编码型 SWE 35 岁后竞争力下降。转型架构师/管理/创业是主要出路。如果不转型，可能面临降薪或被迫转行。",
        "typical_exits": ["技术管理", "架构师", "转行PM", "创业", "降薪去二线"],
    },
    "AI/算法工程师": {
        "base_salary": {"tier1": 32, "tier2": 28, "tier3": 22},
        "growth_model": "steep_continued",
        "growth_factors": {
            "1-3年": 1.4,
            "3-5年": 1.8,
            "5-8年": 2.5,
            "8-12年": 3.5,
            "12-20年": 5.0,
        },
        "age_35_risk": "medium_low",
        "age_35_note": "算法功底是稀缺资源。但研究方向可能被新范式颠覆，需要持续学习。落地型比研究型更安全。",
        "typical_exits": ["技术总监", "首席科学家", "创业", "去高校", "独立顾问"],
    },
    "产品经理": {
        "base_salary": {"tier1": 20, "tier2": 16, "tier3": 12},
        "growth_model": "bimodal",  # 两极分化：功能型PM平缓，业务型PM陡峭
        "growth_factors": {
            "1-3年": 1.3,
            "3-5年": 1.6,
            "5-8年": 2.2,
            "8-12年": 3.0,
            "12-20年": 4.0,
        },
        "age_35_risk": "medium_high",
        "age_35_note": "功能型PM 30 岁后极危险。业务型PM（能定义做什么、能算ROI）35 岁后反而稀缺。关键是你有没有从'传话员'进化到'业务Owner'。",
        "typical_exits": ["产品总监", "创业", "转行VC", "业务负责人", "独立顾问"],
    },
    "售前/解决方案": {
        "base_salary": {"tier1": 22, "tier2": 18, "tier3": 14},
        "growth_model": "steady_climb",
        "growth_factors": {
            "1-3年": 1.2,
            "3-5年": 1.5,
            "5-8年": 2.0,
            "8-12年": 3.0,
            "12-20年": 4.5,
        },
        "age_35_risk": "low",
        "age_35_note": "35 岁最安全的岗位之一。护城河来自行业认知+客户关系+技术广度。越老越值钱。",
        "typical_exits": ["行业首席架构师", "技术总监", "独立顾问", "去甲方", "创业"],
    },
    "客户成功": {
        "base_salary": {"tier1": 15, "tier2": 13, "tier3": 10},
        "growth_model": "flat_slow",
        "growth_factors": {
            "1-3年": 1.2,
            "3-5年": 1.4,
            "5-8年": 1.7,
            "8-12年": 2.0,
            "12-20年": 2.3,
        },
        "age_35_risk": "medium",
        "age_35_note": "客户关系是资产，但技能可迁移性有限。天花板低于售前和销售。需往行业深耕或管理转。",
        "typical_exits": ["CS 总监", "客户成功VP", "转销售", "转产品"],
    },
    "ToB销售/BD": {
        "base_salary": {"tier1": 15, "tier2": 12, "tier3": 8},  # 底薪，提成另算
        "growth_model": "high_variance",
        "growth_factors": {
            "1-3年": 1.5,    # 提成开始生效
            "3-5年": 2.5,    # 积累客户后爆发
            "5-8年": 5.0,    # Top Sales 阶段
            "8-12年": 6.0,
            "12-20年": 6.0,
        },
        "age_35_risk": "medium",
        "age_35_note": "客户关系是真正的护城河。但业绩每月归零的压力不随年龄消失。身体和家庭是天花板。",
        "typical_exits": ["销售VP", "创业", "投资", "做代理商", "退休"],
        "note": "⚠️ 以上为含提成的总包估算，实际波动极大。Top Sales 可能远超此表，一般销售可能远低于此表。"
    },
    "FDE（真·工程向）": {
        "base_salary": {"tier1": 32, "tier2": 26, "tier3": 20},
        "growth_model": "steep_early",
        "growth_factors": {
            "1-3年": 1.5,
            "3-5年": 2.0,
            "5-8年": 3.0,
            "8-12年": 4.0,
            "12-20年": 5.0,
        },
        "age_35_risk": "medium",
        "age_35_note": "工程能力+行业know-how+客户信任三重叠加。但出差和随时待命对家庭生活侵蚀严重。多数FDE在30岁出头转型技术管理或独立顾问。",
        "typical_exits": ["技术交付主管", "独立顾问", "创业", "去甲方", "解决方案架构师"],
    },
    "FDE（假·销售支持贴牌）": {
        "base_salary": {"tier1": 18, "tier2": 15, "tier3": 12},
        "growth_model": "flat_slow",
        "growth_factors": {
            "1-3年": 1.2,
            "3-5年": 1.4,
            "5-8年": 1.6,
            "8-12年": 1.8,
            "12-20年": 1.8,
        },
        "age_35_risk": "high",
        "age_35_note": "核心技能（无代码工具配置+写SOP）年轻人两周就能上手。35 岁基本没有护城河，技能绑定飞书/钉钉平台，跳槽选择面窄。",
        "typical_exits": ["转销售", "转客户成功", "转培训", "换平台重复同样工作"],
    },
    "公务员（江浙沪）": {
        "base_salary": {"tier1": 20, "tier2": 16, "tier3": 12},  # 含公积金+年终
        "growth_model": "very_slow_steady",
        "growth_factors": {
            "1-5年": 1.1,
            "5-8年": 1.3,     # 副科
            "8-12年": 1.5,    # 正科
            "12-20年": 1.8,   # 副处（大部分人天花板）
            "20年+": 2.0,
        },
        "age_35_risk": "none",
        "age_35_note": "体制内最大护城河：不存在因年龄被裁员。但'一眼望到头'是真实的——大部分人到正科/副处就是终点。",
        "typical_exits": ["退休", "提前退休", "去国企", "下海（极少数）"],
        "note": "含公积金+年终+补贴。隐性福利（医保/住房）未量化。薪资增长极慢但绝对稳定。"
    },
    "高校教职": {
        "base_salary": {"tier1": 12, "tier2": 10, "tier3": 8},
        "growth_model": "delayed_jump",
        "growth_factors": {
            "讲师": 1.0,
            "副教授（6-8年）": 1.8,
            "教授（10-15年）": 2.8,
        },
        "age_35_risk": "none",
        "age_35_note": "有编制=永久安全。薪资不高但社会地位高。非升即走压力集中在讲师→副教授阶段。",
        "typical_exits": ["终身教授", "去企业研究院", "行政岗", "退休"],
        "note": "未含科研经费、项目收入、人才补贴、安家费。实际总收入可能高 30-50%。"
    },
}


CITY_TIER_MAP = {
    "北京": "tier1", "上海": "tier1", "深圳": "tier1",
    "杭州": "tier2", "广州": "tier2", "成都": "tier2",
    "南京": "tier2", "苏州": "tier2", "武汉": "tier2",
    "西安": "tier2", "重庆": "tier2", "长沙": "tier2",
}


def simulate(role: str, city: str, start_age: int = 25) -> dict:
    """模拟完整职业时间线"""
    curve = CAREER_CURVES.get(role)
    if not curve:
        # 模糊匹配
        matches = [r for r in CAREER_CURVES if role in r or r in role]
        if len(matches) == 1:
            curve = CAREER_CURVES[matches[0]]
            role = matches[0]
        else:
            return {"error": f"未找到岗位 '{role}'", "available": list(CAREER_CURVES.keys())}

    tier = CITY_TIER_MAP.get(city, "tier2")
    base = curve["base_salary"].get(tier, curve["base_salary"]["tier1"])

    timeline = []
    current_age = start_age

    # 起薪点（校招）
    timeline.append({
        "age": current_age,
        "stage": "入职",
        "years_of_exp": 0,
        "salary": base,
        "note": "校招入职"
    })

    # 按阶段模拟
    stages = [
        ("1-3年", 3),
        ("3-5年", 5),
        ("5-8年", 8),
        ("8-12年", 12),
        ("12-20年", 20),
    ]

    for stage_name, years in stages:
        factor = curve["growth_factors"].get(stage_name, 1.0)
        salary = round(base * factor, 1)
        timeline.append({
            "age": start_age + years,
            "stage": stage_name,
            "years_of_exp": years,
            "salary": salary,
        })

    # 关键节点评估
    milestones = []
    age_35_point = None
    for t in timeline:
        if t["age"] >= 35 and not age_35_point:
            age_35_point = t["salary"]
            milestones.append({
                "age": 35,
                "event": "35 岁节点",
                "salary_at_35": t["salary"],
                "risk_level": curve["age_35_risk"],
                "assessment": curve["age_35_note"],
                "typical_exits": curve["typical_exits"],
            })
            break

    # 40 岁和 45 岁
    for t in timeline:
        if t["age"] >= 40:
            milestones.append({
                "age": t["age"],
                "event": f"{t['age']} 岁节点",
                "salary": t["salary"],
                "stage": t["stage"],
            })
            break

    return {
        "role": role,
        "city": city,
        "city_tier": tier,
        "growth_model": curve["growth_model"],
        "start_age": start_age,
        "timeline": timeline,
        "milestones": milestones,
        "total_20yr_earnings_est": round(sum(
            t["salary"] * 3 if t["years_of_exp"] <= 3
            else t["salary"] * 2 if t["years_of_exp"] <= 5
            else t["salary"] * 3 if t["years_of_exp"] <= 8
            else t["salary"] * 4 if t["years_of_exp"] <= 12
            else t["salary"] * 8
            for t in timeline
        ), 0),
        "note": curve.get("note", ""),
    }


def compare(role1: str, role2: str, city: str, start_age: int = 25) -> dict:
    """对比两个岗位的 20 年发展曲线"""
    r1 = simulate(role1, city, start_age)
    r2 = simulate(role2, city, start_age)

    if "error" in r1 or "error" in r2:
        return {"role1": r1, "role2": r2}

    # 薪资交叉点检测
    cross_points = []
    for t1, t2 in zip(r1["timeline"], r2["timeline"]):
        if t1["salary"] > t2["salary"] and r1["timeline"][0]["salary"] <= r2["timeline"][0]["salary"]:
            cross_points.append({
                "age": t1["age"],
                "event": f"薪资交叉：{role1}({t1['salary']}万) 超越 {role2}({t2['salary']}万)"
            })
        elif t2["salary"] > t1["salary"] and r2["timeline"][0]["salary"] <= r1["timeline"][0]["salary"]:
            cross_points.append({
                "age": t1["age"],
                "event": f"薪资交叉：{role2}({t2['salary']}万) 超越 {role1}({t1['salary']}万)"
            })

    return {
        "comparison": {
            "city": city,
            "role1": {
                "name": role1,
                "start_salary": r1["timeline"][0]["salary"],
                "salary_at_10yr": r1["timeline"][4]["salary"] if len(r1["timeline"]) > 4 else None,
                "salary_at_20yr": r1["timeline"][-1]["salary"],
                "total_20yr": r1["total_20yr_earnings_est"],
                "age_35_risk": r1["milestones"][0]["risk_level"] if r1["milestones"] else None,
            },
            "role2": {
                "name": role2,
                "start_salary": r2["timeline"][0]["salary"],
                "salary_at_10yr": r2["timeline"][4]["salary"] if len(r2["timeline"]) > 4 else None,
                "salary_at_20yr": r2["timeline"][-1]["salary"],
                "total_20yr": r2["total_20yr_earnings_est"],
                "age_35_risk": r2["milestones"][0]["risk_level"] if r2["milestones"] else None,
            },
            "cross_points": cross_points,
            "verdict": (
                f"{role1} 20年总收入 {r1['total_20yr_earnings_est']}万 vs "
                f"{role2} {r2['total_20yr_earnings_est']}万。"
                f"差距 {abs(r1['total_20yr_earnings_est'] - r2['total_20yr_earnings_est'])} 万"
            )
        }
    }


def main():
    parser = argparse.ArgumentParser(description="职业时间线模拟器")
    parser.add_argument("--role", type=str, help="岗位名称")
    parser.add_argument("--city", type=str, default="北京", help="城市")
    parser.add_argument("--start-age", type=int, default=25, help="入职年龄")
    parser.add_argument("--compare", nargs=2, metavar=("ROLE1", "ROLE2"), help="对比两个岗位")
    parser.add_argument("--list", action="store_true", help="列出所有可用岗位")

    args = parser.parse_args()

    if args.list:
        print(json.dumps(list(CAREER_CURVES.keys()), ensure_ascii=False, indent=2))
        return

    if args.compare:
        result = compare(args.compare[0], args.compare[1], args.city, args.start_age)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if args.role:
        result = simulate(args.role, args.city, args.start_age)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
