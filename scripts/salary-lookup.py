#!/usr/bin/env python3
"""
Salary Lookup - 按岗位+城市+经验层级查询薪资基线数据。

用途：Claude 在分析岗位时运行此脚本，获取该岗位的结构化薪资带数据。
用法：python3 scripts/salary-lookup.py --role "产品经理" --city "北京" --level "校招"
      python3 scripts/salary-lookup.py --role "SWE" --all
      python3 scripts/salary-lookup.py --list-roles

数据来源：综合多源交叉验证（招聘平台、公司官方、从业者分享），定期更新。
"""

import json
import sys
import argparse

# ============================================================
# 薪资基线数据库（2025-2026 参考值）
# 格式：{ role: { level: { tier1/2/3: (min, max, unit) } } }
# tier1 = 北京/上海/深圳
# tier2 = 杭州/广州/成都/南京/苏州
# tier3 = 其他城市
# ============================================================

SALARY_DATA = {
    "软件开发工程师": {
        "实习": {"tier1": (300, 500, "元/天"), "tier2": (250, 400, "元/天"), "tier3": (150, 300, "元/天")},
        "校招-白菜": {"tier1": (18, 28, "万/年"), "tier2": (15, 22, "万/年"), "tier3": (10, 18, "万/年")},
        "校招-SP/SSP": {"tier1": (30, 50, "万/年"), "tier2": (25, 40, "万/年"), "tier3": (18, 30, "万/年")},
        "3年经验": {"tier1": (30, 50, "万/年"), "tier2": (25, 40, "万/年"), "tier3": (18, 30, "万/年")},
        "5-8年资深": {"tier1": (50, 100, "万/年"), "tier2": (40, 70, "万/年"), "tier3": (30, 50, "万/年")},
        "source": "2025-2026 多源交叉验证 (BOSS直聘/脉脉/OfferShow/公司官方)"
    },
    "AI/算法工程师": {
        "校招-白菜": {"tier1": (25, 40, "万/年"), "tier2": (22, 35, "万/年"), "tier3": (18, 28, "万/年")},
        "校招-SP/SSP": {"tier1": (40, 70, "万/年"), "tier2": (35, 55, "万/年"), "tier3": (28, 40, "万/年")},
        "3年经验": {"tier1": (50, 80, "万/年"), "tier2": (40, 60, "万/年"), "tier3": (30, 45, "万/年")},
        "5-8年资深": {"tier1": (80, 200, "万/年"), "tier2": (60, 120, "万/年"), "tier3": (40, 80, "万/年")},
        "source": "2025-2026 多源交叉验证 (BOSS直聘/脉脉/OfferShow/公司官方)"
    },
    "数据分析师": {
        "校招": {"tier1": (15, 25, "万/年"), "tier2": (12, 20, "万/年"), "tier3": (8, 15, "万/年")},
        "3年经验": {"tier1": (25, 40, "万/年"), "tier2": (20, 32, "万/年"), "tier3": (15, 25, "万/年")},
        "5-8年资深": {"tier1": (40, 70, "万/年"), "tier2": (32, 50, "万/年"), "tier3": (25, 40, "万/年")},
        "source": "2025-2026 多源交叉验证"
    },
    "产品经理": {
        "实习": {"tier1": (250, 500, "元/天"), "tier2": (200, 400, "元/天"), "tier3": (150, 250, "元/天")},
        "校招": {"tier1": (15, 28, "万/年"), "tier2": (12, 22, "万/年"), "tier3": (10, 18, "万/年")},
        "3年经验": {"tier1": (25, 45, "万/年"), "tier2": (20, 35, "万/年"), "tier3": (15, 28, "万/年")},
        "5-8年资深": {"tier1": (45, 80, "万/年"), "tier2": (35, 60, "万/年"), "tier3": (25, 40, "万/年")},
        "产品总监": {"tier1": (80, 200, "万/年"), "tier2": (60, 120, "万/年"), "tier3": (40, 80, "万/年")},
        "source": "2025-2026 多源交叉验证 (BOSS直聘/脉脉/OfferShow/公司官方)"
    },
    "售前/解决方案": {
        "校招": {"tier1": (18, 30, "万/年"), "tier2": (15, 25, "万/年"), "tier3": (10, 18, "万/年")},
        "3-5年经验": {"tier1": (30, 55, "万/年"), "tier2": (25, 42, "万/年"), "tier3": (18, 30, "万/年")},
        "5-10年资深": {"tier1": (50, 100, "万/年"), "tier2": (40, 70, "万/年"), "tier3": (30, 50, "万/年")},
        "行业首席": {"tier1": (100, 200, "万/年"), "tier2": (70, 120, "万/年"), "tier3": (50, 80, "万/年")},
        "source": "2025-2026 多源交叉验证"
    },
    "客户成功": {
        "校招": {"tier1": (12, 20, "万/年"), "tier2": (10, 16, "万/年"), "tier3": (8, 12, "万/年")},
        "3年经验": {"tier1": (20, 35, "万/年"), "tier2": (16, 28, "万/年"), "tier3": (12, 20, "万/年")},
        "5-8年资深": {"tier1": (35, 60, "万/年"), "tier2": (28, 45, "万/年"), "tier3": (18, 30, "万/年")},
        "source": "2025-2026 多源交叉验证"
    },
    "ToB销售/BD": {
        "校招底薪": {"tier1": (8, 15, "K/月"), "tier2": (6, 12, "K/月"), "tier3": (5, 8, "K/月")},
        "3年总包": {"tier1": (30, 60, "万/年"), "tier2": (20, 40, "万/年"), "tier3": (12, 25, "万/年")},
        "资深Top Sales": {"tier1": (80, 200, "万/年"), "tier2": (50, 120, "万/年"), "tier3": (30, 60, "万/年")},
        "source": "2025-2026 多源交叉验证（注意：销售薪资波动极大，提成部分不可预测）"
    },
    "FDE（真·工程向）": {
        "校招": {"tier1": (25, 45, "万/年"), "tier2": (20, 35, "万/年"), "tier3": (15, 25, "万/年")},
        "3年经验": {"tier1": (40, 70, "万/年"), "tier2": (32, 50, "万/年"), "tier3": (25, 40, "万/年")},
        "5-8年资深": {"tier1": (70, 150, "万/年"), "tier2": (50, 100, "万/年"), "tier3": (40, 70, "万/年")},
        "source": "2025-2026 参考字节豆包/火山引擎；硅谷 Anthropic/OpenAI 底薪$17-30万 + 股权"
    },
    "FDE（假·销售支持贴牌）": {
        "实习": {"tier1": (100, 400, "元/天"), "tier2": (80, 350, "元/天"), "tier3": (60, 250, "元/天")},
        "校招转正": {"tier1": (20, 35, "万/年"), "tier2": (16, 28, "万/年"), "tier3": (12, 20, "万/年")},
        "3年经验": {"tier1": (30, 50, "万/年"), "tier2": (22, 38, "万/年"), "tier3": (15, 28, "万/年")},
        "source": "2025-2026 参考飞书商业化销售支持序列薪资；注意与真 FDE 区分"
    },
    "公务员（江浙沪）": {
        "入职": {"tier1": (15, 25, "万/年"), "tier2": (12, 20, "万/年"), "tier3": (8, 15, "万/年")},
        "10年+": {"tier1": (20, 40, "万/年"), "tier2": (15, 30, "万/年"), "tier3": (10, 22, "万/年")},
        "note": "含公积金+年终。隐性福利：补充医保、住房补贴（部分单位）。薪资增长缓慢但非常稳定",
        "source": "2025-2026 江浙沪公务员薪资参考"
    },
    "国企/央企科技岗": {
        "校招": {"tier1": (12, 20, "K/月"), "tier2": (10, 16, "K/月"), "tier3": (7, 12, "K/月")},
        "5-8年": {"tier1": (25, 50, "万/年"), "tier2": (20, 38, "万/年"), "tier3": (12, 25, "万/年")},
        "note": "公积金通常按较高比例缴纳。稳定性高于私企，薪资天花板低于互联网",
        "source": "2025-2026 参考国家电网/中移动/联通数科等"
    },
    "高校教职": {
        "讲师": {"tier1": (8, 15, "K/月"), "tier2": (7, 12, "K/月"), "tier3": (6, 10, "K/月")},
        "副教授": {"tier1": (12, 22, "K/月"), "tier2": (10, 18, "K/月"), "tier3": (8, 14, "K/月")},
        "教授": {"tier1": (18, 35, "K/月"), "tier2": (14, 28, "K/月"), "tier3": (10, 22, "K/月")},
        "note": "另有科研经费、项目收入、人才补贴、安家费（各地差异大）。有编制的稳定性极高",
        "source": "2025-2026 参考 985/211 高校薪资水平"
    },
    "企业研究院": {
        "校招（博）": {"tier1": (40, 80, "万/年"), "tier2": (35, 60, "万/年"), "tier3": (30, 50, "万/年")},
        "5年+": {"tier1": (70, 150, "万/年"), "tier2": (50, 100, "万/年"), "tier3": (40, 80, "万/年")},
        "note": "参考华为2012实验室/阿里达摩院/腾讯AI Lab/字节Seed",
        "source": "2025-2026 多源交叉验证"
    },
}


# 城市分级
CITY_TIERS = {
    "北京": "tier1", "上海": "tier1", "深圳": "tier1",
    "杭州": "tier2", "广州": "tier2", "成都": "tier2",
    "南京": "tier2", "苏州": "tier2", "武汉": "tier2",
    "西安": "tier2", "重庆": "tier2", "长沙": "tier2",
    # 其他默认 tier3
}


def get_tier(city: str) -> str:
    """根据城市名返回 tier 级别"""
    return CITY_TIERS.get(city, "tier3")


def lookup_salary(role: str, city: str = None, level: str = None) -> dict:
    """查询薪资数据"""
    role_data = SALARY_DATA.get(role)
    if not role_data:
        # 模糊匹配
        matches = []
        for r in SALARY_DATA:
            if role in r or r in role:
                matches.append(r)
        if len(matches) == 1:
            role_data = SALARY_DATA[matches[0]]
            role = matches[0]
        elif len(matches) > 1:
            return {"error": "多个匹配", "matches": matches}
        else:
            return {"error": f"未找到岗位 '{role}'", "available_roles": list(SALARY_DATA.keys())}

    tier = get_tier(city) if city else "tier1"

    if level:
        level_data = role_data.get(level)
        if not level_data:
            # 模糊匹配 level
            for l in role_data:
                if level in l:
                    level_data = role_data[l]
                    level = l
                    break
        if not level_data:
            return {"error": f"岗位 '{role}' 无 '{level}' 级别数据", "available_levels": [k for k in role_data if k != "source" and k != "note"]}

        result = {"role": role, "city": city or "一线城市", "city_tier": tier, "level": level}
        tier_data = level_data.get(tier)
        if tier_data:
            result["salary_range"] = list(tier_data[:2])
            result["unit"] = tier_data[2]
        else:
            # fallback to tier1
            result["salary_range"] = list(level_data["tier1"][:2])
            result["unit"] = level_data["tier1"][2]
        result["source"] = role_data.get("source", "")
        if "note" in role_data:
            result["note"] = role_data["note"]
        return result
    else:
        # 返回所有级别
        result = {"role": role, "city_tier": tier, "levels": {}}
        for lv, data in role_data.items():
            if lv in ("source", "note"):
                continue
            td = data.get(tier)
            if td:
                result["levels"][lv] = {"range": list(td[:2]), "unit": td[2]}
        result["source"] = role_data.get("source", "")
        if "note" in role_data:
            result["note"] = role_data["note"]
        return result


def main():
    parser = argparse.ArgumentParser(description="岗位薪资查询工具")
    parser.add_argument("--role", type=str, help="岗位名称")
    parser.add_argument("--city", type=str, default=None, help="城市（可选）")
    parser.add_argument("--level", type=str, default=None, help="经验级别（可选）")
    parser.add_argument("--all", action="store_true", help="输出岗位所有级别数据")
    parser.add_argument("--list-roles", action="store_true", help="列出所有可用岗位")
    parser.add_argument("--compare", nargs=2, metavar=("ROLE1", "ROLE2"), help="对比两个岗位的薪资")

    args = parser.parse_args()

    if args.list_roles:
        print(json.dumps({"available_roles": list(SALARY_DATA.keys())}, ensure_ascii=False, indent=2))
        return

    if args.compare:
        r1 = lookup_salary(args.compare[0], args.city, args.level or "校招")
        r2 = lookup_salary(args.compare[1], args.city, args.level or "校招")
        print(json.dumps({"comparison": [r1, r2]}, ensure_ascii=False, indent=2))
        return

    if not args.role:
        parser.print_help()
        sys.exit(1)

    result = lookup_salary(args.role, args.city, args.level)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
